import os
from datetime import datetime

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.strategies import *
from strategies_tester.utils_backtest import backtest_strategy

optuna_storage = os.getenv("OPTUNA_STORAGE", "sqlite:///data/optuna.db")

time_periods = [
    (datetime(year=2017, month=1, day=1), datetime(year=2020, month=1, day=1)),
]
analyzer = "sharpe_ratio"
tf = "1h"
start_cash = 1000
symbol = "XBTUSD"
exchange = "bitmex"
max_evals = 100
perc_size = 100
commission = 0.00075
# n_jobs: numero di trial eseguti in contemporanea.
#         se si usa sqlite come storage potrebbe creare problemi eseguire più di trial in contemporanea
n_jobs = os.cpu_count()
study_name = f"cross-{symbol}-{analyzer}-{tf}"

# parametri passati a sqlalchemy solo per postgresql
if optuna_storage and optuna_storage.startswith("postgresql"):
    engine_kwargs = {
        "pool_size": n_jobs * 20 if n_jobs and n_jobs > 0 else os.cpu_count() * 20,
        "max_overflow": 0,
        "connect_args": {'connect_timeout': 100},
    }
else:
    engine_kwargs = None

opt = OptimizeCrossStrategy(
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

best = opt.run(
    max_evals=max_evals,
    n_jobs=n_jobs,
    engine_kwargs=engine_kwargs
)

print(f"best result: {best}")

f = time_periods[-1][0]
t = time_periods[-1][1]

dfetch = DataFetcher()
df = dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1h', date_from=f, date_to=t)

start_cash = 1000
cerebro, thestrats = backtest_strategy(
    df=df,
    strategy=opt.strategy,
    start_cash=start_cash,
    commission=commission,
    perc_size=perc_size,
    verbose=True,

    **best
)

portvalue = cerebro.broker.getvalue()
print(f"final value: {portvalue - start_cash}")
cerebro.plot()
