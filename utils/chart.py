import logging
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)


def _trendline_endpoints(
    slope: float,
    points: list[dict],
    candles: list[dict],
) -> tuple[float, float]:
    """슬로프 + 첫 기준점으로 차트 시작/끝 y값 계산."""
    ts_to_idx = {c["timestamp"]: i for i, c in enumerate(candles)}
    i0 = ts_to_idx.get(points[0]["timestamp"], 0)
    y0 = points[0]["price"]
    n = len(candles)
    return y0 + slope * (0 - i0), y0 + slope * (n - 1 - i0)


def render_candle_chart(
    candles: list[dict],
    entry_time_ms: int,
    exit_time_ms: int,
    symbol: str,
    obs: list[dict] | None = None,
    trendline: dict | None = None,
) -> None:
    if not candles:
        st.warning("캔들 데이터가 없습니다.")
        return

    df = pd.DataFrame(candles)
    df["dt"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)

    fig = go.Figure(
        data=[
            go.Candlestick(
                x=df["dt"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=symbol,
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350",
            )
        ]
    )

    entry_dt = datetime.fromtimestamp(entry_time_ms / 1000, tz=timezone.utc)
    exit_dt  = datetime.fromtimestamp(exit_time_ms  / 1000, tz=timezone.utc)

    # 진입/청산 시점에 해당하는 캔들 가격 조회
    entry_row = df[df["timestamp"] <= entry_time_ms].tail(1)
    exit_row  = df[df["timestamp"] <= exit_time_ms].tail(1)

    entry_price = float(entry_row["low"].iloc[0])  * 0.999 if not entry_row.empty else None
    exit_price  = float(exit_row["high"].iloc[0])  * 1.001 if not exit_row.empty else None

    if entry_price is not None:
        fig.add_trace(
            go.Scatter(
                x=[entry_dt],
                y=[entry_price],
                mode="markers",
                marker=dict(symbol="triangle-up", size=14, color="#1565C0"),
                name="진입",
            )
        )

    if exit_price is not None:
        fig.add_trace(
            go.Scatter(
                x=[exit_dt],
                y=[exit_price],
                mode="markers",
                marker=dict(symbol="triangle-down", size=14, color="#C62828"),
                name="청산",
            )
        )

    # OB 오버레이
    if obs:
        dt_max = df["dt"].max()
        for ob in obs:
            ob_dt = pd.to_datetime(ob["timestamp"], unit="ms", utc=True)
            color = "rgba(0,200,100,0.15)" if ob["type"] == "bullish" else "rgba(200,50,50,0.15)"
            fig.add_shape(
                type="rect",
                x0=ob_dt, x1=dt_max,
                y0=ob["bottom"], y1=ob["top"],
                fillcolor=color,
                line_width=0,
                layer="below",
            )

    # 추세선 오버레이
    if trendline:
        dt0 = df["dt"].iloc[0]
        dt1 = df["dt"].iloc[-1]
        res = trendline.get("resistance")
        sup = trendline.get("support")

        if res:
            ry0, ry1 = _trendline_endpoints(res["slope"], res["points"], candles)
            fig.add_trace(go.Scatter(
                x=[dt0, dt1], y=[ry0, ry1],
                mode="lines",
                line=dict(color="red", dash="dash", width=1),
                opacity=0.6,
                name="저항선",
            ))

        if sup:
            sy0, sy1 = _trendline_endpoints(sup["slope"], sup["points"], candles)
            fig.add_trace(go.Scatter(
                x=[dt0, dt1], y=[sy0, sy1],
                mode="lines",
                line=dict(color="green", dash="dash", width=1),
                opacity=0.6,
                name="지지선",
            ))

        if trendline.get("is_channel") and res and sup:
            ry0, ry1 = _trendline_endpoints(res["slope"], res["points"], candles)
            sy0, sy1 = _trendline_endpoints(sup["slope"], sup["points"], candles)
            fig.add_trace(go.Scatter(
                x=[dt0, dt1, dt1, dt0, dt0],
                y=[ry0, ry1, sy1, sy0, ry0],
                fill="toself",
                fillcolor="rgba(150,150,150,0.08)",
                line=dict(width=0),
                showlegend=False,
                hoverinfo="skip",
            ))

    fig.update_layout(
        title=f"{symbol} 캔들차트",
        xaxis_title="시간 (UTC)",
        yaxis_title="가격 (USDT)",
        xaxis_rangeslider_visible=False,
        height=500,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    logger.info("Rendering candle chart for %s (entry=%d exit=%d)", symbol, entry_time_ms, exit_time_ms)
    st.plotly_chart(fig, use_container_width=True)
