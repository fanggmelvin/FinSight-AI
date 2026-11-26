"""Overview-only presentation helpers."""
import pandas as pd


def reporting_label(months):
    dates = pd.to_datetime(pd.Series(months).astype(str), errors='coerce').dropna()
    if dates.empty:
        return 'Reporting period unavailable'
    start, end = dates.min().strftime('%b %Y'), dates.max().strftime('%b %Y')
    return start if start == end else f'{start} – {end}'


def overview_css():
    return '''
    .st-key-fs_workspace_overview h1 {padding-top: 0; padding-bottom: .2rem;}
    .st-key-overview_revenue_card, .st-key-overview_margin_card {
      background: rgba(255,255,255,.80); border: 1px solid rgba(255,255,255,.85);
      border-radius: 14px; padding: 12px 14px 4px; min-width: 0;
    }
    .st-key-overview_charts [data-testid="stPlotlyChart"] {
      background: transparent !important; border: none !important;
      box-shadow: none !important; padding: 0 !important;
    }
    .st-key-overview_charts h3 {font-size: 1.2rem; padding: .2rem 0;}
    .st-key-fs_workspace_overview [data-testid="stCaptionContainer"] p {color: #40566d;}
    '''
