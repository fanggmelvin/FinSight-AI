"""Presentation-only helpers; raw anomaly values remain unchanged."""
import pandas as pd


def anomaly_findings(flags):
    return tuple(min((f for f in flags if f['category'] == category), key=lambda f: f['value'], default=None)
                 for category in ('Revenue Decline', 'Margin Compression'))


def anomaly_display(flags, severity='All flags'):
    rows = [dict(f) for f in flags if severity == 'All flags' or f['severity'] == severity]
    for row in rows:
        row['value'] = (f"{row['value']:+.2f} pp" if row['category'] == 'Margin Compression' else f"{row['value']:+.2%}")
    return pd.DataFrame(rows, columns=['period','category','severity','value','description'])


def anomaly_chart(fig):
    return fig.update_layout(height=260, margin=dict(l=20,r=24,t=35,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)').update_xaxes(title_text=None)


def anomaly_css():
    return '''
    @media (min-width:1100px) {
      .stMainBlockContainer:has(.st-key-fs_workspace_anomaly_detection) {padding-top:2.5rem;padding-bottom:1rem;}
      .st-key-fs_workspace_anomaly_detection h1 {font-size:2rem;padding:0 0 .15rem;}
      .st-key-fs_workspace_anomaly_detection [data-testid="stVerticalBlock"] {gap:.65rem;}
      .st-key-fs_workspace_anomaly_detection [data-testid="stMetric"] {padding:10px 14px;min-height:0;}
      .st-key-fs_workspace_anomaly_detection [data-testid="stMetricValue"] {font-size:1.65rem;}
    }
    .st-key-fs_workspace_anomaly_detection [data-testid="stPlotlyChart"] {background:rgba(255,255,255,.80)!important;border:1px solid rgba(255,255,255,.85);border-radius:14px;}
    '''
