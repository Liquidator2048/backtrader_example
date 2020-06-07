from ._base import BaseStrategy
from ._cross import *
from ._ema_slope import *
from ._mfi import *
from ._optimize import *
from ._rsi2 import *

strategies = {
    'cross': CrossStrategy,
    'ema_slope': EMASplopeStrategy,
    'mfi': MFIStrategy,
}

strategy_optimizers = {
    'cross': OptimizeCrossStrategy,
    'ema_slope': OptimizeEMASplopeStrategy,
    'mfi': OptimizeMFIStrategy,
}