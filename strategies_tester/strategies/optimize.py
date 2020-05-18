import logging
from datetime import datetime
from typing import List, Tuple

import optuna
import optuna.storages
import optuna.storages.rdb.models
from optuna.trial import TrialState

from strategies_tester.datafetcher import DataFetcher
from strategies_tester.utils_backtest import BaseStrategy, backtest_strategy

logger = logging.getLogger(__name__)

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
        assert (analyzer or 'none').lower() in ['sharpe_ratio', 'sqn', 'vwr', 'none']
        self.study_name = study_name
        self.perc_size = perc_size
        self.commission = commission
        self.start_cash = start_cash
        self.analyzer = (analyzer or 'none')
        self.optuna_storage = optuna_storage

        logger.info("download data")
        self.data = []
        for start, end in time_periods:
            self.data.append(DataFetcher().download_data(
                exchange=exchange,
                symbol=symbol,
                bin_size=bin_size,
                date_from=start,
                date_to=end
            ))

    def backtest(self, df, **kwargs):
        try:
            cerebro, thestrats = backtest_strategy(
                df=df,
                strategy=self.strategy,
                perc_size=self.perc_size,
                commission=self.commission,
                start_cash=self.start_cash,
                verbose=False,

                **kwargs
            )

            portvalue = cerebro.broker.getvalue()
            pnl = portvalue - self.start_cash

            if self.analyzer == 'sqn':
                thestrat = thestrats[0]
                sr = thestrat.analyzers.sqn.get_analysis()
                result = sr['sqn']
            elif self.analyzer == 'vwr':
                thestrat = thestrats[0]
                sr = thestrat.analyzers.vwr.get_analysis()
                result = sr['vwr']
            elif self.analyzer == 'sharpe_ratio':
                thestrat = thestrats[0]
                sr = thestrat.analyzers.sharpe_ratio.get_analysis()
                result = sr['sharperatio']
            elif self.analyzer == 'none':
                result = pnl
                # logger.info(f"end objective with result {result}")
            else:
                # raise optuna.exceptions.TrialPruned()
                raise Exception(f"{self.analyzer}: analyzer not found")
            return result, pnl
        except Exception as e:
            logger.error(e)
            return None, None

    def get_parameters(self, trial: optuna.Trial):
        return {}

    def _objective(self, trial: optuna.Trial):

        kwargs = self.get_parameters(trial)

        step = 0
        result = None
        for df in self.data:
            step += 1

            result, pnl = self.backtest(df, **kwargs)

            if result is None:
                raise optuna.exceptions.TrialPruned()

            trial.report(result, step)
            trial.set_user_attr('backtest_pnl', pnl)

            if trial.should_prune():
                raise optuna.exceptions.TrialPruned()

        # result = self.backtest(self.data[0], **kwargs)
        if result is None:
            raise optuna.exceptions.TrialPruned()
        return result

    def run(self, max_evals, n_jobs, engine_kwargs=None):

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

        study_model = optuna.storages.rdb.models.StudyModel.find_by_name(
            study.study_name,
            session=storage.scoped_session()
        )

        count = optuna.storages.rdb.models.TrialModel.count(
            session=storage.scoped_session(),
            study=study_model,
            state=TrialState.COMPLETE
        )

        if count >= max_evals:
            n_trials = 0
        else:
            n_trials = max_evals - count

        if n_trials > 0:
            study.optimize(
                self._objective,
                n_trials=n_trials,
                n_jobs=n_jobs
            )

        study = optuna.load_study(study_name=self.study_name, storage=storage)

        logger.info(f"study best value: {study.best_value}")
        return study.best_params
