import array
import logging
import math
import traceback
import types
import urllib2
import ystockquote

from appengine_django import models
from datetime import date
from datetime import datetime
from datetime import timedelta
from google.appengine.api import memcache
from google.appengine.api.urlfetch_errors import DownloadError
from google.appengine.ext import db

class ATransaction(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(auto_now_add=True)

  is_long = db.BooleanProperty(required=True)
  """True is this transaction has bought shares, False otherwise."""

  quantity_list_ = db.ListProperty(int, required=True)
  """An ordered list of share quantities touched by this transaction."""

  price_list_ = db.ListProperty(float, required=True)
  """An ordered list of share prices touched by this transaction."""

  fees = db.FloatProperty(required=True)
  taxes = db.FloatProperty(required=True)
  stop = db.FloatProperty(required=True, default=0.0)
  """The value at which the stocks of this transaction should be sold"""

  def Add(self, quantity, price):
    self.quantity_list_.append(quantity)
    self.price_list_.append(price)

  def GetQuantity(self):
    """Returns the total number of shares handled by this transaction."""
    return sum(self.quantity_list_)

  def GetAverageCost(self):
    """Returns the average cost of the shares handled by this transaction."""

    if not self.quantity_list_:
      raise Exception('Must add some shares first')

    return self.GetCost() / self.GetQuantity()
    pass

  def GetCost(self):
    """The cost of this transaction, including fees and taxes."""
    
    if not self.quantity_list_:
      raise Exception('Must add some shares first')
    share_cost = sum(map(lambda x,y: x*y, self.quantity_list_, self.price_list_))
    return self.fees + self.taxes + share_cost

class Portfolio():

  def GetOpenPositions(self):
    pass

  def GetAllPositions(self):
    pass

class APosition(models.BaseModel):
  
  #closed = db.BooleanProperty(required=True, default=False)
  opened_on = db.DateProperty(required=True, auto_now_add=True)
  transactions_ = []

  def __init__(self):
    self.transactions_ = []

  def AddAndStoreTransaction(self, transaction):
    """Add a transaction to this position. The transaction is persisted."""
    self.transactions_.append(transaction)
    transaction.put()
  
  def GetOutstandingShares(self):
    """The number of shares currently owned."""
    return sum(map(
        lambda x: x.GetQuantity() if x.is_long else -x.GetQuantity(),
        self.transactions_))

  def GetTransactions(self):
    """Returns all the transactions associated to this position"""
    return self.transactions_
  
  def GetBuyingTransactions(self):
    """Returns all the buying transactions associated to this position"""

    return filter(lambda x: x.is_long, self.transactions_)

  def GetTotalBuyingCost(self):
    """Sum of all costs substained to reach this position.
      
    This includes the share cost, fees and taxes of all buying transactions.
          
    """

    return reduce(lambda x, y: x + y.GetCost() if y.is_long else x,
        [0] + self.transactions_)

  def GetShareAverageCost(self):
    """The average cost of a single share.

    This is the equivalent cost you would have sustained if you had bought
    all the shares at the same price with zero fees or taxes.
    """

    transactions = self.GetBuyingTransactions()
    return (reduce(lambda x, y: x + y.GetAverageCost(), [0] + transactions) /
        len(transactions))

  def GetStop(self):
    """The maximum stop of all open positions."""
    
    return reduce(lambda x, y: max(x, y.stop),
         [0] + self.GetBuyingTransactions())

  def GetRisk(self):
    """How much I loose if I sell all invested shares at the stop price.

    Takes into account enter fees and taxes.
    """
    self.GetOutstandingShares() * (
        self.GetShareAverageCost() - self.GetStop())

    return self.GetOutstandingShares() * (
        self.GetShareAverageCost() - self.GetStop())

  def GetNetValue(self):
    """How much is the position worth if I sold it at the current price.

    All the fees are deducted from the value.

    """
    pass

  def GetGain(self):
    """How much I win if I sell all invested shares at the current price.
      
    All the fees are deducted from the value.
    """
    pass

  def IsOpen(self):
    """True if there is at least an unsold stock."""
    pass
