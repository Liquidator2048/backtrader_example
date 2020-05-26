from typing import Type, Any, Tuple

import backtrader as bt
import pandas as pd

from strategies_tester.strategies import BaseStrategy

__all__ = ['BacktestData', 'backtest_strategy']


class BacktestData(bt.feeds.PandasData):
    pass


def backtest_strategy(
        df: pd.DataFrame,
        strategy: Type[BaseStrategy],
        perc_size=10,
        commission=0.00075,
        start_cash=1000.0,
        returns_analyzer=False,
        use_replay=False,
        timeframe=bt.TimeFrame.Minutes,
        compression=60,
        *args, **kwargs
) -> Tuple[bt.Cerebro, Any]:
    cerebro = bt.Cerebro()

    # data
    data = BacktestData(dataname=df)
    if use_replay:
        cerebro.replaydata(
            data,
            timeframe=timeframe,
            compression=compression
        )
    else:
        cerebro.adddata(data)

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

    # run
    thestrats = cerebro.run(runonce=False)

    return cerebro, thestrats
