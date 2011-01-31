#!/usr/bin/env python

import urllib
import logging
from datetime import datetime

def download_(url):
    return urllib.urlopen(url).readlines()
 
def convert_date_(from_string):
  from_date = datetime.strptime(from_string, '%d-%b-%y').date()
  return from_date.strftime("%Y-%m-%d")
  #from 10-Jan-11 to 2011-01-10
  return date
   
def get_historical_prices(symbol, start_date, end_date):
    """
    Get historical prices for the given ticker symbol.
    Date format is 'YYYYMMDD'
    
    Returns a nested list.
    """
    url = 'http://ichart.yahoo.com/table.csv?s=%s&' % symbol + \
          'd=%s&' % str(int(end_date[4:6]) - 1) + \
          'e=%s&' % str(int(end_date[6:8])) + \
          'f=%s&' % str(int(end_date[0:4])) + \
          'g=d&' + \
          'a=%s&' % str(int(start_date[4:6]) - 1) + \
          'b=%s&' % str(int(start_date[6:8])) + \
          'c=%s&' % str(int(start_date[0:4])) + \
          'ignore=.csv'
    days = download_(url)
    header = ['Date','Open','High','Low','Close']
    days = [header] + days[1:]
    data = []
    data.append(header)
    for day in days[1:]:
      row = day.split(',')[:-1]
      row[0] = convert_date_(row[0])
      data.append(row)

    return data
