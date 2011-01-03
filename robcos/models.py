from appengine_django import models
from google.appengine.ext import db
from datetime import date
from datetime import datetime
from datetime import timedelta
import ystockquote
from google.appengine.api import memcache
import types
import urllib2
from google.appengine.api.urlfetch_errors import DownloadError
import logging
import array

class DuplicateException(Exception):
  def __init__(self, value):
    self.value = value

  def __str__(self):
    return repr(self.value)

def long_cached(f):
  def g(*args, **kwargs):
    key =  str((f, tuple(args), frozenset(kwargs.items()))) + 'long'
    if memcache.get(key) is None:
      value = f(*args, **kwargs)
      memcache.add(key, value, 3600) # Cache for 1 hour
      logging.info("no hit for %s" % key)
    else:
      logging.debug("hit for %s" % key)
    return memcache.get(key)
  return g


def cached(f):
  def g(*args, **kwargs):
    key =  str((f, tuple(args), frozenset(kwargs.items())))
    if memcache.get(key) is None:
      value = f(*args, **kwargs)
      memcache.add(key, value, 55) # Cache for 5 seconds
      logging.debug("no hit for %s" % key)
    else:
      logging.debug("hit for %s" % key)
    return memcache.get(key)
  return g

class RealtimeQuote(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  price = db.FloatProperty(required=True)
  
  @staticmethod
  @long_cached
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
    all = None
    try:
      all = ystockquote.get_all(symbol)
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
      _from = date.today() - timedelta(days=60)
  
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
      logging.warning('Could not download %s" % e')
      return None
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

  def tr(self):
    query = db.Query(Quote)
    query.filter('symbol = ', self.symbol)
    query.filter('date < ', self.date)
    query.order('-date')
    prev = query.get()
    if prev == None:
      return self.high - self.low
    else:
      return max(self.high, prev.close) - min(self.low, prev.close)

  @staticmethod
  def get_idx(headers, query):
    for index, item in enumerate(headers):
      if (item == query):
        return index
    raise Exception('Could not get index for %s in %s', (query, headers))

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
  stop = db.FloatProperty(required=False, default=1.0)
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
    return self.shares * self.realtime_quote().price
  
  def local_value(self):
    return self.shares * self.realtime_quote().price * Currency.load(self.currency, self.portfolio.currency).rate
  
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
  
  @cached
  def realtime_quote(self):    
    return RealtimeQuote.load(self.symbol)
  
  def atr_exp_20(self):
    #quotes = self.latest_quote(2)[0].date
    quotes = self.latest_quote(3)
    quotes.reverse()
    v = map(lambda x: x.tr(), quotes)
    #print v
    #print "saa"
    #print reduce(lambda yesterday, today: (today * 19 + yesterday)/20, quotes)
    #print reduce(lambda x,y: x+y, quotes)
    #print "later"
    #.tr()
    #return self.latest_quote(1)[0].tr()

  @cached
  def atr_20(self):
    return self.atr(self.latest_quote(20))
 
  def calculated_stop(self):
    return self.enter_price - 3 * self.atr_20_at_enter()
  
  def below_ll_10(self):
    return self.realtime_quote().price < self.ll_10()

  def below_stop(self):
    return self.realtime_quote().price < self.calculated_stop()

  @long_cached
  def latest_quote(self, number):
    query = db.Query(Quote)
    query.filter('symbol = ', self.symbol)
    query.order('-date')
    return query.fetch(number)
    
  @staticmethod
  def delete_all():
    query = db.Query(Position)
    for p in query:
      p.delete()

  @long_cached
  def atr_20_at_enter(self):
    query = db.Query(Quote)
    query.filter('symbol = ', self.symbol)
    query.filter('date < ', self.enter_date)
    query.order('-date')
    atr = self.atr(query.fetch(20))
    if not atr:
      logging.info('No atr_20_at_enter for %s', (self.symbol))
    return atr

  def atr(self, quotes):
    trs = map(lambda x: x.tr(), quotes)
    if len(trs):
      return sum(trs)/len(trs)
    else:
      return None

  @long_cached
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
  @long_cached
  def load(_from, to):
    logging.info("Loading currency from %s to %s " % (_from, to))
    query = db.Query(Currency)
    symbol = '%s%s=X' % (_from, to)
    query.filter('symbol = ', symbol)
    query.filter('date = ', date.today())
    currency = query.get()
    if currency:
      logging.info("Found currency from %s to %s " % (_from, to))
      return currency

    if _from == to:
      return Currency(symbol = _from + to + '=X',
        date = date.today(),
        rate = 1.0
        )
        
    url ='http://finance.yahoo.com/d/quotes.csv?s=%s%s=X&t=2d&f=sd1l1' % (_from, to)
    try:
      result = urllib2.urlopen(url)
      parts = result.read().replace('"', '').strip().split(',')
      currency = Currency(symbol = parts[0],
        date = datetime.strptime(parts[1], '%m/%d/%Y').date(),
        rate = float(parts[2])
        )
      currency.put()
      return currency
        
    except urllib2.URLError, e:
      print e
    except DownloadError, e:
      print e
    return None


  @staticmethod
  def all():
    currencies = []
    currencies.append(Currency.load('USD', 'SEK'))
    currencies.append(Currency.load('USD', 'GBP'))
    currencies.append(Currency.load('SEK', 'SEK'))
    return currencies

