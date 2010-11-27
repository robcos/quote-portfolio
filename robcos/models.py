from appengine_django import models
from google.appengine.ext import db
from datetime import date
from datetime import datetime
from datetime import timedelta
import ystockquote
from google.appengine.api import memcache
import types
import urllib2

class DuplicateException(Exception):
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)


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
      _date = datetime.strptime(all['date'], '"%m/%d/%Y"').date()
    except Exception, e:
      return None

    return {
        'symbol': symbol,
        'date': _date,
        'price': all['price'], 
        'high': all['high'], 
        'low': all['low'], 
        'open': all['open']
    }
 
class Quote(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  close = db.FloatProperty(required=True)
  high = db.FloatProperty(required=True)
  low = db.FloatProperty(required=True)
  open = db.FloatProperty(required=True)
  
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

  @staticmethod
  def yahoo(symbol):
    """
    Loads the prices from the start date for the given symbol
    Only new quotes are downloaded.
    """
    to = date.today().strftime("%Y%m%d")
    query = db.Query(Quote)
    query.order('-date')
    query.filter('symbol = ', symbol)
    latest_quote = query.get()
    if latest_quote:
      _from = latest_quote.date
    else:
      _from = date.today() - timedelta(days=30)
  
    if _from == date.today():
      #print "Skipping %s" % symbol
      return
    #print "Downloading %s" % symbol
    if _from is None: 
      _from = start_date
    else:
      _from = _from.strftime("%Y%m%d")
    prices = ystockquote.get_historical_prices(symbol, _from, to)
    headers = prices[0]
    try:
      close = Quote.get_idx(headers, 'Close')
      date_ = Quote.get_idx(headers, 'Date')
      open = Quote.get_idx(headers, 'Open')
      high = Quote.get_idx(headers, 'High')
      low = Quote.get_idx(headers, 'Low')
    except Exception, e:
      raise Exception('Could not download %s" % e')
    quotes = prices[1:]
    return_value = []
    for l in quotes:
      try:
        q = Quote(symbol=symbol, 
          date = datetime.strptime(l[date_], '%Y-%m-%d').date(),
          close=float(l[close]),
          high=float(l[high]),
          low=float(l[low]),
          open=float(l[open])
          ).save()
        return_value.append(q)
      except DuplicateException, e:
        pass
    return return_value

  @staticmethod
  def get_idx(headers, query):
    for index, item in enumerate(headers):
      if (item == query):
        return index
    raise "Eror ind downloading quote"

  def save(self):
    p = Quote.load(self.symbol, self.date)
    if p is None:
      self.put()
      return self
    else:
      raise DuplicateException('Quote already exists')


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
      raise DuplicateException('Portfolio already exists')

  @cached
  def get_positions(self):
    query = db.Query(Position)
    query.filter("portfolio =", self)
    query.order('symbol')
    query.order('enter_date')
    return query.fetch(query.count())
  
  def local_value(self):
    return reduce(lambda x,y: x + y.local_value(), [0] + self.get_positions())
  
  def gain(self):
    return reduce(lambda x,y: x + y.gain(), [0] + self.get_positions())
  
  def cost(self):
    return reduce(lambda x,y: x + y.cost(), [0] + self.get_positions())

  def loosing(self):
    return self.gain() < 0

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
  # remove API does not work so I have to keep currency_rate
  #enter_currency_rate = db.FloatProperty(required=True, default=1)
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
      raise DuplicateException('Position already exists')

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
  
  def gainp(self):
    if self.cost() > 0:
      return self.gain()/self.cost() * 100
    else:
      return ""
  
  def cost(self):
    return self.shares * self.enter_price * self.currency_rate + self.enter_commission

  def loosing(self):
    return self.gain() < 0
  
  def latest_quote(self):    
    return RealtimeQuote.load(self.symbol)
    
  @staticmethod
  def delete_all():
    query = db.Query(Position)
    for p in query:
      p.delete()

  @cached
  def ll_10(self):
    query = db.Query(Quote)
    query.filter('symbol = ', self.symbol)
    query.order('-date')
    quotes = query.fetch(10)
    if len(quotes) > 0:
      return min(map(lambda x: x.low, quotes))
    else:
      return None

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

