import bitmex
import sqlite3
from indicator.base_symbol import Symbol
import pandas as pd
from strategies.res_brkout import ResistanceBreakoutBackTest, ResistanceBreakout


class BitMEXSymbol(Symbol):
    def __init__(self, *args, **kwargs):
        self.client = kwargs.pop('client')
        super(BitMEXSymbol, self).__init__(*args, **kwargs)

    def data_to_df(self, data):
        dataframe = pd.DataFrame(data)
        df1 = dataframe[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        df1.rename(columns={"timestamp": "Datetime", "open": "Open", "high": "High", "low": "Low", "close": "Adj Close",
                            "volume": "Volume"}, inplace=True)
        df1.set_index('Datetime', inplace=True)
        return df1

    def fetch_data(self, start_time, count=1000):
        if type(start_time) is not str:
            start_time = start_time.strftime("%Y-%m-%d %H:%M")
        filter = '{"symbol": "%s", "startTime": "%s"}' % (self.symbol, start_time)
        data, response = self.client.Trade.Trade_getBucketed(binSize=self.frequency, count=count,
                                                                  filter=filter).result()
        if response.status_code != 200:
            print("Error fetching BitMEX data")
            print("Response code: {}".format(response.status_code))
            print("Reason: {}".format(response.reason))
            print("Text: {}".format(response.text))
            return None

        return self.data_to_df(data)


def sample(key, secret):
    db = '/Users/jganesan/workspace/algotrading/symbols.sqlite3'
    conn = sqlite3.connect(db)
    key = "UzlrFYMJJGo_A7QDihj3ZtY8"
    secret = "LuA5rSvqLGDghJ8A-6ZtDEgahvbIroqFPpRdKd-uI3DPSXQG"
    symbol = 'XBTUSD'
    frequency = '5m'
    client = bitmex.bitmex(api_key=key, api_secret=secret)
    xbt = BitMEXSymbol(symbol, conn=conn, client=client, frequency=frequency)
    df1 = xbt.fetch_data()
    xbt.write_to_db(df1)
    df = xbt.read_from_db()
    conn.close()

    s = ResistanceBreakoutBackTest(df)
    s.weighted = False
    s.rolling_period = 10
    s.min_profit = 13.5
    s.setup()
    s.run()

    sum = 0
    for r in s.returns:
        sum += r[-1] - 13.5