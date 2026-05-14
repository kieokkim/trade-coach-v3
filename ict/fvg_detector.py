import logging

logger = logging.getLogger(__name__)


def detect_fvg(candles: list[dict]) -> list[dict]:
    """
    FVG (Fair Value Gap) rule-based 탐지.

    3개 연속 캔들에서:
    - Bullish FVG: candle[0].high < candle[2].low  (상승 공백)
    - Bearish FVG: candle[0].low  > candle[2].high (하락 공백)

    반환: [{"type": "bullish"|"bearish", "top": float, "bottom": float, "timestamp": int}, ...]
    timestamp 은 중간(1번) 캔들 기준.
    """
    fvgs: list[dict] = []

    if len(candles) < 3:
        logger.warning("캔들 수 부족 (%d개) — FVG 탐지 불가", len(candles))
        return fvgs

    for i in range(len(candles) - 2):
        c0, c1, c2 = candles[i], candles[i + 1], candles[i + 2]

        if c0["high"] < c2["low"]:
            fvgs.append({
                "type":      "bullish",
                "top":       c2["low"],
                "bottom":    c0["high"],
                "timestamp": c1["timestamp"],
            })
        elif c0["low"] > c2["high"]:
            fvgs.append({
                "type":      "bearish",
                "top":       c0["low"],
                "bottom":    c2["high"],
                "timestamp": c1["timestamp"],
            })

    logger.info("FVG 탐지 완료: %d개 캔들 → %d개 FVG", len(candles), len(fvgs))
    return fvgs
