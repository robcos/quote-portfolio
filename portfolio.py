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
from robcos.models import Portfolio
from robcos.models import Position
from robcos.models import Quote
from robcos.models import RealtimeQuote

# Python
import logging
import os
import re
from datetime import date
from datetime import datetime

def fixture(request):
  Position.delete_all()
  Quote.delete_all()
  Portfolio.delete_all()
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
        high=1234.5,
        low=1234.5,
        open=1234.5,
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

def get_portfolios(request):
  portfolios = Portfolio.all()
  show_closed_positions = request.GET.get('show_closed', False) == 'true'
  for p in portfolios:
    p.set_show_closed(show_closed_positions)
  return portfolios

def index(request):
  portfolios = get_portfolios(request)
  currencies = Currency.all()

  if request.method == 'POST':
    form = PositionForm(request.POST)
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = PositionForm()

  return shortcuts.render_to_response('index.html', locals())

def alerts(request):
  body = ''
  for position in Position.all():
    if position.below_stop():
      body += '\n%s in portfolio %s below stop' % (position.symbol, position.portfolio.name)
    if position.below_ll_10():
      body += '\n%s in portfolio %s below ll10' % (position.symbol, position.portfolio.name)
  if len(body) == 0:
    return HttpResponseRedirect('/')

  body = 'The following alerts have been triggered:\n' + body
  body += '\n\nVisit http://quote-portfolio.appspot.com for details.'

  mail.send_mail(sender="robcos@robcos.com",
    to="robcos@robcos.com",
    subject="Portfolio alert",
    body=body)

  return HttpResponseRedirect('/')
  
def edit(request, key):
  portfolios = get_portfolios(request)
  if request.method == 'POST':
    form = PositionForm(request.POST, instance=db.get(key))
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  else:
    form = PositionForm(instance=db.get(key))

  return shortcuts.render_to_response('index.html', locals())

def position(request):
  """ To import positions """
  form = PositionForm(request.GET)
  form.save()
  return HttpResponseRedirect('/')

def cash(request):
  if request.method == 'POST':
    key = request.POST['key']
    cash = float(request.POST['cash'])
    other = float(request.POST['other'])
    nominal_value = float(request.POST['nominal_value'])
    portfolio = db.get(db.Key(key))
    portfolio.cash = cash
    portfolio.other = other
    portfolio.nominal_value = nominal_value
    portfolio.put()
  return HttpResponseRedirect('/')

def quotes(request):  
  symbols = []
  for position in Position.all():
    symbols.append(position.symbol)

  RealtimeQuote.delete_all()
  RealtimeQuote.download_all(symbols)
  
  return redirect(request)

def historical_quotes(request):  
  symbols = []
  for position in Position.all():
    symbols.append(position.symbol)
    start_date = request.GET.get('start_date')
    stop_date = request.GET.get('stop_date')
    if start_date:
      Quote.yahoo(
          position.symbol, 
          start_date=datetime.strptime(start_date, '%Y-%m-%d').date(),
          stop_date=datetime.strptime(stop_date, '%Y-%m-%d').date())
    else:
       Quote.yahoo(position.symbol)
  
  return redirect(request)

def currencies(request):  
  Currency.delete_all()
  Currency.download_all()
  
  return redirect(request)

def redirect(request):
  if request.GET.get('no-redirect'):
    return HttpResponse()
  else:
    return HttpResponseRedirect('/')
