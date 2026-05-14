import logging
from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)


def get_candles(
    symbol: str,
    entry_time_ms: int,
    interval: str = "15",
    limit: int = 50,
) -> list[dict]:
    start = entry_time_ms - (int(interval) * 60 * 1000 * (limit // 2))

    session = HTTP(testnet=False)

    logger.info("Fetching kline: symbol=%s interval=%s limit=%d start=%d", symbol, interval, limit, start)

    response = session.get_kline(
        category="linear",
        symbol=symbol,
        interval=interval,
        start=start,
        limit=limit,
    )

    raw = response["result"]["list"]

    candles = [
        {
            "timestamp": int(c[0]),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5]),
        }
        for c in raw
    ]

    candles.sort(key=lambda x: x["timestamp"])

    logger.info("Retrieved %d candles for %s", len(candles), symbol)

    return candles
