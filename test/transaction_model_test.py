import unittest
import logging

from robcos.transaction import APortfolio
from robcos.transaction import APosition
from robcos.transaction import ATransaction
from robcos.transaction import ATransaction
from robcos.models import RealtimeQuote

from mock import Mock
from mock import patch
from datetime import date

from google.appengine.ext import db

class TestTransaction(unittest.TestCase):
  FEES = 90.0
  TAXES = 10.0

  def setUp(self):
    portfolio = APortfolio(name='Avanza')
    portfolio.put()
    position = APosition(
        symbol='AAPL',
        portfolio=portfolio)
    position.put()

    self.t = ATransaction(
        is_buying=True,
        fees=self.FEES,
        date=date.today(),
        position=position,
        taxes=self.TAXES)

  def test_Add(self):
    self.t.Add(1, 100)
    self.assertEquals(1, self.t.quantity_list[0])
    self.assertEquals(100, self.t.price_list[0])
  
  def test_GetQuantity(self):
    self.assertEquals(0, self.t.GetQuantity())
    self.t.Add(1, 100)
    self.t.Add(2, 100)
    self.assertEquals(3, self.t.GetQuantity())

  def test_GetCost(self):
    fixed_cost = self.FEES + self.TAXES
    self.assertRaises(Exception, self.t.GetCost)
    self.t.Add(2, 50)
    self.assertEquals(fixed_cost + 100, self.t.GetCost())
    self.t.Add(3, 100)
    self.assertEquals(fixed_cost + 100 + 300, self.t.GetCost())
 
  def test_GetAverageCost(self):
    fixed_cost = self.FEES + self.TAXES
    self.assertRaises(Exception, self.t.GetAverageCost)
    self.t.Add(2, 50)
    self.assertEquals(100, self.t.GetAverageCost())
    self.t.Add(2, 50)
    self.assertEquals(75, self.t.GetAverageCost())

  def test_GetAveragePrice(self):
    self.assertRaises(Exception, self.t.GetAveragePrice)
    self.t.Add(2, 100)
    self.assertEquals(100, self.t.GetAveragePrice())
    self.t.Add(2, 50)
    self.assertEquals(75, self.t.GetAveragePrice())

class TestPosition(unittest.TestCase):

  def setUp(self):
    portfolio = APortfolio(
      name='Avanza',
      default_fees = 9.0,
    )
    portfolio.put()
    self.p = APosition(
        symbol='AAPL',
        portfolio=portfolio)
    self.p.put()

    self.lt = ATransaction(
        symbol='AAPL',
        is_buying=True,
        fees=1.0,
        date=date.today(),
        position=self.p,
        taxes=2.0)

    self.st = ATransaction(
        symbol='AAPL',
        is_buying=False,
        fees=1.0,
        date=date.today(),
        position=self.p,
        taxes=0.0)

  def test_AddAndStoreTransaction(self):
    self.assertEquals(0, db.Query(ATransaction).count())
    self.p.AddAndStoreTransaction(self.lt)
    self.assertEquals(1, db.Query(ATransaction).count())

  @patch('robcos.models.Indicator.load')
  def test_LoadTransaction(self, load):
    self.assertFalse(self.p.transactions_)
    self.p.AddAndStoreTransaction(self.lt)
    load.return_value = 'an indicator'

    # Reload
    self.p.LoadTransactions()
    loaded_transaction = self.p.GetTransactions()[0]
    self.assertEquals(self.lt, loaded_transaction)
    self.assertTrue(loaded_transaction.indicator_at_enter)
    self.assertTrue(loaded_transaction.indicator)

  def test_GetOutstandingShares(self):
    self.lt.Add(100, 1.0)
    self.lt.Add(50, 1.1)
    self.p.AddAndStoreTransaction(self.lt)
    self.assertEquals(150, self.p.GetOutstandingShares())

    self.st.Add(100, 1.0)
    self.p.AddAndStoreTransaction(self.st)
    self.assertEquals(50, self.p.GetOutstandingShares())

  def test_GetTransaction(self):
    
    self.assertFalse(self.p.GetTransactions())
    self.p.AddAndStoreTransaction(self.lt)
    self.p.AddAndStoreTransaction(self.st)
    self.assertEquals(2, len(self.p.GetTransactions()))

  def test_GetBuyingTransaction(self):
    
    self.assertFalse(self.p.GetBuyingTransactions())
    self.p.AddAndStoreTransaction(self.lt)
    self.p.AddAndStoreTransaction(self.st)
    self.assertEquals(1, len(self.p.GetBuyingTransactions()))
  
  def test_GetTotalBuyingCost(self):
    self.assertEquals(0, self.p.GetTotalBuyingCost())
    self.p.AddAndStoreTransaction(self.lt)
    self.p.AddAndStoreTransaction(self.st)
    self.lt.GetCost = Mock(return_value = 1.0)
    self.st.GetCost = Mock(return_value = 2.0)
    # Only buying transactions count.
    self.assertEquals(1 + 9, self.p.GetTotalBuyingCost())

  def test_GetShareAverageCost(self):
    self.assertEquals(None, self.p.GetShareAverageCost())

    # Buying 200 in two tranches
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(100, 1.0)
    self.assertEquals(1.03, self.p.GetShareAverageCost())
    self.lt.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())

    # Selling 100, average cost should not change.
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(50, 1.0).Add(50, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())

  def test_GetShareAveragePrice(self):
    self.assertEquals(None, self.p.GetShareAveragePrice())

    # Buying 200 in two tranches
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(100, 1.0)
    self.assertEquals(1.0, self.p.GetShareAveragePrice())
    self.lt.Add(100, 1.0)
    self.assertEquals(1.0, self.p.GetShareAveragePrice())

    # Selling 100, average price should not change.
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(50, 1.0).Add(50, 1.0)
    self.assertEquals(1.0, self.p.GetShareAveragePrice())

  def test_GetStop(self):
    self.assertEquals(0, self.p.GetStop())

    # Buying 
    self.lt.stop = 100.0
    self.p.AddAndStoreTransaction(self.lt)
    self.assertEquals(100, self.p.GetStop())

    # Selling
    self.st.stop = 150.0 # selling transaction should not have a stop
    self.p.AddAndStoreTransaction(self.st)
    self.assertEquals(100, self.p.GetStop())

  def test_GetRisk(self):
    self.assertRaises(Exception, self.p.GetRisk)

    # Buying 200 in two tranches
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(100, 1.0)
    self.lt.stop = 0.80
    self.assertEquals(100 * 0.20 + 1.0 + 2.0 + 9.0, self.p.GetRisk())
    self.lt.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())
    self.assertEquals(200 * (1.015-0.80) + 9.0, self.p.GetRisk())
    
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())
    self.assertEquals(100 * (1.015-0.80) + 9.0, self.p.GetRisk())

  def test_GetValue(self):
    self.assertRaises(Exception, self.p.GetValue)

    self.p.realtime_quote = RealtimeQuote(
      date=date.today(),
      symbol='AAPL',
      price=2.0)

    # Buying 200
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(200, 1.0)
    self.assertEquals(400, self.p.GetValue())

    # Selling 100
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(100, 1.0)
    self.assertEquals(200, self.p.GetValue())

  def test_GetGain(self):
    self.assertRaises(Exception, self.p.GetGain)

    self.p.realtime_quote = RealtimeQuote(
      date=date.today(),
      symbol='AAPL',
      price=2.0)

    # Buying 200@1
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(200, 1.0)
    self.assertEquals(200.0 - 2.0 - 1.0 - 9.0, round(self.p.GetGain()))

    # Selling 100
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(100, 1.0)
    self.assertEquals(100.0 - 1.0 - 0.5 - 9.0, round(self.p.GetGain(), 2))

  def test_GetGainPercentage(self):
    self.p.GetGain = Mock(return_value=10.0)
    self.p.GetTotalBuyingCost = Mock(return_value=100.0)
    
    self.assertEquals(10, self.p.GetGainPercentage())

  def test_GetRtr(self):
    self.p.GetGain = Mock(return_value=20.0)
    self.p.GetRisk = Mock(return_value=10.0)
    
    self.assertEquals(2, self.p.GetRtr())

  def test_GetRtr_NoGain(self):
    self.p.GetGain = Mock(return_value=0.0)
    self.p.GetRisk = Mock(return_value=10.0)
    
    self.assertEquals(0, self.p.GetRtr())



class TestPortfolio(unittest.TestCase):

  @patch('robcos.models.RealtimeQuote.load')
  def test_LoadAllPositions(self, load):
    portfolio = APortfolio(name='Avanza')
    portfolio.put()
    p1 = APosition(
        portfolio=portfolio, 
        symbol='AAPL')

    p2 = APosition(
        portfolio=portfolio, 
        symbol='GOOG')
    p1.put()
    p2.put()

    p1.LoadTransactions = Mock()
    p2.LoadTransactions = Mock()

    def side_effect(*args, **kwargs):
      return 'quote for %s' % args[0]
    load.side_effect = side_effect

    portfolio.LoadAllPositions()
    positions = portfolio.GetAllPositions()
    self.assertEquals(p1, positions[0])
    self.assertEquals(p2, positions[1])

    self.assertEquals('quote for AAPL', positions[0].realtime_quote)
    self.assertEquals('quote for GOOG', positions[1].realtime_quote)

    p1.LoadTransactions.assertCalled()
    p2.LoadTransactions.assertCalled()

  def test_GetValue(self):
    portfolio = APortfolio(name='Avanza')
    portfolio.put()

    p1 = APosition(
        portfolio=portfolio, 
        symbol='AAPL')

    p2 = APosition(
        portfolio=portfolio, 
        symbol='GOOG')
    positions = []
    positions.append(p1)
    positions.append(p2)

    p1.GetValue = Mock(return_value = 10.0)
    p2.GetValue = Mock(return_value = 20.0)
    
    portfolio.GetAllPositions = Mock(return_value = positions)
    self.assertEquals(30.0, portfolio.GetValue())
 
  def test_GetRiskUnit(self):
    portfolio = APortfolio(
      name='Avanza',
      nominal_value=100.0)
    
    self.assertEquals(1.0, portfolio.GetRiskUnit())
