# -*- coding: utf-8 -*-

import logging

import pandas as pd

from tradeking import api
from tradeking import utils


LOG = logging.getLogger(__name__)


def bid_ask_avg(symbol, quotes):
    mean = quotes[['bid', 'ask']].T.mean()
    return utils.Price(mean[symbol])


def tradeking_cost(num_legs, *args, **kwargs):
    base_fee = utils.Price(4.95)
    per_leg = utils.Price(0.65)
    return base_fee + per_leg * num_legs


def tradeking_premium(tkapi=None, price_func=bid_ask_avg, **kwargs):
    if tkapi is None:
        consumer_key = kwargs.get('consumer_key')
        consumer_secret = kwargs.get('consumer_secret')
        oauth_token = kwargs.get('oauth_token')
        oauth_secret = kwargs.get('oauth_secret')

        if not all((consumer_key, consumer_secret, oauth_token, oauth_secret)):
            LOG.warning('No tkapi or tokens found. All premiums will be 0.')

            def zero(symbol, *args, **kwargs):
                return 0

            return zero

        tkapi = api.TradeKing(consumer_key=consumer_key,
                              consumer_secret=consumer_secret,
                              oauth_token=oauth_token,
                              oauth_secret=oauth_secret)

    def premium(symbol, *args, **kwargs):
        quotes = tkapi.market.quotes(symbol)
        return price_func(symbol, quotes)

    return premium


class Leg(object):
    def __init__(self, symbol, long_short=utils.LONG, expiration=None,
                 call_put=None, strike=None, price_range=20, tick_size=0.01,
                 cost_func=tradeking_cost, premium_func=None, **kwargs):

        if premium_func is None:
            premium_func = tradeking_premium(**kwargs)

        price_range = utils.Price(price_range)
        self._tick_size = utils.Price(tick_size)
        self._cost_func = cost_func
        self._premium_func = premium_func

        if not all((expiration, call_put, strike)):
            (symbol, expiration,
             call_put, strike) = utils.parse_option_symbol(symbol)

        self._symbol = utils.option_symbol(symbol, expiration, call_put,
                                           strike)
        self._underlying = symbol
        self._expiration = expiration
        self._call_put = call_put.upper()
        self._long_short = long_short.upper()
        self._strike = utils.Price(strike)
        self._start = self._strike - price_range
        self._stop = self._strike + price_range + 1

        if self._call_put == utils.PUT:
            self._payoff_func = lambda x: max(self._strike - x, 0)
        else:
            self._payoff_func = lambda x: max(x - self._strike, 0)

    def reset_start_stop(self, start, stop):
        if hasattr(self, '_cache') and 'payoffs' in self._cache:
            del self._cache['payoffs']

        self._start = start
        self._stop = stop

    def payoff(self, price):
        '''
        Evaluate the payoff for the leg at price.

        `price` *MUST* be a decimal shifted int. That is the price 7.95 is
            represented  as 7950. Wrap the price in utils.Price to easily
            convert prior to passing to this function.

            E.g.

            price = 7.95
            price = utils.Price(price)


        returns a decimal shifted int/long. Use utils.Price.decode to convert
            to a float.

            E.g

            result = payoff(price)
            result = utils.Price.decode(result)
        '''
        payoff = self._payoff_func(price)

        if self._long_short == utils.SHORT:
            payoff = payoff * -1

        return payoff

    @utils.cached_property()
    def payoffs(self):
        prices = pd.Series(range(self._start, self._stop, self._tick_size))

        payoffs = prices.apply(self._payoff_func)
        payoffs.index = prices

        if self._long_short == utils.SHORT:
            payoffs = payoffs * -1
        return payoffs

    @utils.cached_property()
    def cost(self):
        return self._cost_func(1)

    @utils.cached_property()
    def premium(self):
        premium = self._premium_func(self._symbol)

        if self._long_short == utils.SHORT:
            premium = premium * -1

        return premium


class MultiLeg(object):
    def __init__(self, *legs, **leg_kwargs):
        self._cost_func = leg_kwargs.pop('cost_func', tradeking_cost)
        self.__leg_kwargs = leg_kwargs
        self._legs = []

        for leg in legs:
            self.add_leg(leg)

    def add_leg(self, leg, **leg_kwargs):
        '''
        Add a leg to the MultiLeg.

        `leg` can either be an option symbol or an Leg instance. If it is
            an option symbol then either **leg_kwargs or the leg_kwargs to
            MultiLeg is used to construct the Leg, preferring **leg_kwargs.
        '''
        if not isinstance(leg, Leg):
            if not leg_kwargs:
                leg_kwargs = self.__leg_kwargs

            leg = Leg(leg, **leg_kwargs)

        self._legs.append(leg)

    def payoff(self, price):
        '''
        Evaluate the payoff for the MultiLeg at price.

        `price` *MUST* be a decimal shifted int/long. That is the price 7.95 is
            represented  as 7950. Wrap the price in utils.Price to easily
            convert prior to passing to this function.

            E.g.

            price = 7.95
            price = utils.Price(price)


        returns a decimal shifted int/long. Use utils.Price.decode to convert
            to a float.

            E.g

            result = payoff(price)
            result = utils.Price.decode(result)
        '''
        return sum([leg.payoff(price)for leg in self._legs])

    @utils.cached_property()
    def payoffs(self):
        start = min([leg._start for leg in self._legs])
        stop = max([leg._stop for leg in self._legs])

        for leg in self._legs:
            leg.reset_start_stop(start, stop)

        payoffs = pd.Series()
        for leg in self._legs:
            payoffs = payoffs.add(leg.payoffs, fill_value=0)
        return payoffs

    @utils.cached_property()
    def cost(self):
        return self._cost_func(len(self._legs))

    @utils.cached_property()
    def premium(self):
        return sum([leg.premium for leg in self._legs])


def _leg(symbol, long_short, call_put, expiration=None, strike=None,
         **leg_kwargs):

    if not all((expiration, strike)):
        (symbol, expiration,
         _call_put, strike) = utils.parse_option_symbol(symbol)

    return Leg(symbol, long_short=long_short, call_put=call_put,
               expiration=expiration, strike=strike, **leg_kwargs)


def Call(symbol, long_short=utils.LONG, expiration=None, strike=None,
         **leg_kwargs):
    # NOTE(jkoelker) Ignore anything that was parsed, this is a Call
    call_put = utils.CALL
    return MultiLeg(_leg(symbol, long_short, call_put, expiration=expiration,
                         strike=strike, **leg_kwargs), **leg_kwargs)


def Put(symbol, long_short=utils.LONG, expiration=None, strike=None,
        **leg_kwargs):
    # NOTE(jkoelker) Ignore anything that was parsed, this is a Put
    call_put = utils.PUT
    return MultiLeg(_leg(symbol, long_short, call_put, expiration=expiration,
                         strike=strike, **leg_kwargs), **leg_kwargs)


def Straddle(symbol, long_short=utils.LONG, expiration=None, strike=None,
             **leg_kwargs):
    put = _leg(symbol, long_short=long_short, call_put=utils.PUT,
               expiration=expiration, strike=strike, **leg_kwargs)
    call = _leg(symbol, long_short=long_short, call_put=utils.CALL,
                expiration=expiration, strike=strike, **leg_kwargs)
    return MultiLeg(put, call, **leg_kwargs)


def Strangle(symbol, call_strike, put_strike, long_short=utils.LONG,
             expiration=None,  **leg_kwargs):
    if not expiration:
        (symbol, expiration,
         _call_put, _strike) = utils.parse_option_symbol(symbol)

    put = _leg(symbol, long_short=long_short, call_put=utils.PUT,
               expiration=expiration, strike=put_strike, **leg_kwargs)
    call = _leg(symbol, long_short=long_short, call_put=utils.CALL,
                expiration=expiration, strike=call_strike, **leg_kwargs)
    return MultiLeg(put, call, **leg_kwargs)


def Collar(symbol, put_strike, call_strike, expiration=None, **leg_kwargs):

    if not expiration:
        (symbol, expiration,
         _call_put, _strike) = utils.parse_option_symbol(symbol)

    put = _leg(symbol, long_short=utils.LONG, call_put=utils.PUT,
               expiration=expiration, strike=put_strike, **leg_kwargs)
    call = _leg(symbol, long_short=utils.SHORT, call_put=utils.CALL,
                expiration=expiration, strike=call_strike, **leg_kwargs)

    return MultiLeg(put, call, **leg_kwargs)


def plot(option, ypad=5, ylim=None, include_cost=True, include_premium=True,
         **kwargs):
    payoffs = option.payoffs
    index = [utils.Price.decode(i) for i in payoffs.index]

    if include_cost:
        payoffs = payoffs - option.cost

    if include_premium:
        payoffs = payoffs - option.premium

    payoffs = pd.Series([utils.Price.decode(i) for i in payoffs],
                        index=index)

    if ylim is None:
        ylim = (payoffs.min() - ypad, payoffs.max() + ypad)

    return pd.tools.plotting.plot_series(payoffs, ylim=ylim, **kwargs)


Leg.plot = plot
MultiLeg.plot = plot
