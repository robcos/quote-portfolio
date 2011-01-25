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
    self.assertEquals([0,1,2,3], field.clean('0,1,2,3'))
    self.assertEquals([], field.clean(''))
    self.assertEquals([], field.clean(None))
    self.assertRaises(forms.ValidationError, field.clean, '1,2,abc')

  def testClean_float(self):
    field = transaction.CSField(type=float)
    self.assertEquals([0.0, 1.2,2.0,3.0], field.clean('0,1.2,2.0,3'))
    self.assertEquals([], field.clean(''))
    self.assertEquals([], field.clean(None))
    self.assertRaises(forms.ValidationError, field.clean, '1,2,abc')

  def testClean_empty(self):
    field = transaction.CSField(type=int)
    self.assertEquals([], field.clean(',,,,,,,'))
    self.assertEquals([2], field.clean('2,,,,,,,'))
    self.assertEquals([2], field.clean(',,,2,,,,,,,'))
    self.assertEquals([2,3], field.clean('2,,,,,,,3'))

class TestCSInput(unittest.TestCase):

  def testClean_int(self):
    field = transaction.CSInput()
    self.assertEquals('<input type="text" name="myfield" value="1,2,3" />',
        field.render('myfield', ['1','2','3']))
    self.assertEquals('<input type="text" name="myfield" value="1.0,2.0,3.0" />',
        field.render('myfield', ['1.0','2.0','3.0']))
    self.assertEquals('<input type="text" name="myfield" />',
        field.render('myfield', []))
    self.assertEquals('<input type="text" name="myfield" value="0" />',
        field.render('myfield', ['0']))
    self.assertEquals('<input type="text" name="myfield" />',
        field.render('myfield', ['','','']))
    self.assertEquals('<input type="text" name="myfield" />',
        field.render('myfield', [',']))

class TestForm(unittest.TestCase):

  def testClean(self):
    form = transaction.Form()
    form.cleaned_data = {
      'quantity_list': [1,2],
      'price_list': [3,4]
    }

    self.assertEquals(form.cleaned_data, form.clean())

  def testClean_emptyLists(self):
    form = transaction.Form()
    form.cleaned_data = {
      'quantity_list': [],
      'price_list': []
    }

    self.assertEquals(form.cleaned_data, form.clean())

  def testClean_missingPrice(self):
    form = transaction.Form()
    form.cleaned_data = {
      'quantity_list': [1,2],
      'price_list': [3]
    }

    self.assertRaises(forms.ValidationError, form.clean)

