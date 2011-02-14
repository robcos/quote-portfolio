import array
import logging
import math
import traceback
import types
import urllib2

from appengine_django import models
from datetime import date
from datetime import datetime
from datetime import timedelta
from google.appengine.api import memcache
from google.appengine.api.urlfetch_errors import DownloadError
from google.appengine.ext import db

from robcos.models import RealtimeQuote
from robcos.models import Indicator

class BaseModel(models.BaseModel):

  @classmethod
  def DeleteAll(cls):
    """Deletes all the entities"""

    query = db.Query(cls)
    for p in query:
      p.delete()


class APortfolio(BaseModel):
  name = db.StringProperty(required=True)
  default_fees = db.FloatProperty(required=False, default=0.0)
  nominal_value = db.FloatProperty(required=True, default=0.0)
  """The nominal value of portfolio used to calculate position sizes."""
  all_positions_ = []

  def __str__(self):
    return self.name

  def GetOpenPositions(self):
    pass
  
  def GetAllPositions(self):
    return self.all_positions_ 

  def LoadAllPositions(self):
    query = db.Query(APosition).filter("portfolio =", self)
    self.all_positions_ = []
    for position in query:
      position.realtime_quote = RealtimeQuote.load(position.symbol)
      position.LoadTransactions()
      self.all_positions_.append(position)

  def GetRiskUnit(self):
    """Returns the risk unit for this portfolio.

    Each transaction should not risk more than this value.
    """

    return self.nominal_value / 100
    
  def GetValue(self):
    return reduce(lambda x, y: x + y.GetValue(), [0] + self.GetAllPositions())

class APosition(BaseModel):
  symbol = db.StringProperty(required=True)
  portfolio = db.ReferenceProperty(APortfolio, required=True)
  opened_on = db.DateProperty(required=True, auto_now_add=True)
  closed = db.BooleanProperty(required=False, default=False)
  transactions_ = []
  realtime_quote = None

  def __init__(self, *args, **kwargs):
    super(APosition, self).__init__(**kwargs)
    self.transactions_ = []
  
  def __str__(self):
    return '%s:%s' % (self.portfolio.name, self.symbol) 

  def AddAndStoreTransaction(self, transaction):
    """Add a transaction to this position. The transaction is persisted."""
    self.transactions_.append(transaction)
    transaction.position = self
    transaction.put()
 
  def LoadTransactions(self):
    self.transactions_ = []
    for t in db.Query(ATransaction).filter('position = ', self).fetch(limit=500):
      self.transactions_.append(t)
      t.LoadIndicators()
  
  def GetOutstandingShares(self):
    """The number of shares currently owned."""
    return sum(map(
        lambda x: x.GetQuantity() if x.is_buying else -x.GetQuantity(),
        self.transactions_))

  def GetTransactions(self):
    """Returns all the transactions associated to this position"""
    return self.transactions_
  
  def GetBuyingTransactions(self):
    """Returns all the buying transactions associated to this position"""

    return filter(lambda x: x.is_buying, self.transactions_)

  def GetTotalBuyingCost(self):
    """Sum of all costs substained to reach this position.
      
    This includes the share cost, fees and taxes of all buying transactions.
    An estimate sell if also included.
          
    """
    cost = reduce(lambda x, y: x + y.GetCost() if y.is_buying else x,
        [0] + self.transactions_) 
    return cost + self.portfolio.default_fees if cost else 0.0

  def GetShareAverageCost(self):
    """The average cost of a single share.

    This is the equivalent cost you would have sustained if you had bought
    all the shares at the same price with zero fees or taxes.

    Returns: None if not transactions have been added yet.
    """

    transactions = self.GetBuyingTransactions()
    if not transactions:
      return None

    return (reduce(lambda x, y: x + y.GetAverageCost(), [0] + transactions) /
        len(transactions))

  def GetShareAveragePrice(self):
    """The average cost of a single share.

    This is the equivalent cost you would have sustained if you had bought
    all the shares at the same price with zero fees or taxes.

    Returns: None if not transactions have been added yet.
    """

    transactions = self.GetBuyingTransactions()
    if not transactions:
      return None

    return (reduce(lambda x, y: x + y.GetAveragePrice(), [0] + transactions) /
        len(transactions))


  def GetStop(self):
    """The maximum stop of all open positions."""
    
    return reduce(lambda x, y: max(x, y.stop),
         [0] + self.GetBuyingTransactions())

  def GetRisk(self):
    """How much I loose if I sell all invested shares at the stop price.

    Takes into account enter fees and taxes.
    """

    return self.GetOutstandingShares() * (
        self.GetShareAverageCost() - self.GetStop()) + self.portfolio.default_fees

  def GetNetValue(self):
    """How much is the position worth if I sold it at the current price.

    All the fees are deducted from the value.

    """
    pass

  def GetValue(self):
    """How much is the position worth if I sold it at the current price.

    No exit fees are taken into account.

    """
  
    return self.GetOutstandingShares() * self.realtime_quote.price

  def GetGain(self):
    """How much I win if I sell all invested shares at the current price.
      
    All the fees are deducted from the value.
    """
  
    return self.GetOutstandingShares() * (
       self.realtime_quote.price - self.GetShareAverageCost()) - self.portfolio.default_fees


  def GetGainPercentage(self):
    """How much I win if I sell all invested shares at the current price.
      
    All the fees are deducted from the value.
    """
  
    return self.GetGain() / self.GetTotalBuyingCost() * 100

  def GetRtr(self):
    """Returns the ration between the risk unit and the gain.""" 
    
    return self.GetGain() / self.GetRisk()


class ATransaction(BaseModel):
  date = db.DateProperty(required=True)
  position = db.ReferenceProperty(APosition, required=True)

  is_buying = db.BooleanProperty(required=False, default=True)
  """True is this transaction has bought shares, False otherwise."""

  quantity_list = db.ListProperty(int, required=True)
  """An ordered list of share quantities touched by this transaction."""

  price_list = db.ListProperty(float, required=True)
  """An ordered list of share prices touched by this transaction."""

  fees = db.FloatProperty(required=True)
  taxes = db.FloatProperty(required=True)
  stop = db.FloatProperty(required=True, default=0.0)
  """The value at which the stocks of this transaction should be sold"""

  indicator_at_enter = None
  indicator = None

  def Add(self, quantity, price):
    self.quantity_list.append(quantity)
    self.price_list.append(price)
    return self

  def LoadIndicators(self):
    self.indicator_at_enter = Indicator.load(self.position.symbol, self.date)
    self.indicator = Indicator.load(self.position.symbol, date.today())

  def GetQuantity(self):
    """Returns the total number of shares handled by this transaction."""
    return sum(self.quantity_list)

  def GetAveragePrice(self):
    if not self.quantity_list:
      raise Exception('Must add some shares first')
    return sum(map(lambda x,y: x*y, self.quantity_list, self.price_list)
        ) / self.GetQuantity()

  def GetAverageCost(self):
    """Returns the average cost of the shares handled by this transaction."""

    if not self.quantity_list:
      raise Exception('Must add some shares first')

    return self.GetCost() / self.GetQuantity()
    pass

  def GetCost(self):
    """The cost of this transaction, including fees and taxes."""
    
    return self.fees + self.taxes + self.GetAveragePrice() * self.GetQuantity()

  def GetAtr20(self):
    return self.indicator.atr_20
  
  def GetAtr20AtEnter(self):
    return self.indicator_at_enter.atr_20
  
  def GetLL10(self):
    return self.indicator.ll_10

  def GetCommission(self):
    return self.fees + self.taxes + self.position.portfolio.default_fees
  
  def GetSuggestedPosition(self):
    allowed_risk = self.position.portfolio.GetRiskUnit() - self.GetCommission()
    risk_per_share = self.GetAveragePrice() - self.GetSuggestedStop()
    shares = 0
    if risk_per_share:
      shares = math.floor(allowed_risk / risk_per_share)
    if shares > 0:
      return shares
    else:
      return None
  
  def GetSuggestedStop(self):
    return self.GetAveragePrice() - 3 * self.GetAtr20AtEnter()
