import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# ── 유틸 함수 ────────────────────────────────────────────────────────────────

def _ms_to_kst(ms) -> str:
    return (
        pd.to_datetime(int(ms), unit="ms", utc=True)
        .tz_convert("Asia/Seoul")
        .strftime("%Y-%m-%d %H:%M")
    )

def _pair_label(trade_id: str, buy: dict, sell: dict) -> str:
    pnl = float(sell.get("closedPnl", 0) or 0)
    date_kst = _ms_to_kst(buy.get("execTime", 0))[:10]
    emoji   = "✅" if pnl >= 0 else "❌"
    pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"
    return f"{trade_id} | {date_kst} ({emoji} {pnl_str})"

_COL_KO = {
    "execTime":  "체결시간(KST)",
    "symbol":    "종목",
    "side":      "방향",
    "execPrice": "체결가",
    "orderQty":  "수량",
    "closedPnl": "손익(USDT)",
}

from nodes.replay_coach_node import replay_coach_node
from nodes.entry_reason_node import entry_reason_node
from ict.fvg_detector import detect_fvg
from ict.ob_detector import detect_ob
from ict.trend_detector import detect_trendline
from market.candles import get_candles, validate_price_in_candle
from db import save_trade_tag, load_trade_tags, get_setting, save_setting
from utils.styles import (inject_global_css, render_sidebar_brand,
                           render_dashboard_header, render_kpi_cards,
                           render_trade_table, render_section_header)

st.set_page_config(page_title="TradeCoach | 대시보드", page_icon="📊", layout="wide")

inject_global_css()
render_sidebar_brand()

# ── 결과 없으면 API 입력 페이지로 ──────────────────────────────────────────
if "last_result" not in st.session_state:
    st.info("분석 결과가 없습니다. API 입력 페이지에서 시작해주세요.")
    if st.button("← API 입력 페이지로"):
        st.switch_page("pages/1_api_input.py")
    st.stop()

session_id = st.session_state.get("session_id", "default")
res        = st.session_state["last_result"]

if "trade_tags" not in st.session_state:
    st.session_state["trade_tags"] = load_trade_tags(session_id)

# ── 전역: Buy/Sell 페어링 ────────────────────────────────────────────────────
raw_trades  = res.get("raw_trades", [])
buy_trades  = [t for t in raw_trades if str(t.get("side", "")).lower() == "buy"]
sell_trades = [t for t in raw_trades if str(t.get("side", "")).lower() == "sell"
               and str(t.get("closedPnl", "0")) != "0"]

trade_pairs: list[tuple[str, dict, dict]] = []
used_sells: set[int] = set()
sym_counter: dict[str, int] = {}
for buy in buy_trades:
    for j, sell in enumerate(sell_trades):
        if j in used_sells:
            continue
        if buy.get("symbol") == sell.get("symbol"):
            sym = buy.get("symbol", "XXX")
            sym_counter[sym] = sym_counter.get(sym, 0) + 1
            trade_id = f"{sym[:3]}-{sym_counter[sym]:03d}"
            trade_pairs.append((trade_id, buy, sell))
            used_sells.add(j)
            break

# ═══════════════════════════════ 사이드바 ═══════════════════════════════════

# ① 루프 버튼
if st.sidebar.button("🔄 새 분석 시작", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.switch_page("pages/1_api_input.py")

if st.sidebar.button(
    "📈 신규 거래 추가 확인",
    use_container_width=True,
    help="샘플 #2로 재분석 — 신규 거래 3건 추가된 버전",
):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["sample_mode"] = "sample_2"
    st.switch_page("pages/2_loading.py")

st.sidebar.caption("💡 매일 거래 후 새 분석을 시작하세요")
st.sidebar.divider()

# ② 대시보드 expander
stats     = st.session_state.get("last_stats", {})
total_pnl = sum(float(t.get("closedPnl", 0) or 0) for t in raw_trades)
pnl_display = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"

_default_loss_saved = float(get_setting("default_fixed_loss", "0") or "0")
if "default_fixed_loss" not in st.session_state:
    st.session_state["default_fixed_loss"] = _default_loss_saved

with st.sidebar.expander("📊 대시보드", expanded=True):
    kpi_desc_html = """
<div style="background:#1E2A3A;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:11px;line-height:1.8;color:#A8B8C8">
<b style="color:#7EB8D4">📐 지표 설명</b><br>
<b>승률</b> = 익절 건수 ÷ 전체 거래 건수 × 100<br>
<b>평균 수익률</b> = closedPnl ÷ execValue × 100 (투자금 대비 수익률)<br>
<b>수익금</b> = closedPnl 합계 (수수료 제외 실현 손익)<br>
<b>손절 일관성</b> = 손실 표준편차 ÷ 평균손실 (낮을수록 규칙적)
</div>
"""
    st.markdown(kpi_desc_html, unsafe_allow_html=True)

    weaknesses = st.session_state.get("last_weaknesses", [])
    if weaknesses:
        st.caption("⚠️ 약점")
        tag_html = " ".join([
            f'<span style="background:#FFF3CD;color:#856404;'
            f'padding:2px 8px;border-radius:12px;'
            f'font-size:11px;margin:2px;display:inline-block">'
            f'{w}</span>'
            for w in weaknesses
        ])
        st.markdown(tag_html, unsafe_allow_html=True)

    action_rule = st.session_state.get("last_action_rule", "")
    if action_rule:
        st.success(f"★ {action_rule}")

    judge_result = res.get("judge_result", "")
    judge_passed = res.get("judge_passed", True)
    if judge_result and judge_passed:
        st.success(f"✅ {judge_result}")

    with st.expander("📋 트레이딩 철학 & ICT 원칙", expanded=False):
        PHILOSOPHY = [
            "하루 3번 이상 손절 시 당일 거래 중단",
            "매 거래 최대 손실금액 사전 고정",
            "Revenge Trading 절대 금지",
            "No Setup = No Trade",
            "손절선은 진입 전에 결정",
        ]
        for rule in PHILOSOPHY:
            st.markdown(f"✅ {rule}")

        st.divider()

        ICT_RULES = [
            ("🕐", "킬존 진입",  "런던 02-05 UTC / 뉴욕 07-10 UTC"),
            ("📊", "구조적 진입", "FVG 또는 OB 구간 내 진입"),
            ("📈", "추세 정렬",  "상위 추세 방향으로만 진입"),
            ("🛡️", "손절 위치",  "구조적 레벨(FVG/OB 하단) 바깥"),
        ]
        for icon, title, desc in ICT_RULES:
            st.markdown(f"{icon} **{title}**: {desc}")

# ═══════════════════════════ 메인 화면 ══════════════════════════════════════

# 상단: 제목 + 모드 표시
sample_label = st.session_state.get("sample_label", "")
mode_label   = sample_label if sample_label else "실계정"
render_dashboard_header(mode_label)

win_rate_raw     = stats.get("win_rate", 0)
avg_return       = stats.get("avg_return_rate", 0)
stop_consistency = stats.get("loss_consistency", 0)
render_kpi_cards(win_rate_raw * 100, avg_return, total_pnl, stop_consistency)

# ── 거래내역 테이블 ──────────────────────────────────────────────────────────
st.subheader("📋 거래내역")

if trade_pairs:
    trade_list = []
    for tid, buy, sell in trade_pairs:
        pnl         = float(sell.get("closedPnl", 0) or 0)
        entry_price = float(buy.get("execPrice", 0) or 0)
        exit_price  = float(sell.get("execPrice", 0) or 0)
        if exit_price == entry_price:
            _pnl_fb  = float(sell.get("closedPnl", 0) or 0)
            _qty_fb  = float(buy.get("orderQty", 1) or 1)
            if _qty_fb > 0:
                exit_price = entry_price + _pnl_fb / _qty_fb
        _dir_raw  = buy.get("direction")
        direction = _dir_raw if _dir_raw in ("Long", "Short") else \
                    ("Long" if buy.get("side", "Buy") == "Buy" else "Short")
        trade_list.append({
            "id":          tid,
            "symbol":      buy.get("symbol", ""),
            "side":        "↗️ Long" if direction == "Long" else "↘️ Short",
            "entry_price": f"{entry_price:,.2f}",
            "exit_price":  f"{exit_price:,.2f}",
            "qty":         float(buy.get("orderQty", 0)),
            "result":      "WIN" if pnl >= 0 else "LOSS",
            "pnl":         pnl,
            "entry_time":  _ms_to_kst(buy.get("execTime", 0)),
        })
    render_trade_table(trade_list)
elif raw_trades:
    df_trades = pd.DataFrame(raw_trades)
    display_cols = [c for c in ["execTime", "symbol", "side", "execPrice", "orderQty", "closedPnl"]
                    if c in df_trades.columns]
    df_display = df_trades[display_cols].copy() if display_cols else df_trades.copy()
    if "execTime" in df_display.columns:
        df_display["execTime"] = df_display["execTime"].apply(_ms_to_kst)
    df_display.rename(columns={k: v for k, v in _COL_KO.items() if k in df_display.columns}, inplace=True)
    st.dataframe(df_display, use_container_width=True)
else:
    st.caption("거래내역 없음")

# ── 포지션 사이징 기본값 설정 ─────────────────────────────────────────────────
st.divider()
with st.expander("💰 포지션 사이징 기본값 설정", expanded=False):
    st.caption("모든 거래에 적용되는 기본 고정 손실 금액. 복기 뷰어에서 거래별로 개별 조정 가능.")
    _gc1, _gc2 = st.columns([2, 1])
    with _gc1:
        _new_default = st.number_input(
            "거래당 최대 손실 ($)",
            min_value=0.0,
            value=st.session_state["default_fixed_loss"],
            step=1.0,
            key="global_default_loss",
            help="모든 거래의 포지션 사이징 초기값",
        )
    with _gc2:
        if _new_default > 0:
            st.markdown(
                f'<div style="background:#1E2A3A;border-radius:8px;'
                f'padding:10px;text-align:center;margin-top:24px">'
                f'<div style="font-size:11px;color:#85B7EB">기본 손실 한도</div>'
                f'<div style="font-size:20px;font-weight:700;color:#26a69a">'
                f'${_new_default:.0f}</div></div>',
                unsafe_allow_html=True,
            )
    if _new_default != st.session_state["default_fixed_loss"]:
        save_setting("default_fixed_loss", str(_new_default))
        st.session_state["default_fixed_loss"] = _new_default
        st.success("✅ 기본값 저장됨")

# ── 복기 뷰어 ────────────────────────────────────────────────────────────────
st.divider()
render_section_header("복기 뷰어", "트레이드 선택 후 복기 시작")

if not trade_pairs:
    st.caption("복기할 트레이드 쌍이 없습니다. (raw_trades에 Buy/Sell 쌍 필요)")
else:
    pair_labels = [_pair_label(tid, b, s) for tid, b, s in trade_pairs]

    if "replay_selected" not in st.session_state:
        st.session_state["replay_selected"] = pair_labels[0] if pair_labels else None

    selected_label = st.selectbox(
        "트레이드 선택",
        pair_labels,
        key="replay_select",
        index=pair_labels.index(st.session_state["replay_selected"])
              if st.session_state["replay_selected"] in pair_labels else 0,
    )
    st.session_state["replay_selected"] = selected_label
    sel_idx = pair_labels.index(selected_label)

    sel_trade_id, buy_t, sell_t = trade_pairs[sel_idx]
    symbol   = buy_t.get("symbol", "BTCUSDT")
    entry_ms = int(buy_t.get("execTime",  0))
    exit_ms  = int(sell_t.get("execTime", 0))
    order_id = buy_t.get("orderId", "")
    cache_key = f"replay_{order_id or str(entry_ms)}"

    if st.button("▶ 복기 시작", key="btn_replay_start"):
        st.session_state["replay_open"] = True
        if cache_key not in st.session_state:
            with st.spinner("캔들 데이터 수집 중..."):
                st.session_state[cache_key] = get_candles(
                    symbol, entry_ms, interval="15", limit=50,
                    order_id=order_id,
                    sample_mode=st.session_state.get("sample_mode", ""),
                )

    if st.session_state.get("replay_open"):
        if cache_key not in st.session_state:
            with st.spinner("캔들 데이터 수집 중..."):
                st.session_state[cache_key] = get_candles(
                    symbol, entry_ms, interval="15", limit=50,
                    order_id=order_id,
                    sample_mode=st.session_state.get("sample_mode", ""),
                )
        candles = st.session_state[cache_key]
        fvgs    = detect_fvg(candles)
        obs     = detect_ob(candles)
        tl      = detect_trendline(candles)

        # ── 손절가 입력 ──
        st.divider()
        st.markdown("#### ✂️ 손절가 입력")
        _dir_raw   = buy_t.get("direction")
        _direction = _dir_raw if _dir_raw in ("Long", "Short") else \
                     ("Long" if buy_t.get("side", "Buy") == "Buy" else "Short")
        _entry_display = f"{float(buy_t.get('execPrice', 0)):,.2f}"
        _saved_stop = float(
            st.session_state["trade_tags"].get(order_id, {}).get("stop_price", 0.0) or 0.0
        )
        col1, col2 = st.columns([2, 1])
        with col1:
            stop_price = st.number_input(
                f"손절가 USDT  (진입가: {_entry_display} USDT)",
                min_value=0.0,
                value=_saved_stop,
                step=0.01,
                key=f"stop_{order_id}",
                help="진입 전 설정했던 손절가를 USDT 기준으로 입력하세요.",
            )
        if stop_price > 0 and stop_price != _saved_stop:
            save_trade_tag(
                session_id=session_id,
                order_id=order_id,
                symbol=symbol,
                ict_tag=st.session_state["trade_tags"].get(order_id, {}).get("tag", "확인필요"),
                user_confirmed=0,
                stop_price=stop_price,
            )
            st.session_state["trade_tags"][order_id] = {
                **st.session_state["trade_tags"].get(order_id, {}),
                "stop_price": stop_price,
            }
        with col2:
            if stop_price > 0:
                _entry  = float(buy_t.get("execPrice", 0))
                _exit_p = float(sell_t.get("execPrice", 0))
                if _exit_p == _entry:
                    _pnl_fb = float(sell_t.get("closedPnl", 0) or 0)
                    _qty_fb = float(buy_t.get("orderQty", 1) or 1)
                    if _qty_fb > 0:
                        _exit_p = _entry + _pnl_fb / _qty_fb
                if _direction == "Long":
                    _risk   = _entry - stop_price
                    _reward = _exit_p - _entry
                else:
                    _risk   = stop_price - _entry
                    _reward = _entry - _exit_p
                _rr = round(_reward / _risk, 2) if _risk > 0 else 0.0
                _color = "#2E7D32" if _rr >= 2 else "#E65100" if _rr >= 1 else "#C62828"
                st.markdown(
                    f'<div style="background:#1E2A3A;border-radius:8px;padding:10px 14px;text-align:center">'
                    f'<div style="font-size:11px;color:#85B7EB">손익비 (RR)</div>'
                    f'<div style="font-size:24px;font-weight:700;color:{_color}">'
                    f'{_rr:.2f}</div></div>',
                    unsafe_allow_html=True,
                )

        # ── 포지션 사이징 ──
        st.markdown("#### 💰 포지션 사이징")
        _ps_col1, _ps_col2, _ps_col3 = st.columns(3)
        with _ps_col1:
            _saved_fixed   = float(
                st.session_state["trade_tags"].get(order_id, {}).get("fixed_loss", 0.0) or 0.0
            )
            _default_fixed = st.session_state.get("default_fixed_loss", 0.0)
            _init_fixed    = _saved_fixed if _saved_fixed > 0 else _default_fixed
            fixed_loss = st.number_input(
                "고정 손실 금액 ($)",
                min_value=0.0,
                value=float(_init_fixed),
                step=1.0,
                key=f"fixed_loss_{order_id}",
                help="기본값에서 이 거래만 개별 조정 가능",
            )

        _entry_p    = float(buy_t.get("execPrice", 0))
        _actual_qty = float(buy_t.get("orderQty", 0))
        if stop_price > 0 and fixed_loss > 0:
            _risk_per_unit = abs(_entry_p - stop_price)
            _ideal_qty = round(fixed_loss / _risk_per_unit, 4) if _risk_per_unit > 0 else 0.0
        else:
            _ideal_qty = 0.0

        with _ps_col2:
            if _ideal_qty > 0:
                st.metric("적정 진입 수량", f"{_ideal_qty}")
            else:
                st.metric("적정 진입 수량", "—")

        with _ps_col3:
            if stop_price > 0 and fixed_loss > 0 and _ideal_qty > 0:
                _ratio = round(_actual_qty / _ideal_qty, 1)
                _ps_color = "#2E7D32" if _ratio <= 1.2 else "#E65100" if _ratio <= 2.0 else "#C62828"
                _ps_label = "적정" if _ratio <= 1.2 else "과다" if _ratio <= 2.0 else "위험"
                st.markdown(
                    f'<div style="text-align:center;padding:12px;'
                    f'background:#1E2A3A;border-radius:8px">'
                    f'<div style="font-size:11px;color:#85B7EB">실제/적정 비율</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{_ps_color}">'
                    f'{_ratio}x {_ps_label}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.metric("실제/적정 비율", "—")

        if fixed_loss > 0 and _ideal_qty > 0:
            save_trade_tag(
                session_id=session_id,
                order_id=order_id,
                symbol=symbol,
                ict_tag=st.session_state.get(f"user_tag_{order_id}", "확인필요"),
                user_confirmed=0,
                fixed_loss=fixed_loss,
                ideal_qty=_ideal_qty,
                actual_qty=_actual_qty,
            )

        # ── A+ 채점 (수동 실행) ──
        cache_key_aplus = f"aplus_{order_id}_{stop_price}_{fixed_loss}"
        st.divider()
        if stop_price > 0:
            st.caption("✅ 손절가 입력됨 — A+ 채점을 시작할 수 있습니다")
        else:
            st.caption("⚠️ 손절가를 입력하면 더 정확한 채점이 가능합니다")

        if st.button("🏆 A+ 채점 시작", key=f"btn_aplus_{order_id}",
                     help="손절가와 고정 손실 금액 입력 후 채점하세요"):
            with st.spinner("A+ 채점 중..."):
                try:
                    st.session_state[cache_key_aplus] = entry_reason_node(
                        candles=candles,
                        ict_patterns={"fvg_zones": fvgs, "ob_zones": obs, "trend_info": tl},
                        trade={
                            "symbol":    symbol,
                            "side":      buy_t.get("side", ""),
                            "direction": _direction,
                            "execPrice": buy_t.get("execPrice", 0),
                            "exitPrice": sell_t.get("execPrice", 0),
                            "execTime":  buy_t.get("execTime", 0),
                            "closedPnl": sell_t.get("closedPnl", 0),
                            "stop_price": stop_price,
                        },
                        session_id=session_id,
                    )
                except Exception:
                    st.session_state[cache_key_aplus] = None

        # ── 캔들차트 + ICT 오버레이 ──
        df_c = pd.DataFrame(candles)
        df_c["dt"] = (
            pd.to_datetime(df_c["timestamp"], unit="ms", utc=True)
            .dt.tz_convert("Asia/Seoul")
        )

        fig = go.Figure(data=[go.Candlestick(
            x=df_c["dt"],
            open=df_c["open"],
            high=df_c["high"],
            low=df_c["low"],
            close=df_c["close"],
            name=symbol,
            increasing_line_color="#26a69a",
            decreasing_line_color="#ef5350",
        )])

        for fvg in fvgs:
            fvg_dt = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True).tz_convert("Asia/Seoul")
            color  = "rgba(255,200,0,0.2)" if fvg["type"] == "bullish" else "rgba(255,80,80,0.15)"
            fig.add_shape(
                type="rect",
                x0=fvg_dt, x1=df_c["dt"].max(),
                y0=fvg["bottom"], y1=fvg["top"],
                fillcolor=color, line_width=0, layer="below",
            )

        for ob in obs:
            ob_dt  = pd.to_datetime(ob["timestamp"], unit="ms", utc=True).tz_convert("Asia/Seoul")
            ob_clr = "rgba(0,200,100,0.15)" if ob["type"] == "bullish" else "rgba(200,50,50,0.15)"
            fig.add_shape(
                type="rect",
                x0=ob_dt, x1=df_c["dt"].max(),
                y0=ob["bottom"], y1=ob["top"],
                fillcolor=ob_clr, line_width=0, layer="below",
            )

        if tl:
            dt0 = df_c["dt"].iloc[0]
            dt1 = df_c["dt"].iloc[-1]
            ts_to_idx = {c["timestamp"]: i for i, c in enumerate(candles)}

            def _tl_y(line_dict):
                slope  = line_dict["slope"]
                pts    = line_dict["points"]
                i0     = ts_to_idx.get(pts[0]["timestamp"], 0)
                y0_ref = pts[0]["price"]
                n      = len(candles)
                return y0_ref + slope * (0 - i0), y0_ref + slope * (n - 1 - i0)

            res_tl = tl.get("resistance")
            sup_tl = tl.get("support")

            if res_tl:
                ry0, ry1 = _tl_y(res_tl)
                fig.add_trace(go.Scatter(
                    x=[dt0, dt1], y=[ry0, ry1],
                    mode="lines", line=dict(color="red", dash="dash", width=1),
                    opacity=0.6, name="저항선",
                ))
            if sup_tl:
                sy0, sy1 = _tl_y(sup_tl)
                fig.add_trace(go.Scatter(
                    x=[dt0, dt1], y=[sy0, sy1],
                    mode="lines", line=dict(color="green", dash="dash", width=1),
                    opacity=0.6, name="지지선",
                ))
            if tl.get("is_channel") and res_tl and sup_tl:
                ry0, ry1 = _tl_y(res_tl)
                sy0, sy1 = _tl_y(sup_tl)
                fig.add_trace(go.Scatter(
                    x=[dt0, dt1, dt1, dt0, dt0],
                    y=[ry0, ry1, sy1, sy0, ry0],
                    fill="toself", fillcolor="rgba(150,150,150,0.08)",
                    line=dict(width=0), showlegend=False, hoverinfo="skip",
                ))

        _KST      = ZoneInfo("Asia/Seoul")
        entry_dt  = datetime.fromtimestamp(entry_ms / 1000, tz=_KST)
        exit_dt   = datetime.fromtimestamp(exit_ms  / 1000, tz=_KST)
        entry_row = df_c[df_c["timestamp"] <= entry_ms].tail(1)
        exit_row  = df_c[df_c["timestamp"] <= exit_ms].tail(1)
        _entry_price_marker = float(buy_t.get("execPrice", 0))
        _exit_price_marker  = float(sell_t.get("execPrice", 0))
        if not entry_row.empty:
            fig.add_trace(go.Scatter(
                x=[entry_dt], y=[_entry_price_marker],
                mode="markers", marker=dict(symbol="triangle-up", size=14, color="#1565C0"),
                name="진입",
            ))
        if not exit_row.empty:
            fig.add_trace(go.Scatter(
                x=[exit_dt], y=[_exit_price_marker],
                mode="markers", marker=dict(symbol="triangle-down", size=14, color="#C62828"),
                name="청산",
            ))

        if stop_price > 0:
            fig.add_hline(
                y=stop_price,
                line_dash="dot",
                line_color="#FF6B6B",
                line_width=1.5,
                annotation_text=f"SL {stop_price:,.2f}",
                annotation_position="right",
            )

        exec_date_kst = (
            pd.to_datetime(entry_ms, unit="ms", utc=True)
            .tz_convert("Asia/Seoul")
            .strftime("%Y-%m-%d")
        )
        fig.update_layout(
            title=f"{symbol} 거래 복기 — {exec_date_kst}",
            xaxis_rangeslider_visible=False,
            height=520,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"candle_{order_id}")

        _entry_v = validate_price_in_candle(float(buy_t.get("execPrice", 0)), candles, entry_ms)
        _exit_v  = validate_price_in_candle(float(sell_t.get("execPrice", 0)), candles, exit_ms)
        if not _entry_v["valid"] and _entry_v.get("warning"):
            st.warning(f"⚠️ 진입가 {_entry_v['warning']}")
        if not _exit_v["valid"] and _exit_v.get("warning"):
            st.warning(f"⚠️ 청산가 {_exit_v['warning']}")

        # ── A+ 채점 결과 ──
        aplus_result = st.session_state.get(cache_key_aplus)
        if aplus_result:
            render_section_header("A+ 채점", "ICT 기준 5가지 진입 품질 평가")
            score = aplus_result["aplus_score"]
            score_color = "#2E7D32" if score >= 4 else "#E65100" if score >= 2 else "#C62828"
            st.markdown(
                f'<div style="font-size:24px; font-weight:700; color:{score_color}; margin-bottom:12px;">{score}/5</div>',
                unsafe_allow_html=True,
            )
            bd = aplus_result["aplus_breakdown"]
            CRITERIA_DESC = {
                "structure_entry": ("구조 진입", "FVG 또는 OB 구조권 내 진입"),
                "bounce_confirm":  ("반등 확인", "진입 전 캔들 반등 1개 이상 확인"),
                "trend_aligned":   ("추세 정렬", "상위 타임프레임 추세 방향과 일치"),
                "killzone":        ("킬존",      "런던(02-05 UTC) 또는 뉴욕(07-10 UTC) 세션"),
                "stop_discipline": ("손절 규율", "당일 손절 횟수 3회 미만"),
            }
            desc_html = '<div style="background:#1E2A3A;border-radius:8px;padding:10px 14px;margin:8px 0;font-size:11px;line-height:1.9;color:#A8B8C8">'
            desc_html += '<b style="color:#7EB8D4">📐 A+ 채점 기준</b><br>'
            for _k, (_label, _desc) in CRITERIA_DESC.items():
                icon = "✅" if bd.get(_k) else "❌"
                desc_html += f"{icon} <b>{_label}</b>: {_desc}<br>"
            _stop_assessment = bd.get("stop_assessment", "")
            if _stop_assessment and _stop_assessment != "손절가 미입력":
                _stop_icon = "✅" if bd.get("stop_position") else "❌"
                _rr_disp   = f" | RR {bd['rr']:.2f}" if bd.get("rr", 0) > 0 else ""
                desc_html += f"{_stop_icon} <b>손절 위치</b>: {_stop_assessment}{_rr_disp}<br>"
            desc_html += "</div>"
            st.markdown(desc_html, unsafe_allow_html=True)

        # ── ICT 복기 분석 ──
        render_section_header("ICT 복기 분석", "진입 근거 추론 + 코칭")
        if aplus_result:
            st.info(f"**진입 근거:** {aplus_result['entry_reason']}")
            st.warning(f"**코칭:** {aplus_result['coaching']}")
        else:
            pnl = float(sell_t.get("closedPnl", 0) or 0)
            selected_trade = {
                "symbol":      symbol,
                "side":        buy_t.get("side", ""),
                "entry_price": float(buy_t.get("execPrice",  0)),
                "exit_price":  float(sell_t.get("execPrice", 0)),
                "closed_pnl":  pnl,
                "result":      "win" if pnl > 0 else "loss",
                "entry_ms":    entry_ms,
            }
            with st.spinner("복기 코멘트 생성 중..."):
                comment = replay_coach_node(candles, {"fvg_zones": fvgs, "ob_zones": obs}, selected_trade)
            st.info(comment)

        # ── 자동 감지 셋업 ──
        detected_setups = []
        if fvgs: detected_setups.append("FVG")
        if obs:  detected_setups.append("OB")
        auto_setup = "+".join(detected_setups) if detected_setups else "확인필요"
        st.badge(f"자동 감지 셋업: {auto_setup}")

        save_trade_tag(session_id, order_id, symbol, auto_setup, user_confirmed=0)
        st.session_state["trade_tags"][order_id] = {"tag": auto_setup, "confirmed": 0}

        _col1, _col2, _col3 = st.columns(3)
        with _col1:
            st.metric("FVG", f"{len(fvgs)}개")
        with _col2:
            st.metric("OB", f"{len(obs)}개")
        with _col3:
            _channel = tl.get("channel_type", "불명확") if tl else "불명확"
            st.metric("추세", _channel)

        with st.expander("ICT 패턴 상세 보기", expanded=False):
            col_fvg, col_ob, col_tl = st.columns(3)
            with col_fvg:
                if fvgs:
                    st.markdown(f"**FVG: {len(fvgs)}개**")
                    for fvg in fvgs:
                        fvg_time = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True).strftime("%m-%d %H:%M")
                        tag = "📈 Bull" if fvg["type"] == "bullish" else "📉 Bear"
                        st.caption(f"{tag} | {fvg_time} | {fvg['bottom']:.1f}~{fvg['top']:.1f}")
                else:
                    st.info("FVG 없음")

            with col_ob:
                if obs:
                    st.markdown(f"**OB: {len(obs)}개**")
                    for ob in obs:
                        ob_time = pd.to_datetime(ob["timestamp"], unit="ms", utc=True).strftime("%m-%d %H:%M")
                        tag = "🟢 Bull" if ob["type"] == "bullish" else "🔴 Bear"
                        st.caption(f"{tag} | {ob_time} | {ob['bottom']:.1f}~{ob['top']:.1f}")
                else:
                    st.info("OB 없음")

            with col_tl:
                if tl and (tl.get("resistance") or tl.get("support")):
                    channel_label = f" ({tl['channel_type']} 채널)" if tl.get("is_channel") else ""
                    st.markdown(f"**추세선{channel_label}**")
                    if tl.get("resistance"):
                        st.caption(f"저항선 기울기: {tl['resistance']['slope']:.2f}")
                    if tl.get("support"):
                        st.caption(f"지지선 기울기: {tl['support']['slope']:.2f}")
                else:
                    st.info("추세선 없음")

        journal_entries = st.session_state.get("last_journal_entries", [])
        matching = [e for e in journal_entries if e.get("symbol") == symbol]
        if matching:
            with st.expander("📒 매매일지"):
                for entry in matching:
                    st.write(f"**진입 근거**: {entry.get('entry_reason', '') or '추론 불가'}")
                    st.write(f"**청산 근거**: {entry.get('exit_reason', '') or '추론 불가'}")
                    st.write(f"**회고**: {entry.get('reflection', '') or '-'}")

        # ── 태그 확인/수정 ──
        _tag_options = ["FVG", "OB", "FVG+OB", "추세추종", "확인필요", "셋업없음"]
        _default_idx = _tag_options.index(auto_setup) if auto_setup in _tag_options else 4
        user_tag = st.selectbox(
            "태그 확인/수정",
            _tag_options,
            index=_default_idx,
            key=f"user_tag_{order_id}",
        )
        if st.button("✅ 태그 확정", key=f"confirm_tag_{order_id}"):
            save_trade_tag(session_id, order_id, symbol, user_tag, user_confirmed=1)
            st.session_state["trade_tags"][order_id] = {"tag": user_tag, "confirmed": 1}
            st.success(f"태그 저장: {user_tag}")
