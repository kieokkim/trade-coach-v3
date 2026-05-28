import os
from pathlib import Path

import streamlit as st

from graph import DEFAULT_STATE, graph
from utils.styles import inject_global_css, render_sidebar_brand

st.set_page_config(page_title="TradeCoach | 분석 중", page_icon="⏳", layout="centered")

inject_global_css()
render_sidebar_brand()

st.title("⏳ 데이터 수집 & 분석")

sample_label = st.session_state.get("sample_label", "")
if sample_label:
    st.caption(f"모드: {sample_label}")

STEP_LABELS = [
    ("📡", "거래내역 수집"),
    ("🔧", "데이터 전처리"),
    ("📓", "저널 작성"),
    ("📊", "KPI 분석"),
    ("🔍", "약점 탐지"),
    ("🤖", "AI 코칭 생성"),
    ("🧠", "메모리 저장"),
]

NODE_TO_STEP = {
    "bybit_fetch":          0,
    "preprocess":           1,
    "journal_write":        2,
    "journal_analysis":     3,
    "weakness_detect":      4,
    "performance_analysis": 4,
    "backtest_coach":       5,
    "coaching_judge":       5,
    "memory_save":          6,
}


def render_steps(current_idx):
    html = '<div style="max-width:480px; margin:24px auto;">'
    for i, (icon, label) in enumerate(STEP_LABELS):
        if i < current_idx:
            color = "#10b981"; status = "✅"
        elif i == current_idx:
            color = "#3b82f6"; status = "⏳"
        else:
            color = "#2d3748"; status = "○"
        weight = "600" if i == current_idx else "400"
        html += f"""
        <div style="display:flex; align-items:center; gap:12px;
                    padding:9px 0; border-bottom:1px solid #1e1e2e;">
            <span style="font-size:15px; width:20px;
                         text-align:center;">{status}</span>
            <span style="font-size:13px; color:{color};
                         font-weight:{weight};">{icon} {label}</span>
        </div>"""
    html += '</div>'
    return html


steps_placeholder = st.empty()
steps_placeholder.markdown(render_steps(0), unsafe_allow_html=True)

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
current_step:        int       = 0

for chunk in graph.stream(invoke_state, stream_mode="updates"):
    for node_name, node_output in chunk.items():
        completed.append(node_name)
        if node_output:
            result.update(node_output)
            if "raw_trades" in node_output:
                raw_trades_captured = node_output["raw_trades"]
                closed_count = len([t for t in raw_trades_captured
                                    if t.get("closedPnl", "0") != "0"])

        step = NODE_TO_STEP.get(node_name, -1)
        if step >= 0:
            current_step = step + 1
        steps_placeholder.markdown(render_steps(current_step), unsafe_allow_html=True)

# 완료
steps_placeholder.markdown(render_steps(len(STEP_LABELS)), unsafe_allow_html=True)

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
st.switch_page("pages/3_main.py")
