import logging

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
4. 200자 이내 평문으로 작성

""" + TRADING_PHILOSOPHY

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = get_llm(temperature=0.3)
    return _llm


def _summarize_candles(candles: list[dict], n: int = 5) -> str:
    # 리스트 중간부터 n개 선택 (진입 시점 근처)
    mid = len(candles) // 2
    start = max(0, mid - n // 2)
    subset = candles[start: start + n]

    lines = []
    for i, c in enumerate(subset, 1):
        import pandas as pd
        dt = pd.to_datetime(c["timestamp"], unit="ms", utc=True).strftime("%Y-%m-%d %H:%M")
        lines.append(
            f"{i}. {dt} UTC | O:{c['open']:.1f} H:{c['high']:.1f} L:{c['low']:.1f} C:{c['close']:.1f}"
        )
    return "\n".join(lines)


def replay_coach_node(
    candles: list[dict],
    ict_patterns: dict,
    trade: dict,
) -> str:
    """
    candles       : 진입 전후 캔들 리스트
    ict_patterns  : {"fvg_zones": [...]}  (detect_fvg 결과)
    trade         : {"symbol", "side", "entry_price", "exit_price", "closed_pnl", "result"}
    반환          : 복기 코멘트 str (한국어)
    """
    symbol      = trade.get("symbol", "")
    side        = trade.get("side", "")
    entry_price = trade.get("entry_price", 0)
    exit_price  = trade.get("exit_price", 0)
    closed_pnl  = trade.get("closed_pnl", 0)
    result      = trade.get("result", "unknown")

    fvg_zones: list[dict] = ict_patterns.get("fvg_zones", [])

    candle_summary = _summarize_candles(candles)

    fvg_text = "없음"
    if fvg_zones:
        parts = []
        for fvg in fvg_zones[:5]:
            import pandas as pd
            dt = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True).strftime("%H:%M")
            parts.append(f"{fvg['type'].capitalize()} FVG {fvg['bottom']:.1f}~{fvg['top']:.1f} ({dt})")
        fvg_text = ", ".join(parts)

    user_content = f"""\
거래 정보:
- 심볼: {symbol}, 방향: {side}
- 진입가: {entry_price:.2f}, 청산가: {exit_price:.2f}
- 손익: {closed_pnl} ({result})

진입 전후 캔들 요약 (OHLC 5개):
{candle_summary}

감지된 ICT 패턴:
- FVG {len(fvg_zones)}개: {fvg_text}

위 데이터를 바탕으로 이 진입이 ICT 관점에서 왜 좋았는지/나빴는지 분석하고, 개선 제안 1개를 포함해 복기 코멘트를 작성하세요."""

    logger.info(
        "replay_coach_node 호출 | symbol=%s side=%s pnl=%s fvg_count=%d",
        symbol, side, closed_pnl, len(fvg_zones),
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
        comment = f"{symbol} {side} 거래 ({result_label}). FVG {len(fvg_zones)}개 감지. LLM 호출 실패: {e}"

    logger.info("replay_coach_node 완료 | comment_len=%d", len(comment))
    return comment
