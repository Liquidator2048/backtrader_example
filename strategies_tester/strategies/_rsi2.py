from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import backtrader as bt

from ._base import BaseStrategy

__all__ = ['RSI2Startegy']


class RSI2Startegy(BaseStrategy):
    params = {
        'rsi_len': 2,
        'traling_stop': 2,
        'rsi_up': 90,
        'rsi_down': 10,
        'slow_ema': 610,
        'fast_ema': 9,

        '_accumulate': False,
        '_concurrent': False,
        '_data': None,
        'verbose': True
    }

    def __init__(self):
        super().__init__()

        self.rsi = bt.indicators.RelativeStrengthIndex(period=self.p.rsi_len)
        # self.rsi = bt.indicators.RSI_EMA(period=self.p.rsi_len)

        self.ema_fast = bt.indicators.ExponentialMovingAverage(period=self.p.fast_ema)
        self.ema_slow = bt.indicators.ExponentialMovingAverage(period=self.p.slow_ema)

        self.long_signal = bt.indicators.And(
            self.ema_fast > self.ema_slow,
            self.data.close > self.ema_slow,
            self.rsi < self.p.rsi_down
        )

        self.short_signal = bt.indicators.And(
            self.ema_fast < self.ema_slow,
            self.data.close < self.ema_slow,
            self.rsi > self.p.rsi_up
        )

    def next(self):

        if not self.position:
            if self.long_signal:
                o = self.buy()
                self.order = None
            if self.short_signal:
                self.sell()
                self.order = None
        elif self.order is None:  # se in posizione ma nessun trailing stop
            if self.position.size > 0:
                self.order = self.sell(exectype=bt.Order.StopTrail, trailpercent=self.p.traling_stop / 100)
            if self.position.size < 0:
                self.order = self.buy(exectype=bt.Order.StopTrail, trailpercent=self.p.traling_stop / 100)


