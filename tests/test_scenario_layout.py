from pathlib import Path
import plotly.graph_objects as go
from finsight.scenario_layout import compact_value, scenario_rows, scenario_chart, scenario_css

def test_compact_values():
    assert compact_value(118726350.26) == '118.73M'
    assert compact_value(-5091632.4, delta=True) == '-5.09M'
    assert compact_value(1000, delta=True) == '+1.00K'
    assert compact_value(None, True) == 'N/A'

def test_exact_rows():
    base={'Revenue':100.,'COGS':80.,'Gross profit':20.,'Gross margin (%)':20.}
    projected={'Revenue':0.,'COGS':80.,'Gross profit':-80.,'Gross margin (%)':None}
    rows=scenario_rows(base,projected)
    assert rows[2]['Change']=='-100.00'
    assert rows[3]['Projected']=='N/A'
    assert base['Revenue']==100.

def test_chart_negative_values():
    fig=go.Figure(go.Bar(y=[100,-80])); scenario_chart(fig)
    assert list(fig.data[0].y)==[100,-80]
    assert fig.layout.legend.orientation=='h'
    assert 'fs_workspace_scenario_modeling' in scenario_css()

def test_workspace_preserves_engines_and_cases():
    s=(Path(__file__).resolve().parents[1]/'app.py').read_text().split('elif page == "Scenario Modeling":')[1].split('elif page == "AI Copilot":')[0]
    assert 'simulate_controls(df, rev, cost' in s and 'target_controls(df, target)' in s
    assert 'for case in cases:' in s and 'SIM_DEFAULTS' in s
    assert 'st.columns(4)' in s


def test_compact_desktop_layout():
    fig = scenario_chart(go.Figure())
    assert fig.layout.height == 205
    css = scenario_css()
    assert 'min-height:112px' in css
    assert '@media (min-width:1100px)' in css
