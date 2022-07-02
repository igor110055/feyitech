import os
from loguru import logger
import pandas as pd
import sqlalchemy
from binance.client import Client
from binance import BinanceSocketManager
from utils.config import Config

from utils.core import update_to_chat_id
from utils.constants import Constants
from utils.generic import chat_message, check_chat_id, get_trade_path, get_trades_keyboard_layout
from utils.msg import MSG

import time
from typing import Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, Update
from telegram.ext import CallbackContext, CallbackQueryHandler, CommandHandler, ConversationHandler, Defaults, Updater
from conversations.addtrade import AddTradeConversation
from conversations.removetrade import RemoveTradeConversation
from conversations.updatetrade import UpdateTradeConversation

from trader import Trader

# user database
db = sqlalchemy.create_engine('sqlite:///accounts.db')

class TradeBot:
    def __init__(self, config: Config):
        self.config = config
        self.is_test = config.is_test
        self.use_trailing_sl_tp = True

        # create needed folders and files
        self.init()
        
        #The percentage x% of the prime numbers 3, 5, 7, and 11 is used in the stop loss/take profit
        # calculations of the weak, strong, very strong, and extrmely strong adx respectively
        # where x is the average adx rounded to the nearest tens
        self.weak_trend = 3
        self.strong_trend = 5
        self.very_strong_trend = 7
        self.extremely_strong_trend = 11
        self.trades = {}

        defaults = Defaults(parse_mode=ParseMode.HTML, disable_web_page_preview=True, timeout=120)
        # persistence = PicklePersistence(filename='botpersistence')
        self.updater = Updater(token=config.secrets.telegram_token, persistence=None, defaults=defaults)
        self.dispatcher = self.updater.dispatcher
        self.convos = {
            'addtrade': AddTradeConversation(parent=self, config=self.config),
            'updatetrade': UpdateTradeConversation(parent=self, config=self.config),
            'removetrade': RemoveTradeConversation(parent=self, config=self.config)
        }
        self.setup_telegram()
        #self.start_status_update()
        self.last_status_message_id: Optional[int] = None
        self.prompts_select_token = {
            'updatetrade': 'Which trade do you want to update its settings?',
            'removetrade': 'Which trade do you want to cancel?'
        }

    def init(self):
        if not os.path.isdir(Constants.chart_photos_dir_name):
            os.mkdir(Constants.chart_photos_dir_name)

    def setupuser(self, update: Update):
        user_key = self.get_user_key(update)
        if user_key is not None and user_key not in self.trades:
            self.trades[user_key] = {
                Constants.TradeType.spot: {},
                Constants.TradeType.futures: {}
            }

    def get_user_key(self, update: Update):
        chat_id = update_to_chat_id(update)
        return f'chat_{chat_id}' if chat_id is not None else None 

    def get_trade_key(self, tradetype):
        return f'{tradetype}'

    def get_user_trades_by_type(self, type: str, update: Update):
        user_key = self.get_user_key(update)
        user_trades = None
        logger.info("UserTrades101")
        logger.info(self.trades)
        if user_key not in self.trades:
            user_trades = {}
        else:
            user_trades = self.trades[user_key][self.get_trade_key(type)]
        logger.info("UserTrades")
        logger.info(user_trades)
        return user_trades

    def trade_exists(self, symbol: str, trade_type: str, update: Update):
        return symbol.upper() in self.get_user_trades_by_type(trade_type, update)

    def get_trade(self, symbol: str, trade_type: str, update: Update):
        return self.get_user_trades_by_type(trade_type, update)[symbol.upper()]

    # checks the symbol on the list of binance futures pairs, and return true if the symbol exists
    def futures_has_symbol(self, symbol):
        return True

    # checks the symbol on the list of binance spot pairs, and return true if the symbol exists
    def spot_has_symbol(self, symbol):
        return True

    def setup_telegram(self):
        self.dispatcher.add_handler(CommandHandler('start', self.command_start))
        self.dispatcher.add_handler(CommandHandler('status', self.command_status))
        self.dispatcher.add_handler(CommandHandler('updatetrade', self.command_show_all_trades))
        self.dispatcher.add_handler(CommandHandler('removetrade', self.command_show_all_trades))
        self.dispatcher.add_handler(
            CallbackQueryHandler(
                self.command_show_all_trades, pattern='^updatetrade$|^removetrade$'
            )
        )
        self.dispatcher.add_handler(CallbackQueryHandler(self.cancel_command, pattern='^removetradechoice$'))
        for convo in self.convos.values():
            self.dispatcher.add_handler(convo.handler)
        commands = [
            ('status', 'Display all trades and their PNL'),
            ('addtrade', 'Buy/Long or sell/Short an asset'),
            ('updatetrade', 'Update the settings of a trade'),
            ('removetrade', 'Remove/Stop a trade'),
            ('cancel', 'Cancel the current operation'),
        ]
        self.dispatcher.bot.set_my_commands(commands=commands)
        self.dispatcher.add_error_handler(self.error_handler)
        
    def start(self):
        try:
            self.dispatcher.bot.send_message(chat_id=self.config.secrets.admin_chat_id, text='🤖 Bot started')
        except Exception:  # chat doesn't exist yet, do nothing
            logger.info('Chat with user doesn\'t exist yet.')
        logger.info('Bot started')
        self.updater.start_polling()
        self.updater.idle()

    @check_chat_id
    def command_start(self, update: Update, context: CallbackContext):
        chat_message(
            update,
            context,
            text='Hi! You can start trading futures and spot with the '
            + '<a href="/addtrade">/addtrade</a> command.',
            edit=False,
        )

    @check_chat_id
    def command_status(self, update: Update, context: CallbackContext):
        chat_id = update_to_chat_id(update)
        spot_trades = self.get_user_trades_by_type(Constants.TradeType.spot, update)
        futures_trades = self.get_user_trades_by_type(Constants.TradeType.futures, update)

        if len(spot_trades) == 0 and len(futures_trades) == 0:
            chat_message(
                update,
                context,
                text=MSG.no_trade_info,
                edit=False,
            )
        else:
            if len(spot_trades) > 0:
                for trader in sorted(spot_trades.values(), key=lambda trader: trader.symbol):
                    status = trader.get_status(chat_id)
                    trade_path = get_trade_path(trade_type=Constants.TradeType.spot, trade_symbol=trader.symbol)
                    reply_markup = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton('✏️ Edit Trade', callback_data=f'updatetrade:{trade_path}'),
                            InlineKeyboardButton('❌ Remove Trade', callback_data=f'removetrade:{trade_path}')
                        ]
                    ])
                    chat_message(
                        update,
                        context,
                        text=status,
                        reply_markup=reply_markup,
                        edit=False,
                        photo_up=trader.chart_photo_path
                    )
                    time.sleep(0.2)
            if len(futures_trades) > 0:
                for trader in sorted(futures_trades.values(), key=lambda trader: trader.symbol):
                    status = trader.get_status(chat_id)
                    trade_path = get_trade_path(trade_type=Constants.TradeType.futures, trade_symbol=trader.symbol)
                    reply_markup = InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton('✏️ Edit Trade', callback_data=f'updatetrade:{trade_path}'),
                            InlineKeyboardButton('❌ Remove Trade', callback_data=f'removetrade:{trade_path}')
                        ]
                    ])
                    chat_message(
                        update,
                        context,
                        text=status,
                        reply_markup=reply_markup,
                        edit=False,
                        photo_up=trader.chart_photo_path
                    )
                    time.sleep(0.2)

    @check_chat_id
    def command_show_all_trades(self, update: Update, context: CallbackContext):
        if update.message: # process text command such as /removetrade, /updatetrade... from user
            assert update.message.text
            command = update.message.text.strip()[1:] # e.g turns /removetrade to removetrade
            try:
                # get the message to display before the trades buttons
                msg = self.prompts_select_token[command]
            except KeyError:
                chat_message(update, context, text='⛔️ Invalid command.', edit=False)
                return
            buttons_layout = get_trades_keyboard_layout(
                self.get_user_trades_by_type(Constants.TradeType.spot, update), 
                self.get_user_trades_by_type(Constants.TradeType.futures, update), 
                callback_prefix=command,
                order_by='symbol'
            )
        else:  # callback query from button
            assert update.callback_query
            query = update.callback_query
            assert query.data
            try:
                msg = self.prompts_select_token[query.data]
            except KeyError:
                chat_message(update, context, text='⛔️ Invalid command.', edit=False)
                return
            buttons_layout = get_trades_keyboard_layout(
                self.get_user_trades_by_type(Constants.TradeType.spot, update), 
                self.get_user_trades_by_type(Constants.TradeType.futures, update), 
                callback_prefix=query.data,
                order_by='symbol'
            )

        if len(buttons_layout) == 0:
            chat_message(
                update,
                context,
                text=MSG.no_trade_info,
                edit=False,
            )
            return ConversationHandler.END
        else:
            reply_markup = InlineKeyboardMarkup(buttons_layout)
            chat_message(
                update,
                context,
                text=msg,
                reply_markup=reply_markup,
                edit=False,
            )

    @check_chat_id
    def cancel_command(self, update: Update, _: CallbackContext):
        assert update.callback_query and update.effective_chat
        query = update.callback_query
        query.delete_message()


    def send_feedback(self, update: Update, context: CallbackContext, msg):
        chat_message(
            update,
            context,
            text=msg,
            edit=False
        )

    def addtrade(self, symbol: str, is_futures: bool, margin_pct: float, leverage: int, update: Update, context: CallbackContext):
        trader = Trader(
            self.is_test,
            self.use_trailing_sl_tp, 
            self.weak_trend, self.strong_trend, self.very_strong_trend, self.extremely_strong_trend,
            symbol, is_futures, margin_pct, leverage
        )
        if trader is not None:
            self.trades[self.get_user_key(update)][Constants.TradeType.futures if is_futures else Constants.TradeType.spot][symbol.upper()] = trader
        logger.info(self.trades)
        self.send_feedback(update, context, trader.feedback)
        trader.trade()

    def updatetrade(self, symbol: str, is_futures: bool, margin_pct: float, leverage: int, update: Update, context: CallbackContext):
        trade_type = Constants.TradeType.futures if is_futures else Constants.TradeType.spot
        trader = self.get_trade(symbol=symbol, trade_type=trade_type, update=update)
        trader.update(
            margin_pct=margin_pct, leverage=leverage
        )
        self.send_feedback(update, context, trader.feedback)

    def removetrade(self, symbol: str, trade_type: str, update: Update, context: CallbackContext):
        trader = self.get_trade(symbol=symbol, trade_type=trade_type, update=update)
        trader.stop()
        del self.trades[self.get_user_key(update)][trade_type][symbol]
        logger.info(self.trades)
        self.send_feedback(update, context, trader.feedback)

    def error_handler(self, update: Update, context: CallbackContext) -> None:
        logger.error('Exception while handling an update')
        logger.error(context.error)
        chat_message(update, context, text=f'⛔️ Exception while handling an update\n{context.error}', edit=False)