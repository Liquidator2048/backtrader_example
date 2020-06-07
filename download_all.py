#!/usr/bin/env python
from strategies_tester.datafetcher import DataFetcher

import logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO, datefmt='%d/%m/%Y %H:%M:%S')

logger = logging.getLogger(__name__)

dfetch = DataFetcher()

logger.info("downloading binance BTCUSDT 1h")
dfetch.download_data(exchange='binance', symbol='BTCUSDT', bin_size='1h')

logger.info("downloading binance BTCUSDT 1d")
dfetch.download_data(exchange='binance', symbol='BTCUSDT', bin_size='1d')

logger.info("downloading bitmex XBTUSD 1d")
dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1d')

logger.info("downloading bitmex XBTUSD 1h")
dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1h')

logger.info("downloading bitmex XBTUSD 5m")
dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='5m')

logger.info("downloading bitmex XBTUSD 1m")
dfetch.download_data(exchange='bitmex', symbol='XBTUSD', bin_size='1m')
