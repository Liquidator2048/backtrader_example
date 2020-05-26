from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import os
from datetime import datetime

from dotenv import load_dotenv, find_dotenv

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.strategies import *

load_dotenv(find_dotenv())

optuna_storage = os.getenv("OPTUNA_STORAGE", "sqlite:///data/optuna.db")

time_periods = [
    (datetime(year=2017, month=1, day=1), datetime(year=2019, month=1, day=1)),
]
analyzer = "sharpe_ratio"
tf = "1h"
start_cash = 1000
symbol = "XBTUSD"
exchange = "bitmex"
max_evals = 100
perc_size = 100
commission = 0.00075

study_name = f"ema_slope-{symbol}-{analyzer}-{tf}"

opt = OptimizeEMASplopeStrategy(
    study_name=study_name,
    exchange=exchange,
    symbol=symbol,
    bin_size=tf,
    analyzer=analyzer,
    perc_size=perc_size,
    commission=commission,
    start_cash=start_cash,
    optuna_storage=optuna_storage,
    time_periods=time_periods
)

best = opt.run(max_evals=max_evals)

print(f"best result: {best}")

f = time_periods[-1][0]
t = time_periods[-1][1]

dfetch = DataFetcher()
df = dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1h', date_from=f, date_to=t)

result, pnl, cerebro, thestrats = opt.backtest(
    df=df,
    verbose=True,
    **best
)

print(f"PNL: {pnl}")
cerebro.plot()

for name, analyzer in list(thestrats[0].analyzers.getitems()):
    analyzer.print()
