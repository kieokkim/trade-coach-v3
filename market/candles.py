import json
import logging
import random
from pathlib import Path

from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)

CANDLE_FILE_MAP = {
    "sample_1":     "data/sample_candles.json",
    "sample_2":     "data/sample_candles.json",
    "beginner":     "data/sample_candles_beginner.json",
    "intermediate": "data/sample_candles_intermediate.json",
    "expert":       "data/sample_candles_expert.json",
}

_ROOT = Path(__file__).parent.parent
_sample_candles_cache: dict = {}


def _load_sample_candles_cache(sample_mode: str) -> dict:
    if sample_mode not in _sample_candles_cache:
        rel = CANDLE_FILE_MAP.get(sample_mode, "data/sample_candles.json")
        path = _ROOT / rel
        try:
            _sample_candles_cache[sample_mode] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("sample_candles load failed [%s]: %s", sample_mode, e)
            _sample_candles_cache[sample_mode] = {}
    return _sample_candles_cache[sample_mode]


def _generate_dummy_candles(entry_time_ms: int, limit: int = 50, interval: str = "15") -> list[dict]:
    interval_ms = int(interval) * 60 * 1000
    candles = []
    price = 1000.0
    for i in range(limit):
        ts = entry_time_ms - interval_ms * (limit // 2 - i)
        delta = random.uniform(-0.004, 0.004) * price
        o = round(price, 2)
        c = round(price + delta, 2)
        h = round(max(o, c) + abs(random.uniform(0, 0.002) * price), 2)
        l = round(min(o, c) - abs(random.uniform(0, 0.002) * price), 2)
        candles.append({
            "timestamp": ts,
            "open": o, "high": h, "low": l, "close": c,
            "volume": round(random.uniform(0.5, 50.0), 4),
        })
        price = c
    return candles


def get_candles(
    symbol: str,
    entry_time_ms: int,
    interval: str = "15",
    limit: int = 50,
    order_id: str | None = None,
    sample_mode: str | bool = False,
) -> list[dict]:
    if sample_mode and order_id:
        mode_key = sample_mode if isinstance(sample_mode, str) else "sample_1"
        cache = _load_sample_candles_cache(mode_key)
        if order_id in cache and cache[order_id]:
            logger.info("get_candles: sample cache hit | order_id=%s mode=%s", order_id, mode_key)
            return cache[order_id]
        logger.warning("get_candles: sample cache miss | order_id=%s mode=%s", order_id, mode_key)
        return _generate_dummy_candles(entry_time_ms, limit, interval)

    start = entry_time_ms - (int(interval) * 60 * 1000 * (limit // 2))
    session = HTTP(testnet=False)
    logger.info("Fetching kline: symbol=%s interval=%s limit=%d start=%d", symbol, interval, limit, start)

    try:
        response = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=interval,
            start=start,
            limit=limit,
        )
        candles = [
            {
                "timestamp": int(c[0]),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
            }
            for c in response["result"]["list"]
        ]
        candles.sort(key=lambda x: x["timestamp"])
        logger.info("Retrieved %d candles for %s", len(candles), symbol)
        return candles
    except Exception as e:
        logger.warning("get_candles: API failed: %s", e)
        return _generate_dummy_candles(entry_time_ms, limit, interval)
