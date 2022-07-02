
from datetime import datetime
from decimal import Decimal
from typing import Mapping, NamedTuple
from loguru import logger

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    Filters,
    MessageHandler,
)
from utils.config import Config
from utils.constants import Constants
from utils.generic import chat_message, check_chat_id, get_trade_path
from utils.msg import MSG

class RemoveTradeResponses(NamedTuple):
    CONFIRM: int = 0

class RemoveTradeConversation:
    def __init__(self, parent, config: Config):
        self.parent = parent
        self.config = config
        self.next = RemoveTradeResponses()
        self.handler = ConversationHandler(
            entry_points=[CallbackQueryHandler(self.command_removetrade, pattern='^removetrade:[^:]*$')],
            states={
                self.next.CONFIRM: [CallbackQueryHandler(self.command_removetrade_confirm)],
            },
            fallbacks=[CommandHandler('cancel', self.command_removetrade_cancel)],
            name='removetrade_conversation',
        )

    @check_chat_id
    def command_removetrade(self, update: Update, context: CallbackContext):
        assert update.callback_query
        query = update.callback_query
        assert query.data
        query.delete_message()
        trade_keys = query.data.split(':')[1].split(Constants.trade_keys_separator)
        trade_type = trade_keys[0]
        trade_symbol = trade_keys[1]
        if not self.parent.trade_exists(symbol=trade_symbol, trade_type=trade_type, update=update):
            chat_message(update, context, text='⛔️ Invalid trade.', edit=False)
            return ConversationHandler.END
        
        trader = self.parent.get_trade(symbol=trade_symbol, trade_type=trade_type, update=update)
        chat_message(
            update,
            context,
            text=f'Are you sure you want to remove <b>{trader.name}</b>?',
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton('✅ Confirm', callback_data=get_trade_path(trade_type=trade_type, trade_symbol=trade_symbol)),
                        InlineKeyboardButton('❌ Cancel', callback_data='cancel'),
                    ]
                ]
            ),
            edit=False,
        )
        return self.next.CONFIRM

    @check_chat_id
    def command_removetrade_confirm(self, update: Update, context: CallbackContext):
        assert update.callback_query and update.effective_chat
        query = update.callback_query
        if query.data == 'cancel':
            self.cancel_command(update, context)
            return ConversationHandler.END
        assert query.data
        trade_keys = query.data.split(Constants.trade_keys_separator)
        trade_type = trade_keys[0]
        trade_symbol = trade_keys[1]
        if not self.parent.trade_exists(symbol=trade_symbol, trade_type=trade_type, update=update):
            chat_message(update, context, text='⛔️ Invalid trade.', edit=False)
            return ConversationHandler.END
        
        self.parent.removetrade(
            symbol=trade_symbol, 
            trade_type=trade_type,
            update=update,
            context=context
        )
        return ConversationHandler.END

    @check_chat_id
    def command_removetrade_cancel(self, update: Update, context: CallbackContext):
        self.cancel_command(update, context)
        return ConversationHandler.END

    def cancel_command(self, update: Update, context: CallbackContext):
        chat_message(update, context, text='⚠️ OK, I\'m cancelling this command.', edit=False)