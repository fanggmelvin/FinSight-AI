"""Presentation helpers for the performance drivers workspace."""
def drivers_css():
    return '''
    @media (min-width: 1100px) {
      .stMainBlockContainer:has(.st-key-fs_workspace_performance_drivers) {padding-top:2.5rem;padding-bottom:1rem;}
      .st-key-fs_workspace_performance_drivers h1 {font-size:2rem;padding:0 0 .15rem;}
      .st-key-fs_workspace_performance_drivers [data-testid="stVerticalBlock"] {gap:.65rem;}
      .st-key-fs_workspace_performance_drivers [data-testid="stMetric"] {padding:10px 14px;min-height:0;}
      .st-key-fs_workspace_performance_drivers [data-testid="stMetricValue"] {font-size:1.65rem;}
    }
    .st-key-fs_workspace_performance_drivers [data-testid="stPlotlyChart"] {background:rgba(255,255,255,.80)!important;border:1px solid rgba(255,255,255,.85);border-radius:14px;}
    '''


def driver_chart(fig, categories=6, horizontal=False):
    height = max(240, 65 + categories * 25) if horizontal else 240
    return fig.update_layout(height=height, margin=dict(l=20,r=20,t=35,b=22),paper_bgcolor='rgba(0,0,0,0)',plot_bgcolor='rgba(0,0,0,0)')

