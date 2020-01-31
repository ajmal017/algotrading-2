import pandas as pd
import sys
import json
from dateutil.tz import tzutc
from datetime import datetime, timedelta
from exchanges.BitMEX.bitmex_symbol import BitMEXSymbol
from strategies.res_brkout import ResistanceBreakoutBackTest, ResistanceBreakoutParentChildBackTest
from strategies.renko_macd import RenkoMACDBackTest
from exchanges.BitMEX.rest_client import RestClient
from time import sleep


def import_data(symbol, file_name):
    fp = open(file_name, 'r')
    data = [eval(d.replace('datetime.datetime', 'datetime')) for d in fp.readlines()]
    fp.close()
    df = symbol.data_to_df(data)
    return df

def renkomacd_backtest(key, secret, product, frequency):
    client = RestClient(False, key, secret, product)
    symbol = BitMEXSymbol(product, client=client, frequency=frequency)
    # dataframe = pd.DataFrame(symbol.fetch_data(datetime.utcnow() - timedelta(days=365)))
    dataframe = import_data(symbol, 'XBTUSD_5m_100days.txt')
    backtest = RenkoMACDBackTest(dataframe)
    # backtest.atr_period = 60
    # backtest.slope_period = 3
    # backtest.macd_array = (6, 15, 6)
    backtest.min_profit = 0
    backtest.min_loss = 0
    backtest.setup()
    backtest.run()

    sum = 0
    trades = []
    time_series = backtest.dataframe.index.tolist()
    max_loss = 0
    max_loss_frame = None
    loss_frames = []
    for r in backtest.returns:
        sum += max(-200, r[2]) - 14.5
        open_frame = backtest.dataframe.iloc[r[0]]
        open_time = time_series[r[0]]
        close_frame = backtest.dataframe.iloc[r[1]]
        close_time = time_series[r[1]]
        frame = backtest.dataframe.iloc[r[0]:r[1] + 1]
        trades.append((open_time, open_frame['Adj Close'], close_time, close_frame['Adj Close'], r[2]))
        if r[2] < max_loss:
            max_loss_frame = frame
            max_loss = r[2]
        if r[2] < 0:
            loss_frames.append((r[5], r[3], r[4], r[2], frame))

    print(sum)
    return backtest

def resbrk_backtest(key, secret, product, frequency):
    client = RestClient(False, key, secret, product)
    symbol = BitMEXSymbol(product, client=client, frequency=frequency)
    # dataframe = pd.DataFrame(symbol.fetch_data(datetime.utcnow() - timedelta(days=3)))
    # dataframe = import_data(symbol, 'XBTUSD_1h_365days.txt')
    fp = open('XBTUSD_5m_100days.txt', 'r')
    data = [eval(d.replace('datetime.datetime', 'datetime')) for d in fp.readlines()]
    fp.close()
    dataframe = symbol.fetch_data(datetime.utcnow(), data=data)
    res_bro = ResistanceBreakoutBackTest(dataframe)
    # res_bro.weighted = False
    res_bro.rolling_period = 40
    res_bro.min_profit = 15
    res_bro.min_loss = -75
    res_bro.volume_factor = 3.5
    res_bro.setup()
    res_bro.run()

    sum = 0
    trades = []
    time_series = res_bro.dataframe.index.tolist()
    max_loss = 0
    max_loss_frame = None
    loss_frames = []
    for r in res_bro.returns:
        sum += max(-200, r[2]) - 14.5
        open_frame = res_bro.dataframe.iloc[r[0]]
        open_time = time_series[r[0]]
        close_frame = res_bro.dataframe.iloc[r[1]]
        close_time = time_series[r[1]]
        frame = res_bro.dataframe.iloc[r[0]:r[1]+1]
        trades.append((open_time, open_frame['Adj Close'], close_time, close_frame['Adj Close'], r[2]))
        if r[2] < max_loss:
            max_loss_frame = frame
            max_loss = r[2]
        if r[2] < 0:
            loss_frames.append((r[5], r[3], r[4], r[2], frame))


    print(sum)
    return res_bro

def resbrk_parentchild(key, secret, product, frequency, child_frequency='5m'):
    client = RestClient(False, key, secret, product)
    symbol = BitMEXSymbol(product, client=client, frequency=frequency)

    fp = open('XBTUSD_1h_365days.txt', 'r')
    data = [eval(d.replace('datetime.datetime', 'datetime')) for d in fp.readlines()]
    fp.close()
    parent_dataframe = symbol.fetch_data(datetime.utcnow(), data=data, frequency=frequency)

    fp = open('XBTUSD_5m_100days.txt', 'r')
    data = [eval(d.replace('datetime.datetime', 'datetime')) for d in fp.readlines()]
    fp.close()
    child_dataframe = symbol.fetch_data(datetime.utcnow(), data=data, frequency=child_frequency)

    # parent_dataframe = import_data(symbol, "XBTUSD_1h_365days.txt")
    bt = ResistanceBreakoutParentChildBackTest(parent_dataframe.iloc[-1 * 24 * 90:], child_dataframe, frequency, child_frequency=child_frequency)
    bt.rolling_period = 30
    bt.min_profit = 100
    bt.min_loss = -150
    bt.volume_factor = 1
    bt.max_loss = -150
    bt.setup()
    bt.run()

    sum = 0
    trades = []
    for r in bt.returns:
        signal, entry_p, exit_p, net, best_price = r
        if net < 0:
            if signal == 'Buy' and best_price > entry_p + bt.min_profit:
                net = (best_price - entry_p) / 2
            elif signal == 'Sell' and best_price < entry_p - bt.min_profit:
                net = (entry_p - best_price) / 2
            net = max(bt.max_loss, net)
        sum += net - 14.5
        trades.append((signal, entry_p, exit_p, net, best_price))
    return bt


def combo():
    atr_range = (20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120)
    combo = []
    fp = open('combo.txt', 'w')
    for atr in atr_range:
        for slow_ma in range(2, 27):
            for fast_ma in range(1, int(slow_ma / 2)):
                for avg in range(fast_ma, int(slow_ma / 2)):
                    for slope in range(2, avg):
                        macd_array = (fast_ma, slow_ma, avg)
                        combo.append((atr, slope, macd_array))
                        fp.write("%s\n" % str(combo[-1]))
    fp.close()
    sys.exit(0)


def dump_history():
    frequency = '1m'
    days_before = 365 * 3
    key = 'VvD5-fMBfiZ9dlMtXP2pffHj'
    secret = 'jROi3UZ5q_hkVW2RnK3xbCQEnTzpLXcnbOdUCJTnQFrrdUgj'
    symbol = 'XBTUSD'
    file_name = "%s_%s_%sdays.txt" % (symbol, frequency, days_before)
    file_name = 'temp.txt'
    client = RestClient(False, key, secret, symbol)

    fp = open(file_name, 'w')
    start_time = datetime.utcnow() - timedelta(days=days_before)
    start_time = datetime(2020, 1, 29, 8, 57, tzinfo=tzutc())
    wanted_ones = ['open', 'close', 'low', 'high', 'volume', 'timestamp']
    while True:
        start_time = start_time.strftime("%Y-%m-%d %H:%M")
        filter = '{"symbol": "%s", "startTime": "%s"}' % (symbol, start_time)
        temp = client.trade_bucket(binSize=frequency, count=1000, filter=filter)
        ohlc = []
        for t in temp:
            d = {k: t[k] for k in wanted_ones}
            ohlc.append(str(d))
        sleep(2)
        fp.write('\n'.join(ohlc))
        fp.write('\n')
        if len(temp) < 1000:
            break
        start_time = temp[-1]['timestamp'] + timedelta(minutes=1)
        pass
    fp.close()



if __name__ == '__main__':
    with open("config.json", 'r') as f:
        data = json.load(f)

    params = data['prod']
    key = params['key']
    secret = params['secret']
    product = params['symbol']
    frequency = '1h'
    btc = resbrk_parentchild(key, secret, product, frequency)
