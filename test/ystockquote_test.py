import unittest
import stockquote
from mock import Mock

class TestYstockquote(unittest.TestCase):

  @staticmethod
  def get_yahoo_data():
    return [
    'Date,Open,High,Low,Close,Volume,Adj Close',
    '2011-01-10,338.83,343.23,337.17,342.45,16000400,342.45',
    '2011-01-07,333.99,336.35,331.90,336.12,11096800,336.12',
    '2011-01-06,334.72,335.25,332.90,333.73,10709500,333.73',
    '2011-01-05,329.55,334.34,329.50,334.00,9058700,334.00',
    '2011-01-04,332.44,332.50,328.15,331.29,11038600,331.29',
    '2011-01-03,325.64,330.26,324.84,329.57,15883600,329.57'
    ]

  @staticmethod
  def get_google_data():
    return [
    'Date,Open,High,Low,Close,Volume',
    '10-Jan-11,338.83,343.23,337.17,342.45,16019926',
    '7-Jan-11,333.99,336.35,331.90,336.12,11140316',
    '6-Jan-11,334.72,335.25,332.90,333.73,10729518',
    '5-Jan-11,329.55,334.34,329.50,334.00,9125599',
    '4-Jan-11,332.44,332.50,328.15,331.29,11048143',
    '3-Jan-11,325.64,330.26,324.84,329.57,15897201',
    ]

  def test_get_historical_prices_yahoo(self):
    stockquote.download_ = Mock(return_value=self.get_yahoo_data())

    data = stockquote.get_historical_prices(
        'AAPL', 
        '20100101',
        '20100110')
    self.assertData(data)

  def test_get_historical_prices_google(self):
    stockquote.download_ = Mock(return_value=self.get_google_data())

    data = stockquote.get_historical_prices(
        'LON:AAPL', 
        '20100101',
        '20100110')
    self.assertData(data)


  def assertData(self, data):
    self.assertEquals(7, len(data))
    self.assertEquals(
        ['Date','Open','High','Low','Close'],
        data[0])
    self.assertEquals(['2011-01-10','338.83','343.23','337.17','342.45'], data[1])
    self.assertEquals(['2011-01-07','333.99','336.35','331.90','336.12'], data[2])
    self.assertEquals(['2011-01-06','334.72','335.25','332.90','333.73'], data[3])
    self.assertEquals(['2011-01-05','329.55','334.34','329.50','334.00'], data[4])
    self.assertEquals(['2011-01-04','332.44','332.50','328.15','331.29'], data[5])
    self.assertEquals(['2011-01-03','325.64','330.26','324.84','329.57'], data[6])
 
if __name__ == '__main__':
    unittest.main()
