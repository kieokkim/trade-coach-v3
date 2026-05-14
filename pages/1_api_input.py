import os

import streamlit as st

st.set_page_config(page_title="TradeCoach | API 연결", page_icon="🔑", layout="centered")

st.title("🔑 Bybit API 연결")
st.caption("API 키는 브라우저 세션에만 임시 저장됩니다.")

st.divider()

with st.form("api_form"):
    api_key = st.text_input("API Key", type="password", placeholder="Bybit API Key")
    api_secret = st.text_input("API Secret", type="password", placeholder="Bybit API Secret")
    submitted = st.form_submit_button("🔗 연결 확인", type="primary", use_container_width=True)

if submitted:
    if api_key.strip() and api_secret.strip():
        os.environ["BYBIT_API_KEY"] = api_key.strip()
        os.environ["BYBIT_API_SECRET"] = api_secret.strip()
        st.session_state["api_ready"] = True
        st.success("API 연결 성공! 데이터 수집 페이지로 이동합니다...")
        st.switch_page("pages/2_loading.py")
    else:
        st.error("API Key와 Secret을 모두 입력해주세요.")

st.divider()

if st.button("📂 샘플 데이터로 체험하기", use_container_width=True):
    st.session_state["api_ready"] = False
    st.switch_page("pages/2_loading.py")
