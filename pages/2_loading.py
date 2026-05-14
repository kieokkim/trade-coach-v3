import os
from pathlib import Path

import streamlit as st

from graph import DEFAULT_STATE, graph
from utils.constants import NODE_LABELS

st.set_page_config(page_title="TradeCoach | 분석 중", page_icon="⏳", layout="centered")

st.title("⏳ 데이터 수집 & 분석")

sample_label = st.session_state.get("sample_label", "")
if sample_label:
    st.caption(f"모드: {sample_label}")

# ── 샘플 모드: TC_SAMPLE_FILE env var 설정 후 API 키 임시 제거 ───────────────
_SAMPLE_FILE_MAP = {
    "sample_1": str(Path(__file__).parent.parent / "data" / "sample_trades_1.json"),
    "sample_2": str(Path(__file__).parent.parent / "data" / "sample_trades_2.json"),
}

sample_mode    = st.session_state.get("sample_mode", "")
_saved_api_key = None

if sample_mode in _SAMPLE_FILE_MAP:
    os.environ["TC_SAMPLE_FILE"] = _SAMPLE_FILE_MAP[sample_mode]
    _saved_api_key = os.environ.pop("BYBIT_API_KEY", None)
elif not st.session_state.get("api_ready", False):
    _saved_api_key = os.environ.pop("BYBIT_API_KEY", None)

# ── invoke_state 구성 ────────────────────────────────────────────────────────
session_id  = st.session_state.get("session_id", "default")
invoke_state = {
    **DEFAULT_STATE,
    "session_id":  session_id,
    "input_type":  "bybit",
    "journal_data": "",
    "raw_trades":  [],
}

# ── graph.stream() 실시간 노드 로그 ─────────────────────────────────────────
completed: list[str] = []
result:    dict      = {}
log_area   = st.empty()

for chunk in graph.stream(invoke_state, stream_mode="updates"):
    for node_name, node_output in chunk.items():
        completed.append(node_name)
        result.update(node_output)

        lines = []
        for n in completed[:-1]:
            ic, lb = NODE_LABELS.get(n, ("⚙️", n))
            lines.append(f"✅ {ic} {lb}")
        ic, lb = NODE_LABELS.get(node_name, ("⚙️", node_name))
        lines.append(f"▶️ {ic} **{lb}**")
        log_area.markdown("\n\n".join(lines))

# 전체 완료 표시
lines = []
for n in completed:
    ic, lb = NODE_LABELS.get(n, ("⚙️", n))
    lines.append(f"✅ {ic} {lb}")
log_area.markdown("\n\n".join(lines))

# ── 환경 변수 복원 ───────────────────────────────────────────────────────────
os.environ.pop("TC_SAMPLE_FILE", None)
if _saved_api_key:
    os.environ["BYBIT_API_KEY"] = _saved_api_key

# ── session_state 저장 ───────────────────────────────────────────────────────
st.session_state["completed_nodes"]      = completed
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

# ── 거래 건수 표시 ───────────────────────────────────────────────────────────
raw_trades = result.get("raw_trades", [])
closed     = len([t for t in raw_trades if t.get("closedPnl", "0") != "0"])

if not invoke_state.get("last_fetched_at"):
    st.info(f"📦 신규 데이터 {closed}건을 분석했습니다.")
else:
    st.info(f"📦 기존 데이터를 제외한 신규 데이터 {closed}건을 분석했습니다.")

st.switch_page("pages/3_main.py")
