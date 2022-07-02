
import numpy as np
import pandas as pd
import sqlalchemy
from binance.client import Client
from binance.enums import HistoricalKlinesType
import plotly.express as px

def klines_to_dataframe(klines):
        df = pd.DataFrame(np.array(klines).reshape(-1,12), dtype=float, columns = ('open_time',
                                            'open',
                                            'high',
                                            'low',
                                            'close',
                                            'volume',
                                            'close_time',#close time
                                            'quote_asset_volume',
                                            'number_of_trades',
                                            'taker_buy_base_asset_volume',
                                            'taker_buy_quote_asset_volume',
                                            'ignore'))
        
        df = pd.DataFrame({
            'time': df['close_time'],
            'open': df['open'],
            'high': df['high'],
            'low': df['low'],
            'close': df['close'],
            'volume': df['volume']
        })
        
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df.index = df.time
        return df

key = "4hujbcxhNKoPNdev14IJpMKAGEPZigP98rfmngim76kaVUqZijpsw7gk1s04Si8N"
secret = "UbLKzMvbkd1cvr5ec4HArGFlHCL5Q46hC7KNmeWDGK4PqIO7gnxGdxGKrsRFJ57w"

client = Client(key, secret)

klines = client.get_historical_klines("ETHBUSD", Client.KLINE_INTERVAL_1MINUTE, limit=10, klines_type=HistoricalKlinesType.SPOT)
df = klines_to_dataframe(klines)
fig = px.line(df, x='time', y='close', title="ETHBUSD" + ' - Close Prices')  # creating a figure using px.line
fig.write_image("zfig.png")
print(df)