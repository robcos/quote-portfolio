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

from robcos.models import RealtimeQuote

class BaseModel(models.BaseModel):

  @classmethod
  def DeleteAll(cls):
    """Deletes all the entities"""

    query = db.Query(cls)
    for p in query:
      p.delete()


class APortfolio(BaseModel):
  name = db.StringProperty(required=True)
  nominal_value = db.FloatProperty(required=True, default=0.0)
  """The nominal value of portfolio used to calculate position sizes."""

  def __str__(self):
    return self.name

  def GetOpenPositions(self):
    pass

  def GetAllPositions(self):
    query = db.Query(APosition).filter("portfolio =", self)
    positions = []
    for position in query:
      position.realtime_quote = RealtimeQuote.load(position.symbol)
      position.LoadTransactions()
      positions.append(position)
    return positions

  def GetRiskUnit(self):
    """Returns the risk unit for this portfolio.

    Each transaction should not risk more than this value.
    """

    return self.nominal_value / 100
    

class APosition(BaseModel):
  symbol = db.StringProperty(required=True)
  portfolio = db.ReferenceProperty(APortfolio, required=True)
  opened_on = db.DateProperty(required=True, auto_now_add=True)
  transactions_ = []
  realtime_quote = None

  def __init__(self, *args, **kwargs):
    super(APosition, self).__init__(**kwargs)
    self.transactions_ = []

  def AddAndStoreTransaction(self, transaction):
    """Add a transaction to this position. The transaction is persisted."""
    self.transactions_.append(transaction)
    transaction.position = self
    transaction.put()
 
  def LoadTransactions(self):
    self.transactions_ = db.Query(ATransaction).filter('position = ', self).fetch(limit=500)
  
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
       self.realtime_quote.price - self.GetShareAverageCost())


  def GetGainPercentage(self):
    """How much I win if I sell all invested shares at the current price.
      
    All the fees are deducted from the value.
    """
  
    return self.GetGain() / self.GetTotalBuyingCost() * 100

  def GetRtr(self):
    """Returns the ration between the risk unit and the gain.""" 
    
    return self.portfolio.GetRiskUnit() / self.GetGain()


class APositionForm(BaseModel):
  position = db.ReferenceProperty(APosition, required=False)
  portfolio = db.ReferenceProperty(APortfolio, required=True)
  symbol = db.StringProperty(required=True)
  quantity_list = db.StringProperty(required=True)
  price_list = db.StringProperty(required=True)
  enter_date = db.DateProperty(required=True, default=date.today())
  enter_commission = db.FloatProperty(required=True, default='99')
  
  def GetPriceList(self):
    """Converts the price_list property into a list.

    Returns: A list of floats.
    """
    return map(lambda x: float(x), self.price_list.split(','))

  def GetQuantityList(self):
    """Converts the price_list property into a list.

    Returns: A list of ints.
    """
    return map(lambda x: int(x), self.quantity_list.split(','))

  def Save(self):
    """Saves this form into a position and its transactions.

      Returns: The key of the saved position.
    """

    position = APosition(
        key=self.position.key() if self.position else None,
        symbol=self.symbol,
        portfolio=self.portfolio)

    position.put()
    self.position = position

    transaction = ATransaction(
        is_long=True,
        fees=self.enter_commission,
        position=self.position,
        taxes=0.0)

    for price, quantity in zip(self.GetPriceList(), self.GetQuantityList()):
      transaction.Add(quantity, price)   
      
    transaction.put()
    return position

  @staticmethod
  def Get(key):
    position = db.get(key)
    transaction = db.Query(ATransaction).filter('position =', position).get()
    return APositionForm(
        position=position,
        portfolio=position.portfolio,
        enter_commission=transaction.fees,
        price_list=','.join(map(lambda x: str(x), transaction.price_list_)),
        quantity_list=','.join(map(lambda x: str(x), transaction.quantity_list_)),
        symbol=position.symbol
    )

class ATransaction(BaseModel):
  date = db.DateProperty(auto_now_add=True)
  position = db.ReferenceProperty(APosition, required=False)

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
    return self

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


