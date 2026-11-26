"""Presentation-only helpers for Financial Analysis."""
import pandas as pd


def monthly_display(monthly):
    result = monthly.copy()
    result['month'] = pd.to_datetime(result['month']).dt.strftime('%b %Y')
    return result


def compact_chart(fig):
    return fig.update_layout(height=220, margin=dict(l=20, r=16, t=34, b=16),
                             paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)").update_xaxes(title_text=None)


def analysis_css():
    return '''
    @media (min-width: 1100px) {
      .stMainBlockContainer:has(.st-key-fs_workspace_financial_analysis) {padding-top: 2.5rem; padding-bottom: 1rem;}
      .st-key-fs_workspace_financial_analysis h1 {font-size: 2rem; padding: 0 0 .15rem;}
      .st-key-fs_workspace_financial_analysis [data-testid="stVerticalBlock"] {gap: .65rem;}
      .st-key-fs_workspace_financial_analysis [data-testid="stMetric"] {padding: 10px 14px; min-height: 0;}
      .st-key-fs_workspace_financial_analysis [data-testid="stMetricValue"] {font-size: 1.65rem;}
    }
    .st-key-fs_workspace_financial_analysis [data-testid="stCaptionContainer"] p {color:#40566d;}
    .st-key-analysis_charts [data-testid="stPlotlyChart"] {
      background:rgba(255,255,255,.80) !important;
      border:1px solid rgba(255,255,255,.85); border-radius:14px;
    }
    '''
