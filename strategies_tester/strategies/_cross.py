from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

"""Semplice strategia di esempio. Entry al cross di due medie mobili + filtro MFI"""


__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"

import backtrader as bt

from ._base import BaseStrategy
from ._indicators import MFI

__all__ = ['CrossStrategy', 'OptimizeCrossStrategy']


class CrossStrategy(BaseStrategy):
    params = {
        'ma_fast_type': 'ema',
        'ma_fast_period': 9,

        'ma_slow_type': 'ema',
        'ma_slow_period': 610,

        'use_filter_fast': True,

        'use_mfi': True,
        'mfi_high': 80,
        'mfi_low': 30,

        'stop_loss': 50,

        '_accumulate': False,
        '_concurrent': False,
        '_data': None,
        'verbose': True,
    }

    def __init__(self):
        super().__init__()

        if self.p.ma_fast_type == 'sma':
            self.ma_fast = bt.indicators.MovingAverageSimple(period=self.p.ma_fast_period)
        elif self.p.ma_fast_type == 'ema':
            self.ma_fast = bt.ind.ExponentialMovingAverage(period=self.p.ma_fast_period)
        else:
            raise Exception(f"{self.p.ma_fast_type}: not valid value for 'ma_fast_type'")

        if self.p.ma_slow_type == 'sma':
            self.ma_slow = bt.indicators.MovingAverageSimple(period=self.p.ma_slow_period)
        elif self.p.ma_slow_type == 'ema':
            self.ma_slow = bt.ind.ExponentialMovingAverage(period=self.p.ma_slow_period)
        else:
            raise Exception(f"{self.p.ma_slow_type}: not valid value for 'ma_slow_type'")

        self.long_signal = bt.indicators.CrossUp(self.ma_fast, self.ma_slow)
        self.short_signal = bt.indicators.CrossDown(self.ma_fast, self.ma_slow)

        if self.p.use_filter_fast:
            self.long_signal = bt.indicators.And(self.long_signal, self.data.close > self.ma_fast)
            self.short_signal = bt.indicators.And(self.short_signal, self.data.close < self.ma_fast)

        if self.p.use_mfi:
            self.mfi = MFI()
            self.long_signal = bt.indicators.And(self.long_signal, self.mfi >= self.p.mfi_high)
            self.short_signal = bt.indicators.And(self.short_signal, self.mfi < self.p.mfi_low)

        self.market_order = None
        self.stop_order = None

    def next(self):

        if self.long_signal:
            self.log("cross up")

        if self.short_signal:
            self.log("cross down")

        if self.long_signal and self.position.size <= 0:
            price = self.data.close[0]

            # close previous position
            if self.market_order and self.market_order.issell():
                self.close(oco=self.market_order)

            # cancel previous stop loss
            if self.stop_order and self.stop_order.isbuy():
                self.cancel(self.stop_order)

            self.market_order = self.buy()

            self.stop_order = None

        if self.short_signal and self.position.size >= 0:
            price = self.data.close[0]
            # close previous position
            if self.market_order and self.market_order.isbuy():
                self.close(oco=self.market_order)

            # cancel previous stop loss
            if self.stop_order and self.stop_order.issell():
                self.cancel(self.stop_order)

            self.market_order = self.sell()

            self.stop_order = None

        if not self.stop_order and self.position.size != 0:
            price = self.position.price
            if self.position.size > 0:
                self.stop_order = self.sell(
                    exectype=bt.Order.Stop,
                    price=price - self.p.stop_loss,
                    oco=self.market_order
                )
                self.stop_order.addinfo(name='Long Stop Loss')
            else:
                self.stop_order = self.buy(
                    exectype=bt.Order.Stop,
                    price=price + self.p.stop_loss,
                    oco=self.market_order
                )
                self.stop_order.addinfo(name='Short Stop Loss')


from ._optimize import OptunaOptimizeStrategy
import optuna


class OptimizeCrossStrategy(OptunaOptimizeStrategy):
    strategy = CrossStrategy

    def get_parameters(self, trial: optuna.Trial):
        kwargs = {
            "ma_fast_type": trial.suggest_categorical('ma_fast_type', ['ema', 'sma']),
            "ma_fast_period": trial.suggest_categorical('ma_fast_period', [5, 9, 10, 13, 21, 34, 55, 89, 144]),

            "ma_slow_type": trial.suggest_categorical('ma_slow_type', ['ema', 'sma']),
            "ma_slow_period": trial.suggest_categorical('ma_slow_period', [21, 34, 55, 89, 144, 200, 233, 377, 610]),

            "stop_loss": trial.suggest_int("stop_loss", 1, 200, step=10),

            "use_mfi": trial.suggest_categorical('use_mfi', [True, False])
        }

        if kwargs['use_mfi']:
            kwargs['mfi_high'] = trial.suggest_int("mfi_high", 1, 100)
            kwargs['mfi_low'] = trial.suggest_int("mfi_low", 1, 100)

        return kwargs
