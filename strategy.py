import pandas as pd
import ta
import ta.trend

def create_dataframe(bar_data_list: list):
    data = {
        "Date": [bar.date for bar in bar_data_list],
        "Open": [bar.open for bar in bar_data_list],
        "High": [bar.high for bar in bar_data_list],
        "Low": [bar.low for bar in bar_data_list],
        "Close": [bar.close for bar in bar_data_list],
        "Volume": [bar.volume for bar in bar_data_list],
        "Average": [bar.average for bar in bar_data_list],
        "BarCount": [bar.barCount for bar in bar_data_list]
    }
    df = pd.DataFrame(data)
    df = ta.add_trend_ta(df, high='High', low='Low', close='Close', fillna=True)
    return df

def simple_trading_strategy(bar_data_list: list):
    bar_data = create_dataframe(bar_data_list)

    signals = pd.DataFrame(index=bar_data.index)
    
    signals['Buy Signal'] = (bar_data['trend_sma_fast'] > bar_data['trend_sma_slow']) & (bar_data['trend_sma_fast'].shift(1) <= bar_data['trend_sma_slow'].shift(1))
    signals['Sell_Signal'] = (bar_data['trend_sma_fast'] < bar_data['trend_sma_slow']) & (bar_data['trend_sma_fast'].shift(1) >= bar_data['trend_sma_slow'].shift(1))
    signals['Position'] = 0
    signals.loc[signals['Buy_Signal'], 'Position'] = 1
    signals.loc[signals['Sell_Signal'], 'Position'] = -1
    return signals