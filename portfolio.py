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

# robcos
from robcos.models import Portfolio
from robcos.models import Position

# Python
import logging
import os
import re
import datetime

def fixture(request):
  Position.delete_all()
  Portfolio.delete_all()
  avanza = Portfolio(name='Avanza', currency='SEK').save()
  Portfolio(name='XO', currency='GBP').save()
  Position(symbol='AAPL', 
        currency='SEK', 
        currency_rate=1.0, 
        enter_date=datetime.date(2001, 1, 3),
        enter_price=5000.0, 
        enter_commission=99.0, 
        shares=1000.0, 
        portfolio=avanza).save()

  return shortcuts.render_to_response('index.html', {
  })

def index(request):
  portfolios = Portfolio.all()
  #for portfolio in portfolios:
    #portfolio.positions = portfolio.get_positions().fetch(10)
  #  print portfolio.positions

  return shortcuts.render_to_response('index.html', {
    'portfolios': portfolios
  })
