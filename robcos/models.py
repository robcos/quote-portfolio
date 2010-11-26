from appengine_django import models
from google.appengine.ext import db

class Portfolio(models.BaseModel):
  name = db.StringProperty(required=True)
  currency = db.StringProperty(required=True)
  positions ="c"

  @staticmethod
  def load(name):
    query = db.Query(Portfolio)
    query.filter('name = ', name)
    return query.get()
  
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
    return query

  @staticmethod
  def delete_all():
    query = db.Query(Portfolio)
    for p in query:
      p.delete()

class Position(models.BaseModel):
  symbol = db.StringProperty(required=True)
  currency = db.StringProperty(required=True)
  currency_rate = db.FloatProperty(required=True)
  enter_date = db.DateProperty(required=True)
  exit_date = db.DateProperty(required=False)
  enter_price = db.FloatProperty(required=True)
  exit_price = db.FloatProperty(required=False)
  enter_commission = db.FloatProperty(required=True)
  exit_commission = db.FloatProperty(required=False)
  shares = db.FloatProperty(required=True)
  portfolio = db.ReferenceProperty(Portfolio)

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
