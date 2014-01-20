A python wrapper for the Tradeking API
======================================

Usage
=====

Obtain OAuth keys/secrets from
`TradeKing <https://developers.tradeking.com/applications>`_.

.. code-block:: python

    import tradeking

    CONSUMER_KEY = 'consumer_key'
    CONSUMER_SECRET = 'consumer_secret'
    OAUTH_TOKEN = 'oauth_token'
    OAUTH_SECRET = 'oauth_secret'

    tkapi = tradeking.TradeKing(consumer_key=CONSUMER_KEY,
                                consumer_secret=CONSUMER_SECRET,
                                oauth_token=OAUTH_TOKEN,
                                oauth_secret=OAUTH_SECRET)

    quotes = tkapi.market.quotes('IBM')


Note
====

In the near future the format of parsed results will return
`Pandas <http://pandas.pydata.org/>`_ objects instead of dictionaries.
