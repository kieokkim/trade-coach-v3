import pandas as pd
import plotly.graph_objects as go
import streamlit as st

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

st.title("📊 TradeCoach 대시보드")

tab1, tab2, tab3 = st.tabs(["📊 KPI 대시보드", "📋 거래내역 리스트", "📚 셋업 태깅"])

# ═══════════════════════════ Tab 1: KPI 대시보드 ════════════════════════════

with tab1:
    stats = st.session_state.get("last_stats", {})

    st.subheader("📌 핵심 지표")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("승률",        f"{stats.get('win_rate', 0):.1%}")
    c2.metric("평균 수익률", f"{stats.get('avg_return_rate', 0):.2f}%")
    c3.metric("기대값",       f"{stats.get('expected_value', 0):.2f}%")
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
                    st.rerun()

# ════════════════════════ Tab 2: 거래내역 리스트 + 복기 뷰어 ════════════════

with tab2:
    st.subheader("📋 거래내역")

    raw_trades = res.get("raw_trades", [])

    # journal_entries가 비어있을 경우 raw_trades에서 청산 거래 필터링
    journal_entries = st.session_state.get("last_journal_entries", [])

    # 복기에 사용할 트레이드 쌍 구성 (buy + sell 매칭)
    buy_trades  = [t for t in raw_trades if str(t.get("side", "")).lower() == "buy"]
    sell_trades = [t for t in raw_trades if str(t.get("side", "")).lower() == "sell"
                   and str(t.get("closedPnl", "0")) != "0"]

    trade_pairs: list[tuple[dict, dict]] = []
    used_sells: set[int] = set()
    for buy in buy_trades:
        for j, sell in enumerate(sell_trades):
            if j in used_sells:
                continue
            if buy.get("symbol") == sell.get("symbol"):
                trade_pairs.append((buy, sell))
                used_sells.add(j)
                break

    # ── 거래 테이블 표시 ──────────────────────────────────────────────────────
    if raw_trades:
        df_trades = pd.DataFrame(raw_trades)
        display_cols = [c for c in ["execTime", "symbol", "side", "execPrice", "orderQty", "closedPnl"] if c in df_trades.columns]
        st.dataframe(df_trades[display_cols] if display_cols else df_trades, use_container_width=True)
    else:
        st.caption("거래내역 없음")

    # ── 매매일지 (journal_entries 기반) ──────────────────────────────────────
    if journal_entries:
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
        pair_labels = [
            f"{b.get('symbol')} | 진입 {b.get('execPrice')} → 청산 {s.get('execPrice')}  PnL={s.get('closedPnl', '?')}"
            for b, s in trade_pairs
        ]
        selected_label = st.selectbox("트레이드 선택", pair_labels, key="replay_select")
        sel_idx = pair_labels.index(selected_label)

        if st.button("▶ 복기 시작", type="primary", key="replay_btn"):
            buy_t, sell_t = trade_pairs[sel_idx]
            symbol   = buy_t.get("symbol", "BTCUSDT")
            entry_ms = int(buy_t.get("execTime",  0))
            exit_ms  = int(sell_t.get("execTime", 0))

            # ── 캔들 캐싱 (동일 거래 재선택 시 API 재호출 방지) ──────────────
            cache_key = f"replay_{buy_t.get('orderId', str(entry_ms))}"
            if cache_key not in st.session_state:
                with st.spinner("캔들 데이터 수집 중..."):
                    st.session_state[cache_key] = get_candles(symbol, entry_ms, interval="15", limit=50)
            candles = st.session_state[cache_key]
            fvgs    = detect_fvg(candles)

            # ── Plotly Figure 구성 (FVG 오버레이) ────────────────────────────
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

            from datetime import datetime, timezone
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

            # ── FVG 결과 텍스트 ───────────────────────────────────────────────
            if fvgs:
                st.markdown(f"**FVG 감지: {len(fvgs)}개**")
                for fvg in fvgs:
                    fvg_time = pd.to_datetime(fvg["timestamp"], unit="ms", utc=True).strftime("%Y-%m-%d %H:%M")
                    tag      = "📈 Bullish" if fvg["type"] == "bullish" else "📉 Bearish"
                    st.caption(f"{tag} FVG  |  {fvg_time} UTC  |  {fvg['bottom']:.2f} ~ {fvg['top']:.2f}")
            else:
                st.info("이 구간에서 FVG가 탐지되지 않았습니다.")

            # ── LLM 복기 코멘트 ───────────────────────────────────────────────
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

    # ── 섹션 2: 셋업별 수익률 차트 ─────────────────────────────────────────
    # setup_analysis가 비어있으면 journal_entries의 symbol 기준으로 파생
    if not setup_analysis and journal_entries:
        from collections import defaultdict
        ret_by_setup: dict[str, list[float]] = defaultdict(list)
        for e in journal_entries:
            sym = e.get("symbol", "기타")
            rr  = float(e.get("rr", 0) or 0)
            ret_by_setup[sym].append(rr)
        setup_analysis = {
            sym: round(sum(vals) / len(vals), 4)
            for sym, vals in ret_by_setup.items()
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

    raw_trades_t3 = res.get("raw_trades", [])
    buy_t3  = [t for t in raw_trades_t3 if str(t.get("side", "")).lower() == "buy"]
    sell_t3 = [t for t in raw_trades_t3 if str(t.get("side", "")).lower() == "sell"]

    tag_pairs: list[tuple[dict, dict]] = []
    used: set[int] = set()
    for b in buy_t3:
        for j, s in enumerate(sell_t3):
            if j in used:
                continue
            if b.get("symbol") == s.get("symbol"):
                tag_pairs.append((b, s))
                used.add(j)
                break

    if not tag_pairs:
        st.caption("표시할 트레이드 쌍이 없습니다.")
    else:
        tag_labels = [
            f"{b.get('symbol')} | {b.get('execTime')} → {s.get('execTime')}"
            for b, s in tag_pairs
        ]
        selected_tag = st.selectbox("트레이드 선택", tag_labels, key="tag_select")
        idx = tag_labels.index(selected_tag)
        buy_trade, sell_trade = tag_pairs[idx]

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
        col1, col2 = st.columns(2)
        with col1:
            setup_tag = st.selectbox(
                "셋업 태그",
                ["FVG", "OB", "유동성스윕", "브레이커", "기타"],
                key=f"setup_{idx}",
            )
        with col2:
            note = st.text_input("메모", key=f"note_{idx}", placeholder="진입 근거 등")

        if st.button("💾 저장", key=f"save_{idx}"):
            st.success(f"저장 완료: {symbol} | {setup_tag} | {note}")
