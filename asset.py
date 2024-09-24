from datetime import datetime, timedelta

from yfinance import Ticker
from pandas import DataFrame, to_datetime
from numpy import datetime64

class Asset:

    def __init__(self, name: str, cache_history: bool = True, days_before: int = 30):
        self.asset = Ticker(name)
        self.cache_history = cache_history
        self.days_before = days_before
        self.history = None

    def get_history(self):
        if self.cache_history:
            if self.history is not None:
                return self.history

        start_date = datetime.now() - timedelta(days=self.days_before)
        history = self.asset.history(start=start_date, rounding=True).reset_index()
        self._transform_history(history)

        if self.cache_history:
            self.history = history

        return history

    def update_history(self):
        if not self.cache_history:
            return

        self.history = None
        self.get_history()

    def get_trend_price(self):
        data = (self.get_history()
                .filter(items=['date', 'open', 'close'])
                .assign(diff_percentage=lambda x: round((100 - (x['close'] * 100) / x['open']), 2) * -1)
                .assign(diff_sum=lambda x: round(x['diff_percentage'].sum(), 2))
        )
        self._add_percentage(data, columns=['diff_percentage', 'diff_sum'])

        return data

    def get_moving_mean(self):
        return (self.get_history()
                .filter(items=['date', 'close'])
                .assign(mean=lambda x: round(x['close'].mean(), 2))
                .assign(above_average=lambda x: x['close'] >= x['mean'])
        )

    def get_standart_deviation(self):
        return (self.get_history()
                .filter(items=['date','close'])
                .assign(standart_deviante=lambda x: x['close'].std())
        )

    def _classify_situation(self, close, superior, inferior):
        if close > superior:
            return 'Overvalued'
        elif close < inferior:
            return 'Undervalued'
        else:
            return 'Normal'

    def get_outlier_bollinger_band_check(self):
        data = self.get_history().filter(items=['date', 'open', 'close', 'volume'])
        bollinger_superior = data['close'].mean() + (2 * data['close'].std())
        bollinger_inferior = data['close'].mean() - (2 * data['close'].std())

        data['situation'] = data.apply(lambda row: self._classify_situation(row['close'], bollinger_superior, bollinger_inferior), axis=1)

        return data
    
    def get_sharpe_ratio(self):

        if self.days_before % 365 != 0 and self.days_before % 366 != 0:
            print(f'Você só pode obter o índice sharpe atualmente em períodos anuais.')
            return

        df = (self.get_history()
              .filter(items=['date', 'close'])
              .assign(daily_return=lambda x: round(x['close'].pct_change(), 6))
        )

        monthly_return = DataFrame(df.groupby(df['date'].dt.month)['daily_return'].sum()).reset_index()
        std = monthly_return['daily_return'].std()

        monthly_return['accumulated_return'] = (1 + monthly_return['daily_return']).cumprod() - 1
        accumulated_return = (monthly_return.tail(1)['accumulated_return']).item()
        sharpe_ratio = (accumulated_return - 0.1375) / std

        return round(sharpe_ratio, 2)

    def _transform_history(self, history):
        history.columns = history.columns.str.lower()

        date_object = history['date'].dtype != datetime64
        if date_object:
            history['date'] = to_datetime(history['date'])

        history['date'] = to_datetime(history['date'].dt.strftime('%Y-%m-%d'))

    def _add_percentage(self, data_frame: DataFrame, columns: list[str]):
        for column in columns:
            data_frame[column] = data_frame[column].astype(str) + '%'
