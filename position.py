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
from robcos.transaction import APosition
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

class PositionForm(ModelForm):
  class Meta:
    model = APosition

def update(request, key):
  """ To store positions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    form = PositionForm(request.POST, instance=db.get(db.Key(key)))
    if form.is_valid():
      model = form.save()
      return HttpResponseRedirect('/')
  if request.method == 'DELETE':
    db.get(db.Key(key)).delete()
    return HttpResponseRedirect('/')
  else:
    form = PositionForm(instance=db.get(db.Key(key)))
  
  return shortcuts.render_to_response('index.html', locals())

def create(request):
  """ To store positions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    form = PositionForm(request.POST)
    if form.is_valid():
      model = form.save()
      return HttpResponseRedirect('/')
  else:
    form = Form()

  return shortcuts.render_to_response('index.html', locals())
