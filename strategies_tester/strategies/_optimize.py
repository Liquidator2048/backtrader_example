from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

"""Helper per ottizzazione dei parametri di una strategia di backtrader usando optuna"""

__author__ = "Liquidator"
__copyright__ = "Copyright 2020, Liquidator"

import logging
import os
from datetime import datetime
from typing import List, Tuple

import optuna
import optuna.storages
import optuna.storages.rdb.models
from optuna.trial import TrialState

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.utils_backtest import BaseStrategy, backtest_strategy

__all__ = ['OptunaOptimizeStrategy']


class OptunaOptimizeStrategy(object):
    strategy = BaseStrategy

    def __init__(self,
                 study_name: str,
                 exchange: str,
                 symbol: str,
                 bin_size: str,
                 time_periods: List[Tuple[datetime, datetime]],
                 analyzer: str = None,
                 perc_size: int = 10,
                 commission: float = 0.00075,
                 start_cash: float = 10000,
                 optuna_storage: str = None
                 ):
        analyzer = (analyzer or 'none').lower().replace(" ", "_")
        assert analyzer in ['sharpe_ratio', 'sqn', 'vwr', 'winrate', 'none']
        self.study_name = study_name
        self.perc_size = perc_size
        self.commission = commission
        self.start_cash = start_cash
        self.analyzer = analyzer
        self.optuna_storage = optuna_storage
        self.logger = logging.getLogger(__name__)

        self.logger.info("download data")
        self.data = []
        for start, end in time_periods:
            self.data.append(DataFetcher().download_data(
                exchange=exchange,
                symbol=symbol,
                bin_size=bin_size,
                date_from=start,
                date_to=end
            ))

    def backtest(self, df, date_from: datetime = None, date_to: datetime = None, verbose=False, **kwargs):
        try:
            cerebro, thestrats = backtest_strategy(
                df=df,
                date_from=date_from,
                date_to=date_to,
                strategy=self.strategy,
                perc_size=self.perc_size,
                commission=self.commission,
                start_cash=self.start_cash,
                verbose=verbose,

                **kwargs
            )

            portvalue = cerebro.broker.getvalue()
            pnl = portvalue - self.start_cash

            thestrat = thestrats[0]
            trade_analyzer = thestrat.analyzers.trade.get_analysis()
            stats = {
                'pnl': pnl,
                'sqn': thestrat.analyzers.sqn.get_analysis()['sqn'],
                'vwr': thestrat.analyzers.vwr.get_analysis()['vwr'],
                'sharpe_ratio': thestrat.analyzers.sharpe_ratio.get_analysis()['sharperatio'],
                'winrate': (trade_analyzer.won.total / trade_analyzer.lost.total) * 100
            }

            if self.analyzer == 'sqn':
                result = stats['sqn']
            elif self.analyzer == 'vwr':
                result = stats['vwr']
            elif self.analyzer == 'sharpe_ratio':
                result = stats['sharpe_ratio']
            elif self.analyzer == 'winrate':
                result = stats['winrate']
            elif self.analyzer == 'none' or self.analyzer == 'pnl':
                result = pnl
            else:
                raise Exception(f"{self.analyzer}: analyzer not found")
            return result, stats, cerebro, thestrats
        except Exception as e:
            self.logger.error(e)
            return None, None, None, None

    def get_parameters(self, trial: optuna.Trial):
        return {}

    def _objective(self, trial: optuna.Trial):

        kwargs = self.get_parameters(trial)

        step = 0
        result = None
        for df in self.data:
            step += 1

            result, stats, cerebro, thestrats = self.backtest(df, **kwargs)

            if result is None:
                raise optuna.exceptions.TrialPruned("no result")

            trial.report(result, step)

            for k in stats.keys():
                trial.set_user_attr(f'backtest_{k}', stats[k])

            if trial.should_prune():
                raise optuna.exceptions.TrialPruned("should_prune")

        # result = self.backtest(self.data[0], **kwargs)
        if result is None:
            raise optuna.exceptions.TrialPruned("no result")
        return result

    def run(self, max_evals, n_jobs=None, engine_kwargs=None):
        n_jobs = self._default_n_jobs(n_jobs)
        engine_kwargs = self._default_engine_kwargs(engine_kwargs, n_jobs)

        storage = optuna.storages.RDBStorage(
            self.optuna_storage,
            engine_kwargs=engine_kwargs
        )

        study = optuna.create_study(
            study_name=self.study_name,
            direction='maximize',
            storage=storage,
            load_if_exists=True,
            pruner=optuna.pruners.NopPruner()
            # pruner=optuna.pruners.MedianPruner(n_startup_trials=len(self.data))
        )

        n_trials = self._calc_n_trials(study_name=study.study_name, storage=storage, max_evals=max_evals)

        if n_trials > 0:
            study.optimize(
                self._objective,
                n_trials=n_trials,
                n_jobs=n_jobs
            )

        study = optuna.load_study(study_name=self.study_name, storage=storage)

        self.logger.info(f"study best value: {study.best_value}")
        return study.best_params

    def _calc_n_trials(self, study_name, storage, max_evals):
        session = storage.scoped_session()

        study_model = optuna.storages.rdb.models.StudyModel.find_by_name(
            study_name,
            session=session
        )

        count = optuna.storages.rdb.models.TrialModel.count(
            session=session,
            study=study_model,
            state=TrialState.COMPLETE
        )

        if count >= max_evals:
            n_trials = 0
        else:
            n_trials = max_evals - count
        return n_trials

    def _default_n_jobs(self, n_jobs: int = None):
        if n_jobs != None:
            return n_jobs
        # n_jobs: numero di trial eseguti in contemporanea.
        #         utilizzare sqlite come storage potrebbe creare problemi nell'eseguire più di trial in contemporanea
        if self.optuna_storage and self.optuna_storage.startswith("sqlite"):
            n_jobs = 1
        else:
            n_jobs = os.cpu_count()
        return n_jobs

    def _default_engine_kwargs(self, engine_kwargs: dict = None, n_jobs=None):
        if engine_kwargs != None:
            return engine_kwargs
        n_jobs = self._default_n_jobs(n_jobs)
        # parametri passati a sqlalchemy solo per postgresql
        if self.optuna_storage and self.optuna_storage.startswith("postgresql"):
            engine_kwargs = {
                "pool_size": n_jobs * 20 if n_jobs and n_jobs > 0 else os.cpu_count() * 20,
                "max_overflow": 0,
                "connect_args": {'connect_timeout': 100},
            }
        else:
            engine_kwargs = None
        return engine_kwargs
