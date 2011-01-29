# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from django.conf.urls.defaults import *
# Tests don't run without this import (?)
from mock import Mock

urlpatterns = patterns(
    '',
    (r'^$', 'portfolio.index'),
    (r'^download/quotes$', 'portfolio.quotes'),
    (r'^download/historical_quotes$', 'portfolio.historical_quotes'),
    (r'^download/currencies$', 'portfolio.currencies'),
    (r'^alerts$', 'portfolio.alerts'),
    (r'^position/(?P<key>[a-zA-Z0-9-_]+)$', 'position.update'),
    (r'^position/$', 'position.create'),
    (r'^transaction/(?P<key>[a-zA-Z0-9-_]+)/json$', 'transaction.json'),
    (r'^transaction/(?P<key>[a-zA-Z0-9-_]+)$', 'transaction.update'),
    (r'^transaction/$', 'transaction.create'),
    (r'^cash$', 'portfolio.cash'),
    ('fixture.html', 'portfolio.fixture'),
    (r'^test', include('gaeunit.urls')),
    )
