#!/usr/bin/python2.4
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""A special handler file for rendering template files of various types."""

# AppEngine
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from django.template import TemplateDoesNotExist
from google.appengine.api import mail

import os

from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

import django
from django import http
from django import shortcuts
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound
from django.forms import ModelForm
from django.forms import ValidationError

# robcos
from robcos.models import Currency
from robcos.transaction import APortfolio
from robcos.transaction import ATransaction
from robcos.models import Position
from robcos.models import Quote
from robcos.models import RealtimeQuote

# Python
import logging
import os
import re
from datetime import date
from datetime import datetime

import common
from django import forms

class CSField(forms.Field):
  
  def __init__(self, *args, **kwargs):
    self.type = kwargs['type']
    del kwargs['type']
    forms.Field.__init__(self, *args, **kwargs)

  def clean(self, value):
    if value:
      try:
        list = filter(lambda x: len(x), value.split(','))
        return map(lambda x: self.type(x), list)
      except ValueError:
        raise forms.ValidationError('Could not parse %s' % value)
    return []

class CSInput(forms.widgets.TextInput):

    def render(self, name, value, attrs=None):
        if value:
          value = map(lambda x: str(x), value)
          list = filter(lambda x: len(x) and x is not ',', value)
          value = ','.join(list)
        else:
          value = ''
        return super(forms.widgets.TextInput, self).render(name, value, attrs)


class Form(ModelForm):
  quantity_list = CSField(type=int, widget=CSInput)
  price_list = CSField(type=float, widget=CSInput)

  class Meta:
    model = ATransaction

  def clean(self):
    cleaned_data = self.cleaned_data
    quantity_list = cleaned_data.get('quantity_list')
    price_list = cleaned_data.get('price_list')
    if price_list and quantity_list:
      if len(price_list) != len(quantity_list):
        raise forms.ValidationError('Quantity list must match price list')
    return cleaned_data


def update(request, key):
  """ To store transactions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    transaction_form = Form(request.POST, instance=db.get(db.Key(key)))
    if transaction_form.is_valid():
      transaction_form.save()
      return HttpResponseRedirect('/')
  if request.method == 'DELETE':
    db.get(db.Key(key)).delete()
    return HttpResponseRedirect('/')
  else:
    transaction_form = Form(instance=db.get(db.Key(key)))
  
  return shortcuts.render_to_response('index.html', locals())

def create(request):
  """ To store transactions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    transaction_form = Form(request.POST)
    if transaction_form.is_valid():
      model = transaction_form.save()
      return HttpResponseRedirect('/')
  else:
    transaction_form = Form()

  return shortcuts.render_to_response('index.html', locals())
