import os
from pathlib import Path

import streamlit as st

from graph import DEFAULT_STATE, graph
from utils.constants import NODE_LABELS

st.set_page_config(page_title="TradeCoach | 분석 중", page_icon="⏳", layout="centered")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.title("⏳ 데이터 수집 & 분석")

sample_label = st.session_state.get("sample_label", "")
if sample_label:
    st.caption(f"모드: {sample_label}")

progress    = st.progress(0)
status_text = st.empty()

# ── 샘플 모드: TC_SAMPLE_FILE env var 설정 후 API 키 임시 제거 ───────────────
_SAMPLE_FILE_MAP = {
    "sample_1":     str(Path(__file__).parent.parent / "data" / "sample_trades_1.json"),
    "sample_2":     str(Path(__file__).parent.parent / "data" / "sample_trades_2.json"),
    "beginner":     str(Path(__file__).parent.parent / "data" / "sample_trades_beginner.json"),
    "intermediate": str(Path(__file__).parent.parent / "data" / "sample_trades_intermediate.json"),
    "expert":       str(Path(__file__).parent.parent / "data" / "sample_trades_expert.json"),
}

sample_mode    = st.session_state.get("sample_mode", "")
_saved_api_key = None

if sample_mode in _SAMPLE_FILE_MAP:
    os.environ["TC_SAMPLE_FILE"] = _SAMPLE_FILE_MAP[sample_mode]
    _saved_api_key = os.environ.pop("BYBIT_API_KEY", None)
elif not st.session_state.get("api_ready", False):
    _saved_api_key = os.environ.pop("BYBIT_API_KEY", None)

# ── invoke_state 구성 ────────────────────────────────────────────────────────
session_id   = st.session_state.get("session_id", "default")
invoke_state = {
    **DEFAULT_STATE,
    "session_id":   session_id,
    "input_type":   "bybit",
    "journal_data": "",
    "raw_trades":   [],
    "sample_mode":  sample_mode,
}

# ── graph.stream() ───────────────────────────────────────────────────────────
completed:           list[str] = []
result:              dict      = {}
raw_trades_captured: list      = []
closed_count:        int       = 0
_total = len(NODE_LABELS)

for chunk in graph.stream(invoke_state, stream_mode="updates"):
    for node_name, node_output in chunk.items():
        completed.append(node_name)
        if node_output:
            result.update(node_output)
            if "raw_trades" in node_output:
                raw_trades_captured = node_output["raw_trades"]
                closed_count = len([t for t in raw_trades_captured
                                    if t.get("closedPnl", "0") != "0"])

        n = closed_count
        STATUS_MESSAGES = {
            "memory_load":          "이전 세션 기록을 불러오는 중...",
            "new_data_check":       "신규 거래내역을 확인하는 중...",
            "bybit_fetch":          f"거래내역 {n}건 수집 완료" if n else "거래내역을 수집하는 중...",
            "preprocess":           f"{n}건 데이터를 정리하는 중..." if n else "데이터를 정리하는 중...",
            "journal_write":        f"{n}건 매매일지를 작성하는 중..." if n else "매매일지를 작성하는 중...",
            "journal_analysis":     f"{n}건 핵심 지표를 분석하는 중..." if n else "핵심 지표를 분석하는 중...",
            "weakness_detect":      f"{n}건 약점 패턴을 탐지하는 중..." if n else "약점 패턴을 탐지하는 중...",
            "performance_analysis": "성과를 요약하는 중...",
            "backtest_coach":       "ICT 코칭을 생성하는 중...",
            "quiz_generate":        "퀴즈를 생성하는 중...",
            "memory_save":          "분석 결과를 저장하는 중...",
        }

        status_text.text(STATUS_MESSAGES.get(node_name, "분석 중..."))
        progress.progress(len(completed) / _total)

# 완료
status_text.text("✅ 분석 완료!")
progress.progress(1.0)

if closed_count:
    if not invoke_state.get("last_fetched_at"):
        st.info(f"📦 신규 데이터 {closed_count}건 분석 완료")
    else:
        st.info(f"📦 기존 데이터를 제외한 신규 {closed_count}건 분석 완료")

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

st.switch_page("pages/3_main.py")
