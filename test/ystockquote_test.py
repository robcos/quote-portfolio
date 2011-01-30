import unittest
import ystockquote
from mock import Mock

class TestYstockquote(unittest.TestCase):

  def test_get_historical_prices(self):
    ystockquote.download_ = Mock(
      return_value=[
      'Date,Open,High,Low,Close,Volume,Adj Close',
      '2010-01-08,210.30,212.00,209.06,211.98,15986100,211.98',
      '2010-01-07,211.75,212.00,209.05,210.58,17040400,210.58',
      '2010-01-06,214.38,215.23,210.75,210.97,19720000,210.97',
      '2010-01-05,214.60,215.59,213.25,214.38,21496600,214.38',
      '2010-01-04,213.43,214.50,212.38,214.01,17633200,214.01'])

    data = ystockquote.get_historical_prices(
        'AAPL', 
        '20100101',
        '20100110')
    self.assertEquals(6, len(data))
    self.assertEquals(
        ['Date','Open','High','Low','Close','Volume','Adj Close'],
        data[0])
    self.assertEquals(
        ['2010-01-08','210.30','212.00','209.06','211.98','15986100','211.98'],
        data[1])


if __name__ == '__main__':
    unittest.main()
