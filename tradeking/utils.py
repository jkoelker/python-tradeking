# -*- coding: utf-8 -*-

import itertools
import time

import pandas as pd


CALL = 'C'
PUT = 'P'
LONG = 'L'
SHORT = 'S'


class Price(int):
    BASE = 1000.0

    def __new__(cls, value=0):
        return int.__new__(cls, cls.encode(value))

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return self._decode().__repr__()

    @classmethod
    def encode(cls, value):
        return int(value * cls.BASE)

    @classmethod
    def decode(cls, value):
        return float(value) / cls.BASE

    def _decode(self):
        return self.decode(self.real)


def option_symbol(underlying, expiration, call_put, strike):
    '''Format an option symbol from its component parts.'''
    call_put = call_put.upper()
    if call_put not in (CALL, PUT):
        raise ValueError("call_put value not one of ('%s', '%s'): %s" %
                         (CALL, PUT, call_put))

    expiration = pd.to_datetime(expiration).strftime('%y%m%d')

    strike = str(Price.encode(strike)).rstrip('L')
    strike = ('0' * (8 - len(strike))) + strike

    return '%s%s%s%s' % (underlying, expiration, call_put, strike)


def option_symbols(underlying, expirations, strikes, calls=True, puts=True):
    '''Generate a list of option symbols for expirations and strikes.'''
    if not calls and not puts:
        raise ValueError('Either calls or puts must be true')

    call_put = ''

    if calls:
        call_put = call_put + CALL

    if puts:
        call_put = call_put + PUT

    return [option_symbol(*args) for args in
            itertools.product([underlying], expirations, call_put, strikes)]


def parse_option_symbol(symbol):
    '''
    Parse an option symbol into its component parts.

    returns (Underlying, Expiration, C/P, strike)
    '''
    strike = Price.decode(symbol[-8:])
    call_put = symbol[-9:-8].upper()
    expiration = pd.to_datetime(symbol[-15:-9])
    underlying = symbol[:-15].upper()
    return underlying, expiration, call_put, strike


#
# © 2011 Christopher Arndt, MIT License
#
class cached_property(object):
    '''
    Decorator for read-only properties evaluated only once within TTL period.

    It can be used to created a cached property like this::

        import random

        # the class containing the property must be a new-style class
        class MyClass(object):
            # create property whose value is cached for ten minutes
            @cached_property(ttl=600)
            def randint(self):
                # will only be evaluated every 10 min. at maximum.
                return random.randint(0, 100)

    The value is cached  in the '_cache' attribute of the object instance that
    has the property getter method wrapped by this decorator. The '_cache'
    attribute value is a dictionary which has a key for every property of the
    object which is wrapped by this decorator. Each entry in the cache is
    created only when the property is accessed for the first time and is a
    two-element tuple with the last computed property value and the last time
    it was updated in seconds since the epoch.

    The default time-to-live (TTL) is 300 seconds (5 minutes). Set the TTL to
    zero for the cached value to never expire.

    To expire a cached property value manually just do::

        del instance._cache[<property name>]

    '''
    def __init__(self, ttl=300):
        self.ttl = ttl

    def __call__(self, fget, doc=None):
        self.fget = fget
        self.__doc__ = doc or fget.__doc__
        self.__name__ = fget.__name__
        self.__module__ = fget.__module__
        return self

    def __get__(self, inst, owner):
        now = time.time()
        try:
            value, last_update = inst._cache[self.__name__]
            if self.ttl > 0 and now - last_update > self.ttl:
                raise AttributeError
        except (KeyError, AttributeError):
            value = self.fget(inst)
            try:
                cache = inst._cache
            except AttributeError:
                cache = inst._cache = {}
            cache[self.__name__] = (value, now)
        return value
