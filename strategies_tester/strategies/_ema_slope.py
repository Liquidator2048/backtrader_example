from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

"""
Strategia ideata da 'The Crypto Gateway' www.thecryptogateway.it. 
All credits for the startegy goes to 'The Crypto Gateway' www.thecryptogateway.it

source code strategy: https://www.tradingview.com/script/TKg40Ska/
showing: https://www.youtube.com/watch?v=dEYKDubBULA
"""

__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"
__credits__ = ["The Crypto Gateway ( www.thecryptogateway.it )"]

import backtrader as bt

from ._base import BaseStrategy
from ._indicators import Slope

__all__ = ['EMASplopeStrategy', 'OptimizeEMASplopeStrategy']


class EMASplopeStrategy(BaseStrategy):
    params = {
        'slope_average': 'ema',
        'slope_ma_length': 130,
        'slope_fast_length': 9,
        'slope_slow_length': 21,
        'slope_trend_filter_enable': True,
        'slope_trend_filter_length': 200,

        'stop_loss': 50,

        '_accumulate': False,
        '_concurrent': False,
        '_data': None,
        'verbose': True,
    }

    lines = ('slp',)

    def __init__(self):
        super().__init__()

        if self.p.slope_average == 'ema':
            self.ma = bt.indicators.ExponentialMovingAverage(period=self.p.slope_ma_length)
        elif self.p.slope_average == 'sma':
            self.ma = bt.ind.MovingAverageSimple(period=self.p.slope_ma_length)
        else:
            raise Exception(f"{self.p.ma_fast_type}: not valid value for 'ma_fast_type'")

        if self.p.slope_trend_filter_enable:
            self.trend_filter = bt.indicators.ExponentialMovingAverage(period=self.p.slope_trend_filter_length)

        self.slp = Slope(self.ma)

        self.emaslopeF = bt.indicators.ExponentialMovingAverage(self.slp, period=self.p.slope_fast_length)
        self.emaslopeS = bt.indicators.ExponentialMovingAverage(self.slp, period=self.p.slope_slow_length)

        self.long_signal = bt.indicators.CrossUp(self.emaslopeF, self.emaslopeS)

        if self.p.slope_trend_filter_enable:
            self.long_signal = bt.indicators.And(
                self.long_signal,
                self.data.lines.close > self.trend_filter.lines.ema
            )

        self.short_signal = bt.indicators.CrossDown(self.emaslopeF, self.emaslopeS)
        if self.p.slope_trend_filter_enable:
            self.short_signal = bt.indicators.And(
                self.short_signal,
                self.data.lines.close < self.trend_filter.lines.ema
            )

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


class OptimizeEMASplopeStrategy(OptunaOptimizeStrategy):
    strategy = EMASplopeStrategy

    def get_parameters(self, trial: optuna.Trial):
        kwargs = {
            'stop_loss': trial.suggest_int("stop_loss", 1, 200, step=10),

            'slope_average': trial.suggest_categorical('slope_average', ['ema', 'sma']),
            'slope_ma_length': trial.suggest_int('slope_ma_length', 5, 610),
            'slope_fast_length': trial.suggest_int('slope_fast_length', 5, 610),
            'slope_slow_length': trial.suggest_int('slope_slow_length', 5, 610),
            'slope_trend_filter_enable': trial.suggest_categorical('slope_trend_filter_enable', [True, False]),
        }

        if kwargs['slope_fast_length'] >= kwargs['slope_slow_length']:
            raise optuna.exceptions.TrialPruned("slope_fast_length >= slope_slow_length")

        if kwargs['slope_trend_filter_enable']:
            kwargs['slope_trend_filter_length'] = trial.suggest_int('slope_trend_filter_length', 5, 610)

        return kwargs
