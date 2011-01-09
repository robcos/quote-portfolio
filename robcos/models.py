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
import math
import traceback

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
      logging.debug("no hit for %s" % key)
    else:
      logging.debug("hit for %s" % key)
    return memcache.get(key)
  return g

def cached(f):
  def g(*args, **kwargs):
    key =  str((f, tuple(args), frozenset(kwargs.items())))
    if memcache.get(key) is None:
      value = f(*args, **kwargs)
      memcache.add(key, value, 300) # Cache for X seconds
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
  def load(symbol):
    query = db.Query(RealtimeQuote)
    query.filter('symbol = ', symbol)
    quote = query.get()
    if not quote:
      logging.info("no quote for %s", symbol)
    return quote

  @staticmethod
  def download_all(symbols):
    symbols = '+'.join(symbols)
    yahoos = RealtimeQuote.yahoo(symbols)
    for yahoo in yahoos:
      RealtimeQuote.from_yahoo(yahoo).put()

  @staticmethod
  def from_yahoo(q):
    data = RealtimeQuote(
      symbol = q['symbol'],
      date = q['date'],
      price = float(q['price'])
    )
    return data

  @staticmethod
  def delete_all():
    query = db.Query(RealtimeQuote)
    for p in query:
      p.delete()


  @staticmethod
  def yahoo(symbols):
    """
       Downloads the latest quote for the given symbols
    """
    all = None
    try:
      return ystockquote.get_all(symbols)
    except Exception, e:
      logging.error('Could not download quote %s:%s', symbols, e)
      return None
 
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
  def yahoo(symbol, start_date=None, stop_date=None):
    """
    Loads the prices from the start date for the given symbol
    Only new quotes are downloaded.
    """
    if not stop_date:
      stop_date = date.today().strftime("%Y%m%d")
    if not start_date:
      query = db.Query(Quote)
      query.order('-date')
      query.filter('symbol = ', symbol)
      latest_quote = query.get()
      if latest_quote:
        start_date = latest_quote.date
      else:
        start_date = date.today() - timedelta(days=120)
      if start_date == date.today():
        return

    start_date = start_date.strftime("%Y%m%d")
    prices = ystockquote.get_historical_prices(symbol, start_date, stop_date)
    headers = prices[0]
    try:
      close = Quote.get_idx(headers, 'Close')
      date_ = Quote.get_idx(headers, 'Date')
      open = Quote.get_idx(headers, 'Open')
      high = Quote.get_idx(headers, 'High')
      low = Quote.get_idx(headers, 'Low')
    except Exception, e:
      logging.warning('Could not download %s:%s', symbol, e)
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
  cash = db.FloatProperty(required=True, default=0.0)
  other = db.FloatProperty(required=True, default=0.0)
  nominal_value = db.FloatProperty(required=True, default=0.0)
  currency = db.StringProperty(required=True, default='SEK', choices=['SEK', 'USD', 'GBP'])
  show_closed = True

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
  
  def set_show_closed(self, value):
    self.show_closed = value
  
  def risk_unit(self):
    return self.nominal_value / 100

  def get_positions(self):
    query = db.Query(Position)
    query.filter("portfolio =", self)
    if not self.show_closed:
      query.filter("exit_date =", None)
    query.order('symbol')
    query.order('enter_date')
    return query.fetch(query.count())
  
  def local_value(self):
    return reduce(lambda x,y: x + y.local_value(), [0] + self.get_positions()) + self.cash + self.other
  
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
      return self.gain() / self.cost() * 100
    else:
      return None
  
  def cost(self):
    return self.shares * self.enter_price * self.currency_rate + self.commission()

  def loosing(self):
    return self.gain() < 0
  
  def realtime_quote(self):    
    return RealtimeQuote.load(self.symbol)
  
  def atr_20(self):
    return Indicator.load(self.symbol, date.today()).atr_20
 
  def suggested_stop(self):
    return self.enter_price - 3 * self.atr_20_at_enter()
  
  def suggested_shares(self):
    allowed_risk = self.portfolio.risk_unit() - self.commission()
    risk_per_share = self.enter_price - self.stop
    shares = 0
    if risk_per_share:
      shares = math.floor(allowed_risk / risk_per_share)
    if shares > 0:
      return shares
    else:
      return None
  
  def below_ll_10(self):
    return self.realtime_quote().price <= self.ll_10()

  def below_stop(self):
    return self.realtime_quote().price <= self.stop

  def commission(self):
    commission = 2 * self.enter_commission
    if self.exit_commission:
      commission = self.enter_commission + self.exit_commission
    return commission

  def risk(self):
    return self.shares * (self.enter_price - self.stop) * self.currency_rate + self.commission()

  def too_risky(self):
    return self.risk() >= self.portfolio.risk_unit()

  def rtr(self):
    risk = self.portfolio.risk_unit()
    if risk == 0:
      return None
    return self.gain() / risk

  @staticmethod
  def delete_all():
    query = db.Query(Position)
    for p in query:
      p.delete()

  def atr_20_at_enter(self):
    atr = Indicator.load(self.symbol, self.enter_date).atr_20
    if not atr:
      logging.warn('No atr_20_at_enter for %s', (self.symbol))
    return atr

  def ll_10(self):
    return Indicator.load(self.symbol, date.today()).ll_10

class Indicator(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  ll_10 = db.FloatProperty(required=True)
  atr_20 = db.FloatProperty(required=True)

  @staticmethod
  def load(symbol, date):
    query = db.Query(Indicator)
    query.filter('symbol = ', symbol)
    query.filter('date = ', date)
    indicator = query.get()
    if indicator:
      logging.debug("Found indicator for %s on %s " % (symbol, date))
    else:
      indicator = Indicator.build(symbol, date)
    return indicator
 
  @staticmethod 
  def atr(quotes):
    trs = map(lambda x: x.tr(), quotes)
    if len(trs):
      return sum(trs)/len(trs)
    else:
      return None

  @staticmethod
  def build(symbol, date):
    logging.debug("Building indicator for %s on %s " % (symbol, date))
    query = db.Query(Quote)
    query.filter('symbol = ', symbol)
    query.filter('date < ', date)
    query.order('-date')
    quotes = query.fetch(20)
    atr_20 = Indicator.atr(quotes)
    ll_10 = None
    if len(quotes) > 0:
      last_10_quotes = quotes[:10]
      ll_10 = min(map(lambda x: x.low, last_10_quotes))
    else:
      logging.debug("Could not build indicator for %s on %s " % (symbol, date))
      return
    indicator = Indicator(symbol = symbol,
              date = date,
              atr_20 = atr_20,
              ll_10 = ll_10)
    indicator.put()
    return indicator

  @staticmethod
  def delete_all():
    query = db.Query(Indicator)
    for p in query:
      p.delete()

class Currency(models.BaseModel):
  symbol = db.StringProperty(required=True)
  date = db.DateProperty(required=True)
  rate = db.FloatProperty(required=True)
  
  @staticmethod
  def delete_all():
    query = db.Query(Currency)
    for p in query:
      p.delete()

  @staticmethod
  def download_all():
    Currency.download('USD', 'SEK').put()
    Currency.download('USD', 'GBP').put()
    Currency.download('USD', 'USD').put()

    Currency.download('SEK', 'USD').put()
    Currency.download('SEK', 'GBP').put()
    Currency.download('SEK', 'SEK').put()

    Currency.download('GBP', 'USD').put()
    Currency.download('GBP', 'SEK').put()
    Currency.download('GBP', 'GBP').put()

  @staticmethod
  @cached
  def load(_from, to):
    query = db.Query(Currency)
    symbol = '%s%s=X' % (_from, to)
    query.filter('symbol = ', symbol)
    return query.get()
 
  @staticmethod
  def download(_from, to):
    logging.info("Loading currency from %s to %s " % (_from, to))
    if _from == to:
      return Currency(symbol = _from + to + '=X',
        date = date.today(),
        rate = 1.0
        )
        
    symbol = '%s%s=X' % (_from, to)
    url ='http://finance.yahoo.com/d/quotes.csv?s=%s%s=X&t=2d&f=sd1l1' % (_from, to)
    try:
      result = urllib2.urlopen(url)
      parts = result.read().replace('"', '').strip().split(',')
      currency = Currency(symbol = parts[0],
        date = datetime.strptime(parts[1], '%m/%d/%Y').date(),
        rate = float(parts[2])
        )
      return currency
        
    except Exception, e:
      logging.error('Could not download quote %s:%s', symbol, e)
    return None

  @staticmethod
  @cached
  def all():
    return db.Query(Currency)

