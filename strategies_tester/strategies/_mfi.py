from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import backtrader as bt

from ._base import BaseStrategy
from ._indicators import MFI

__all__ = ['MFIStrategy', 'OptimizeMFIStrategy']


class MFIStrategy(BaseStrategy):
    params = {
        'mfi_length': 14,
        'mfi_limit_high': 80,
        'mfi_limit_low': 67,

        'stop_loss': 50,

        '_accumulate': False,
        '_concurrent': False,
        '_data': None,
        'verbose': True,
    }

    def __init__(self):
        super().__init__()
        self.mfi = MFI(period=self.p.mfi_length)

        self.long_signal = bt.indicators.CrossUp(self.mfi, self.p.mfi_limit_high)
        self.short_signal = bt.indicators.CrossDown(self.mfi, self.p.mfi_limit_low)

        self.market_order = None
        self.stop_order = None

    def next(self):
        if self.long_signal and self.position.size <= 0:
            # close previous position
            if self.market_order and self.market_order.issell():
                self.close(oco=self.market_order)

            # cancel previous stop loss
            if self.stop_order and self.stop_order.isbuy():
                self.cancel(self.stop_order)

            self.market_order = self.buy()

            self.stop_order = None

        if self.short_signal and self.position.size >= 0:
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


class OptimizeMFIStrategy(OptunaOptimizeStrategy):
    strategy = MFIStrategy

    def get_parameters(self, trial: optuna.Trial):
        kwargs = {
            "stop_loss": trial.suggest_int("stop_loss", 1, 200, step=10),

            'mfi_length': trial.suggest_int("mfi_length", 5, 200),
            'mfi_limit_high': trial.suggest_int("mfi_limit_high", 1, 100),
            'mfi_limit_low': trial.suggest_int("mfi_limit_low", 1, 100),
        }

        return kwargs
