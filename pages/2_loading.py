import streamlit as st
import requests

from utils.styles import inject_global_css, render_sidebar_brand

st.set_page_config(page_title="TradeCoach | 분석 중", page_icon="⏳", layout="centered")

inject_global_css()
render_sidebar_brand()

st.title("⏳ 데이터 수집 & 분석")

sample_label = st.session_state.get("sample_label", "")
if sample_label:
    st.caption(f"모드: {sample_label}")

API_BASE = "http://localhost:8000"

STEP_LABELS = [
    ("📡", "거래내역 수집"),
    ("🔧", "데이터 전처리"),
    ("📓", "저널 작성"),
    ("📊", "KPI 분석"),
    ("🔍", "약점 탐지"),
    ("🤖", "AI 코칭 생성"),
    ("🧠", "메모리 저장"),
]


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

payload = {
    "session_id": st.session_state.get("session_id", "default"),
    "sample_mode": st.session_state.get("sample_mode", ""),
    "exchange": st.session_state.get("exchange", "Bybit"),
}

try:
    steps_placeholder.markdown(render_steps(1), unsafe_allow_html=True)

    resp = requests.post(f"{API_BASE}/analyze", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()

    steps_placeholder.markdown(render_steps(5), unsafe_allow_html=True)

    result = data["result"]
    completed_nodes = data["completed_nodes"]

    raw_trades = result.get("raw_trades", [])
    closed_count = len([t for t in raw_trades if t.get("closedPnl", "0") != "0"])

    steps_placeholder.markdown(render_steps(len(STEP_LABELS)), unsafe_allow_html=True)

    if closed_count:
        st.info(f"📦 {closed_count}건 분석 완료")

    st.session_state["completed_nodes"] = completed_nodes
    st.session_state["last_result"] = result
    st.session_state["last_stats"] = result.get("stats", {})
    st.session_state["last_weaknesses"] = result.get("weaknesses", [])
    st.session_state["last_action_rule"] = result.get("action_rule", "")
    st.session_state["last_setup"] = result.get("setup_analysis", {})
    st.session_state["last_coaching"] = result.get("coaching_output", "")
    st.session_state["last_journal_entries"] = result.get("journal_entries", [])
    st.switch_page("pages/3_main.py")

except requests.ConnectionError:
    st.error(
        "⚠️ API 서버에 연결할 수 없습니다.\n\n"
        "터미널에서 `uv run python api/main.py`로 서버를 먼저 실행해주세요."
    )
except requests.HTTPError as e:
    detail = ""
    try:
        detail = e.response.json().get("detail", "")
    except Exception:
        pass
    st.error(f"분석 중 오류가 발생했습니다: {detail or e}")
except Exception as e:
    st.error(f"분석 중 오류가 발생했습니다: {e}")
