import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timezone

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
from market.candles import get_candles
from db import save_trade_tag, load_trade_tags

st.set_page_config(page_title="TradeCoach | 대시보드", page_icon="📊", layout="wide")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

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

with st.sidebar.expander("📊 대시보드", expanded=True):
    c1, c2 = st.columns(2)
    c1.metric("승률",        f"{stats.get('win_rate', 0):.1%}")
    c2.metric("평균 수익률", f"{stats.get('avg_return_rate', 0):.2f}%")
    c3, c4 = st.columns(2)
    c3.metric("수익금",      pnl_display)
    c4.metric("손절 일관성", f"{stats.get('loss_consistency', 0):.2f}")

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

    st.divider()
    st.markdown("**📋 트레이딩 철학**")
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

    st.markdown("**📐 ICT 핵심 원칙**")
    ICT_RULES = [
        ("🕐", "킬존 진입",  "런던 02-05 UTC / 뉴욕 07-10 UTC"),
        ("📊", "구조적 진입", "FVG 또는 OB 구간 내 진입"),
        ("📈", "추세 정렬",  "상위 추세 방향으로만 진입"),
        ("🛡️", "손절 위치",  "구조적 레벨(FVG/OB 하단) 바깥"),
    ]
    for icon, title, desc in ICT_RULES:
        st.markdown(f"{icon} **{title}**: {desc}")

    judge_result = res.get("judge_result", "")
    judge_passed = res.get("judge_passed", True)
    if judge_result:
        if judge_passed:
            st.success(f"✅ {judge_result}")
        else:
            st.warning(f"⚠️ 보완 필요: {judge_result}")

# ③ 퀴즈 expander
quiz_q = st.session_state.get("last_quiz_question", "")
if quiz_q:
    with st.sidebar.expander("📝 오늘의 퀴즈", expanded=False):
        try:
            quiz = json.loads(quiz_q)
            st.write(quiz["question"])
            selected_quiz = st.radio(
                "보기를 선택하세요",
                quiz["options"],
                key="quiz_radio",
                index=None,
            )
            if st.button("제출", key="quiz_submit"):
                correct_idx  = quiz["answer"]
                selected_idx = quiz["options"].index(selected_quiz) if selected_quiz else -1
                if selected_idx == correct_idx:
                    st.success(f"✅ 정답! {quiz['options'][correct_idx]}")
                else:
                    st.error(f"❌ 오답. 정답: {quiz['options'][correct_idx]}")
                with st.expander("해설 보기"):
                    st.write(quiz["explanation"])
        except (json.JSONDecodeError, KeyError):
            st.write(quiz_q)

# ═══════════════════════════ 메인 화면 ══════════════════════════════════════

# 상단: 제목 + 모드 표시
sample_label = st.session_state.get("sample_label", "")
mode_badge   = f" ({sample_label})" if sample_label else " (실계정)"
st.title(f"📊 TradeCoach 대시보드{mode_badge}")

# ── 거래내역 테이블 ──────────────────────────────────────────────────────────
st.subheader("📋 거래내역")

if trade_pairs:
    rows = []
    for tid, buy, sell in trade_pairs:
        pnl         = float(sell.get("closedPnl", 0) or 0)
        entry_price = float(buy.get("execPrice", 0) or 0)
        exit_price  = float(sell.get("execPrice", 0) or 0)
        qty         = float(buy.get("orderQty", 0) or 0)
        ret_pct     = (exit_price - entry_price) / entry_price * 100 if entry_price else 0
        direction   = buy.get("direction", "Long" if buy.get("side", "Buy") == "Buy" else "Short")
        rows.append({
            "거래번호":      tid,
            "종목":          buy.get("symbol", ""),
            "방향":          "🟢 Long" if direction == "Long" else "🔴 Short",
            "진입가":        entry_price,
            "청산가":        exit_price,
            "수량":          qty,
            "실현손익($)":   f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}",
            "수익률(%)":     round(ret_pct, 2),
            "진입시각(KST)": _ms_to_kst(buy.get("execTime", 0)),
            "청산시각(KST)": _ms_to_kst(sell.get("execTime", 0)),
            "결과":          "✅ WIN" if pnl >= 0 else "❌ LOSS",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
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

# ── 복기 뷰어 ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("🔍 복기 뷰어")

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
    cache_key       = f"replay_{order_id or str(entry_ms)}"
    cache_key_aplus = f"aplus_{order_id}"

    if st.button("▶ 복기 시작", type="primary", key="btn_replay_start"):
        st.session_state["replay_open"] = True
        if cache_key not in st.session_state:
            with st.spinner("캔들 데이터 수집 중..."):
                st.session_state[cache_key] = get_candles(
                    symbol, entry_ms, interval="15", limit=50,
                    order_id=order_id,
                    sample_mode=st.session_state.get("sample_mode", ""),
                )
        if cache_key_aplus not in st.session_state:
            _c    = st.session_state[cache_key]
            _fvgs = detect_fvg(_c)
            _obs  = detect_ob(_c)
            _tl   = detect_trendline(_c)
            with st.spinner("A+ 채점 중..."):
                try:
                    st.session_state[cache_key_aplus] = entry_reason_node(
                        candles=_c,
                        ict_patterns={"fvg_zones": _fvgs, "ob_zones": _obs, "trend_info": _tl},
                        trade={
                            "symbol":    symbol,
                            "side":      buy_t.get("side", ""),
                            "execPrice": buy_t.get("execPrice", 0),
                            "execTime":  buy_t.get("execTime",  0),
                            "closedPnl": sell_t.get("closedPnl", 0),
                        },
                        session_id=session_id,
                    )
                except Exception:
                    st.session_state[cache_key_aplus] = None

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

        # ── 캔들차트 + ICT 오버레이 ──
        df_c = pd.DataFrame(candles)
        df_c["dt"] = pd.to_datetime(df_c["timestamp"], unit="ms", utc=True)

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
            fvg_dt = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True)
            color  = "rgba(255,200,0,0.2)" if fvg["type"] == "bullish" else "rgba(255,80,80,0.15)"
            fig.add_shape(
                type="rect",
                x0=fvg_dt, x1=df_c["dt"].max(),
                y0=fvg["bottom"], y1=fvg["top"],
                fillcolor=color, line_width=0, layer="below",
            )

        for ob in obs:
            ob_dt  = pd.to_datetime(ob["timestamp"], unit="ms", utc=True)
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

        entry_dt  = datetime.fromtimestamp(entry_ms / 1000, tz=timezone.utc)
        exit_dt   = datetime.fromtimestamp(exit_ms  / 1000, tz=timezone.utc)
        entry_row = df_c[df_c["timestamp"] <= entry_ms].tail(1)
        exit_row  = df_c[df_c["timestamp"] <= exit_ms].tail(1)
        if not entry_row.empty:
            fig.add_trace(go.Scatter(
                x=[entry_dt], y=[float(entry_row["low"].iloc[0]) * 0.999],
                mode="markers", marker=dict(symbol="triangle-up", size=14, color="#1565C0"),
                name="진입",
            ))
        if not exit_row.empty:
            fig.add_trace(go.Scatter(
                x=[exit_dt], y=[float(exit_row["high"].iloc[0]) * 1.001],
                mode="markers", marker=dict(symbol="triangle-down", size=14, color="#C62828"),
                name="청산",
            ))

        fig.update_layout(
            title=f"{symbol} 복기 차트 (FVG/OB/추세선 오버레이)",
            xaxis_rangeslider_visible=False,
            height=520,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"candle_{order_id}")

        # ── A+ 채점 결과 ──
        aplus_result = st.session_state.get(cache_key_aplus)
        if aplus_result:
            score = aplus_result["aplus_score"]
            score_color = "#2E7D32" if score >= 4 else "#E65100" if score >= 2 else "#C62828"
            st.markdown(
                f'<h3 style="color:{score_color}">A+ 점수: {score}/5</h3>',
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
            desc_html += "</div>"
            st.markdown(desc_html, unsafe_allow_html=True)

        # ── ICT 복기 분석 ──
        st.markdown("#### 🔍 ICT 복기 분석")
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
