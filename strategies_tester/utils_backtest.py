from datetime import datetime
from typing import Type, Any, Tuple

import backtrader as bt
import pandas as pd

from strategies_tester.strategies import BaseStrategy

__all__ = ['BacktestData', 'backtest_strategy']


class BacktestData(bt.feeds.PandasData):
    pass


def backtrader_data(dataname: pd.DataFrame, compression=None, timeframe=None, *args, **kwargs):
    td = dataname.index[2] - dataname.index[1]
    if timeframe is None or compression is None:
        if td.resolution_string == 'H':  # hours
            timeframe = bt.TimeFrame.Minutes
            compression = td.components.minutes + (td.components.hours * 60)
        elif td.resolution_string == 'T':  # minutes
            timeframe = bt.TimeFrame.Minutes
            compression = td.components.minutes + (td.components.hours * 60)
        elif td.resolution_string == 'D':  # days
            timeframe = bt.TimeFrame.Days
            compression = td.components.days
    return BacktestData(
        dataname=dataname,
        timeframe=timeframe,
        compression=compression,
        *args,
        **kwargs
    )


def backtest_strategy(
        df: pd.DataFrame,
        strategy: Type[BaseStrategy],
        date_from: datetime = None,
        date_to: datetime = None,
        perc_size=10,
        commission=0.00075,
        start_cash=1000.0,
        returns_analyzer=False,
        use_replay=False,
        df_resample=None,
        timeframe=bt.TimeFrame.Minutes,
        compression=60,
        output=None,
        *args, **kwargs
) -> Tuple[bt.Cerebro, Any]:
    cerebro = bt.Cerebro()

    if date_from is None:
        date_from = df.index.min().to_pydatetime()

    if date_to is None:
        date_to = df.index.max().to_pydatetime()

    # data
    data = backtrader_data(
        dataname=df,
        fromdate=date_from,
        todate=date_to
    )

    if use_replay:
        cerebro.replaydata(
            data,
            timeframe=timeframe,
            compression=compression
        )
    else:
        cerebro.adddata(data)

    if df_resample is not None:
        data_resample = BacktestData(dataname=df_resample)
        cerebro.resampledata(
            data_resample,
            timeframe=timeframe,
            compression=compression
        )

    # strategy
    cerebro.addstrategy(strategy, *args, **kwargs)

    # analysers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe_ratio', timeframe=bt.TimeFrame.Days)
    if returns_analyzer:
        cerebro.addanalyzer(bt.analyzers.LogReturnsRolling, _name='log_returns_rolling')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='draw_down')
    cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
    cerebro.addanalyzer(bt.analyzers.VWR, _name='vwr')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade')
    cerebro.addanalyzer(bt.analyzers.GrossLeverage, _name='gross_leverage')
    # cerebro.addanalyzer(bt.analyzers.Calmar, _name='calmar')

    # params
    cerebro.broker.setcash(start_cash)
    cerebro.broker.setcommission(commission=commission)
    cerebro.addsizer(bt.sizers.PercentSizer, percents=perc_size)
    cerebro.signal_accumulate(False)
    cerebro.signal_concurrent(False)
    if output is None:
        if 'verbose' in kwargs and kwargs['verbose']:
            import sys
            output = sys.stdout
        else:
            import os
            output = open(os.devnull, "w")
    cerebro.addwriter(bt.WriterFile, csv=True, out=output)
    # run
    thestrats = cerebro.run(runonce=False)

    return cerebro, thestrats
