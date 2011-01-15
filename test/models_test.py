import unittest
import datetime
from robcos.models import Portfolio
from robcos.models import Position

class TestPorfolio(unittest.TestCase):
  def test_creation(self):
    Portfolio(name='Avanza', currency='SEK').save()
    fetched_model = Portfolio.load('Avanza')
    self.assertEquals('Avanza', fetched_model.name)
    self.assertEquals('SEK', fetched_model.currency)

  def test_creation_duplicates(self):
    Portfolio(name='Avanza', currency='SEK').save()
    p = Portfolio(name='Avanza', currency='SEK')
    self.assertRaises(Exception, p.save)
  
  def test_delete_all(self):
    Portfolio(name='Avanza', currency='SEK').save()
    Portfolio.delete_all()
    self.assertFalse(Portfolio.load('Avanza'))


class TestPosition(unittest.TestCase):
  def test_creation(self):
    p = Portfolio(name='Avanza', currency='SEK').save()
    a_date = datetime.date(2001, 1, 3)
    Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=a_date,
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=p).save()

    fetched_model = Position.load(
        symbol='AAPL', 
        enter_date=a_date,
        portfolio=p)

    self.assertEquals('AAPL', fetched_model.symbol)
    self.assertEquals(a_date, fetched_model.enter_date)
    self.assertEquals(p, fetched_model.portfolio)
 
  def test_get_positions(self):
    p = Portfolio(name='Avanza', currency='SEK').save()
    a_date = datetime.date(2001, 1, 3)
    Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=a_date,
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=p).save()
    self.assertEquals('AAPL', p.get_positions()[0].symbol)
    self.assertEquals(1, len(p.get_positions()))
 
  def test_creation_duplicates(self):
    p = Portfolio(name='Avanza', currency='SEK').save()
    a_date = datetime.date(2001, 1, 3)
    pos = Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=a_date,
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=p)
    pos.save()
    self.assertRaises(Exception, pos.save)
  
  def test_delete_all(self):
    p = Portfolio(name='Avanza', currency='SEK').save()
    a_date = datetime.date(2001, 1, 3)
    pos = Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=a_date,
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=p)
    pos.save()
    Position.delete_all()
    fetched_model = Position.load(
        symbol='AAPL', 
        enter_date=a_date,
        portfolio=p)
    self.assertFalse(fetched_model)
