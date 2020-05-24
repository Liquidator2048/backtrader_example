from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

import logging

import backtrader as bt

__all__ = ['BaseStrategy']


class BaseStrategy(bt.SignalStrategy):
    params = (
        ('signals', []),
        ('_accumulate', False),
        ('_concurrent', False),
        ('_data', None),
        ('verbose', True)
    )

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.trades = []

    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        if self.p.verbose:
            self.logger.info(f'{dt.isoformat()}, {txt}')

    def notify_order(self, order):
        super().notify_order(order)
        price = f'{order.executed.price:.2f}'
        value = f'{order.executed.value:.2f}'
        comm = f'{order.executed.comm:.2f}'
        type = order.getordername()
        dir = order.ordtypename()
        id = order.ref
        pos_size = self.position.size * self.position.price
        if order.status == order.Completed:
            self.log(
                f'Order #{id} - {type} {dir} - EXECUTED, Price: {price}, Cost: {value}, Comm: {comm}, Pos. Size: {pos_size}')
        elif order.status == order.Canceled:
            self.log(f'Order #{id} - {type} {dir} - Canceled - Pos. Size: {pos_size}')
        elif order.status == order.Margin:
            self.log(f'Order #{id} - {type} {dir} - Margin -  Pos. Size: {pos_size}')
        elif order.status == order.Rejected:
            self.log(f'Order #{id} - {type} {dir} - Rejected')
        elif order.status == order.Submitted:
            self.log(f'Order #{id} - {type} {dir} - Submitted: Price {price}, Cost: {value},  Pos. Size: {pos_size}')
        elif order.status == order.Accepted:
            self.log(f'Order #{id} - {type} {dir} - Accepted: Price {price}, Cost: {value},  Pos. Size: {pos_size}')

    def notify_trade(self, trade):
        super().notify_trade(trade)
        if not trade.isclosed:
            return
        pnl = f'{trade.pnl:.2f}'
        pnlcomm = f'{trade.pnlcomm:.2f}'
        self.log(f'OPERATION PROFIT, GROSS {pnl}, NET {pnlcomm}')
