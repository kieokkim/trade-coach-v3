import os

import streamlit as st

st.set_page_config(page_title="TradeCoach | API 연결", page_icon="🔑", layout="centered")

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.title("📊 TradeCoach")
st.caption("ICT 기반 트레이딩 코치 — 거래를 분석하고, 복기하고, 채점합니다.")
st.markdown("""
- 📊 **거래내역 분석** — 승률·수익률·손절 일관성 자동 진단
- 🕯️ **거래 복기** — 진입 캔들 복원 + FVG/OB 자동 감지
- 🏆 **A+ 채점** — ICT 기준 5가지로 진입 품질 채점
- 🧠 **진입 근거 추론** — 캔들 패턴 보고 LLM이 근거 분석
""")

st.divider()

st.subheader("🔑 Bybit API 연결")
st.caption("API 키는 브라우저 세션에만 임시 저장됩니다.")

with st.form("api_form"):
    api_key = st.text_input("API Key", type="password", placeholder="Bybit API Key")
    api_secret = st.text_input("API Secret", type="password", placeholder="Bybit API Secret")
    submitted = st.form_submit_button("🔗 연결 확인", type="primary", use_container_width=True)

if submitted:
    if api_key.strip() and api_secret.strip():
        os.environ["BYBIT_API_KEY"] = api_key.strip()
        os.environ["BYBIT_API_SECRET"] = api_secret.strip()
        st.session_state["api_ready"] = True
        st.session_state.pop("sample_mode", None)
        st.success("API 연결 성공! 데이터 수집 페이지로 이동합니다...")
        st.switch_page("pages/2_loading.py")
    else:
        st.error("API Key와 Secret을 모두 입력해주세요.")

st.divider()
st.subheader("🎮 데모 모드")
st.caption("Bybit 계정 없이 샘플 데이터로 체험해보세요")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**👶 초보 트레이더**")
    st.caption("감에 의존 · 불규칙한 손절")
    if st.button("체험하기", key="btn_beginner", use_container_width=True):
        st.session_state["sample_mode"]  = "beginner"
        st.session_state["sample_label"] = "초보 트레이더 데모"
        st.switch_page("pages/2_loading.py")

with col2:
    st.markdown("**🧑 중급 트레이더**")
    st.caption("ICT 기초 이해 · 감정적 진입")
    if st.button("체험하기", key="btn_intermediate", use_container_width=True):
        st.session_state["sample_mode"]  = "intermediate"
        st.session_state["sample_label"] = "중급 트레이더 데모"
        st.switch_page("pages/2_loading.py")

with col3:
    st.markdown("**🏆 고수 트레이더**")
    st.caption("ICT 심층 이해 · 이성적 판단")
    if st.button("체험하기", key="btn_expert", use_container_width=True):
        st.session_state["sample_mode"]  = "expert"
        st.session_state["sample_label"] = "고수 트레이더 데모"
        st.switch_page("pages/2_loading.py")
