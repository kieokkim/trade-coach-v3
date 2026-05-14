import logging

logging.basicConfig(level=logging.INFO)

from market.candles import get_candles
from data.sample_trades import get_sample_trade

trade = get_sample_trade()
symbol = trade["symbol"]
entry_time_ms = int(trade["execTime"])

print(f"심볼: {symbol}, 진입시각(ms): {entry_time_ms}")
candles = get_candles(symbol, entry_time_ms, interval="15", limit=50)
print(f"캔들 수: {len(candles)}")
print(f"첫 캔들: {candles[0]}")
print(f"마지막 캔들: {candles[-1]}")
