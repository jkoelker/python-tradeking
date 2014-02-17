# -*- coding: utf-8 -*-

import pandas as pd

import utils


def tradeking_cost(num_legs, *args, **kwargs):
    base_fee = utils.Price(4.95)
    per_leg = utils.Price(0.65)
    return base_fee + per_leg * num_legs


class Leg(object):
    def __init__(self, symbol, long_short=utils.LONG, expiration=None,
                 call_put=None, strike=None, price_range=20,
                 cost_func=tradeking_cost, tick_size=0.01):

        price_range = utils.Price(price_range)
        self._tick_size = utils.Price(tick_size)
        self._cost_func = cost_func

        if not all((expiration, call_put, strike)):
            (symbol, expiration,
             call_put, strike) = utils.parse_option_symbol(symbol)

        self._symbol = symbol
        self._expiration = expiration
        self._call_put = call_put.upper()
        self._long_short = long_short.upper()
        self._strike = utils.Price(strike)
        self._start = self._strike - price_range
        self._stop = self._strike + price_range + 1

    def reset_start_stop(self, start, stop):
        if hasattr(self, '_cache') and 'payoffs' in self._cache:
            del self._cache['payoffs']

        self._start = start
        self._stop = stop

    @utils.cached_property()
    def payoffs(self):
        if self._call_put == utils.PUT:
            func = lambda x: max(self._strike - x, 0)
        else:
            func = lambda x: max(x - self._strike, 0)

        prices = pd.Series(xrange(self._start, self._stop, self._tick_size))

        payoffs = prices.apply(func)
        payoffs.index = prices

        if self._long_short == utils.SHORT:
            payoffs = payoffs * -1
        return payoffs

    @utils.cached_property()
    def cost(self):
        return self._cost_func(1)


class MultiLeg(object):
    def __init__(self, *legs, **leg_kwargs):
        self._cost_func = leg_kwargs.pop('cost_func', tradeking_cost)
        self.__leg_kwargs = leg_kwargs
        self._legs = []

        for leg in legs:
            self.add_leg(leg)

    def add_leg(self, leg, **leg_kwargs):
        if not isinstance(leg, Leg):
            if not leg_kwargs:
                leg_kwargs = self.__leg_kwargs

            leg = Leg(leg, **leg_kwargs)

        self._legs.append(leg)

    @utils.cached_property()
    def payoffs(self):
        start = min([leg._start for leg in self._legs])
        stop = min([leg._stop for leg in self._legs])

        for leg in self._legs:
            leg.reset_start_stop(start, stop)

        payoffs = pd.Series()
        for leg in self._legs:
            payoffs = payoffs.add(leg.payoffs, fill_value=0)
        return payoffs

    @utils.cached_property()
    def cost(self):
        return self._cost_func(len(self._legs))


def plot(option, include_cost=True, ypad=2, ylim=None, **kwargs):
    payoffs = option.payoffs
    index = [utils.Price._decode(i) for i in payoffs.index]
    if include_cost:
        payoffs = payoffs - option.cost
    payoffs = pd.Series([utils.Price._decode(i) for i in payoffs],
                        index=index)

    if ylim is None:
        ylim = (payoffs.min() - ypad, payoffs.max() + ypad)

    return pd.tools.plotting.plot_series(payoffs, ylim=ylim, **kwargs)


Leg.plot = plot
MultiLeg.plot = plot
