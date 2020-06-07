#!/usr/bin/env python
from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import argparse
import logging
from datetime import datetime

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.strategies import *
from strategies_tester.utils_backtest import *

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S')

parser = argparse.ArgumentParser(description='Optimize strategy with optuna')

parser.add_argument('--strategy', dest='strategy_name', help='strategy', choices=strategies.keys(), required=True)
parser.add_argument('--start-cash', dest='start_cash', type=int, default=1000)
parser.add_argument('--tf', dest='tf', help='time frame', default="1h")
parser.add_argument('--exchange', dest='exchange', help='exchange', default='bitmex')
parser.add_argument('--symbol', dest='symbol', help='symbol', default='XBTUSD')
parser.add_argument('--perc-size', dest='perc_size', type=float, help='%% size of position', default="100.0")
parser.add_argument('--commission', dest='commission', type=lambda s: float(s), help='%% of commission',
                    default="0.00075")
parser.add_argument('--date-start', dest='date_start', type=lambda s: datetime.strptime(f'{s} +0000', '%Y-%m-%d %z'),
                    default='2017-01-01')
parser.add_argument('--date-end', dest='date_end', type=lambda s: datetime.strptime(f'{s} +0000', '%Y-%m-%d %z'),
                    default='2019-01-01')
parser.add_argument('--out', default=None)

args = parser.parse_args()

StrategyClass = strategies[args.strategy_name]

dfetch = DataFetcher()
df = dfetch.download_data(exchange=args.exchange, symbol=args.symbol, bin_size=args.tf)

cerebro, thestrats = backtest_strategy(
    df=df,
    date_from=args.date_start,
    date_to=args.date_end,
    strategy=StrategyClass,
    start_cash=args.start_cash,
    commission=args.commission,
    perc_size=args.perc_size,
    verbose=True,
    output=args.out
)

portvalue = cerebro.broker.getvalue()

print(f"PNL: {portvalue - args.start_cash}")

cerebro.plot(style='candlestick')

for name, analyzer in list(thestrats[0].analyzers.getitems()):
    analyzer.print()
