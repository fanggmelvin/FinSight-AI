from finsight.aurora_theme import aurora_css


def apply_theme(motion=True):
    """Shared presentation only; no financial or session-state changes."""
    import streamlit as st
    st.markdown("""<style>
    .block-container {max-width: 1440px; padding-top: 1.5rem; padding-bottom: 3rem;}
    [data-testid="stMetric"] {background: #fff; border: 1px solid #DCE3EB; border-radius: 14px; padding: 18px; box-shadow: 0 2px 6px #10243D08;}
    [data-testid="stMetricValue"] {font-size: clamp(1.25rem, 2.2vw, 2rem); font-weight: 650;}
    [data-testid="stMetricLabel"] {color: #475569;}
    [data-testid="stVerticalBlockBorderWrapper"] {border-radius: 14px;}
    [data-testid="stSidebar"] .stButton button {justify-content: flex-start !important; text-align: left; border-radius: 8px;}
    [data-testid="stSidebar"] .stButton button p {text-align: left;}
    [data-testid="stSidebar"] .stButton button[kind="secondary"] {background: transparent; color: #F1F5F9; border-color: #38506A;}
    [data-testid="stSidebar"] .stButton button[kind="primary"] {background: #426E9B; color: white; border-color: #426E9B;}
    [data-testid="stSidebar"] .stButton button:hover {border-color: #93C5FD;}
    h1, h2, h3 {letter-spacing: -0.025em;}
    [data-testid="stChatMessage"] {border: 1px solid #DCE3EB; border-radius: 14px; padding: 12px; background: white;}
    [data-testid="stSidebar"] .stButton button > div {justify-content: flex-start !important;}
    [data-testid="stPlotlyChart"] {background: white; border: 1px solid #DCE3EB; border-radius: 14px; padding: 8px; overflow: hidden;}
    [data-testid="stExpander"] {background: white; border-radius: 10px;}
    [data-testid="stMain"] [data-testid="stCaptionContainer"] {color: #475569;}
    [data-testid="stMain"] [data-testid="stCaptionContainer"] p {color: #475569;}
    [data-testid="stMain"] hr {margin: 0.65rem 0;}
    /* Use actual workspace width, not viewport width (sidebar consumes space). */
    .st-key-overview_metrics, .st-key-overview_charts {container-type: inline-size;}
    [data-testid="stMetricValue"] > div, [data-testid="stMetricLabel"] p {
      white-space: normal !important; overflow-wrap: anywhere; text-overflow: clip !important;
    }
    @container (max-width: 850px) {
      .st-key-overview_metrics [data-testid="stHorizontalBlock"] {flex-wrap: wrap !important;}
      .st-key-overview_metrics [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {flex: 1 1 calc(50% - 1rem) !important; width: calc(50% - 1rem) !important; min-width: 0 !important;}
      .st-key-overview_charts [data-testid="stHorizontalBlock"] {flex-direction: column !important;}
      .st-key-overview_charts [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {width: 100% !important; flex: 1 1 auto !important; min-width: 0 !important;}
    }
    @container (max-width: 360px) {
      .st-key-overview_metrics [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {flex-basis: 100% !important; width: 100% !important;}
    }
    @media (max-width: 1100px) {
      [data-testid="stMetric"] {padding: 12px; min-width: 0;}
      [data-testid="stMetricValue"] {font-size: 1.25rem;}
    }
    </style>""", unsafe_allow_html=True)

    st.markdown("<style>" + aurora_css(motion) + "</style>", unsafe_allow_html=True)
