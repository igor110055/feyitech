import time
import threading
import uuid
import os
from loguru import logger
import numpy as np
import pandas as pd
import plotly.express as px
from binance.client import Client
from binance.enums import HistoricalKlinesType
import plotly.express as px
from position import Position
from utils.config import Config

from utils.constants import Constants
from utils.core import is_admin
from utils.indicators import get_adx, get_atr, get_mfi, get_rsi, get_supertrend, get_vwap
from utils.math import roundup
from traderstatus import TraderStatus

atr_period = 14

class Trader:

    def __init__(
        self, 
        is_test,
        use_trailing_sl_tp, 
        tp_sl_ratio_weak, 
        tp_sl_ratio_strong,
        tp_sl_ratio_very_strong,
        tp_sl_ratio_extremely_strong, 
        symbol, is_futures, margin_pct, leverage
    ):
        self.is_test = is_test
        self.is_futures = is_futures
        self.client = Client(Config.Binance.ReadAndWrite.key, Config.Binance.ReadAndWrite.secret)
        self.use_trailing_sl_tp = use_trailing_sl_tp
        self.tp_sl_ratio_weak = tp_sl_ratio_weak
        self.tp_sl_ratio_strong = tp_sl_ratio_strong
        self.tp_sl_ratio_very_strong = tp_sl_ratio_very_strong
        self.tp_sl_ratio_extremely_strong = tp_sl_ratio_extremely_strong
        self.symbol = symbol.upper()
        self.margin_pct = margin_pct
        self.leverage = leverage if is_futures else 0
        self.name = f'{self.symbol} {(Constants.TradeType.futures if is_futures else Constants.TradeType.spot).capitalize()}'
        
        self.klines_type = HistoricalKlinesType.FUTURES if is_futures else HistoricalKlinesType.SPOT

        self.balance = 1000
        self.profits = 0
        self.pnl = 1000 # balance + profits
        self.total_longs = 0
        self.total_shorts =  0
        self.total_trades = 0
        self.avg_trend_strength = 0
        self.status = None # waiting for optimum position | trading | stopped
        self.test_counter = 0
        self.feedback = None
        self.alive = False
        self.thread = None

        self.chart_photo_path = None
        self.positions = []

        self.close = 0
        self.adx = 0
        self.vwap = 0
        self.supertrend_is_uptrend_10 = 0
        self.supertrend_vwc_10 = 0
        self.supertrend_trend_10 = 0
        self.supertrend_is_uptrend_14 = 0
        self.supertrend_vwc_14 = 0
        self.supertrend_trend_14 = 0
        self.supertrend_is_uptrend_15 = 0
        self.supertrend_vwc_15 = 0
        self.supertrend_trend_15 = 0

        
        self.first_trade_time = None
        self.last_trade_time = None

        self.last_trade_type = 0
        self.last_trade_price = 0
        self.last_trade_volume = 0
        self.last_trade_cost = 0
        self.last_trade_tp = 0
        self.last_trade_sl = 0

    # calulate the volume of an unstable coin an amount of stable coin can buy
    # e.g, the volume/size of ETH a particular amount of BUSD can buy
    def amount_to_volume(self, amount, volume_price):
        return amount * volume_price

    def build_key_value(self, key, value, futures_only=False, admin_only=None):
        return f'<b>{key}:</b> {value if value is not None else ""}\n' if (self.is_futures or futures_only is False) and (admin_only is None or is_admin(admin_only)) else ''

    def get_status(self, caller_id):
        return f"\
        ===== <b>{self.name}</b> =====\n\n\
        {self.build_key_value('PNL', self.pnl)}\
        {self.build_key_value('Status', self.status)}\
        {self.build_key_value('Total Longs', self.total_longs, True)}\
        {self.build_key_value('Total Shorts', self.total_shorts, True)}\
        {self.build_key_value('Total Trades', self.total_trades)}\
        {self.build_key_value('Margin Percentage', f'{self.margin_pct}%')}\
        {self.build_key_value('Leverage', f'{round(self.leverage, 2)}x')}\
        {self.build_key_value('First Trade Time', self.first_trade_time if self.first_trade_time is None else self.first_trade_time.strftime('%b, %d %Y at %I:%M:%S %p'))}\
        {self.build_key_value('Last Trade Time', self.last_trade_time if self.last_trade_time is None else self.first_trade_time.strftime('%b, %d %Y at %I:%M:%S %p'))}\
        {self.build_key_value('Last Trade Type', self.last_trade_type)}\
        {self.build_key_value('Last Trade Price', round(self.last_trade_price, 2))}\
        {self.build_key_value('Last Trade Volume', round(self.last_trade_volume, 2))}\
        {self.build_key_value('Last Trade Cost', round(self.last_trade_cost, 2))}\
        {self.build_key_value('Last Trade Current TP', round(self.last_trade_tp, 2))}\
        {self.build_key_value('Last Trade Current SL', round(self.last_trade_sl, 2))}\
        {self.build_key_value('16hrs Average Trend Strength Percentage', f'{round(self.avg_trend_strength, 2)}%')}\n\
        {self.build_key_value('', '===== <b>Logs For The Developer</b> =====<b>:</b>', False, caller_id)}\n\
        {self.build_key_value('close', round(self.close, 2), False, caller_id)}\
        {self.build_key_value('adx', round(self.adx, 2), False, caller_id)}\
        {self.build_key_value('vwap', round(self.vwap, 2), False, caller_id)}\
        {self.build_key_value('supertrend_is_uptrend_10', self.supertrend_is_uptrend_10, False, caller_id)}\
        {self.build_key_value('supertrend_vwc_10', round(self.supertrend_vwc_10, 2), False, caller_id)}\
        {self.build_key_value('supertrend_trend_10', round(self.supertrend_trend_10, 2), False, caller_id)}\
        {self.build_key_value('supertrend_is_uptrend_14', self.supertrend_is_uptrend_14, False, caller_id)}\
        {self.build_key_value('supertrend_vwc_14', round(self.supertrend_vwc_14, 2), False, caller_id)}\
        {self.build_key_value('supertrend_trend_14', round(self.supertrend_trend_14, 2), False, caller_id)}\
        {self.build_key_value('supertrend_is_uptrend_15', self.supertrend_is_uptrend_15, False, caller_id)}\
        {self.build_key_value('supertrend_vwc_15', round(self.supertrend_vwc_15, 2), False, caller_id)}\
        {self.build_key_value('supertrend_trend_15', round(self.supertrend_trend_15, 2), False, caller_id)}\
    "

    def run_trade(self):
        while True:
            klines = self.client.get_historical_klines(
                self.symbol, 
                Client.KLINE_INTERVAL_1MINUTE, 
                limit=Config.max_positions_per_chart, 
                klines_type=self.klines_type
            )
            df = self.klines_to_dataframe(klines)
            if df is not None:
                df = self.react(df)
                self.update_chart_photo(df)
            time.sleep(10)
            if self.alive is False:
                self.react(None)
                break

    def trade(self):
        self.alive = True
        self.status = TraderStatus.waiting
        self.thread = threading.Thread(target = self.run_trade)
        self.thread.start()
        self.feedback = f'✅ <b>{self.name}</b> trade was successfully started for execution once the time is right. \n\nYou can update the settings with the <a href="/{Constants.Commands.updatetrade}">/{Constants.Commands.updatetrade}</a> command. \n\nYou can also cancel it with the <a href="/{Constants.Commands.removetrade}">/{Constants.Commands.removetrade}</a> command. \n\nTo view the status of your trades like checking if a trade has been executed, use the <a href="/{Constants.Commands.status}">/{Constants.Commands.status}</a> command.'
        
    def update(self, margin_pct, leverage):
        self.margin_pct = margin_pct
        self.leverage = leverage
        self.feedback = f'✅ <b>{self.name}</b> trade was successfully updated. The trading bot will start using the settings on the next trade action.'

    def stop(self):
        self.alive = False
        self.status = TraderStatus.stopped
        self.thread.join()
        self.feedback = f'✅ <b>{self.name}</b> trade was successfully stopped with all BTC sold into the USDT stable coin at market price.'

    def get_positions_df(self):
        df = pd.DataFrame([position.asdict() for position in self.positions])
        return df

    def set_last_trade_info(self, position):
        self.positions.append(position)
        self.last_trade_type = position.order_type
        self.last_trade_price = position.open_price
        self.last_trade_volume = position.volume
        self.last_trade_cost = position.open_price * position.volume
        self.last_trade_tp = position.tp
        self.last_trade_sl = position.sl

    def add_position(self, position):
        # remove the oldest position if the total postions has exceeded the limit size
        if len(self.positions) > Config.max_positions_per_chart:
            self.positions = self.positions[len(self.positions) - Config.max_positions_per_chart:]
        return True

    def get_last_position(self):
        return self.positions[len(self.positions) - 1] if len(self.positions) > 0 else None

    def update_chart_photo(self, chart_df):
        fig = px.line(chart_df, x='time', y=['close', 'vwap'], title=f'{Config.bot_name} {self.name} Quantitatively Analysed {Config.timeframe} Chart.')
        
        trades_df = self.get_positions_df()
        for i, position in trades_df.iterrows():
            if position.is_closed:
                fig.add_shape(type="line",
                    x0=position.open_time, y0=position.open_price, x1=position.close_time, y1=position.close_price,
                    line=dict(
                        color = "green" if position.profit >= 0 else "red",
                        width = 3
                    )
                )
        photo_path = self.save_chart_photo(fig)
        if photo_path is not None:
            # delete previous photo then assign a new one
            if self.chart_photo_path is not None and os.path.isfile(self.chart_photo_path):
                os.remove(self.chart_photo_path)
            self.chart_photo_path = photo_path

    def save_chart_photo(self, fig):
        filename = f'{Constants.chart_photos_dir_name}/{str(uuid.uuid4())}.png'
        try:
            fig.write_image(filename)
            return filename
        except:
            return None


    def klines_to_dataframe(self, klines):
        df = pd.DataFrame(np.array(klines).reshape(-1,12), dtype=float, columns = ('open_time',
                                            'open',
                                            'high',
                                            'low',
                                            'close',
                                            'volume',
                                            'close_time',#close time
                                            'quote_asset_volume',
                                            'number_of_trades',
                                            'taker_buy_base_asset_volume',
                                            'taker_buy_quote_asset_volume',
                                            'ignore'))
        
        df = pd.DataFrame({
            'time': df['close_time'],
            'open': df['open'],
            'high': df['high'],
            'low': df['low'],
            'close': df['close'],
            'volume': df['volume']
        })
        
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.index = df.time
        return df

    def react(self, df: pd.DataFrame):
        if df is None:
            # this means the bots has stopped, so all trades should be closed
            return None
        else:
            atr_indicator = get_atr(df['high'], df['low'], atr_period)
            adx_indicator = get_adx(df['high'], df['low'], atr_indicator['atr'])
            rsi_indicator = get_rsi(df['open'], df['close'], atr_period)
            mfi_indicator = get_mfi(df['close'], df['high'], df['low'], df['volume'], atr_period)
            supertrend_10 = get_supertrend(
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                volume=df['volume'], 
                atr_period=5,
                multiplier=2
            )
            supertrend_14 = get_supertrend(
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                volume=df['volume'], 
                atr_period=7,
                multiplier=1.5
            )
            supertrend_15 = get_supertrend(
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                volume=df['volume'], 
                atr_period=14,
                multiplier=3
            )
            vwap_indicator = get_vwap(
                high=df['high'], 
                low=df['low'], 
                close=df['close'], 
                volume=df['volume']
            )
            strategy_feed = pd.DataFrame({
                    "time": df['time'],
                    "atr": atr_indicator['atr'],
                    "adx": adx_indicator['adx'],
                    "adx_pdi": adx_indicator['pdi'],
                    "adx_ndi": adx_indicator['ndi'],
                    "rsi": rsi_indicator['rsi'],
                    "mfi": mfi_indicator['mfi'],
                    "open": df['open'],
                    "close": df['close'],
                    "high": df['high'],
                    "low": df['low'],
                    "supertrend_is_uptrend_10": supertrend_10['supertrend_is_uptrend'],
                    "supertrend_trend_10": supertrend_10['supertrend'],
                    "supertrend_vwc_10": supertrend_10['volume_weighted_close'],
                    
                    "supertrend_is_uptrend_14": supertrend_14['supertrend_is_uptrend'],
                    "supertrend_trend_14": supertrend_14['supertrend'],
                    "supertrend_vwc_14": supertrend_14['volume_weighted_close'],
                    
                    "supertrend_is_uptrend_15": supertrend_15['supertrend_is_uptrend'],
                    "supertrend_trend_15": supertrend_15['supertrend'],
                    "supertrend_vwc_15": supertrend_15['volume_weighted_close'],
                    "vwap": vwap_indicator['vwap']
                }, 
                index=df.time
            )
            strategy_feed = strategy_feed[atr_period:]  # removing NaN values
            self.strategize(strategy_feed)
            df['vwap'] = vwap_indicator['vwap']
            return df

    def strategize(self, feed):
        self.avg_trend_strength = feed['adx'].sum() / feed['adx'].size
        adx_avg = roundup(self.avg_trend_strength, 10)
        data = feed.iloc[feed['adx'].size - 1]
        new_pos = self.logic(data, adx_avg)
        logger.info(f"Position::Q, {'None' if new_pos is None else new_pos.asdict()}")
        self.close_tp_sl(data=data, new_pos=new_pos)

        last_position = self.get_last_position()
        # strategy logic
        # trade only if a position is not already opened up
        # trade only if there is a signal returned to be traded(indicated by "new_pos")
        # trade only buy signals, unless this trader instance only trades futures, 
        # in which profits can be made in sell(shorts) actions too... yummy
        if (last_position is None or last_position.is_closed) \
            and new_pos is not None and new_pos.volume > 0 \
            and (new_pos.order_type == 'buy' or self.is_futures):
            logger.info(f"Position::R', {new_pos.asdict()}")
            self.status = TraderStatus.trading
            new_pos.is_closed = False
            self.add_position(new_pos)
            self.set_last_trade_info(new_pos)
            if self.first_trade_time is None:
                self.first_trade_time = new_pos.open_time
            self.last_trade_time = new_pos.open_time
            if self.is_futures:
                if new_pos.order_type == 'buy': 
                    self.total_longs = self.total_longs + 1
                else:
                    self.total_shorts = self.total_shorts + 1
            self.total_trades = self.total_trades + 1
            

    # close positions when stop loss or take profit is reached
    def close_tp_sl(self, data, new_pos):
        pos = self.get_last_position()
        if pos and not pos.is_closed:
            if (data['close'] <= pos.sl and pos.order_type == 'buy'):
                pos.close_position(data['time'], pos.sl)
            elif (data['close'] >= pos.sl and pos.order_type == 'sell'):
                pos.close_position(data['time'], pos.sl)
            elif (data['close'] >= pos.tp and pos.order_type == 'buy'):
                # trailing tp and sl
                if new_pos is not None and new_pos.order_type == pos.order_type and self.use_trailing_sl_tp:
                    pos.tp = new_pos.tp
                    pos.sl = new_pos.sl
                    self.set_last_trade_info(pos)
                else:
                    pos.close_position(data['time'], pos.tp)
            elif (data['close'] <= pos.tp and pos.order_type == 'sell'):
                # trailing tp and sl
                if new_pos is not None and new_pos.order_type == pos.order_type and self.use_trailing_sl_tp:
                    pos.tp = new_pos.tp
                    pos.sl = new_pos.sl
                    self.set_last_trade_info(pos)
                else:
                    pos.close_position(data['time'], pos.tp)

    def sl_tp_diff(self, atr, adx, adx_avg):
        ratio = None
        if adx < 20:
            ratio = (adx_avg * self.tp_sl_ratio_weak) / 100
        elif adx < 50:
            ratio = (adx_avg * self.tp_sl_ratio_strong) / 100
        elif adx < 70:
            ratio = (adx_avg * self.tp_sl_ratio_very_strong) / 100
        else:
            ratio = (adx_avg * self.tp_sl_ratio_extremely_strong) / 100
        return ratio * atr

    def calculate_volume(self, price_per_volume):
        max_spent = (self.margin_pct * self.pnl) / 100
        return max_spent / price_per_volume
        
    # strategy logic how positions should be opened/closed
    def logic(self, data, adx_avg) -> Position:
        pos = None
        self.close = data['close']
        self.adx = data['adx']
        self.vwap = data['vwap']
        self.supertrend_is_uptrend_10 = data['supertrend_is_uptrend_10']
        self.supertrend_vwc_10 = data['supertrend_vwc_10']
        self.supertrend_trend_10 = data['supertrend_trend_10']
        self.supertrend_is_uptrend_14 = data['supertrend_is_uptrend_14']
        self.supertrend_vwc_14 = data['supertrend_vwc_14']
        self.supertrend_trend_14 = data['supertrend_trend_14']
        self.supertrend_is_uptrend_15 = data['supertrend_is_uptrend_15']
        self.supertrend_vwc_15 = data['supertrend_vwc_15']
        self.supertrend_trend_15 = data['supertrend_trend_15']
        
        logger.info(f"ADX_TYPE: {data['adx']} => {type(data['adx'])} | {data['adx'] >= 15}")
        logger.info(f"supertrend_is_uptrend_TYPE: {data['supertrend_is_uptrend_10']} => {type(data['supertrend_is_uptrend_10'])} | {bool(data['supertrend_is_uptrend_10']) is True}")
        logger.info(f"supertrend_trend_TYPE: {data['supertrend_trend_10']} => {type(data['supertrend_trend_10'])}")
        logger.info(f"supertrend_TYPE: {data['supertrend_vwc_10']} => {type(data['supertrend_vwc_10'])} | {data['supertrend_vwc_10'] > data['supertrend_trend_10']}")
        logger.info(f"close_TYPE: {data['close']} => {type(data['close'])}")
        logger.info(f"vwap_TYPE: {data['vwap']} => {type(data['vwap'])} | {data['close'] > data['vwap']}")
        if data['adx'] >= 15:
            # USE SUPERTREND INDICATOR TO MAKE A STRATEGY
            if bool(data['supertrend_is_uptrend_10']) is True \
                and data['supertrend_vwc_10'] > data['supertrend_trend_10'] \
                and bool(data['supertrend_is_uptrend_14']) is True \
                and data['supertrend_vwc_14'] > data['supertrend_trend_14'] \
                and bool(data['supertrend_is_uptrend_15']) is True \
                and data['supertrend_vwc_15'] > data['supertrend_trend_15'] \
                and data['close'] > data['vwap']:
                logger.info('PriceAction::LONG')
                # Position variables
                order_type = 'buy'
                open_price = data['close']
                open_time = data['time']
                volume = self.calculate_volume(open_price)
                tp_amount = self.sl_tp_diff(data['atr'], data['adx'], adx_avg)
                tp = open_price + tp_amount
                sl = open_price - tp_amount

                pos = Position(
                    self, open_price, open_time, volume, self.leverage, tp, sl, order_type, 'trend_buy'
                )

            # if is downtrend
            elif bool(data['supertrend_is_uptrend_10']) is False \
                and data['supertrend_vwc_10'] < data['supertrend_trend_10'] \
                and bool(data['supertrend_is_uptrend_14']) is False \
                and data['supertrend_vwc_14'] < data['supertrend_trend_14'] \
                and bool(data['supertrend_is_uptrend_15']) is False \
                and data['supertrend_vwc_15'] < data['supertrend_trend_15'] \
                and data['close'] < data['vwap']:
                logger.info('PriceAction::SHORT')
                # Position variables
                order_type = 'sell'
                open_price = data['close']
                open_time = data['time']
                volume = self.calculate_volume(open_price)
                tp_amount = self.sl_tp_diff(data['atr'], data['adx'], adx_avg)
                tp = open_price - tp_amount
                sl = open_price + tp_amount

                pos = Position(
                    self, open_price, open_time, volume, self.leverage, tp, sl, order_type, 'trend_sell'
                )
        return pos