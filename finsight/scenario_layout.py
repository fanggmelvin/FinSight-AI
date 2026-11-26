"""Presentation helpers for the local scenario workspace."""
from finsight.scenario_presentation import format_value

METRICS = ('Revenue', 'COGS', 'Gross profit', 'Gross margin (%)')

def compact_value(value, margin=False, delta=False):
    if value is None or margin:
        return format_value(value, margin, delta)
    for scale, suffix in ((1e9,'B'),(1e6,'M'),(1e3,'K')):
        if abs(value) >= scale:
            return format(value/scale, '+,.2f' if delta else ',.2f') + suffix
    return format_value(value, delta=delta)

def scenario_rows(base, projected):
    return [{'Metric': k, 'Baseline': format_value(base[k], k.endswith('(%)')), 'Projected': format_value(projected[k], k.endswith('(%)')), 'Change': format_value(projected[k]-base[k] if projected[k] is not None and base[k] is not None else None, k.endswith('(%)'), True)} for k in METRICS]

def scenario_chart(fig):
    return fig.update_layout(height=205, legend=dict(orientation='h', y=1.02, x=0, yanchor='bottom', title_text=''), margin=dict(t=40,l=20,r=20,b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)').update_xaxes(title_text=None)

def scenario_css():
    return '''
    @media (min-width:1100px) {
      .stMainBlockContainer:has(.st-key-fs_workspace_scenario_modeling) {padding-top:1.25rem;padding-bottom:.5rem;}
      .st-key-fs_workspace_scenario_modeling h1 {font-size:2rem;padding:0 0 .15rem;}
      .st-key-fs_workspace_scenario_modeling [data-testid="stVerticalBlock"] {gap:.35rem;}
      .st-key-fs_workspace_scenario_modeling [data-testid="stMetric"] {padding:10px 14px;min-height:112px;}
      .st-key-fs_workspace_scenario_modeling [data-testid="stMetricValue"] {font-size:1.65rem;}
      .st-key-fs_workspace_scenario_modeling [data-testid="stSlider"] {margin-bottom:-.35rem;}
    }
    .st-key-fs_workspace_scenario_modeling [data-testid="stPlotlyChart"] {background:rgba(255,255,255,.80)!important;border:1px solid rgba(255,255,255,.85);border-radius:14px;}
    '''
