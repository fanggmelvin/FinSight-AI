import streamlit as st


def apply_theme():
    """Shared presentation only; no financial or session-state changes."""
    st.markdown("""<style>
    .block-container {max-width: 1440px; padding-top: 2.5rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: #fff; border: 1px solid #DCE3EB; border-radius: 14px; padding: 18px; box-shadow: 0 2px 6px #10243D08;}
    [data-testid="stMetricValue"] {font-size: clamp(1.25rem, 2.2vw, 2rem); font-weight: 650;}
    [data-testid="stMetricLabel"] {color: #475569;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
    [data-testid="stSidebar"] .stButton button {justify-content: flex-start; text-align: left; border-radius: 8px;}
    [data-testid="stSidebar"] .stButton button p {text-align: left;}
    [data-testid="stSidebar"] .stButton button[kind="secondary"] {background: transparent; color: #F1F5F9; border-color: #38506A;}
    [data-testid="stSidebar"] .stButton button[kind="primary"] {background: #426E9B; color: white; border-color: #426E9B;}
    [data-testid="stSidebar"] .stButton button:hover {border-color: #93C5FD;}
    h1, h2, h3 {letter-spacing: -0.025em;}
    [data-testid="stChatMessage"] {border: 1px solid #DCE3EB; border-radius: 14px; padding: 12px; background: white;}
    </style>""", unsafe_allow_html=True)
