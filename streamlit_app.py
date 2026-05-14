import streamlit as st

# Day2: 멀티페이지로 전환 — 아래 기존 로직은 pages/ 로 이전되었으므로 주석 처리
st.switch_page("pages/1_api_input.py")

# ──────────────────── 아래 코드는 pages/ 이전 이후 주석 처리 ─────────────────
# import base64
# import os
#
# import pandas as pd
# import streamlit as st
#
# from graph import DEFAULT_STATE, graph
# from nodes.quiz_nodes import evaluate_quiz
#
# st.set_page_config(page_title="TradeCoach", page_icon="📊", layout="wide")
#
# ──────────────────── 앱 시작 시 DB에서 이전 결과 복원 ─────────────────────
#
# if "last_stats" not in st.session_state:
#     try:
#         from db import get_db
#         _sid = st.session_state.get("session_id", "default")
#         with get_db() as conn:
#             row = conn.execute(
#                 """SELECT win_rate, avg_return_rate, expected_value,
#                           loss_consistency
#                    FROM trade_history
#                    WHERE session_id=? ORDER BY date DESC LIMIT 1""",
#                 (_sid,),
#             ).fetchone()
#         if row:
#             st.session_state["last_stats"] = {
#                 "win_rate":         row["win_rate"] or 0.0,
#                 "avg_return_rate":  row["avg_return_rate"] or 0.0,
#                 "expected_value":   row["expected_value"] or 0.0,
#                 "loss_consistency": row["loss_consistency"] or 0.0,
#             }
#     except Exception:
#         pass
#
#
# def _save_result(result: dict) -> None:
#     """graph.invoke 반환값을 session_state에 저장."""
#     st.session_state["last_result"]          = result
#     st.session_state["last_stats"]           = result.get("stats", {})
#     st.session_state["last_weaknesses"]      = result.get("weaknesses", [])
#     st.session_state["last_action_rule"]     = result.get("action_rule", "")
#     st.session_state["last_setup"]           = result.get("setup_analysis", {})
#     st.session_state["last_coaching"]        = result.get("coaching_output", "")
#     st.session_state["last_journal_entries"] = result.get("journal_entries", [])
#     st.session_state["last_quiz_question"]   = result.get("quiz_question", "")
#     st.session_state["last_quiz_concept"]    = result.get("current_concept", "")
#     st.session_state.pop("last_quiz_result",   None)
#     st.session_state.pop("last_quiz_feedback", None)
#
#
# ──────────────────────────────── 사이드바 ─────────────────────────────────
#
# with st.sidebar:
#     st.title("⚙️ TradeCoach")
#     session_id = st.text_input("Session ID", value="default", key="session_id")
#     st.divider()
#     api_key = os.getenv("BYBIT_API_KEY", "")
#     if api_key:
#         st.sidebar.success("🔗 Bybit API 연결됨")
#     else:
#         st.sidebar.info("📂 샘플 데이터 모드")
#     if st.button("▶ Bybit 분석 시작", type="primary", key="run_bybit"):
#         with st.spinner("Bybit 데이터 수집 및 분석 중..."):
#             state = {**DEFAULT_STATE, "session_id": session_id, "input_type": "bybit",
#                      "journal_data": "", "raw_trades": []}
#             result = graph.invoke(state)
#         _save_result(result)
#     ...
#
# ──── 이하 탭 UI (📊 저널 분석 / 📈 차트 분석 / 🗓️ 성과 기록) 전부 pages/3_main.py 로 이전 ────
