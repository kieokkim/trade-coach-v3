import json
from pathlib import Path

from nodes.entry_reason_node import score_aplus
from ict.fvg_detector import detect_fvg
from ict.ob_detector import detect_ob
from ict.trend_detector import detect_trendline
from market.candles import get_candles
from db import get_db, init_db

GROUND_TRUTH = {
    "fvg":    {"structure_entry": True,  "label": "FVG 구조 진입"},
    "ob":     {"structure_entry": True,  "label": "OB 구조 진입"},
    "sweep":  {"structure_entry": True,  "label": "유동성 스윕 진입"},
    "random": {"structure_entry": False, "label": "근거 없는 진입"},
}

SAMPLE_FILES = {
    "beginner":     "data/sample_trades_beginner.json",
    "intermediate": "data/sample_trades_intermediate.json",
    "expert":       "data/sample_trades_expert.json",
}


def get_ground_truth(order_id: str) -> dict:
    prefix = order_id.split("-")[0]
    return GROUND_TRUTH.get(prefix, {"structure_entry": None, "label": "알수없음"})


def load_buys(level: str) -> list[dict]:
    data = json.loads(Path(SAMPLE_FILES[level]).read_text())
    return [t for t in data["result"]["list"] if t["side"] == "Buy"]


def run_validation():
    init_db()
    results = []

    with get_db() as conn:
        for level in SAMPLE_FILES:
            for buy in load_buys(level):
                order_id = buy["orderId"]
                symbol = buy["symbol"]
                exec_ms = int(buy["execTime"])

                gt = get_ground_truth(order_id)
                if gt["structure_entry"] is None:
                    continue

                candles = get_candles(
                    symbol, exec_ms,
                    order_id=order_id,
                    sample_mode=level,
                )

                fvg = detect_fvg(candles)
                ob = detect_ob(candles)
                tl = detect_trendline(candles)

                trade = {
                    "execPrice": buy["execPrice"],
                    "side": buy["side"],
                    "direction": buy.get("direction", "Long"),
                    "execTime": exec_ms,
                }

                aplus = score_aplus(
                    candles=candles,
                    ict_patterns={"fvg_zones": fvg, "ob_zones": ob, "trend_info": tl},
                    trade=trade,
                    session_id=f"eval_{level}",
                    db_conn=conn,
                )

                ai_structure = aplus["breakdown"].get("structure_entry")
                gt_structure = gt["structure_entry"]
                match = (ai_structure == gt_structure)

                results.append({
                    "level": level,
                    "order_id": order_id,
                    "ground_truth": gt_structure,
                    "ground_truth_label": gt["label"],
                    "ai_judgment": ai_structure,
                    "match": match,
                    "ai_score": aplus["score"],
                })

                status = "✅" if match else "❌"
                print(f"{status} [{level}] {order_id} | "
                      f"정답:{gt_structure} AI:{ai_structure} | {gt['label']}")

    total = len(results)
    matched = sum(1 for r in results if r["match"])
    rate = matched / total * 100 if total else 0

    print(f"\n=== 전체 결과 ===")
    print(f"총 {total}건 | 일치 {matched}건 | 정확도 {rate:.1f}%")

    by_pattern = {}
    for r in results:
        prefix = r["order_id"].split("-")[0]
        by_pattern.setdefault(prefix, {"match": 0, "total": 0})
        by_pattern[prefix]["total"] += 1
        if r["match"]:
            by_pattern[prefix]["match"] += 1

    print(f"\n=== 패턴별 정확도 ===")
    for prefix, v in by_pattern.items():
        p_rate = v["match"] / v["total"] * 100 if v["total"] else 0
        print(f"  {prefix}: {p_rate:.1f}% ({v['match']}/{v['total']})")

    mismatches = [r for r in results if not r["match"]]
    if mismatches:
        print(f"\n=== 불일치 케이스 (AI 오판) ===")
        for m in mismatches:
            print(f"  [{m['level']}] {m['order_id']}: "
                  f"의도={m['ground_truth_label']}, AI판단={m['ai_judgment']}")

    Path("eval_aplus_validation_result.json").write_text(
        json.dumps({
            "total": total, "matched": matched, "accuracy": rate,
            "by_pattern": by_pattern, "mismatches": mismatches,
            "all_results": results,
        }, ensure_ascii=False, indent=2)
    )
    print(f"\n✅ 저장: eval_aplus_validation_result.json")


if __name__ == "__main__":
    run_validation()
