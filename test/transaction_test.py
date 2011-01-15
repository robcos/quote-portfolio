import unittest
import datetime
import logging

from robcos.transaction import ATransaction
from robcos.transaction import APosition

from mock import Mock

from google.appengine.ext import db

class TestTransaction(unittest.TestCase):
  FEES = 90.0
  TAXES = 10.0

  def setUp(self):
    self.t = ATransaction(
        symbol='AAPL',
        is_long=True,
        fees=self.FEES,
        taxes=self.TAXES)

  def test_Add(self):
    self.t.Add(1, 100)
    self.assertEquals(1, self.t.quantity_list_[0])
    self.assertEquals(100, self.t.price_list_[0])
  
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

class TestPosition(unittest.TestCase):

  def setUp(self):
    self.p = APosition(
        )

    self.lt = ATransaction(
        symbol='AAPL',
        is_long=True,
        fees=1.0,
        taxes=2.0)

    self.st = ATransaction(
        symbol='AAPL',
        is_long=False,
        fees=1.0,
        taxes=0.0)

  def test_AddAndStoreTransaction(self):
    self.assertEquals(0, db.Query(ATransaction).count())
    self.p.AddAndStoreTransaction(self.lt)
    self.assertEquals(1, db.Query(ATransaction).count())

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
    self.assertEquals(1, self.p.GetTotalBuyingCost())

  def test_GetShareAverageCost(self):
    self.assertRaises(Exception, self.p.GetShareAverageCost)

    # Buying 200 in two tranches
    self.p.AddAndStoreTransaction(self.lt)
    self.lt.Add(100, 1.0)
    self.assertEquals(1.03, self.p.GetShareAverageCost())
    self.lt.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())

    # Selling 100, average cost should not change.
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())

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
    self.assertEquals(100 * 0.20 + 1.0 + 2.0, self.p.GetRisk())
    self.lt.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())
    self.assertEquals(200 * (1.015-0.80) , self.p.GetRisk())
    
    self.p.AddAndStoreTransaction(self.st)
    self.st.Add(100, 1.0)
    self.assertEquals(1.015, self.p.GetShareAverageCost())
    self.assertEquals(100 * (1.015-0.80) , self.p.GetRisk())
