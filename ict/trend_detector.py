import logging

logger = logging.getLogger(__name__)


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n < 2:
        return 0.0, ys[0] if ys else 0.0
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    sum_xx = sum(x * x for x in xs)
    denom = n * sum_xx - sum_x ** 2
    if denom == 0:
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def detect_trendline(candles: list[dict]) -> dict:
    """
    추세선 + 채널 탐지.
    고점(high) 3개 연결 → 저항선
    저점(low) 3개 연결 → 지지선
    두 선의 기울기가 비슷하면 채널로 판단

    반환:
    {
        "resistance": {"slope": float, "points": list[dict]},
        "support": {"slope": float, "points": list[dict]},
        "is_channel": bool,
        "channel_type": "ascending"|"descending"|"sideways"|None
    }
    points 각 항목: {"timestamp": int, "price": float}
    최소 3개 고점/저점 필요, 부족하면 None 반환
    """
    if len(candles) < 5:
        logger.warning("캔들 수 부족 (%d개) — 추세선 탐지 불가", len(candles))
        return {"resistance": None, "support": None, "is_channel": False, "channel_type": None}

    # 로컬 고점 / 저점 탐지 (인접 캔들과 비교)
    highs: list[tuple[int, int, float]] = []  # (candle_index, timestamp, high)
    lows: list[tuple[int, int, float]] = []   # (candle_index, timestamp, low)

    for i in range(1, len(candles) - 1):
        if candles[i]["high"] >= candles[i - 1]["high"] and candles[i]["high"] >= candles[i + 1]["high"]:
            highs.append((i, candles[i]["timestamp"], candles[i]["high"]))
        if candles[i]["low"] <= candles[i - 1]["low"] and candles[i]["low"] <= candles[i + 1]["low"]:
            lows.append((i, candles[i]["timestamp"], candles[i]["low"]))

    resistance = None
    support = None

    if len(highs) >= 3:
        selected = highs[-5:] if len(highs) > 5 else highs
        slope, _ = _linear_regression([h[0] for h in selected], [h[2] for h in selected])
        resistance = {
            "slope":  slope,
            "points": [{"timestamp": h[1], "price": h[2]} for h in selected],
        }
        logger.debug("저항선 탐지: slope=%.4f, %d개 고점", slope, len(selected))

    if len(lows) >= 3:
        selected = lows[-5:] if len(lows) > 5 else lows
        slope, _ = _linear_regression([l[0] for l in selected], [l[2] for l in selected])
        support = {
            "slope":  slope,
            "points": [{"timestamp": l[1], "price": l[2]} for l in selected],
        }
        logger.debug("지지선 탐지: slope=%.4f, %d개 저점", slope, len(selected))

    is_channel = False
    channel_type = None

    if resistance and support:
        r_slope = resistance["slope"]
        s_slope = support["slope"]
        max_slope = max(abs(r_slope), abs(s_slope))
        if max_slope > 1e-10:
            is_channel = abs(r_slope - s_slope) / max_slope < 0.5
        else:
            is_channel = True  # 둘 다 거의 0 = 수평 채널

        if is_channel:
            avg_slope = (r_slope + s_slope) / 2
            avg_price = sum(c["close"] for c in candles) / len(candles)
            threshold = avg_price * 0.001
            if avg_slope > threshold:
                channel_type = "ascending"
            elif avg_slope < -threshold:
                channel_type = "descending"
            else:
                channel_type = "sideways"

    logger.info(
        "추세선 탐지 완료: resistance=%s, support=%s, is_channel=%s, channel_type=%s",
        "있음" if resistance else "없음",
        "있음" if support else "없음",
        is_channel,
        channel_type,
    )

    return {
        "resistance":   resistance,
        "support":      support,
        "is_channel":   is_channel,
        "channel_type": channel_type,
    }
