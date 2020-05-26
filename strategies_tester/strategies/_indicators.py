from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"

import backtrader as bt

__all__ = ['MFI', 'SuperTrendBand', 'SuperTrend', 'Slope']


class MFI(bt.Indicator):
    lines = ('mfi',)
    params = dict(period=14)

    def __init__(self):
        tprice = (self.data.close + self.data.low + self.data.high) / 3.0
        mfraw = tprice * self.data.volume

        flowpos = bt.ind.SumN(mfraw * (tprice > tprice(-1)), period=self.p.period)
        flowneg = bt.ind.SumN(mfraw * (tprice < tprice(-1)), period=self.p.period)

        mfiratio = bt.ind.DivByZero(flowpos, flowneg, zero=100.0)
        self.l.mfi = 100.0 - 100.0 / (1.0 + mfiratio)


class SuperTrendBand(bt.Indicator):
    """
    Helper inidcator for Supertrend indicator
    credits: https://github.com/subhadeepdas91/backtrader
    """
    params = (('period', 7), ('multiplier', 3))
    lines = ('basic_ub', 'basic_lb', 'st_upper_level', 'st_lower_level')

    def __init__(self):
        self.atr = bt.indicators.AverageTrueRange(period=self.p.period)
        self.l.basic_ub = ((self.data.high + self.data.low) / 2) + (self.atr * self.p.multiplier)
        self.l.basic_lb = ((self.data.high + self.data.low) / 2) - (self.atr * self.p.multiplier)

    def next(self):
        if len(self) - 1 == self.p.period:
            self.l.st_upper_level[0] = self.l.basic_ub[0]
            self.l.st_lower_level[0] = self.l.basic_lb[0]
        else:
            # =IF(OR(basic_ub<st_upper_level*,close*>st_upper_level*),basic_ub,st_upper_level*)
            if self.l.basic_ub[0] < self.l.st_upper_level[-1] or self.data.close[-1] > self.l.st_upper_level[-1]:
                self.l.st_upper_level[0] = self.l.basic_ub[0]
            else:
                self.l.st_upper_level[0] = self.l.st_upper_level[-1]
            # =IF(OR(baisc_lb > st_lower_level *, close * < st_lower_level *), basic_lb *, st_lower_level *)
            if self.l.basic_lb[0] > self.l.st_lower_level[-1] or self.data.close[-1] < self.l.st_lower_level[-1]:
                self.l.st_lower_level[0] = self.l.basic_lb[0]
            else:
                self.l.st_lower_level[0] = self.l.st_lower_level[-1]


class SuperTrend(bt.Indicator):
    """
    Super Trend indicator
    credits: https://github.com/subhadeepdas91/backtrader
    """
    params = (('period', 7), ('multiplier', 3))
    lines = ('super_trend', 'st_trend')
    # plotinfo = dict(subplot=False)
    plotinfo = dict(plotymargin=0.05, plotyhlines=[-1.0, 1.0])
    plotlines = {'st_trend': {'_name': 'supertrend'}, 'super_trend': {'_plotskip': True}}

    def __init__(self):
        self.stb = SuperTrendBand(period=self.p.period, multiplier=self.p.multiplier)

    def next(self):
        if len(self) == 1:
            self.l.st_trend[-1] = 1

        if len(self) - 1 == self.p.period:
            self.l.super_trend[0] = self.stb.st_upper_level[0]
            return

        if self.l.super_trend[-1] == self.stb.st_upper_level[-1]:
            if self.data.close[0] <= self.stb.st_upper_level[0]:
                self.l.super_trend[0] = self.stb.st_upper_level[0]
                self.l.st_trend[0] = -1
            else:
                self.l.super_trend[0] = self.stb.st_lower_level[0]
                self.l.st_trend[0] = 1

        if self.l.super_trend[-1] == self.stb.st_lower_level[-1]:
            if self.data.close[0] >= self.stb.st_lower_level[0]:
                self.l.super_trend[0] = self.stb.st_lower_level[0]
                self.l.st_trend[0] = 1
            else:
                self.l.super_trend[0] = self.stb.st_upper_level[0]
                self.l.st_trend[0] = -1

        # st := st == -1 and close > upper_level_prev ? 1 : st == 1 and close < lower_level_prev ? -1 : st


class Slope(bt.Indicator):
    lines = ('slp',)

    def __init__(self):
        self.addminperiod(2)

    def next(self):
        self.l.slp[0] = (self.data[0] - self.data[-1]) / self.data[0]
