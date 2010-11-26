from appengine_django import models
from google.appengine.ext import db
from datetime import date
from datetime import datetime
import ystockquote

class RealtimeQuote(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  price = db.FloatProperty(required=True)
  
  @staticmethod
  def load(symbol):
    q = RealtimeQuote.yahoo(symbol)
    return RealtimeQuote(
      symbol = q['symbol'],
      date = q['date'],
      price = float(q['price'])
    )

  @staticmethod
  def yahoo(symbol):
    """
       Downloads the latest quote for the given symbol
    """
 
    all = ystockquote.get_all(symbol)
    
    return {
        'symbol': symbol,
        'date': datetime.strptime(all['date'], '"%m/%d/%Y"').date(),
        'price': all['price'], 
        'high': all['high'], 
        'low': all['low'], 
        'open': all['open']
    }
 
class Quote(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  close = db.FloatProperty(required=True)
  
  @staticmethod
  def load(symbol, date):
    query = db.Query(Quote)
    query.filter('symbol = ', symbol)
    query.filter('date = ', date)
    return query.get()

  @staticmethod
  def delete_all():
    query = db.Query(Quote)
    for p in query:
      p.delete()

   

class Portfolio(models.BaseModel):
  name = db.StringProperty(required=True)
  currency = db.StringProperty(required=True, default='SEK', choices=['SEK', 'USD', 'GBP'])

  @staticmethod
  def load(name):
    query = db.Query(Portfolio)
    query.filter('name = ', name)
    return query.get()

  @staticmethod
  def all():
    query = db.Query(Portfolio)
    return query.fetch(query.count())
  
  def save(self):
    p = Portfolio.load(self.name)
    if p is None:
      self.put()
      return self
    else:
      raise Exception('Portfolio already exists')

  def get_positions(self):
    query = db.Query(Position)
    query.filter("portfolio =", self)
    return query.fetch(query.count())

  @staticmethod
  def delete_all():
    query = db.Query(Portfolio)
    for p in query:
      p.delete()
  
  def __str__(self):
    return self.name

class Position(models.BaseModel):
  symbol = db.StringProperty(required=True)
  currency = db.StringProperty(required=True, default='SEK', choices=['SEK', 'USD', 'GBP'])
  currency_rate = db.FloatProperty(required=True, default=1)
  enter_date = db.DateProperty(required=True, default=date.today())
  exit_date = db.DateProperty(required=False)
  enter_price = db.FloatProperty(required=True)
  exit_price = db.FloatProperty(required=False)
  enter_commission = db.FloatProperty(required=True, default='99')
  exit_commission = db.FloatProperty(required=False)
  shares = db.FloatProperty(required=True)
  portfolio = db.ReferenceProperty(Portfolio, required=True)

  def save(self):
    p = Position.load(self.symbol, self.enter_date, self.portfolio)
    if p is None:
      self.put()
      return self
    else:
      raise Exception('Position already exists')

  @staticmethod
  def load(symbol, enter_date, portfolio):
    query = db.Query(Position)
    query.filter("symbol =", symbol)
    query.filter("enter_date =", enter_date)
    query.filter("portfolio =", portfolio)
    return query.get()
    
  @staticmethod
  def delete_all():
    query = db.Query(Position)
    for p in query:
      p.delete()
