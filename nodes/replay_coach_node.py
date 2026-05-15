import logging
from datetime import datetime, timezone

from utils.llm_factory import get_llm

from nodes.coaching_nodes import TRADING_PHILOSOPHY

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """\
당신은 ICT(Inner Circle Trader) 전문 트레이딩 코치입니다.
트레이더의 실제 거래 데이터와 차트 패턴을 분석하여 복기 코멘트를 한국어로 작성하세요.

작성 지침:
1. 진입 근거가 ICT 관점에서 좋았는지 나빴는지 명확하게 판단
2. FVG, OB 등 감지된 패턴과 실제 진입/청산의 관계 언급
3. 개선할 수 있는 구체적인 제안 1개 제시
4. 응답은 반드시 3~5문장으로 제한하세요.
5. 같은 내용을 반복하지 마세요.

""" + TRADING_PHILOSOPHY

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(task="complex", temperature=0.3).bind(max_tokens=300)
    return _llm


def summarize_candles(candles: list[dict], entry_ms: int, max_before: int = 5, max_after: int = 5) -> dict:
    before = [c for c in candles if c["timestamp"] < entry_ms][-max_before:]
    after  = [c for c in candles if c["timestamp"] >= entry_ms][:max_after]

    def fmt(c: dict) -> str:
        t = datetime.fromtimestamp(c["timestamp"] / 1000, tz=timezone.utc)
        return (f"{t.strftime('%H:%M')} "
                f"O:{c['open']} H:{c['high']} L:{c['low']} C:{c['close']}")

    return {
        "before": [fmt(c) for c in before],
        "after":  [fmt(c) for c in after],
    }


def replay_coach_node(
    candles: list[dict],
    ict_patterns: dict,
    trade: dict,
) -> str:
    """
    candles       : 진입 전후 캔들 리스트
    ict_patterns  : {"fvg_zones": [...], "ob_zones": [...]}
    trade         : {"symbol", "side", "entry_price", "exit_price",
                     "closed_pnl", "result", "entry_ms"}
    반환          : 복기 코멘트 str (한국어)
    """
    symbol      = trade.get("symbol", "")
    side        = trade.get("side", "")
    entry_price = trade.get("entry_price", 0)
    exit_price  = trade.get("exit_price", 0)
    closed_pnl  = trade.get("closed_pnl", 0)
    result      = trade.get("result", "unknown")
    entry_ms    = int(trade.get("entry_ms", 0))

    fvg_zones: list[dict] = ict_patterns.get("fvg_zones", [])
    ob_zones:  list[dict] = ict_patterns.get("ob_zones",  [])

    parts = []
    if fvg_zones:
        parts.append(f"FVG {len(fvg_zones)}개")
    if ob_zones:
        parts.append(f"OB {len(ob_zones)}개")
    ict_summary = ", ".join(parts) if parts else "없음"

    summary = summarize_candles(candles, entry_ms)

    user_content = f"""\
거래 정보:
- 종목: {symbol}
- 진입가: {entry_price} / 청산가: {exit_price}
- 결과: {result} (손익: {closed_pnl})

진입 전 캔들 (최근 5개):
{chr(10).join(summary["before"]) or "데이터 없음"}

진입 후 캔들 (5개):
{chr(10).join(summary["after"]) or "데이터 없음"}

감지된 ICT 패턴: {ict_summary}

위 정보를 바탕으로 이 거래의 ICT 관점 복기 코멘트를 작성하세요."""

    logger.info(
        "replay_coach_node 호출 | symbol=%s side=%s pnl=%s fvg=%d ob=%d",
        symbol, side, closed_pnl, len(fvg_zones), len(ob_zones),
    )

    try:
        msg = _get_llm().invoke([
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ])
        comment = msg.content.strip()
    except Exception as e:
        logger.warning("replay_coach_node LLM 오류: %s", e)
        result_label = "수익" if float(closed_pnl or 0) > 0 else "손실"
        comment = f"{symbol} {side} 거래 ({result_label}). {ict_summary} 감지. LLM 호출 실패: {e}"

    logger.info("replay_coach_node 완료 | comment_len=%d", len(comment))
    return comment
