__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"

import logging
import math
import os
import tempfile
import threading
import time
import warnings
from datetime import timedelta, datetime
from typing import Tuple

import pandas as pd
from binance.client import Client as BinanceClient
from bitmex import bitmex
from bravado.exception import HTTPTooManyRequests
from tqdm import tqdm

# suppress bitmex client warnings
warnings.filterwarnings("ignore")

__all__ = ['DataFetcher']


class DataFetcher(object):
    TIMESTAMP_COLUMN = 'timestamp'
    BATCH_SIZE = 750
    DATA_DIR = 'data'

    binsize_str_int = {"1m": 1, "5m": 5, "15m": 5, "30m": 5, "1h": 60, "3h": 180, "4h": 60, "1d": 60 * 24}
    avaiable_bin_size = {"1m": "1m", "5m": "5m", "15m": "5m", "30m": "5m", "1h": "1h", "3h": "1h", "4h": "1h",
                         "1d": "1d"}
    real_bin_size = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "3h": 60 * 3, "4h": 60 * 4, "1d": 60 * 24}

    _save_lock = None
    _save_thread = None

    _bitmex_sleep_time = 1

    def __init__(self, save_after=25):
        self.logger = logging.getLogger(__name__)
        self.save_after = save_after
        self._save_lock = threading.RLock()

    def download_data(self, exchange: str, symbol: str, bin_size: str, date_from=None, date_to=None) -> pd.DataFrame:
        cache_filename = f'{exchange}_{symbol}_{self.avaiable_bin_size[bin_size]}.csv'
        cache_filepath = os.path.join(self.DATA_DIR, cache_filename)

        try:
            if not os.path.exists(cache_filepath):
                raise Exception(f"{cache_filepath}: file not found")
            df = pd.read_csv(cache_filepath).dropna()
            df[self.TIMESTAMP_COLUMN] = pd.to_datetime(df[self.TIMESTAMP_COLUMN], utc=True)
            df.set_index(self.TIMESTAMP_COLUMN, inplace=True)
        except Exception as e:
            self.logger.error(e)
            df = pd.DataFrame()

        if exchange == "bitmex":
            df = self._bitmex_download(
                symbol=symbol,
                bin_size=bin_size,
                data_df=df,
                cache_filepath=cache_filepath
            )
        elif exchange == "binance":
            df = self._binance_download(
                symbol=symbol,
                bin_size=bin_size,
                data_df=df,
                cache_filepath=cache_filepath
            )

        return df[date_from:date_to]

    def _save_df(self, df: pd.DataFrame, cache_filepath: str):
        import shutil
        with self._save_lock:  # wait other threads ( mutex )
            try:
                if not os.path.exists(self.DATA_DIR):
                    os.mkdir(self.DATA_DIR)
                _, tmpfn = tempfile.mkstemp()
                with open(tmpfn, 'w') as fd:
                    df.to_csv(fd)
                shutil.move(tmpfn, cache_filepath)
            except Exception as e:
                self.logger.error(f"_save_df: {e}")

    def save_df(self, df: pd.DataFrame, cache_filepath: str, i: int = 0):
        if i % self.save_after != 0:
            return
        self.logger.info(f"saving ( {i} )")
        if self._save_thread and self._save_thread.is_alive():
            self._save_thread.join()
        self._save_thread = threading.Thread(target=self._save_df, args=(df, cache_filepath))
        self._save_thread.start()

    def _bitmex_client(self, api_key=None, api_secret=None) -> bitmex:
        return bitmex(test=False, api_key=api_key, api_secret=api_secret)

    def _binance_client(self, api_key=None, api_secret=None) -> BinanceClient:
        return BinanceClient(api_key=api_key, api_secret=api_secret)

    def _minutes_of_new_data(self, symbol, kline_size: str, data, exchange) -> Tuple[datetime, datetime]:
        old, new = None, None
        # old
        if len(data) > 0:
            old = data.index[-1]
            old = pd.to_datetime(old, utc=True).to_pydatetime()
        elif exchange == "binance":
            old = datetime(2017, 1, 1)
        elif exchange == "bitmex":
            old = self._bitmex_client().Trade.Trade_getBucketed(
                symbol=symbol,
                binSize=kline_size,
                count=1,
                reverse=False
            ).result()[0][0][self.TIMESTAMP_COLUMN]

        # new
        if exchange == "binance":
            new = pd.to_datetime(
                self._binance_client().get_klines(
                    symbol=symbol,
                    interval=kline_size
                )[-1][0],
                unit='ms'
            )
        if exchange == "bitmex":
            new = self._bitmex_client().Trade.Trade_getBucketed(
                symbol=symbol,
                binSize=kline_size,
                count=1,
                partial=False,
                reverse=True
            ).result()[0][0][self.TIMESTAMP_COLUMN]

        return old, new

    def _bitmex_download(self, symbol, bin_size: str, data_df=pd.DataFrame(), cache_filepath=None) -> pd.DataFrame:
        oldest_point, newest_point = self._minutes_of_new_data(symbol, bin_size, data_df, exchange="bitmex")
        delta_min = (newest_point - oldest_point).total_seconds() / 60
        available_data = math.ceil(delta_min / self.binsize_str_int[bin_size])
        rounds = math.ceil(available_data / self.BATCH_SIZE)
        if rounds <= 0:
            return data_df

        for round_num in tqdm(range(rounds)):
            success = False
            t = time.time()
            while not success:
                try:
                    t_diff = timedelta(minutes=round_num * self.BATCH_SIZE * self.binsize_str_int[bin_size])
                    new_time = (oldest_point + t_diff)
                    data = self._bitmex_client().Trade.Trade_getBucketed(
                        symbol=symbol,
                        binSize=bin_size,
                        count=self.BATCH_SIZE,
                        startTime=new_time
                    ).result()[0]
                    t = time.time()

                    temp_df = pd.DataFrame(data)
                    temp_df.dropna(
                        subset=[self.TIMESTAMP_COLUMN, 'close', 'high', 'low', 'open', 'volume'],
                        inplace=True
                    )
                    temp_df[self.TIMESTAMP_COLUMN] = pd.to_datetime(temp_df[self.TIMESTAMP_COLUMN], utc=True)
                    temp_df.set_index(self.TIMESTAMP_COLUMN, inplace=True)
                    data_df = data_df.append(temp_df, sort=True)
                    success = True

                    if cache_filepath and rounds > 0:
                        self.save_df(data_df, cache_filepath, round_num)
                except HTTPTooManyRequests:
                    self.logger.warning("HTTPTooManyRequests")
                    success = False
                finally:
                    dt = time.time() - t
                    if dt < self._bitmex_sleep_time:
                        s = self._bitmex_sleep_time - dt
                        self.logger.debug(f"sleeping {s}")
                        time.sleep(s)  # cooldown

        return data_df

    def _binance_download(self, symbol, bin_size: str, data_df=pd.DataFrame(), cache_filepath=None) -> pd.DataFrame:
        if data_df is None:
            data_df = pd.DataFrame()
        oldest_point, newest_point = self._minutes_of_new_data(symbol, bin_size, data_df, exchange="binance")
        klines = self._binance_client().get_historical_klines(
            symbol,
            bin_size,
            oldest_point.strftime("%d %b %Y %H:%M:%S"),
            newest_point.strftime("%d %b %Y %H:%M:%S")
        )
        columns = ['close', 'high', 'low', 'open', 'volume']
        data = pd.DataFrame(
            klines,
            columns=columns + [self.TIMESTAMP_COLUMN, 'close_time', 'quote_av', 'trades', 'tb_base_av', 'tb_quote_av',
                               'ignore']
        ).dropna(
            subset=columns + [self.TIMESTAMP_COLUMN, ]
        )
        data['symbol'] = symbol
        data[self.TIMESTAMP_COLUMN] = pd.to_datetime(data[self.TIMESTAMP_COLUMN], unit='ms', utc=True)
        data.set_index(self.TIMESTAMP_COLUMN, inplace=True)
        if cache_filepath:
            self.save_df(data, cache_filepath)
        if len(data_df) > 0:
            data_df = data_df.append(data)
        else:
            data_df = data
        data_df.dropna(subset=columns, inplace=True)
        return data_df[columns + ['symbol']]
