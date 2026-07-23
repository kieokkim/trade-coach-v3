import json
import logging
import os
import random
from pathlib import Path

from market.bybit_client import BybitClient
from market.upbit_client import UpbitClient

logger = logging.getLogger(__name__)


class CandleFetchError(Exception):
    """캔들 조회가 (진짜) 실패했을 때 — API 키 없음/네트워크 예외 등.
    정상 조회했으나 0건인 경우와 구분하기 위한 전용 예외."""


def normalize_exec_time(exec_ms: int, interval_min: int = 15) -> int:
    """execTime을 해당 캔들 시작 타임스탬프로 정규화."""
    interval_ms = interval_min * 60 * 1000
    return (exec_ms // interval_ms) * interval_ms


def validate_price_in_candle(
    price: float,
    candles: list[dict],
    exec_ms: int,
    interval_min: int = 15,
) -> dict:
    """execPrice가 해당 캔들 범위 안에 있는지 검증."""
    candle_start = normalize_exec_time(exec_ms, interval_min)
    matched = [c for c in candles if c["timestamp"] == candle_start]

    if not matched:
        matched = sorted(candles, key=lambda x: abs(x["timestamp"] - exec_ms))[:1]

    if not matched:
        return {"valid": False, "candle_low": 0.0, "candle_high": 0.0, "warning": "캔들 없음"}

    c = matched[0]
    low, high = float(c["low"]), float(c["high"])
    valid = low <= price <= high

    return {
        "valid":       valid,
        "candle_low":  low,
        "candle_high": high,
        "warning":     "" if valid else f"슬리피지 감지: {price:.2f} (캔들 범위 {low:.2f}~{high:.2f})",
    }


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
    exchange: str = "Bybit",
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
    logger.info("Fetching kline: symbol=%s interval=%s limit=%d start=%d exchange=%s",
                symbol, interval, limit, start, exchange)

    client = _get_candle_client(exchange)
    if client is None:
        logger.warning("get_candles: %s API 키 없음 — real fetch 불가", exchange)
        if sample_mode:
            return _generate_dummy_candles(entry_time_ms, limit, interval)
        raise CandleFetchError(f"{exchange} API 키가 설정되지 않았습니다.")

    try:
        candles = client.fetch_candles(symbol, interval, start, limit)
    except Exception as e:
        logger.warning("get_candles: %s fetch_candles 실패 | symbol=%s: %s", exchange, symbol, e)
        if sample_mode:
            return _generate_dummy_candles(entry_time_ms, limit, interval)
        raise CandleFetchError(f"{exchange} 캔들 조회 실패: {e}") from e

    if not candles:
        logger.info("get_candles: %s 정상 응답, 캔들 0건 | symbol=%s", exchange, symbol)

    return candles


def _get_candle_client(exchange: str):
    if exchange == "Upbit":
        access_key = os.getenv("UPBIT_ACCESS_KEY", "")
        secret_key = os.getenv("UPBIT_SECRET_KEY", "")
        if not (access_key and secret_key):
            return None
        return UpbitClient(access_key, secret_key)

    api_key = os.getenv("BYBIT_API_KEY", "")
    api_secret = os.getenv("BYBIT_API_SECRET", "")
    if not (api_key and api_secret):
        return None
    return BybitClient(api_key, api_secret)
