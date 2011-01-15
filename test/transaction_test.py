import unittest
import datetime
from robcos.transaction import Transaction

class TestTransaction(unittest.TestCase):
  FEES = 90.0
  TAXES = 10.0

  def setUp(self):
    self.t = Transaction(
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
