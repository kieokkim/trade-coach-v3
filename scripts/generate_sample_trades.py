"""
샘플 거래 데이터의 execPrice를 실제 Bybit 시장가 기반으로 재설정.
Buy: 해당 시점 캔들 open 가격.
Sell: entry_price + closedPnl / orderQty 역산.
execTime은 변경하지 않음.
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone

from pybit.unified_trading import HTTP

session = HTTP(testnet=False)


def get_price_at_time(symbol: str, exec_ms: int) -> dict:
    """해당 시점 캔들 1개 조회."""
    try:
        resp = session.get_kline(
            category="linear",
            symbol=symbol,
            interval="15",
            start=exec_ms - 15 * 60 * 1000,
            end=exec_ms + 15 * 60 * 1000,
            limit=3,
        )
        candles = resp["result"]["list"]
        if not candles:
            return {}
        c = sorted(candles, key=lambda x: abs(int(x[0]) - exec_ms))[0]
        return {
            "open":  float(c[1]),
            "high":  float(c[2]),
            "low":   float(c[3]),
            "close": float(c[4]),
            "mid":   (float(c[2]) + float(c[3])) / 2,
        }
    except Exception as e:
        print(f"  ⚠️  get_price_at_time 실패 {symbol} {exec_ms}: {e}")
        return {}


SAMPLE_FILES = {
    "beginner":     "data/sample_trades_beginner.json",
    "intermediate": "data/sample_trades_intermediate.json",
    "expert":       "data/sample_trades_expert.json",
}

for level, filepath in SAMPLE_FILES.items():
    print(f"\n▶ {filepath} 처리 중...")
    data   = json.loads(Path(filepath).read_text())
    trades = data["result"]["list"]

    buy_map: dict[str, dict] = {}

    # Pass 1: Buy 가격 업데이트
    for t in trades:
        if t["side"] != "Buy":
            continue
        symbol  = t["symbol"]
        exec_ms = int(t["execTime"])
        dt_str  = datetime.fromtimestamp(exec_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        price   = get_price_at_time(symbol, exec_ms)
        time.sleep(0.3)  # rate-limit 회피

        base_id = t["orderId"].replace("-buy", "")
        if price:
            entry_price = price["open"]
            # open이 캔들 범위 밖이면 mid로 fallback
            if not (price["low"] <= entry_price <= price["high"]):
                entry_price = price["mid"]
            t["execPrice"] = f"{entry_price:.2f}"
            buy_map[base_id] = {
                "price": entry_price,
                "qty":   float(t.get("orderQty", 1)),
                "low":   price["low"],
                "high":  price["high"],
            }
            print(f"  Buy  {symbol} {dt_str} → {entry_price:.2f}")
        else:
            buy_map[base_id] = {
                "price": float(t.get("execPrice", 0)),
                "qty":   float(t.get("orderQty", 1)),
            }
            print(f"  Buy  {symbol} {dt_str} → 캔들 없음, 기존 가격 유지")

    # Pass 2: Sell 가격 역산
    for t in trades:
        if t["side"] != "Sell":
            continue
        base_id    = t["orderId"].replace("-sell", "")
        buy_info   = buy_map.get(base_id)
        if not buy_info:
            continue
        closed_pnl  = float(t.get("closedPnl", 0))
        order_qty   = float(t.get("orderQty", buy_info["qty"]))
        entry_price = buy_info["price"]
        if order_qty > 0:
            exit_price = entry_price + closed_pnl / order_qty
            # 캔들 범위 내로 클램핑 (샘플 데이터 한정)
            candle_low  = buy_info.get("low",  exit_price)
            candle_high = buy_info.get("high", exit_price)
            exit_price = max(candle_low, min(exit_price, candle_high))
            t["execPrice"] = f"{exit_price:.2f}"
            symbol  = t["symbol"]
            exec_ms = int(t["execTime"])
            dt_str  = datetime.fromtimestamp(exec_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            print(f"  Sell {symbol} {dt_str} → {exit_price:.2f} (pnl={closed_pnl:+.2f})")

    Path(filepath).write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
    )
    print(f"✅ {filepath} 저장 완료")
