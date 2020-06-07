from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"

import math

import backtrader as bt

__all__ = ['MFI', 'SuperTrendBand', 'SuperTrend', 'Slope', 'SlopeGrad', 'StochasticSlow', 'STC']


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
        super(MFI, self).__init__()


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
        super(SuperTrendBand, self).__init__()

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
        super(SuperTrend, self).__init__()

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
        super(Slope, self).__init__()

    def next(self):
        self.l.slp[0] = (self.data[0] - self.data[-1]) / self.data[0]


class SlopeGrad(bt.Indicator):
    lines = ('slope',)
    params = {
        'period': 3
    }

    def __init__(self):
        self.addminperiod(self.p.period)
        super(SlopeGrad, self).__init__()

    def next(self):
        self.slope[0] = 180 / math.pi * math.atan(
            (self.data[0] - self.data[-self.p.period]) / self.p.period
        )


from backtrader.indicators import Indicator, MovAv, Highest, Lowest, DivByZero


class StochasticSlow(Indicator):
    lines = ('k', 'd',)
    params = (('period', 10), ('period_smoothk', 6), ('period_smoothd', 3), ('movav', MovAv.Simple),
              ('upperband', 80.0), ('lowerband', 20.0),
              ('safediv', False), ('safezero', 0.0))

    plotlines = dict(percD=dict(_name='%D', ls='--'),
                     percK=dict(_name='%K'))

    csv = True

    def _plotlabel(self):
        plabels = [self.p.period, self.p.period_smoothk, self.p.period_smoothd]
        plabels += [self.p.movav] * self.p.notdefault('movav')
        return plabels

    def _plotinit(self):
        self.plotinfo.plotyhlines = [self.p.upperband, self.p.lowerband]

    def __init__(self):
        lowestlow = Lowest(self.data.low, period=self.p.period)
        highesthigh = Highest(self.data.high, period=self.p.period)

        if self.p.safediv:
            self.l.k = self.p.movav(
                100.0 * DivByZero(self.data.close - lowestlow, highesthigh - lowestlow, zero=self.p.safezero),
                period=self.p.period_smoothk)
        else:
            self.l.k = self.p.movav(100.0 * ((self.data.close - lowestlow) / (highesthigh - lowestlow)),
                                    period=self.p.period_smoothk)
        self.l.d = self.p.movav(self.k, period=self.p.period_smoothd)

        super(StochasticSlow, self).__init__()


class Stoch(Indicator):
    lines = ('k', 'd',)
    params = (('src', None), ('high', None), ('low', None),
              ('period', 14), ('period_dfast', 3), ('movav', MovAv.Exponential),
              ('upperband', 80.0), ('lowerband', 20.0),
              ('safediv', False), ('safezero', 0.0))

    plotlines = dict(percD=dict(_name='%D', ls='--'),
                     percK=dict(_name='%K'))

    csv = True

    def _plotlabel(self):
        plabels = [self.p.period, self.p.period_dfast]
        plabels += [self.p.movav] * self.p.notdefault('movav')
        return plabels

    def _plotinit(self):
        self.plotinfo.plotyhlines = [self.p.upperband, self.p.lowerband]

    def __init__(self):
        #self.addminperiod(self.p.period * self.p.period_dfast)
        self.highesthigh = Highest(self.p.high, period=self.p.period)
        self.lowestlow = Lowest(self.p.low, period=self.p.period)
        self.knum = self.p.src - self.lowestlow
        self.kden = self.highesthigh - self.lowestlow

        if self.p.safediv:
            self.lines.k = 100.0 * DivByZero(self.knum, self.kden, zero=self.p.safezero)
        else:
            self.lines.k = 100.0 * (self.knum / self.kden)
        m = self.p.movav(self.lines.k, period=self.p.period_dfast)
        self.lines.d = m

        super(Stoch, self).__init__()

    def next(self):
        if not self.l.d[0]:
            pass

class STC(Indicator):
    params = {
        'fastLength': 23,
        'slowLength': 50,
        'cycleLength': 10,
        'd1Length': 3,
        'd2Length': 3,

        'movav': MovAv.Exponential
    }

    csv = True

    lines = ('stc',)

    def __init__(self):
        #self.addminperiod(self.p.slowLength * self.p.cycleLength * self.p.d1Length * self.p.d2Length)  # ??

        # me1 - me2
        self.macd = bt.indicators.MACD(
            period_me1=self.p.fastLength,
            period_me2=self.p.slowLength,
            movav=self.p.movav
        ).lines.macd

        self.stoch = Stoch(
            src=self.macd,
            high=self.macd,
            low=self.macd,
            period=self.p.cycleLength,
            period_dfast=self.p.d1Length,
            movav=self.p.movav,
            safediv=True
        )
        self.stochK = Stoch(
            src=self.stoch.l.d,
            high=self.stoch.l.d,
            low=self.stoch.l.d,
            period=self.p.cycleLength,
            period_dfast=self.p.d2Length,
            movav=self.p.movav,
            safediv=True
        )

        super(STC, self).__init__()

    def next(self):
        if self.stochK.l.d[0] > 100:
            self.lines.stc[0] = 100
        elif self.stochK.l.d[0] < 0:
            self.lines.stc[0] = 0
        else:
            self.lines.stc[0] = self.stochK.l.d[0]


    def print(self, *args, **kwargs):
        pass