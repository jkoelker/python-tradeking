# -*- coding: utf-8 -*-

import pandas as pd

import utils


class Option(object):
    def __init__(self, symbol, long_short=utils.LONG, expiration=None,
                 call_put=None, strike=None, price_range=20,
                 contracts=1, base_fee=4.95, per_contract_fee=0.65,
                 tick_size=0.01):
        if per_contract_fee is None:
            per_contract_fee = base_fee

        self._price_range = utils.Price(price_range)
        self._contracts = contracts
        self._base_fee = base_fee
        self._per_contract_fee = per_contract_fee
        self._tick_size = utils.Price(tick_size)

        cost = base_fee + (per_contract_fee * (contracts - 1))
        self._cost = utils.Price(cost)

        if not all((expiration, call_put, strike)):
            (symbol, expiration,
             call_put, strike) = utils.parse_option_symbol(symbol)

        self._symbol = symbol
        self._expiration = expiration
        self._call_put = call_put
        self._strike = utils.Price(strike)

        if call_put.upper() == utils.PUT:
            func = lambda x: max(self._strike - x, 0)
        else:
            func = lambda x: max(x - self._strike, 0)

        start = self._strike - self._price_range
        stop = self._strike + self._price_range + 1
        prices = pd.Series(xrange(start, stop, self._tick_size))

        self._payoffs = prices.apply(func) - self._cost
        self._payoffs.index = prices

        if long_short.upper() == utils.SHORT:
            self._payoffs = self._payoffs * -1

    @property
    def payoffs(self):
        return self._payoffs

    @property
    def cost(self):
        return self._cost


class MultiLeg(object):
    def __init__(self, *legs, **option_kwargs):
        self.__option_kwargs = option_kwargs
        self._legs = []

        for leg in legs:
            self.add_leg(leg)

    def add_leg(self, leg, **option_kwargs):
        if not isinstance(leg, Option):
            if not option_kwargs:
                option_kwargs = self.__option_kwargs

            leg = Option(leg, **option_kwargs)

        self._legs.append(leg)

    @property
    def payoffs(self):
        payoffs = pd.Series()
        for leg in self._legs:
            payoffs = payoffs.add(leg.payoffs, fill_value=0)
        return payoffs

    @property
    def cost(self):
        return sum([leg.cost for leg in self._legs])


def plot(option, ypad=2, ylim=None, **kwargs):
    index = [utils.Price._decode(i) for i in option.payoffs.index]
    payoffs = pd.Series([utils.Price._decode(i) for i in option.payoffs],
                        index=index)

    if ylim is None:
        ylim = (payoffs.min() - ypad, payoffs.max() + ypad)

    return pd.tools.plotting.plot_series(payoffs, ylim=ylim, **kwargs)


Option.plot = plot
MultiLeg.plot = plot
