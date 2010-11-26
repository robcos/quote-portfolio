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

import os

from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

import django
from django import http
from django import shortcuts
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound
from django.forms import ModelForm
from django.forms import ValidationError

# robcos
from robcos.models import Portfolio
from robcos.models import Position
from robcos.models import Quote
from robcos.models import RealtimeQuote

# Python
import logging
import os
import re
from datetime import date

def fixture(request):
  Portfolio.delete_all()
  Position.delete_all()
  Quote.delete_all()
  avanza = Portfolio(name='Avanza', currency='SEK').save()
  Portfolio(name='XO', currency='GBP').save()
  Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=date.today(),
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=avanza).save()
  Quote(symbol='AAPL', 
        close=1234.5,
        date=date.today()).save()

  return HttpResponseRedirect('/')

class PositionForm(ModelForm):
  class Meta:
    model = Position

  def clean(self):
    portfolio = self.cleaned_data.get('portfolio', '')
    symbol = self.cleaned_data.get('symbol', '')
    enter_date = self.cleaned_data.get('enter_date', None)
    if self.instance:
      return self.cleaned_data
    if Position.load(symbol=symbol, enter_date=enter_date, portfolio=portfolio):
      raise ValidationError('There is already a position for %s on %s' % (symbol, enter_date))
    return self.cleaned_data

def index(request):
  portfolios = Portfolio.all()

  if request.method == 'POST':
    form = PositionForm(request.POST)
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = PositionForm()

  return shortcuts.render_to_response('index.html', locals())

def edit(request, key):
  portfolios = Portfolio.all()
  if request.method == 'POST':
    form = PositionForm(request.POST, instance=db.get(key))
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = PositionForm(instance=db.get(key))

  return shortcuts.render_to_response('index.html', locals())
