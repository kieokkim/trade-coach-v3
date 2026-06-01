import streamlit as st


def inject_global_css():
    st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stApp {background: #0a0a14;}

    [data-testid="stSidebar"] {
        background: #0d0d1a;
        border-right: 1px solid #1e1e2e;
    }
    [data-testid="stSidebarNav"] span { display: none; }
    [data-testid="stSidebarNavLink"] p { display: none; }
    [data-testid="stSidebarNavLink"] {
        color: #718096 !important;
        font-size: 13px !important;
        border-radius: 6px !important;
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: #1e1e2e !important;
        color: #e2e8f0 !important;
    }

    .stTabs [data-baseweb="tab"] {
        font-size: 13px;
        color: #718096;
    }
    .stTabs [aria-selected="true"] {
        color: #e2e8f0 !important;
    }

    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }

    hr { border-color: #1e1e2e; }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar_brand():
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 8px 20px;
                    border-bottom:1px solid #1e1e2e;
                    margin-bottom:8px;">
            <div style="font-size:17px; font-weight:700;
                        color:#e2e8f0;">📊 TradeCoach</div>
            <div style="font-size:11px; color:#4a5568; margin-top:3px;">
                ICT 기반 트레이딩 복기 코치
            </div>
        </div>
        """, unsafe_allow_html=True)


def render_dashboard_header(mode_label: str):
    st.markdown(f"""
    <div style="display:flex; justify-content:space-between;
                align-items:center; margin-bottom:24px;">
        <div>
            <div style="font-size:22px; font-weight:700;
                        color:#e2e8f0;">TradeCoach</div>
            <div style="font-size:13px; color:#718096; margin-top:3px;">
                {mode_label}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(win_rate, avg_return, total_pnl, stop_consistency):
    wr_color = "#10b981" if win_rate >= 55 else \
               "#f59e0b" if win_rate >= 45 else "#ef4444"
    pnl_color = "#10b981" if total_pnl >= 0 else "#ef4444"
    pnl_prefix = "+" if total_pnl >= 0 else ""

    st.markdown(f"""
    <div style="display:grid; grid-template-columns:repeat(4,1fr);
                gap:14px; margin-bottom:28px;">
        <div style="background:#1e1e2e; border-radius:12px;
                    padding:18px 20px; border-left:3px solid {wr_color};">
            <div style="font-size:11px; color:#718096;
                        letter-spacing:0.8px; text-transform:uppercase;
                        margin-bottom:8px;">승률</div>
            <div style="font-size:28px; font-weight:700;
                        color:{wr_color};">{win_rate:.1f}%</div>
            <div style="font-size:11px; color:#4a5568;
                        margin-top:4px;">WIN / TOTAL</div>
        </div>
        <div style="background:#1e1e2e; border-radius:12px;
                    padding:18px 20px; border-left:3px solid #3b82f6;">
            <div style="font-size:11px; color:#718096;
                        letter-spacing:0.8px; text-transform:uppercase;
                        margin-bottom:8px;">평균 수익률</div>
            <div style="font-size:28px; font-weight:700;
                        color:#e2e8f0;">{avg_return:.2f}%</div>
            <div style="font-size:11px; color:#4a5568;
                        margin-top:4px;">closedPnl / execValue</div>
        </div>
        <div style="background:#1e1e2e; border-radius:12px;
                    padding:18px 20px; border-left:3px solid {pnl_color};">
            <div style="font-size:11px; color:#718096;
                        letter-spacing:0.8px; text-transform:uppercase;
                        margin-bottom:8px;">수익금</div>
            <div style="font-size:28px; font-weight:700;
                        color:{pnl_color};">{pnl_prefix}${total_pnl:.2f}</div>
            <div style="font-size:11px; color:#4a5568;
                        margin-top:4px;">closedPnl 합계</div>
        </div>
        <div style="background:#1e1e2e; border-radius:12px;
                    padding:18px 20px; border-left:3px solid #8b5cf6;">
            <div style="font-size:11px; color:#718096;
                        letter-spacing:0.8px; text-transform:uppercase;
                        margin-bottom:8px;">손절 일관성</div>
            <div style="font-size:28px; font-weight:700;
                        color:#e2e8f0;">{stop_consistency:.2f}</div>
            <div style="font-size:11px; color:#4a5568;
                        margin-top:4px;">낮을수록 규칙적</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_trade_table(trades: list):
    rows = ""
    for i, t in enumerate(trades):
        bg = "background:#1a1a2e;" if i % 2 == 1 else ""
        is_win = t.get("result") == "WIN"
        result_badge = (
            f'<span style="font-size:11px; padding:2px 8px; border-radius:99px;'
            f' background:{"#064e3b" if is_win else "#450a0a"};'
            f' color:{"#10b981" if is_win else "#ef4444"};">'
            f'{"✅ WIN" if is_win else "❌ LOSS"}</span>'
        )
        pnl = float(t.get("pnl", 0))
        pnl_color = "#10b981" if pnl >= 0 else "#ef4444"
        pnl_str = f"+${pnl:.2f}" if pnl >= 0 else f"-${abs(pnl):.2f}"

        rows += f"""
        <tr style="{bg}">
            <td style="padding:9px 12px; color:#a0aec0; font-size:12px;">{t.get('id','')}</td>
            <td style="padding:9px 12px; font-weight:500; color:#e2e8f0;">{t.get('symbol','')}</td>
            <td style="padding:9px 12px; color:#a0aec0;">{t.get('side','')}</td>
            <td style="padding:9px 12px; color:#a0aec0;">{t.get('entry_price','')}</td>
            <td style="padding:9px 12px; color:#a0aec0;">{t.get('exit_price','')}</td>
            <td style="padding:9px 12px; color:#a0aec0;">{t.get('qty','')}</td>
            <td style="padding:9px 12px;">{result_badge}</td>
            <td style="padding:9px 12px; font-weight:600; color:{pnl_color};">{pnl_str}</td>
            <td style="padding:9px 12px; color:#a0aec0;">{t.get('entry_time','')}</td>
        </tr>"""

    st.markdown(f"""
    <div style="overflow-x:auto; border-radius:12px;
                border:1px solid #1e1e2e; margin-bottom:24px;">
        <table style="width:100%; border-collapse:collapse; font-size:13px;">
            <thead>
                <tr style="background:#1e1e2e; border-bottom:1px solid #2d3748;">
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">거래번호</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">종목</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">방향</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">진입가</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">청산가</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">수량</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">결과</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">수익</th>
                    <th style="padding:10px 12px; text-align:left; color:#718096; font-weight:500;">진입시각</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = ""):
    sub = (
        f'<div style="font-size:12px; color:#718096; margin-top:3px;">{subtitle}</div>'
        if subtitle else ""
    )
    st.markdown(f"""
    <div style="margin:28px 0 16px;">
        <div style="font-size:16px; font-weight:600; color:#e2e8f0;">{title}</div>
        {sub}
    </div>
    """, unsafe_allow_html=True)
