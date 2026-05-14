import logging
from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)


def render_candle_chart(
    candles: list[dict],
    entry_time_ms: int,
    exit_time_ms: int,
    symbol: str,
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
