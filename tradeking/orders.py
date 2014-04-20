# -*- coding: utf-8 -*-

import functools

from lxml import etree


BUY_TO_COVER = '5'

OPTION_CALL = 'OC'
OPTION_PUT = 'OP'

OPEN = 'O'
CLOSE = 'C'

STOCK = 'CS'
OPTION = 'OPT'

BUY = '1'
SELL = '2'
SELL_SHORT = '5'

DAY = '0'
GTC = '1'
MOC = '2'

MARKET = '1'
LIMIT = '2'
STOP = '3'
STOP_LIMIT = '4'
TRAILING_STOP = 'P'

PRICE = '0'
BASIS = '1'


def Order(account, security_type, security, quantity, time_in_force=GTC,
          order_type=MARKET, side=BUY, trailing_stop_offset=None,
          trailing_stop_offset_type=PRICE, trailing_stop_peg_type='1'):
    fixml = etree.Element("FIXML",
                          xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2")
    order = etree.Element("Order",
                          TmInForce=str(time_in_force),
                          Typ=str(order_type),
                          Side=str(side),
                          Acct=str(account))

    instrument = etree.Element("Instrmt",
                               SecTyp=str(security_type),
                               Sym=str(security))

    order_quantity = etree.Element("OrdQty",
                                   Qty=str(quantity))

    if trailing_stop_offset is not None:
        order.set('ExecInst' 'a')
        peg_instruction = etree.Element('PegInstr',
                                        OfstTyp=str(trailing_stop_offset_type),
                                        PegPxType=str(trailing_stop_peg_type),
                                        OfstVal=str(trailing_stop_offset))
        order.append(peg_instruction)

    order.append(instrument)
    order.append(order_quantity)

    fixml.append(order)

    return fixml


Buy = functools.partial(Order, side=BUY)
Sell = functools.partial(Order, side=SELL)
Short = functools.partial(Order, side=SELL_SHORT)

#<FIXML xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2">
#  <Order TmInForce="0" Typ="1" Side="1" Acct="12345678">
#    <Instrmt SecTyp="CS" Sym="F"/>
#    <OrdQty Qty="1"/>
#  </Order>
#</FIXML>
