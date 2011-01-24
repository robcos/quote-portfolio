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
  
  def __init__(self, type=int):
    forms.Field.__init__(self)
    self.type = type

  def clean(self, value):
    if value:
      try:
        return map(lambda x: self.type(x), value.split(','))
      except ValueError:
        raise forms.ValidationError('Could not parse %s' % value)
    return []

class Form(ModelForm):
  quantity_list = CSField(type=int)
  price_list = CSField(type=float)

  class Meta:
    model = ATransaction

def update(request, key):
  """ To store transactions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    form = Form(request.POST, instance=db.get(db.Key(key)))
    model = form.save(commit=False)
    if form.is_valid():
      form.save()
      return HttpResponseRedirect('/')
  if request.method == 'DELETE':
    db.get(db.Key(key)).delete()
    return HttpResponseRedirect('/')
  else:
    form = Form(instance=db.get(db.Key(key)))
  
  return shortcuts.render_to_response('index.html', locals())

def create(request):
  """ To store transactions """
  portfolios = common.get_portfolios(request)
  if request.method == 'POST':
    form = Form(request.POST)
    if form.is_valid():
      model = form.save()
      return HttpResponseRedirect('/')
  else:
    form = Form()

  return shortcuts.render_to_response('index.html', locals())
