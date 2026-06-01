"""
샘플 데이터 Sell execPrice 역산 수정.
exitPrice = entryPrice + closedPnl / orderQty (Long 기준)
"""
import json
from pathlib import Path

FILES = [
    "data/sample_trades_beginner.json",
    "data/sample_trades_intermediate.json",
    "data/sample_trades_expert.json",
]

for filepath in FILES:
    data   = json.loads(Path(filepath).read_text())
    trades = data["result"]["list"]

    buy_map = {
        t["orderId"].replace("-buy", ""): t
        for t in trades if t["side"] == "Buy"
    }

    fixed = 0
    for t in trades:
        if t["side"] != "Sell":
            continue
        base_id = t["orderId"].replace("-sell", "")
        buy = buy_map.get(base_id)
        if not buy:
            continue

        entry_price = float(buy["execPrice"])
        closed_pnl  = float(t.get("closedPnl", 0))
        order_qty   = float(t.get("orderQty", buy.get("orderQty", 1)))

        if order_qty > 0:
            exit_price = entry_price + closed_pnl / order_qty
            t["execPrice"] = f"{exit_price:.2f}"
            fixed += 1

    Path(filepath).write_text(
        json.dumps(data, ensure_ascii=False, indent=2)
    )
    print(f"✅ {filepath}: {fixed}건 수정")
