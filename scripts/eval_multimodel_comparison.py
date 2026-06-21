import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from nodes.entry_reason_node import entry_reason_node
from ict.fvg_detector import detect_fvg
from ict.ob_detector import detect_ob
from ict.trend_detector import detect_trendline
from market.candles import get_candles

SAMPLE_FILE = "data/sample_trades_expert.json"
TEST_COUNT = 5

MODELS = {
    "openai": "openai",
    "groq": "groq",
}


def check_quality(text: str) -> dict:
    words = text.split()
    has_loop = len(set(words)) < len(words) * 0.3 if words else True
    criteria_mentioned = sum(
        1 for k in ["구조", "추세", "킬존", "손절", "반등", "FVG", "OB"]
        if k in text
    )
    return {
        "length": len(text),
        "too_short": len(text) < 30,
        "has_loop": has_loop,
        "criteria_mentioned": criteria_mentioned,
    }


def run_comparison():
    data = json.loads(Path(SAMPLE_FILE).read_text())
    buys = [t for t in data["result"]["list"] if t["side"] == "Buy"][:TEST_COUNT]

    results = []

    for buy in buys:
        symbol = buy["symbol"]
        exec_ms = int(buy["execTime"])
        order_id = buy["orderId"]

        candles = get_candles(symbol, exec_ms, order_id=order_id, sample_mode="expert")
        if not candles:
            continue
        fvg = detect_fvg(candles)
        ob = detect_ob(candles)
        tl = detect_trendline(candles)

        trade = {
            "symbol": symbol,
            "side": buy["side"],
            "direction": buy.get("direction", "Long"),
            "execPrice": buy["execPrice"],
            "execTime": exec_ms,
            "closedPnl": buy.get("closedPnl", 0),
        }
        ict_patterns = {"fvg_zones": fvg, "ob_zones": ob, "trend_info": tl}

        for model_key, provider in MODELS.items():
            os.environ["LLM_PROVIDER"] = provider

            start = time.time()
            try:
                out = entry_reason_node(candles, ict_patterns, trade, f"eval_{model_key}")
                elapsed = time.time() - start
                full_text = f"{out['entry_reason']} {out['coaching']}"
            except Exception as e:
                full_text, elapsed = f"ERROR: {e}", 0

            quality = check_quality(full_text)

            print(f"\n[{order_id}] {model_key} ({provider})")
            print(f"  시간: {elapsed:.2f}s")
            print(f"  품질: 기준언급 {quality['criteria_mentioned']} | "
                  f"길이 {quality['length']} | 짧음:{quality['too_short']} | 루프:{quality['has_loop']}")
            print(f"  내용: {full_text[:150]}")

            results.append({
                "order_id": order_id, "model": model_key,
                "elapsed": elapsed, "quality": quality,
                "text": full_text[:300],
            })

    summary = {}
    for model_key in MODELS:
        m = [r for r in results if r["model"] == model_key]
        if not m:
            continue
        summary[model_key] = {
            "avg_elapsed": sum(r["elapsed"] for r in m) / len(m),
            "avg_criteria": sum(r["quality"]["criteria_mentioned"] for r in m) / len(m),
            "avg_length": sum(r["quality"]["length"] for r in m) / len(m),
            "loop_count": sum(1 for r in m if r["quality"]["has_loop"]),
            "short_count": sum(1 for r in m if r["quality"]["too_short"]),
        }

    print(f"\n=== 모델별 요약 ===")
    for model_key, s in summary.items():
        print(f"\n{model_key}:")
        print(f"  평균 응답시간: {s['avg_elapsed']:.2f}s")
        print(f"  평균 기준언급: {s['avg_criteria']:.1f}/7")
        print(f"  평균 길이: {s['avg_length']:.0f}자")
        print(f"  루프: {s['loop_count']}건 | 너무짧음: {s['short_count']}건")

    Path("eval_multimodel_result.json").write_text(
        json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2)
    )
    print(f"\n✅ 저장: eval_multimodel_result.json")


if __name__ == "__main__":
    run_comparison()
