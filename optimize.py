#!/usr/bin/env python
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import argparse
import logging
import os
from datetime import datetime

from dotenv import load_dotenv, find_dotenv

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.strategies import *

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S')

load_dotenv(find_dotenv())

optuna_storage = os.getenv("OPTUNA_STORAGE", "sqlite:///data/optuna.db")

parser = argparse.ArgumentParser(description='Optimize strategy with optuna')

parser.add_argument('--strategy', dest='strategy_name', help='strategy to optimize', choices=strategy_optimizers.keys(),
                    required=True)
parser.add_argument('--analyzer', dest='analyzer', help='analyzer used in optimization', default='sharpe_ratio',
                    choices=['sharpe_ratio', 'sqn', 'vwr', 'pnl', 'winrate'])
parser.add_argument('--start-cash', dest='start_cash', type=int, default=1000)
parser.add_argument('--tf', dest='tf', help='time frame', default="1h")
parser.add_argument('--exchange', dest='exchange', help='exchange', default='bitmex')
parser.add_argument('--symbol', dest='symbol', help='symbol', default='XBTUSD')
parser.add_argument('--max-evals', dest='max_evals', type=int, help='maximum number of trials', default=1000)
parser.add_argument('--perc-size', dest='perc_size', type=float, help='%% size of position',
                    default="100.0")
parser.add_argument('--commission', dest='commission', type=lambda s: float(s), help='%% of commission',
                    default="0.00075")
parser.add_argument('--date-start', dest='date_start', type=lambda s: datetime.strptime(f'{s} +0000', '%Y-%m-%d %z'),
                    default='2017-01-01')
parser.add_argument('--date-end', dest='date_end', type=lambda s: datetime.strptime(f'{s} +0000', '%Y-%m-%d %z'),
                    default='2019-01-01')

args = parser.parse_args()

time_periods = [
    (args.date_start, args.date_end),
]
analyzer = args.analyzer
tf = args.tf
start_cash = args.start_cash
symbol = args.symbol
exchange = args.exchange
max_evals = args.max_evals
perc_size = args.perc_size
commission = args.commission
strategy_name = args.strategy_name
StrategyOptimizeClass = strategy_optimizers[strategy_name]

study_name = f"{strategy_name}-{symbol}-{analyzer}-{tf}-{args.date_start.strftime('%Y-%m-%d')}-{args.date_end.strftime('%Y-%m-%d')}"

opt = StrategyOptimizeClass(
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
df = dfetch.download_data(exchange=exchange, symbol=symbol, bin_size=tf, date_from=f, date_to=t)

result, stats, cerebro, thestrats = opt.backtest(
    df=df,
    verbose=True,
    **best
)

portvalue = cerebro.broker.getvalue()
print(f"final value: {portvalue - start_cash}")
cerebro.plot()
