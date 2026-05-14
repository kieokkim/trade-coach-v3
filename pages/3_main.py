import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from collections import defaultdict
from datetime import datetime, timezone

# ── 유틸 함수 ────────────────────────────────────────────────────────────────

def _ms_to_kst(ms) -> str:
    return (
        pd.to_datetime(int(ms), unit="ms", utc=True)
        .tz_convert("Asia/Seoul")
        .strftime("%Y-%m-%d %H:%M")
    )

def _extract_setup(order_id: str) -> str:
    oid = str(order_id).lower()
    if oid.startswith("fvg"):    return "FVG"
    if oid.startswith("ob"):     return "OB"
    if oid.startswith("sweep"):  return "유동성스윕"
    if oid.startswith("random"): return "셋업없음"
    return "기타"

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

from nodes.quiz_nodes import evaluate_quiz
from nodes.replay_coach_node import replay_coach_node
from nodes.coaching_nodes import generate_setup_suggestion
from ict.fvg_detector import detect_fvg
from market.candles import get_candles
from utils.chart import render_candle_chart

st.set_page_config(page_title="TradeCoach | 대시보드", page_icon="📊", layout="wide")

# ── 결과 없으면 API 입력 페이지로 ──────────────────────────────────────────
if "last_result" not in st.session_state:
    st.info("분석 결과가 없습니다. API 입력 페이지에서 시작해주세요.")
    if st.button("← API 입력 페이지로"):
        st.switch_page("pages/1_api_input.py")
    st.stop()

session_id = st.session_state.get("session_id", "default")
res        = st.session_state["last_result"]

# ── 전역: Buy/Sell 페어링 ────────────────────────────────────────────────────
raw_trades  = res.get("raw_trades", [])
buy_trades  = [t for t in raw_trades if str(t.get("side", "")).lower() == "buy"]
sell_trades = [t for t in raw_trades if str(t.get("side", "")).lower() == "sell"
               and str(t.get("closedPnl", "0")) != "0"]

trade_pairs: list[tuple[str, dict, dict]] = []  # (trade_id, buy, sell)
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

st.title("📊 TradeCoach 대시보드")

tab1, tab2, tab3 = st.tabs(["📊 KPI 대시보드", "📋 거래내역 리스트", "📚 셋업 태깅"])

# ═══════════════════════════ Tab 1: KPI 대시보드 ════════════════════════════

with tab1:
    stats     = st.session_state.get("last_stats", {})
    total_pnl = sum(float(t.get("closedPnl", 0) or 0) for t in raw_trades)

    st.subheader("📌 핵심 지표")
    with st.expander("ℹ️ 지표 설명 보기"):
        st.markdown(
            "- **승률**: 전체 거래 중 익절로 마감된 비율\n"
            "- **평균 수익률**: 익절/손절을 포함한 거래당 평균 손익률 (%)\n"
            "- **수익금**: 전체 실현 손익 합계 (USDT 기준)\n"
            "- **손절 일관성**: 손절 금액이 얼마나 일정한지 (1에 가까울수록 손절 기준이 규칙적)"
        )
    pnl_display = f"+${total_pnl:.2f}" if total_pnl >= 0 else f"-${abs(total_pnl):.2f}"
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("승률",        f"{stats.get('win_rate', 0):.1%}")
    c2.metric("평균 수익률", f"{stats.get('avg_return_rate', 0):.2f}%")
    c3.metric("수익금",       pnl_display)
    c4.metric("손절 일관성", f"{stats.get('loss_consistency', 0):.2f}")

    weaknesses = st.session_state.get("last_weaknesses", [])
    if weaknesses:
        st.subheader("⚠️ 감지된 약점")
        for w in weaknesses:
            st.info(w)

    action_rule = st.session_state.get("last_action_rule", "")
    if action_rule:
        st.subheader("★ 내일의 규칙")
        st.success(action_rule)

    setup_analysis = st.session_state.get("last_setup", {})
    if setup_analysis:
        st.subheader("📈 셋업별 수익률")
        df_setup = pd.DataFrame(
            list(setup_analysis.items()),
            columns=["셋업", "평균 수익률 (%)"],
        ).set_index("셋업")
        st.bar_chart(df_setup)

    coaching = st.session_state.get("last_coaching", "")
    if coaching:
        st.subheader("💬 코칭 피드백")
        st.write(coaching)

    # 퀴즈
    quiz_question = st.session_state.get("last_quiz_question", "")
    if quiz_question:
        st.divider()
        st.subheader("🧠 개념 확인 퀴즈")
        st.write(f"**{quiz_question}**")

        quiz_result = st.session_state.get("last_quiz_result", "")

        if not quiz_result:
            if st.button("💡 힌트 보기", key="quiz_hint_btn"):
                st.session_state["quiz_show_hint"] = True
            if st.session_state.get("quiz_show_hint"):
                concept = st.session_state.get("last_quiz_concept", "")
                if concept:
                    st.info(f"힌트: 이 문제는 **{concept}** 개념과 관련이 있습니다.")

            quiz_answer = st.text_input(
                "답변을 입력하세요",
                key="quiz_answer_input",
                placeholder="자유롭게 답변해주세요",
            )
            if st.button("📝 답변 제출", key="submit_quiz"):
                if quiz_answer.strip():
                    with st.spinner("답변 평가 중..."):
                        result, feedback = evaluate_quiz(
                            session_id=session_id,
                            quiz_question=quiz_question,
                            quiz_answer=quiz_answer,
                            current_concept=st.session_state.get("last_quiz_concept", ""),
                            retry_count=st.session_state.get("quiz_retry_count", 0),
                        )
                    st.session_state["last_quiz_result"]   = result
                    st.session_state["last_quiz_feedback"] = feedback
                    st.rerun()
                else:
                    st.warning("답변을 입력해주세요.")
        else:
            feedback = st.session_state.get("last_quiz_feedback", "")
            if quiz_result == "pass":
                st.success(f"✅ 정답! {feedback}")
            else:
                st.error(f"❌ 다시 생각해보세요. {feedback}")
                if st.button("🔄 다시 시도", key="retry_quiz"):
                    retry = st.session_state.get("quiz_retry_count", 0) + 1
                    st.session_state["quiz_retry_count"] = retry
                    st.session_state.pop("last_quiz_result",   None)
                    st.session_state.pop("last_quiz_feedback", None)
                    st.session_state.pop("quiz_show_hint",     None)
                    st.rerun()

# ════════════════════════ Tab 2: 거래내역 리스트 + 복기 뷰어 ════════════════

with tab2:
    st.subheader("📋 거래내역")

    # ── Buy/Sell 페어링 테이블 ───────────────────────────────────────────────
    if trade_pairs:
        rows = []
        for tid, buy, sell in trade_pairs:
            pnl = float(sell.get("closedPnl", 0) or 0)
            entry_price = float(buy.get("execPrice", 0) or 0)
            exit_price  = float(sell.get("execPrice", 0) or 0)
            qty         = float(buy.get("orderQty", 0) or 0)
            ret_pct     = (exit_price - entry_price) / entry_price * 100 if entry_price else 0
            rows.append({
                "거래번호":      tid,
                "종목":          buy.get("symbol", ""),
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
        display_cols = [c for c in ["execTime", "symbol", "side", "execPrice", "orderQty", "closedPnl"] if c in df_trades.columns]
        df_display = df_trades[display_cols].copy() if display_cols else df_trades.copy()
        if "execTime" in df_display.columns:
            df_display["execTime"] = df_display["execTime"].apply(_ms_to_kst)
        df_display.rename(columns={k: v for k, v in _COL_KO.items() if k in df_display.columns}, inplace=True)
        st.dataframe(df_display, use_container_width=True)
    else:
        st.caption("거래내역 없음")

    # ── 매매일지 (journal_entries 기반) ──────────────────────────────────────
    journal_entries = st.session_state.get("last_journal_entries", [])
    if journal_entries:
        journal_entries = sorted(journal_entries, key=lambda x: x.get("date", ""))
        st.divider()
        st.subheader("📒 매매일지")
        for entry in journal_entries:
            label = (
                f"{entry.get('date', '')} | "
                f"{entry.get('symbol', '')} | "
                f"{'✅ 승' if entry.get('result') == 'win' else '❌ 패'}"
            )
            with st.expander(label):
                st.write(f"**진입 근거**: {entry.get('entry_reason', '') or '추론 불가'}")
                st.write(f"**청산 근거**: {entry.get('exit_reason', '') or '추론 불가'}")
                st.write(f"**회고**: {entry.get('reflection', '') or '-'}")

    # ── 복기 뷰어 ────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔍 복기 뷰어")

    if not trade_pairs:
        st.caption("복기할 트레이드 쌍이 없습니다. (raw_trades에 Buy/Sell 쌍 필요)")
    else:
        pair_labels = [_pair_label(tid, b, s) for tid, b, s in trade_pairs]
        selected_label = st.selectbox("트레이드 선택", pair_labels, key="replay_select")
        sel_idx = pair_labels.index(selected_label)

        if st.button("▶ 복기 시작", type="primary", key="replay_btn"):
            sel_trade_id, buy_t, sell_t = trade_pairs[sel_idx]
            symbol   = buy_t.get("symbol", "BTCUSDT")
            entry_ms = int(buy_t.get("execTime",  0))
            exit_ms  = int(sell_t.get("execTime", 0))

            # 캔들 캐싱
            cache_key = f"replay_{buy_t.get('orderId', str(entry_ms))}"
            if cache_key not in st.session_state:
                with st.spinner("캔들 데이터 수집 중..."):
                    st.session_state[cache_key] = get_candles(symbol, entry_ms, interval="15", limit=50)
            candles = st.session_state[cache_key]
            fvgs    = detect_fvg(candles)

            # Plotly Figure (FVG 오버레이)
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
                    fillcolor=color,
                    line_width=0,
                    layer="below",
                )

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
                title=f"{symbol} 복기 차트 (FVG 오버레이)",
                xaxis_rangeslider_visible=False,
                height=520,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig, use_container_width=True)

            # 자동 셋업 태깅
            auto_setup = "FVG" if fvgs else "확인필요"
            st.session_state[f"setup_tag_{sel_trade_id}"] = auto_setup
            st.badge(f"자동 감지 셋업: {auto_setup}")

            # FVG 결과 텍스트
            if fvgs:
                st.markdown(f"**FVG 감지: {len(fvgs)}개**")
                for fvg in fvgs:
                    fvg_time = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True).strftime("%Y-%m-%d %H:%M")
                    tag      = "📈 Bullish" if fvg["type"] == "bullish" else "📉 Bearish"
                    st.caption(f"{tag} FVG  |  {fvg_time} UTC  |  {fvg['bottom']:.2f} ~ {fvg['top']:.2f}")
            else:
                st.info("이 구간에서 FVG가 탐지되지 않았습니다.")

            # LLM 복기 코멘트
            pnl = float(sell_t.get("closedPnl", 0) or 0)
            selected_trade = {
                "symbol":      symbol,
                "side":        buy_t.get("side", ""),
                "entry_price": float(buy_t.get("execPrice",  0)),
                "exit_price":  float(sell_t.get("execPrice", 0)),
                "closed_pnl":  pnl,
                "result":      "win" if pnl > 0 else "loss",
            }
            ict_patterns = {"fvg_zones": fvgs}

            with st.spinner("복기 코멘트 생성 중..."):
                comment = replay_coach_node(candles, ict_patterns, selected_trade)
            st.info(comment)

# ═══════════════════════════ Tab 3: 셋업 태깅 ══════════════════════════════

with tab3:
    st.subheader("📚 셋업 태깅")

    journal_entries = st.session_state.get("last_journal_entries", [])
    setup_analysis  = st.session_state.get("last_setup", {})

    win_trades  = [t for t in journal_entries if t.get("result") == "win"]
    loss_trades = [t for t in journal_entries if t.get("result") == "loss"]

    # ── 섹션 1: 익절/손절 분류 요약 ────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("전체 거래", len(journal_entries))
    c2.metric("익절", len(win_trades))
    c3.metric("손절", len(loss_trades))

    # ── 섹션 2: 셋업별 수익률 (orderId prefix 기반) ─────────────────────────
    if not setup_analysis and trade_pairs:
        ret_by_setup: dict[str, list[float]] = defaultdict(list)
        for _, buy, sell in trade_pairs:
            setup       = _extract_setup(buy.get("orderId", ""))
            entry_price = float(buy.get("execPrice", 1) or 1)
            exit_price  = float(sell.get("execPrice", 0) or 0)
            ret_pct     = (exit_price - entry_price) / entry_price * 100
            ret_by_setup[setup].append(ret_pct)
        setup_analysis = {
            s: round(sum(v) / len(v), 4)
            for s, v in ret_by_setup.items()
        }

    best_setup  = max(setup_analysis, key=setup_analysis.get) if setup_analysis else ""
    worst_setup = min(setup_analysis, key=setup_analysis.get) if setup_analysis else ""

    if setup_analysis:
        st.subheader("📈 셋업별 평균 수익률")
        df_setup = pd.DataFrame(
            list(setup_analysis.items()), columns=["셋업", "평균 수익률 (%)"]
        ).set_index("셋업")
        st.bar_chart(df_setup)

        if best_setup:
            st.success(f"가장 많이 수익난 셋업: **{best_setup}** ({setup_analysis[best_setup]:.2f}%)")
        if worst_setup and worst_setup != best_setup:
            st.error(f"가장 많이 손실난 셋업: **{worst_setup}** ({setup_analysis[worst_setup]:.2f}%)")
    else:
        st.info("셋업 분석 데이터가 없습니다. 거래 내역을 먼저 분석해주세요.")

    # ── 섹션 3: LLM 개선 제안 ─────────────────────────────────────────────
    if setup_analysis:
        if st.button("💡 개선 제안 생성", key="tab3_suggest_btn"):
            with st.spinner("LLM 분석 중..."):
                suggestion = generate_setup_suggestion(
                    win_count=len(win_trades),
                    loss_count=len(loss_trades),
                    best_setup=best_setup,
                    worst_setup=worst_setup,
                    setup_analysis=setup_analysis,
                )
            st.session_state["tab3_suggestion"] = suggestion

        if "tab3_suggestion" in st.session_state:
            st.info(st.session_state["tab3_suggestion"])

    # ── 섹션 4: 차트 태깅 ──────────────────────────────────────────────────
    st.divider()
    st.subheader("🏷️ 거래 차트 태깅")

    if not trade_pairs:
        st.caption("표시할 트레이드 쌍이 없습니다.")
    else:
        tag_labels = [_pair_label(tid, b, s) for tid, b, s in trade_pairs]
        selected_tag = st.selectbox("트레이드 선택", tag_labels, key="tag_select")
        idx = tag_labels.index(selected_tag)
        sel_tid_t3, buy_trade, sell_trade = trade_pairs[idx]

        symbol   = buy_trade.get("symbol", "BTCUSDT")
        entry_ms = int(buy_trade.get("execTime", 0))
        exit_ms  = int(sell_trade.get("execTime", 0))

        if entry_ms > 0:
            cache_key_t3 = f"tag_candles_{buy_trade.get('orderId', str(entry_ms))}"
            if cache_key_t3 not in st.session_state:
                with st.spinner("캔들 데이터 수집 중..."):
                    st.session_state[cache_key_t3] = get_candles(symbol, entry_ms, interval="15", limit=50)
            render_candle_chart(st.session_state[cache_key_t3], entry_ms, exit_ms, symbol)
        else:
            st.warning("execTime 정보가 없어 차트를 표시할 수 없습니다.")

        st.divider()
        auto_tag = st.session_state.get(f"setup_tag_{sel_tid_t3}", "")
        col1, col2 = st.columns(2)
        with col1:
            setup_options = ["FVG", "OB", "유동성스윕", "추세추종", "확인필요", "셋업없음"]
            default_idx   = setup_options.index(auto_tag) if auto_tag in setup_options else 0
            label_text    = f"셋업 태그{' (자동)' if auto_tag else ''}"
            setup_tag = st.selectbox(
                label_text,
                setup_options,
                index=default_idx,
                key=f"setup_{idx}",
            )
        with col2:
            note = st.text_input("메모", key=f"note_{idx}", placeholder="진입 근거 등")

        if st.button("💾 저장", key=f"save_{idx}"):
            st.session_state[f"setup_tag_{sel_tid_t3}"] = setup_tag
            st.success(f"저장 완료: {symbol} | {setup_tag} | {note}")
