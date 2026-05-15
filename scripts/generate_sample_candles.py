"""sample_trades_1/2.json의 Buy 거래 캔들을 미리 수집해 data/sample_candles.json에 저장.

샘플 모드에서 Bybit API를 호출하지 않고 사전 생성 캔들을 사용하기 위한 1회성 스크립트.
"""
import json
import random
from pathlib import Path

from pybit.unified_trading import HTTP

TRADES = [
    {"order_id": "random-1-buy",     "symbol": "BTCUSDT", "exec_time_ms": 1775030400000},
    {"order_id": "fvg-1-buy",        "symbol": "BTCUSDT", "exec_time_ms": 1775124000000},
    {"order_id": "ob-1-buy",         "symbol": "ETHUSDT", "exec_time_ms": 1775206800000},
    {"order_id": "random-2-buy",     "symbol": "BTCUSDT", "exec_time_ms": 1775300400000},
    {"order_id": "sweep-1-buy",      "symbol": "BTCUSDT", "exec_time_ms": 1775376000000},
    {"order_id": "random-3-buy",     "symbol": "ETHUSDT", "exec_time_ms": 1775466000000},
    {"order_id": "fvg-2-buy",        "symbol": "SOLUSDT", "exec_time_ms": 1775556000000},
    {"order_id": "ob-2-buy",         "symbol": "BTCUSDT", "exec_time_ms": 1775638800000},
    {"order_id": "random-new-1-buy", "symbol": "BTCUSDT", "exec_time_ms": 1775728800000},
    {"order_id": "random-new-2-buy", "symbol": "BTCUSDT", "exec_time_ms": 1775757600000},
    {"order_id": "random-new-3-buy", "symbol": "ETHUSDT", "exec_time_ms": 1775811600000},
]

INTERVAL = "15"
LIMIT = 50

_BASE_PRICES = {"BTCUSDT": 65000.0, "ETHUSDT": 1800.0, "SOLUSDT": 145.0}


def _generate_dummy_candles(symbol: str, entry_time_ms: int, limit: int = LIMIT) -> list[dict]:
    """Bybit API 실패 시 사용하는 가상 캔들 데이터."""
    interval_ms = int(INTERVAL) * 60 * 1000
    base = _BASE_PRICES.get(symbol, 1000.0)
    candles = []
    price = base * random.uniform(0.97, 1.03)
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


def fetch_candles(symbol: str, entry_time_ms: int) -> list[dict]:
    session = HTTP(testnet=False)
    start = entry_time_ms - (int(INTERVAL) * 60 * 1000 * (LIMIT // 2))
    try:
        resp = session.get_kline(
            category="linear",
            symbol=symbol,
            interval=INTERVAL,
            start=start,
            limit=LIMIT,
        )
        candles = []
        for row in resp["result"]["list"]:
            candles.append({
                "timestamp": int(row[0]),
                "open":   float(row[1]),
                "high":   float(row[2]),
                "low":    float(row[3]),
                "close":  float(row[4]),
                "volume": float(row[5]),
            })
        candles.sort(key=lambda x: x["timestamp"])
        return candles
    except Exception as e:
        print(f"  API 실패: {e}")
        return []


if __name__ == "__main__":
    result = {}
    for trade in TRADES:
        print(f"수집 중: {trade['order_id']} ({trade['symbol']})")
        candles = fetch_candles(trade["symbol"], trade["exec_time_ms"])
        if candles:
            print(f"  → {len(candles)}개 수집 완료 (Bybit API)")
        else:
            candles = _generate_dummy_candles(trade["symbol"], trade["exec_time_ms"])
            print(f"  → {len(candles)}개 더미 생성 (API 없음)")
        result[trade["order_id"]] = candles

    output_path = Path(__file__).parent.parent / "data" / "sample_candles.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장 완료: {output_path}")
    print(f"총 {len(result)}개 거래 캔들 저장됨")
