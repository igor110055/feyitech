from traderstatus import TraderStatus

class Position:
    def __init__(self, parent, open_price, open_time, volume, leverage, tp, sl, order_type, strategy_type):
        self.parent = parent
        self.open_price = open_price
        self.open_time = open_time
        self.volume = volume
        self.leverage = leverage
        self.sl = sl
        self.tp = tp
        self.order_type = order_type
        self.strategy_type = strategy_type
        self.close_price = 0
        self.close_time = 0
        self.profit = 0
        self.is_closed = True

    def close_position(self, close_time, close_price):
        self.close_time = close_time
        self.close_price = close_price
        if self.parent.is_futures:
            leveraged_volume = self.volume * self.leverage
            self.profit = (self.close_price - self.open_price) * leveraged_volume if self.order_type == 'buy' \
                                                    else (self.open_price - self.close_price) * leveraged_volume
        else:
            self.profit = (self.close_price - self.open_price) * self.volume
        self.is_closed = True
        #update the trader's profits by adding the profits to the previous trades profits
        self.parent.profits = self.parent.profits + self.profit
        # update the trader's pnl
        self.parent.pnl = self.parent.balance + self.parent.profits
        self.parent.status = TraderStatus.waiting

    def asdict(self):
        return {
            'open_price': self.open_price,
            'open_time': self.open_time,
            'order_type': self.order_type,
            'volume': self.volume,
            'leverage': self.leverage,
            'sl': self.sl,
            'tp': self.tp,
            'close_price': self.close_price,
            'close_datetime': self.close_time,
            'profit': self.profit,
            'is_closed': self.is_closed,
            'order_type': self.order_type,
            'strategy_type': self.strategy_type
        }