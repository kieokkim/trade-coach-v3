import os

import streamlit as st

from utils.api_safety import check_api_permissions
from utils.styles import inject_global_css, render_sidebar_brand

st.set_page_config(page_title="TradeCoach | API 연결", page_icon="🔑", layout="centered")

inject_global_css()
render_sidebar_brand()

st.markdown("""
<div style="text-align:center; padding:40px 0 32px;">
    <div style="font-size:32px; font-weight:700;
                color:#e2e8f0; margin-bottom:8px;">
        📊 TradeCoach
    </div>
    <div style="font-size:15px; color:#718096; max-width:480px;
                margin:0 auto; line-height:1.6;">
        ICT 기반 트레이딩 복기 코치<br>
        거래를 분석하고, 복기하고, 채점합니다.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="display:grid; grid-template-columns:repeat(2,1fr);
            gap:12px; max-width:640px; margin:0 auto 32px;">
    <div style="background:#1e1e2e; border-radius:10px;
                padding:16px; border-left:3px solid #3b82f6;">
        <div style="font-size:12px; color:#3b82f6;
                    font-weight:600; margin-bottom:4px;">거래내역 분석</div>
        <div style="font-size:13px; color:#a0aec0;">
            승률·수익률·손절 일관성 자동 진단
        </div>
    </div>
    <div style="background:#1e1e2e; border-radius:10px;
                padding:16px; border-left:3px solid #10b981;">
        <div style="font-size:12px; color:#10b981;
                    font-weight:600; margin-bottom:4px;">거래 복기</div>
        <div style="font-size:13px; color:#a0aec0;">
            진입 캔들 복원 + FVG/OB 자동 감지
        </div>
    </div>
    <div style="background:#1e1e2e; border-radius:10px;
                padding:16px; border-left:3px solid #f59e0b;">
        <div style="font-size:12px; color:#f59e0b;
                    font-weight:600; margin-bottom:4px;">A+ 채점</div>
        <div style="font-size:13px; color:#a0aec0;">
            ICT 기준 5가지로 진입 품질 채점
        </div>
    </div>
    <div style="background:#1e1e2e; border-radius:10px;
                padding:16px; border-left:3px solid #8b5cf6;">
        <div style="font-size:12px; color:#8b5cf6;
                    font-weight:600; margin-bottom:4px;">진입 근거 추론</div>
        <div style="font-size:13px; color:#a0aec0;">
            캔들 패턴 보고 LLM이 근거 분석
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

st.subheader("🔑 Bybit API 연결")
st.caption("API 키는 브라우저 세션에만 임시 저장됩니다.")

with st.form("api_form"):
    api_key = st.text_input("API Key", type="password", placeholder="Bybit API Key")
    api_secret = st.text_input("API Secret", type="password", placeholder="Bybit API Secret")
    submitted = st.form_submit_button("🔗 연결 확인", type="primary", use_container_width=True)

if submitted:
    if api_key.strip() and api_secret.strip():
        with st.spinner("API 키 권한 확인 중..."):
            perm_check = check_api_permissions(api_key.strip(), api_secret.strip())

        if not perm_check["valid"]:
            st.error(perm_check["warning"])
        elif not perm_check["read_only"]:
            st.warning(perm_check["warning"])
            st.caption(
                "그래도 계속하시겠습니까? TradeCoach는 거래를 "
                "실행하지 않지만, 안전을 위해 read-only 키 사용을 권장합니다."
            )
            st.session_state["api_perm_warning"] = True
            st.session_state["api_key_pending"] = api_key.strip()
            st.session_state["api_secret_pending"] = api_secret.strip()
        else:
            os.environ["BYBIT_API_KEY"] = api_key.strip()
            os.environ["BYBIT_API_SECRET"] = api_secret.strip()
            st.session_state["api_ready"] = True
            st.session_state.pop("sample_mode", None)
            st.success("✅ 연결 확인 완료 (read-only 키 확인됨)")
            st.switch_page("pages/2_loading.py")
    else:
        st.error("API Key와 Secret을 모두 입력해주세요.")

if st.session_state.get("api_perm_warning"):
    if st.checkbox("권한 경고를 확인했으며 계속 진행합니다"):
        os.environ["BYBIT_API_KEY"] = st.session_state["api_key_pending"]
        os.environ["BYBIT_API_SECRET"] = st.session_state["api_secret_pending"]
        st.session_state["api_ready"] = True
        st.session_state.pop("sample_mode", None)
        st.session_state.pop("api_perm_warning", None)
        st.session_state.pop("api_key_pending", None)
        st.session_state.pop("api_secret_pending", None)
        st.success("✅ 연결 확인 완료 (거래 권한 있는 키 - 주의)")
        st.switch_page("pages/2_loading.py")

st.divider()
st.subheader("🎮 데모 모드")
st.caption("Bybit 계정 없이 샘플 데이터로 체험해보세요")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    <div style="background:#1e1e2e; border-radius:10px;
                padding:14px 16px; border-left:3px solid #ef4444;
                margin-bottom:8px;">
        <div style="font-size:13px; font-weight:700;
                    color:#e2e8f0; margin-bottom:4px;">👶 초보 트레이더</div>
        <div style="font-size:12px; color:#a0aec0;">
            감에 의존 · 불규칙한 손절
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("체험하기", key="btn_beginner", use_container_width=True):
        st.session_state["sample_mode"]  = "beginner"
        st.session_state["sample_label"] = "초보 트레이더 데모"
        st.switch_page("pages/2_loading.py")

with col2:
    st.markdown("""
    <div style="background:#1e1e2e; border-radius:10px;
                padding:14px 16px; border-left:3px solid #f59e0b;
                margin-bottom:8px;">
        <div style="font-size:13px; font-weight:700;
                    color:#e2e8f0; margin-bottom:4px;">🧑 중급 트레이더</div>
        <div style="font-size:12px; color:#a0aec0;">
            ICT 기초 이해 · 감정적 진입
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("체험하기", key="btn_intermediate", use_container_width=True):
        st.session_state["sample_mode"]  = "intermediate"
        st.session_state["sample_label"] = "중급 트레이더 데모"
        st.switch_page("pages/2_loading.py")

with col3:
    st.markdown("""
    <div style="background:#1e1e2e; border-radius:10px;
                padding:14px 16px; border-left:3px solid #10b981;
                margin-bottom:8px;">
        <div style="font-size:13px; font-weight:700;
                    color:#e2e8f0; margin-bottom:4px;">🏆 고수 트레이더</div>
        <div style="font-size:12px; color:#a0aec0;">
            ICT 심층 이해 · 이성적 판단
        </div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("체험하기", key="btn_expert", use_container_width=True):
        st.session_state["sample_mode"]  = "expert"
        st.session_state["sample_label"] = "고수 트레이더 데모"
        st.switch_page("pages/2_loading.py")
