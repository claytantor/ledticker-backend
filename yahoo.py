import sys
from yahoo_finance_api2 import share
from yahoo_finance_api2.exceptions import YahooFinanceError

my_share = share.Share('SPY')
symbol_data = None

try:
    symbol_data = my_share.get_historical(share.PERIOD_TYPE_DAY,
                                          1,
                                          share.FREQUENCY_TYPE_MINUTE,
                                          30)
except YahooFinanceError as e:
    print(e.message)
    sys.exit(1)

print(symbol_data)
