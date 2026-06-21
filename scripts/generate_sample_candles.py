"""샘플 거래 파일(beginner/intermediate/expert)에서 Buy 거래를 추출해
각 레벨별 캔들 파일을 data/sample_candles_{level}.json 에 저장하는 1회성 스크립트.

fvg-*/ob-* 거래는 진입 이전에 해당 구조가 존재하도록 보장.
"""
import json
import random
import sys
from pathlib import Path

_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(_ROOT))

from pybit.unified_trading import HTTP
from ict.fvg_detector import detect_fvg
from ict.ob_detector import detect_ob

SAMPLE_FILES = {
    "beginner":     "data/sample_trades_beginner.json",
    "intermediate": "data/sample_trades_intermediate.json",
    "expert":       "data/sample_trades_expert.json",
}

INTERVAL = "15"
LIMIT = 50
INTERVAL_MS = int(INTERVAL) * 60 * 1000

_BASE_PRICES = {"BTCUSDT": 83000.0, "ETHUSDT": 1660.0, "SOLUSDT": 141.0}


def _get_order_type(order_id: str) -> str | None:
    prefix = order_id.split("-")[0]
    return prefix if prefix in ("fvg", "ob") else None


def _in_zone(price: float, zone: dict) -> bool:
    return float(zone["bottom"]) <= price <= float(zone["top"])


def _has_pre_entry_structure(
    candles: list[dict], exec_ms: int, order_type: str, exec_price: float,
) -> bool:
    if order_type == "fvg":
        zones = detect_fvg(candles)
    elif order_type == "ob":
        zones = detect_ob(candles)
    else:
        return True
    pre = [z for z in zones if z["timestamp"] < exec_ms]
    return any(_in_zone(exec_price, z) for z in pre)


def _inject_fvg_zone(candles: list[dict], exec_ms: int, exec_price: float) -> None:
    """진입가를 포함하는 bullish FVG를 진입 5캔들 전에 주입."""
    pre = [i for i, c in enumerate(candles) if c["timestamp"] < exec_ms]
    if len(pre) < 6:
        return
    idx = pre[-5]
    m = exec_price * 0.003

    candles[idx]["open"] = round(exec_price - m * 3, 2)
    candles[idx]["high"] = round(exec_price - m, 2)
    candles[idx]["low"] = round(exec_price - m * 4, 2)
    candles[idx]["close"] = round(exec_price - m * 2, 2)

    candles[idx + 1]["open"] = round(exec_price - m * 0.5, 2)
    candles[idx + 1]["high"] = round(exec_price + m * 3, 2)
    candles[idx + 1]["low"] = round(exec_price - m, 2)
    candles[idx + 1]["close"] = round(exec_price + m * 2, 2)

    candles[idx + 2]["open"] = round(exec_price + m * 2, 2)
    candles[idx + 2]["high"] = round(exec_price + m * 4, 2)
    candles[idx + 2]["low"] = round(exec_price + m, 2)
    candles[idx + 2]["close"] = round(exec_price + m * 3, 2)


def _inject_ob_zone(candles: list[dict], exec_ms: int, exec_price: float) -> None:
    """진입가를 포함하는 bullish OB를 진입 5캔들 전에 주입."""
    pre = [i for i, c in enumerate(candles) if c["timestamp"] < exec_ms]
    if len(pre) < 6:
        return
    idx = pre[-5]
    m = exec_price * 0.003

    candles[idx]["open"] = round(exec_price + m, 2)
    candles[idx]["close"] = round(exec_price - m, 2)
    candles[idx]["high"] = round(exec_price + m * 2, 2)
    candles[idx]["low"] = round(exec_price - m * 2, 2)

    candles[idx + 1]["open"] = round(exec_price - m * 0.5, 2)
    candles[idx + 1]["close"] = round(exec_price + m * 3, 2)
    candles[idx + 1]["high"] = round(exec_price + m * 4, 2)
    candles[idx + 1]["low"] = round(exec_price - m, 2)


def _generate_dummy_candles(symbol: str, entry_time_ms: int, limit: int = LIMIT) -> list[dict]:
    base = _BASE_PRICES.get(symbol, 1000.0)
    candles = []
    price = base * random.uniform(0.97, 1.03)
    for i in range(limit):
        t = entry_time_ms - INTERVAL_MS * (limit // 2 - i)
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
    start = entry_time_ms - (INTERVAL_MS * (LIMIT // 2))
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


def _fetch_with_retry(symbol: str, exec_ms: int, order_type: str) -> tuple[list[dict], str]:
    """API 조회 후 구조 검증, 실패 시 시간대 변경해서 최대 3회 재시도."""
    offsets = [0, INTERVAL_MS * 10, -INTERVAL_MS * 10, INTERVAL_MS * 20]
    for i, offset in enumerate(offsets):
        candles = fetch_candles(symbol, exec_ms + offset)
        if not candles:
            break
        if _has_pre_entry_structure(candles, exec_ms, order_type, exec_price):
            src = "Bybit API" + (f" (시도 {i+1})" if i > 0 else "")
            return candles, src
    return [], ""


if __name__ == "__main__":
    injected_list = []
    manual_review = []

    for level, trades_path in SAMPLE_FILES.items():
        print(f"\n=== {level} ===")
        raw = json.loads((_ROOT / trades_path).read_text(encoding="utf-8"))
        buys = [t for t in raw["result"]["list"] if t.get("side") == "Buy"]

        result: dict = {}
        for trade in buys:
            order_id = trade["orderId"]
            symbol = trade["symbol"]
            exec_ms = int(trade["execTime"])
            exec_price = float(trade["execPrice"])
            order_type = _get_order_type(order_id)
            print(f"  수집 중: {order_id} ({symbol})")

            candles = []
            source = ""

            if order_type:
                candles, source = _fetch_with_retry(symbol, exec_ms, order_type)

            if not candles:
                candles = fetch_candles(symbol, exec_ms)
                if candles:
                    source = "Bybit API"
                else:
                    candles = _generate_dummy_candles(symbol, exec_ms)
                    source = "더미 생성"

            if order_type and not _has_pre_entry_structure(candles, exec_ms, order_type, exec_price):
                if order_type == "fvg":
                    _inject_fvg_zone(candles, exec_ms, exec_price)
                elif order_type == "ob":
                    _inject_ob_zone(candles, exec_ms, exec_price)

                if _has_pre_entry_structure(candles, exec_ms, order_type, exec_price):
                    source += " + 구조 주입"
                    injected_list.append(order_id)
                    print(f"    → {order_type.upper()} 구조 주입 완료")
                else:
                    manual_review.append(order_id)
                    print(f"    ⚠️ {order_id}: 의도된 구조가 진입 이전에 없음 (수동 검토 필요)")

            print(f"    → {len(candles)}개 ({source})")
            result[order_id] = candles

        out = _ROOT / f"data/sample_candles_{level}.json"
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  저장 완료: {out}  ({len(result)}건)")

    print(f"\n=== 결과 요약 ===")
    if injected_list:
        print(f"구조 주입: {len(injected_list)}건 — {', '.join(injected_list)}")
    if manual_review:
        print(f"⚠️ 수동 검토 필요: {len(manual_review)}건 — {', '.join(manual_review)}")
    if not injected_list and not manual_review:
        print("모든 fvg-/ob- 거래에 진입 이전 구조 확인 완료")
