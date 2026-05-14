import time

import streamlit as st

from graph import DEFAULT_STATE, graph

st.set_page_config(page_title="TradeCoach | 분석 중", page_icon="⏳", layout="centered")

st.title("⏳ 데이터 수집 & 분석")

progress = st.progress(0)
status = st.empty()

steps = [
    (20,  "Bybit API 연결 중..."),
    (50,  "거래내역 수집 중..."),
    (80,  "ICT 패턴 분석 중..."),
    (100, "분석 완료!"),
]

for pct, msg in steps[:-1]:
    status.info(msg)
    progress.progress(pct)
    time.sleep(0.4)

session_id = st.session_state.get("session_id", "default")

state = {
    **DEFAULT_STATE,
    "session_id": session_id,
    "input_type": "bybit",
    "journal_data": "",
    "raw_trades": [],
}

result = graph.invoke(state)

st.session_state["last_result"]          = result
st.session_state["last_stats"]           = result.get("stats", {})
st.session_state["last_weaknesses"]      = result.get("weaknesses", [])
st.session_state["last_action_rule"]     = result.get("action_rule", "")
st.session_state["last_setup"]           = result.get("setup_analysis", {})
st.session_state["last_coaching"]        = result.get("coaching_output", "")
st.session_state["last_journal_entries"] = result.get("journal_entries", [])
st.session_state["last_quiz_question"]   = result.get("quiz_question", "")
st.session_state["last_quiz_concept"]    = result.get("current_concept", "")
st.session_state.pop("last_quiz_result",   None)
st.session_state.pop("last_quiz_feedback", None)

status.success("분석 완료!")
progress.progress(100)
time.sleep(0.5)

st.switch_page("pages/3_main.py")
