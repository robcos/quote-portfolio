import unittest
import logging

from robcos.transaction import APortfolio
from robcos.transaction import APosition
from robcos.transaction import ATransaction
from robcos.transaction import ATransaction
from robcos.models import RealtimeQuote
import transaction

from mock import Mock
from mock import patch
from datetime import date
from django import forms

from google.appengine.ext import db

class TestCSField(unittest.TestCase):

  def testClean_int(self):
    field = transaction.CSField(type=int)
    self.assertEquals([1,2,3], field.clean('1,2,3'))
    self.assertEquals([], field.clean(''))
    self.assertEquals([], field.clean(None))
    self.assertRaises(forms.ValidationError, field.clean, '1,2,abc')

  def testClean_float(self):
    field = transaction.CSField(type=float)
    self.assertEquals([1.2,2.0,3.0], field.clean('1.2,2.0,3'))
    self.assertEquals([], field.clean(''))
    self.assertEquals([], field.clean(None))
    self.assertRaises(forms.ValidationError, field.clean, '1,2,abc')
