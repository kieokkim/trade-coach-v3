import logging

logger = logging.getLogger(__name__)


def analyze_stop_loss(
    stop_price: float,
    entry_price: float,
    exit_price: float,
    side: str,
    fvg_zones: list,
    ob_zones: list,
) -> dict:
    """Rule-based 손절가 분석. LLM 미사용."""
    if side == "Long":
        risk   = entry_price - stop_price
        reward = exit_price - entry_price
    else:
        risk   = stop_price - entry_price
        reward = entry_price - exit_price

    rr = round(reward / risk, 2) if risk > 0 else 0.0

    all_zones = fvg_zones + ob_zones
    stop_outside = True
    nearest = "구조 레벨 없음"

    for zone in all_zones:
        bottom = float(zone.get("bottom", 0))
        top    = float(zone.get("top", 0))
        if side == "Long":
            if stop_price < bottom:
                stop_outside = True
                nearest = f"구조 하단 {bottom:.1f} 바깥"
                break
            else:
                stop_outside = False
                nearest = f"구조 하단 {bottom:.1f} 안쪽"
        else:
            if stop_price > top:
                stop_outside = True
                nearest = f"구조 상단 {top:.1f} 바깥"
                break
            else:
                stop_outside = False
                nearest = f"구조 상단 {top:.1f} 안쪽"

    if not all_zones:
        assessment = "구조 레벨 없음 — 판단 불가"
    elif stop_outside:
        risk_pct = risk / entry_price if entry_price > 0 else 0
        assessment = "너무 넓음" if risk_pct > 0.03 else "적절"
    else:
        assessment = "구조 안쪽"

    logger.debug("stop_loss: rr=%.2f outside=%s assessment=%s", rr, stop_outside, assessment)

    return {
        "rr": rr,
        "stop_outside_structure": stop_outside,
        "nearest_structure": nearest,
        "stop_assessment": assessment,
    }
