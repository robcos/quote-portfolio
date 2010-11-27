from appengine_django import models
from google.appengine.ext import db
from datetime import date
from datetime import datetime
import ystockquote
from google.appengine.api import memcache
import types
import urllib2

def cached(f):
  def g(*args, **kwargs):
    key =  str((f, tuple(args), frozenset(kwargs.items())))
    if memcache.get(key) is None:
      value = f(*args, **kwargs)
      memcache.add(key, value, 5) # Cache for 5 seconds
    return memcache.get(key)
  return g

class RealtimeQuote(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  price = db.FloatProperty(required=True)
  
  @staticmethod
  @cached
  def load(symbol):
    q = RealtimeQuote.yahoo(symbol)
    if not q:
      return None
    data = RealtimeQuote(
      symbol = q['symbol'],
      date = q['date'],
      price = float(q['price'])
    )
    return data

  @staticmethod
  def yahoo(symbol):
    """
       Downloads the latest quote for the given symbol
    """
 
    all = ystockquote.get_all(symbol)
    try:
      date = datetime.strptime(all['date'], '"%m/%d/%Y"').date()
    except Exception, e:
      return None

    return {
        'symbol': symbol,
        'date': date,
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

  @cached
  def get_positions(self):
    query = db.Query(Position)
    query.filter("portfolio =", self)
    return query.fetch(query.count())
  
  def local_value(self):
    return reduce(lambda x,y: x + y.local_value(), [0] + self.get_positions())
  
  def gain(self):
    return reduce(lambda x,y: x + y.gain(), [0] + self.get_positions())
  
  def cost(self):
    return reduce(lambda x,y: x + y.cost(), [0] + self.get_positions())

  @staticmethod

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
  enter_currency_rate = db.FloatProperty(required=True, default=1)
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
  
  def value(self):
    return self.shares * self.latest_quote().price
  
  def local_value(self):
    return self.shares * self.latest_quote().price * Currency.load(self.currency, self.portfolio.currency).rate
  
  def gain(self):
    return self.local_value() - self.cost()
  
  def cost(self):
    return self.shares * self.enter_price * self.enter_currency_rate + self.enter_commission
  
  def latest_quote(self):    
    return RealtimeQuote.load(self.symbol)
    
  @staticmethod
  def delete_all():
    query = db.Query(Position)
    for p in query:
      p.delete()

class Currency(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  rate = db.FloatProperty(required=True)
  
  @staticmethod
  @cached
  def load(_from, to):
    if _from == to:
      return Currency(symbol = _from + to + '=X',
        date = date.today(),
        rate = 1.0
        )
        
    url ='http://finance.yahoo.com/d/quotes.csv?s=%s%s=X&t=2d&f=sd1l1' % (_from, to)
    try:
      result = urllib2.urlopen(url)
      parts = result.read().replace('"', '').strip().split(',')
      return Currency(symbol = parts[0],
        date = datetime.strptime(parts[1], '%m/%d/%Y').date(),
        rate = float(parts[2])
        )
        
    except urllib2.URLError, e:
      print e

  @staticmethod
  def all():
    currencies = []
    currencies.append(Currency.load('USD', 'SEK'))
    currencies.append(Currency.load('USD', 'GBP'))
    currencies.append(Currency.load('SEK', 'SEK'))
    return currencies

