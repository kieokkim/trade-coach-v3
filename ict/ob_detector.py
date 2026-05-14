import logging

logger = logging.getLogger(__name__)


def detect_ob(candles: list[dict]) -> list[dict]:
    """
    Order Block rule-based 탐지.
    - Bullish OB: 하락 후 강한 상승이 나온 직전 하락 캔들
      조건: candle[i].close < candle[i].open (하락캔들)
            이후 2캔들 내 close > candle[i].high (강한 반등)
    - Bearish OB: 상승 후 강한 하락이 나온 직전 상승 캔들
      조건: candle[i].close > candle[i].open (상승캔들)
            이후 2캔들 내 close < candle[i].low (강한 하락)
    반환: [{"type": "bullish"|"bearish", "top": float, "bottom": float, "timestamp": int}, ...]
    """
    obs: list[dict] = []

    if len(candles) < 3:
        logger.warning("캔들 수 부족 (%d개) — OB 탐지 불가", len(candles))
        return obs

    for i in range(len(candles)):
        c = candles[i]

        if c["close"] < c["open"]:  # 하락 캔들 → Bullish OB 후보
            for j in range(i + 1, min(i + 3, len(candles))):
                if candles[j]["close"] > c["high"]:
                    obs.append({
                        "type":      "bullish",
                        "top":       c["open"],
                        "bottom":    c["close"],
                        "timestamp": c["timestamp"],
                    })
                    break

        elif c["close"] > c["open"]:  # 상승 캔들 → Bearish OB 후보
            for j in range(i + 1, min(i + 3, len(candles))):
                if candles[j]["close"] < c["low"]:
                    obs.append({
                        "type":      "bearish",
                        "top":       c["close"],
                        "bottom":    c["open"],
                        "timestamp": c["timestamp"],
                    })
                    break

    logger.info("OB 탐지 완료: %d개 캔들 → %d개 OB", len(candles), len(obs))
    return obs
