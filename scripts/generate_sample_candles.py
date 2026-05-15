"""샘플 거래 파일(beginner/intermediate/expert)에서 Buy 거래를 추출해
각 레벨별 캔들 파일을 data/sample_candles_{level}.json 에 저장하는 1회성 스크립트.
"""
import json
import random
from pathlib import Path

from pybit.unified_trading import HTTP

SAMPLE_FILES = {
    "beginner":     "data/sample_trades_beginner.json",
    "intermediate": "data/sample_trades_intermediate.json",
    "expert":       "data/sample_trades_expert.json",
}

INTERVAL = "15"
LIMIT = 50

_BASE_PRICES = {"BTCUSDT": 83000.0, "ETHUSDT": 1660.0, "SOLUSDT": 141.0}


def _generate_dummy_candles(symbol: str, entry_time_ms: int, limit: int = LIMIT) -> list[dict]:
    interval_ms = int(INTERVAL) * 60 * 1000
    base = _BASE_PRICES.get(symbol, 1000.0)
    candles = []
    price = base * random.uniform(0.97, 1.03)
    for i in range(limit):
        t = entry_time_ms - interval_ms * (limit // 2 - i)
        delta = random.uniform(-0.004, 0.004) * price
        o = round(price, 2)
        c = round(price + delta, 2)
        h = round(max(o, c) + abs(random.uniform(0, 0.002) * price), 2)
        l = round(min(o, c) - abs(random.uniform(0, 0.002) * price), 2)
        candles.append({
            "timestamp": t,
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
        candles = [
            {
                "timestamp": int(row[0]),
                "open":   float(row[1]),
                "high":   float(row[2]),
                "low":    float(row[3]),
                "close":  float(row[4]),
                "volume": float(row[5]),
            }
            for row in resp["result"]["list"]
        ]
        candles.sort(key=lambda x: x["timestamp"])
        return candles
    except Exception as e:
        print(f"  API 실패: {e}")
        return []


if __name__ == "__main__":
    root = Path(__file__).parent.parent

    for level, trades_path in SAMPLE_FILES.items():
        print(f"\n=== {level} ===")
        raw = json.loads((root / trades_path).read_text(encoding="utf-8"))
        buys = [t for t in raw["result"]["list"] if t.get("side") == "Buy"]

        result: dict = {}
        for trade in buys:
            order_id = trade["orderId"]
            symbol   = trade["symbol"]
            exec_ms  = int(trade["execTime"])
            print(f"  수집 중: {order_id} ({symbol})")

            candles = fetch_candles(symbol, exec_ms)
            if candles:
                print(f"    → {len(candles)}개 수집 완료 (Bybit API)")
            else:
                candles = _generate_dummy_candles(symbol, exec_ms)
                print(f"    → {len(candles)}개 더미 생성 (API 없음)")

            result[order_id] = candles

        out = root / f"data/sample_candles_{level}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  저장 완료: {out}  ({len(result)}건)")
