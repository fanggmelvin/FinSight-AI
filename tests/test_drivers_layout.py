from pathlib import Path
import plotly.graph_objects as go
from finsight.drivers_layout import driver_chart, drivers_css


def test_chart_preserves_values_and_colors():
    fig = driver_chart(go.Figure(go.Bar(x=['A','B'],y=[123.456,-42],marker_color=['#16967A','#B91C1C'])))
    assert list(fig.data[0].y) == [123.456,-42]
    assert list(fig.data[0].marker.color) == ['#16967A','#B91C1C']
    assert fig.layout.height == 240


def test_large_rankings_have_room():
    assert driver_chart(go.Figure(),20,True).layout.height >= 565


def test_scoped_css():
    assert '.st-key-fs_workspace_performance_drivers' in drivers_css()
    assert '@media (min-width: 1100px)' in drivers_css()


def test_workspace_views_and_evidence():
    app = (Path(__file__).resolve().parents[1]/'app.py').read_text(encoding='utf-8')
    section = app.split('elif page == "Performance Drivers":',1)[1].split('elif page == "Anomaly Detection":',1)[0]
    assert 'if view == "Performance rankings":' in section
    assert 'Detailed performance breakdown' in section
    assert 'Detailed revenue attribution' in section
    assert 'Download Supporting Evidence' in section
