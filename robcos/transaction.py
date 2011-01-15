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

class Transaction(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)

  date = db.DateProperty(auto_now_add=True)

  is_long = db.BooleanProperty(required=True)
  """True is this transaction has bought shares, False otherwise."""

  quantity_list_ = db.ListProperty(int, required=True)
  """An ordered list of share quantities touched by this transaction."""

  price_list_ = db.ListProperty(float, required=True)
  """An ordered list of share prices touched by this transaction."""

  fees = db.FloatProperty(required=True)
  taxes = db.FloatProperty(required=True)

  def Add(self, quantity, price):
    self.quantity_list_.append(quantity)
    self.price_list_.append(price)

  def GetQuantity(self):
    """Returns the total number of shares handled by this transaction."""
    return sum(self.quantity_list_)

  def GetAverageCost(self):
    """Returns the average cost of the shares handled by this transaction."""

    if not self.quantity_list_:
      raise Exception('Must hadd some shares first')

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

class Position():
  
  closed = False
  opened_on = None

  def GetTransactions(self):
    """Returns all the transactions associated to this position"""
    pass

  def IsOpen(self):
    """True if there is at least an unsold stock."""
    pass

  def GetStop(self):
    """The maximum stop of all open positions."""
    pass

  def GetNetValue(self):
    """How much is the position worth if I sold it at the current price.

    All the fees are deducted from the value.

    """
    pass

  def GetRisk(self):
    """How much I loose if I sell all invested shares at the stop price."""
    pass

  def GetGain(self):
    """How much I win if I sell all invested shares at the current price.
      
    All the fees are deducted from the value.
    """
    pass

  def GetShareAverageCost(self):
    """The average cost of a single share."""
    pass

  def GetTotalCost(self):
    """Sum of all costs.
      
    This includes the share cost, fees and taxes of all transactions.
          
    """
    pass

  def GetCurrentCost(self):
    """Sum of all costs."""
    pass

  def GetOutstandingShares(self):
    """The number of shares currently owned."""
    pass
