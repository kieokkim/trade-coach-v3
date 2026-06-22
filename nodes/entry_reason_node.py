import logging
from datetime import datetime, timezone

from utils.llm_factory import get_llm
from nodes.stop_loss_node import analyze_stop_loss
from tools.ict_rag import search_ict_concept_rag

logger = logging.getLogger(__name__)

TRADING_PHILOSOPHY = """
1. 하루 3번 이상 손절 시 당일 거래 중단
2. 매 거래 최대 손실금액 사전 고정
3. Revenge Trading 금지
4. No Setup = No Trade
5. 손절선은 진입 전에 결정
"""


def _in_zone(price: float, zone: dict) -> bool:
    return float(zone["bottom"]) <= float(price) <= float(zone["top"])


def _near_zone(candle_low: float, zone: dict, tolerance: float = 0.005) -> bool:
    bottom = float(zone["bottom"])
    return abs(candle_low - bottom) / bottom <= tolerance


def _is_killzone(exec_time_ms: int) -> bool:
    hour = datetime.fromtimestamp(exec_time_ms / 1000, tz=timezone.utc).hour
    return 2 <= hour <= 5 or 7 <= hour <= 10


def score_aplus(
    candles: list,
    ict_patterns: dict,
    trade: dict,
    session_id: str,
    db_conn,
) -> dict:
    """rule-based A+ 채점. LLM 미사용."""
    fvg   = ict_patterns.get("fvg_zones", [])
    ob    = ict_patterns.get("ob_zones", [])
    trend = ict_patterns.get("trend_info") or {}
    price   = float(trade.get("execPrice", 0))
    side    = trade.get("side", "Buy")
    exec_ms = int(trade.get("execTime", 0))

    s, bd = 0, {}

    fvg_before = [z for z in fvg if z.get("timestamp", 0) < exec_ms]
    ob_before = [z for z in ob if z.get("timestamp", 0) < exec_ms]
    all_zones = fvg_before + ob_before

    # 1. 구조 진입: 진입가가 진입 이전 FVG/OB 구간 내
    bd["structure_entry"] = any(_in_zone(price, z) for z in all_zones)
    if bd["structure_entry"]:
        s += 1

    # 2. 반등 확인: 직전 2캔들 저점이 FVG/OB 하단 근처
    before_2 = sorted(
        [c for c in candles if c["timestamp"] < exec_ms],
        key=lambda x: x["timestamp"],
    )[-2:]
    bd["bounce_confirm"] = bool(all_zones and any(
        _near_zone(float(c["low"]), z)
        for c in before_2
        for z in all_zones
    ))
    if bd["bounce_confirm"]:
        s += 1

    # 3. 추세 정렬: direction 기반, sideways/None은 중립으로 통과
    direction = trade.get("direction", "Long" if side == "Buy" else "Short")
    ct = trend.get("channel_type")
    bd["trend_aligned"] = (
        (direction == "Long"  and ct == "ascending") or
        (direction == "Short" and ct == "descending") or
        ct == "sideways" or ct is None
    )
    if bd["trend_aligned"]:
        s += 1

    # 4. 킬존: 런던(02-05 UTC) 또는 뉴욕(07-10 UTC) 세션
    bd["killzone"] = _is_killzone(exec_ms)
    if bd["killzone"]:
        s += 1

    # 5. 손절 규율: 당일 손절 3회 미만
    try:
        today = datetime.fromtimestamp(exec_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        row = db_conn.execute(
            "SELECT COUNT(*) FROM journal_entries "
            "WHERE session_id=? AND date LIKE ? AND result='loss'",
            (session_id, f"{today}%"),
        ).fetchone()
        bd["stop_discipline"] = (row[0] if row else 0) < 3
    except Exception:
        bd["stop_discipline"] = True
    if bd["stop_discipline"]:
        s += 1

    # 손절 위치 (stop_price 입력 시 구조적 판단, 점수 미반영)
    stop_price = float(trade.get("stop_price", 0))
    direction = trade.get("direction", "Long" if side == "Buy" else "Short")
    if stop_price > 0:
        stop_result = analyze_stop_loss(
            stop_price=stop_price,
            entry_price=price,
            exit_price=float(trade.get("exitPrice", 0)),
            side=direction,
            fvg_zones=fvg,
            ob_zones=ob,
        )
        bd["stop_position"]  = stop_result["stop_outside_structure"]
        bd["rr"]             = stop_result["rr"]
        bd["stop_assessment"] = stop_result["stop_assessment"]
    else:
        bd["stop_position"]  = False
        bd["rr"]             = 0.0
        bd["stop_assessment"] = "손절가 미입력"

    return {"score": s, "breakdown": bd}


def entry_reason_node(
    candles: list,
    ict_patterns: dict,
    trade: dict,
    session_id: str = "default",
) -> dict:
    from db import get_db
    with get_db() as conn:
        aplus = score_aplus(candles, ict_patterns, trade, session_id, conn)

    exec_ms = int(trade.get("execTime", 0))
    before = sorted(
        [c for c in candles if c["timestamp"] < exec_ms],
        key=lambda x: x["timestamp"],
    )[-5:]
    after = sorted(
        [c for c in candles if c["timestamp"] >= exec_ms],
        key=lambda x: x["timestamp"],
    )[:3]

    def fmt(c: dict) -> str:
        t = datetime.fromtimestamp(c["timestamp"] / 1000, tz=timezone.utc)
        return f"{t.strftime('%H:%M')} O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']}"

    fvg = ict_patterns.get("fvg_zones", [])
    ob  = ict_patterns.get("ob_zones", [])
    bd  = aplus["breakdown"]

    pattern_context = ""
    try:
        if fvg:
            rag_result = search_ict_concept_rag("가격 공백 FVG 패턴", top_k=1)
            if rag_result and rag_result[0]["distance"] < 0.5:
                pattern_context += f"\nFVG 참고: {rag_result[0]['improvement']}"
        if ob:
            rag_result = search_ict_concept_rag("기관 주문 구간 OB 패턴", top_k=1)
            if rag_result and rag_result[0]["distance"] < 0.5:
                pattern_context += f"\nOB 참고: {rag_result[0]['improvement']}"
    except Exception as e:
        logger.warning("entry_reason_node RAG 검색 실패: %s", e)

    prompt = (
        f"거래: {trade.get('symbol')} {trade.get('side')} "
        f"진입가:{trade.get('execPrice')} "
        f"결과:{'익절' if float(trade.get('closedPnl', 0)) > 0 else '손절'}\n"
        f"A+점수: {aplus['score']}/5 | FVG:{len(fvg)}개 OB:{len(ob)}개\n"
        f"채점: "
        f"구조진입{'✅' if bd['structure_entry'] else '❌'} "
        f"반등확인{'✅' if bd['bounce_confirm'] else '❌'} "
        f"추세정렬{'✅' if bd['trend_aligned'] else '❌'} "
        f"킬존{'✅' if bd['killzone'] else '❌'} "
        f"손절규율{'✅' if bd['stop_discipline'] else '❌'}\n"
        f"캔들(진입전→후): {' | '.join(fmt(c) for c in before + after)}\n"
        f"트레이딩 철학: {TRADING_PHILOSOPHY}\n"
        f"{pattern_context}\n"
        f"진입 근거 추론(2문장)과 미충족 항목 개선 코칭(2문장)을 한국어로 작성하세요."
    )

    try:
        llm = get_llm(task="complex", temperature=0.3).bind(max_tokens=350)
        resp = llm.invoke([{"role": "user", "content": prompt}])
        parts = resp.content.strip().split("\n\n", 1)
        reason   = parts[0].strip()
        coaching = parts[1].strip() if len(parts) > 1 else ""
    except Exception as e:
        logger.warning("entry_reason_node LLM error: %s", e)
        reason   = f"{'FVG' if fvg else 'OB' if ob else '불명확한 구조'}에서 진입한 것으로 추정됩니다."
        coaching = f"A+ 점수 {aplus['score']}/5. 미충족 항목을 개선하세요."

    return {
        "entry_reason":    reason,
        "aplus_score":     aplus["score"],
        "aplus_breakdown": bd,
        "coaching":        coaching,
    }
