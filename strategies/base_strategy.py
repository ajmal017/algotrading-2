import numpy as np
import statsmodels.api as sm
import pandas as pd

from stocktrends import Renko
from backtest.backtest import Backtest
from datetime import datetime, timedelta


class Strategy(Backtest):
    def __init__(self, dataframe):
        super(Strategy, self).__init__()
        self.dataframe = dataframe.copy()
        self.signal = None
        self.iter = None
        self.entry_price = None
        self.exit_price = None
        self.entry_index = None
        self.exit_index = None

    def setup(self):
        pass

    def teardown(self):
        pass
    
    def average_true_range(self, n, weighted=False, df=None):
        "function to calculate True Range and Average True Range"
        if df is None:
            df = self.dataframe.copy()
        df['H-L'] = abs(df['High'] - df['Low'])
        df['H-PC'] = abs(df['High'] - df['Adj Close'].shift(1))
        df['L-PC'] = abs(df['Low'] - df['Adj Close'].shift(1))
        df['TR'] = df[['H-L', 'H-PC', 'L-PC']].max(axis=1, skipna=False)
        if weighted is False:
            df['ATR'] = df['TR'].rolling(n).mean()
        else:
            df['ATR'] = df['TR'].ewm(span=n, adjust=False, min_periods=n).mean()
        df2 = df.drop(['H-L', 'H-PC', 'L-PC'], axis=1)
        return df2['ATR']
    
    def rolling(self, n=20, weighted=False, dropna=False, df=None):
        if df is None:
            df = self.dataframe
        df["ATR"] = self.average_true_range(n, weighted=weighted, df=df)
        df["roll_max_cp"] = df["High"].rolling(n).max()
        df["roll_min_cp"] = df["Low"].rolling(n).min()
        df["roll_max_vol"] = df["Volume"].rolling(n).max()
        df["rsi"] = self.RSI(DF=df).copy()
        if dropna is True:
            df.dropna(inplace=True)

    def MACD(self, a, b, c):
        # typical values a = 12; b =26, c =9
        df = self.dataframe.copy()
        df["MA_Fast"] = df["Adj Close"].ewm(span=a, min_periods=a).mean()
        df["MA_Slow"] = df["Adj Close"].ewm(span=b, min_periods=b).mean()
        df["MACD"] = df["MA_Fast"] - df["MA_Slow"]
        df["Signal"] = df["MACD"].ewm(span=c, min_periods=c).mean()
        df.dropna(inplace=True)
        return (df["MACD"], df["Signal"])

    def slope(self, ser, n):
        # function to calculate the slope of n consecutive points on a plot
        slopes = [i * 0 for i in range(n - 1)]
        for i in range(n, len(ser) + 1):
            y = ser[i - n:i]
            x = np.array(range(n))
            y_scaled = (y - y.min()) / (y.max() - y.min())
            x_scaled = (x - x.min()) / (x.max() - x.min())
            x_scaled = sm.add_constant(x_scaled)
            model = sm.OLS(y_scaled, x_scaled)
            results = model.fit()
            slopes.append(results.params[-1])
        slope_angle = (np.rad2deg(np.arctan(np.array(slopes))))
        return np.array(slope_angle)

    def renko_bricks(self, atr_period):
        df = self.dataframe.copy()
        df.reset_index(inplace=True)
        df = df.iloc[:, [0, 1, 2, 3, 4, 5]]
        df.columns = ["date", "open", "high", "low", "close", "volume"]
        df2 = Renko(df)
        df2.brick_size = max(0.5, round(self.average_true_range(atr_period)[-1], 0))
        renko_df = df2.get_ohlc_data()
        renko_df["bar_num"] = np.where(renko_df["uptrend"] == True, 1, np.where(renko_df["uptrend"] == False, -1, 0))
        for i in range(1, len(renko_df["bar_num"])):
            if renko_df["bar_num"][i] > 0 and renko_df["bar_num"][i - 1] > 0:
                renko_df["bar_num"].iloc[i] += renko_df["bar_num"].iloc[i - 1]
            elif renko_df["bar_num"][i] < 0 and renko_df["bar_num"][i - 1] < 0:
                renko_df["bar_num"].iloc[i] += renko_df["bar_num"].iloc[i - 1]
        renko_df.drop_duplicates(subset="date", keep="last", inplace=True)
        renko_df["date"] = pd.to_datetime(renko_df["date"])
        return renko_df

    def RSI(self, DF=None, n=14):
        "function to calculate RSI"
        if DF is None:
            df = self.dataframe.copy()
        else:
            df = DF.copy()
        df['delta'] = df['Adj Close'] - df['Adj Close'].shift(1)
        df['gain'] = np.where(df['delta'] >= 0, df['delta'], 0)
        df['loss'] = np.where(df['delta'] < 0, abs(df['delta']), 0)
        avg_gain = []
        avg_loss = []
        gain = df['gain'].tolist()
        loss = df['loss'].tolist()
        for i in range(len(df)):
            if i < n:
                avg_gain.append(np.NaN)
                avg_loss.append(np.NaN)
            elif i == n:
                avg_gain.append(df['gain'].rolling(n).mean().tolist()[n])
                avg_loss.append(df['loss'].rolling(n).mean().tolist()[n])
            elif i > n:
                avg_gain.append(((n - 1) * avg_gain[i - 1] + gain[i]) / n)
                avg_loss.append(((n - 1) * avg_loss[i - 1] + loss[i]) / n)
        df['avg_gain'] = np.array(avg_gain)
        df['avg_loss'] = np.array(avg_loss)
        df['RS'] = df['avg_gain'] / df['avg_loss']
        df['RSI'] = 100 - (100 / (1 + df['RS']))
        return df['RSI']

    def wait_for_signal(self):
        pass

    def enter_buy(self):
        pass

    def exit_buy(self):
        pass

    def enter_sell(self):
        pass

    def exit_sell(self):
        pass

    def open_position(self):
        pass

    def close_position(self):
        pass

    def run(self):
        pass


class SinglePositionBackTest(Strategy):
    def __init__(self, dataframe):
        super(SinglePositionBackTest, self).__init__(dataframe)

    def before_run(self):
        pass

    def after_run(self):
        pass

    def wait_for_signal(self):
        if self.enter_buy() is True:
            self.signal = 'Buy'
        elif self.enter_sell() is True:
            self.signal = 'Sell'

    def run(self):
        for i in range(len(self.dataframe)):
            self.iter = i
            self.before_run()

            if self.signal is None:
                self.wait_for_signal()
                if self.signal is not None:
                    self.open_position()

            elif self.signal == 'Buy':

                if self.exit_buy() is True:
                    if self.close_position() is True:
                        self.signal = None

                elif self.enter_sell() is True:
                    if self.close_position() is True:
                        self.signal = 'Sell'
                        self.open_position()

            elif self.signal == 'Sell':

                if self.exit_sell() is True:
                    if self.close_position() is True:
                        self.signal = None

                elif self.enter_buy() is True:
                    if self.close_position() is True:
                        self.signal = 'Buy'
                        self.open_position()

            self.after_run()


class SinglePosition(Strategy):
    def __init__(self, dataframe):
        super(SinglePosition, self).__init__(dataframe)
        self.last_frame = 0

    def before_run(self):
        pass

    def after_run(self):
        pass

    def close_price_within_limits(self):
        pass

    def wait_for_signal(self):
        if self.enter_buy() is True:
            self.signal = 'Buy'
        elif self.enter_sell() is True:
            self.signal = 'Sell'

    def run(self):
        if self.signal is None:
            self.wait_for_signal()
            if self.signal is not None:
                if self.open_position() is not True:
                    self.signal = None

        elif self.signal == 'Buy':
            enter_sell = self.enter_sell()
            if self.exit_buy() is True or enter_sell is True:
                self.close_position()
                self.signal = None
            if enter_sell is True:
                self.signal = 'Sell'
                if self.open_position() is not True:
                    self.signal = None

        elif self.signal == 'Sell':
            enter_buy = self.enter_buy()
            if self.exit_sell() is True or enter_buy is True:
                self.close_position()
                self.signal = None
            if enter_buy is True:
                self.signal = 'Buy'
                if self.open_position() is not True:
                    self.signal = None

        self.last_frame = len(self.dataframe)

    def time_bound_run(self, seconds):
        start_time = datetime.now()
        lapsed_seconds = 0

        # Run setup
        self.setup()

        # Being run
        while lapsed_seconds <= seconds:
            self.before_run()
            if len(self.dataframe) > self.last_frame:
                self.run()
            self.after_run()
            curr_time = datetime.now()
            lapsed_seconds = curr_time - start_time
            lapsed_seconds = lapsed_seconds.total_seconds()

        # Run teardown
        self.teardown()
