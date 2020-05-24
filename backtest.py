from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)
import logging
from datetime import datetime

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.strategies import *
from strategies_tester.utils_backtest import *

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S')

f = datetime(2019, 1, 1)
t = datetime(2020, 1, 1)
dfetch = DataFetcher()
df = dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1m', date_from=f, date_to=t)

start_cash = 1000
cerebro, thestrats = backtest_strategy(
    df=df,
    strategy=RSI2Startegy,
    start_cash=start_cash,
    commission=0.00075,
    perc_size=100,
    verbose=True,

    rsi_len=2,
    traling_stop=2,
    rsi_up=90,
    rsi_down=10,
    slow_ema=610,
    fast_ema=9,

    use_replay=True,
    #timeframe=bt.TimeFrame.Minutes,
    compression=240
)

portvalue = cerebro.broker.getvalue()

print(f"PNL: {portvalue - start_cash}")

cerebro.plot()

for name, analyzer in list(thestrats[0].analyzers.getitems()):
    analyzer.print()
