import pandas as pd
from finsight.analysis_layout import monthly_display, analysis_css


def test_month_label():
    assert monthly_display(pd.DataFrame({'month':['2013-09-01']})).month.iloc[0] == 'Sep 2013'


def test_preserves_precision():
    df = pd.DataFrame({'month':['2014-01-01'], 'margin_change_pp':[0.123456], 'revenue':[123.456789]})
    out = monthly_display(df)
    assert out.revenue.equals(df.revenue) and out.margin_change_pp.equals(df.margin_change_pp)
    assert df.month.iloc[0] == '2014-01-01'


def test_missing_preserved():
    df = pd.DataFrame({'month':['2014-01-01'], 'revenue_growth':[float('nan')]})
    assert pd.isna(monthly_display(df).revenue_growth.iloc[0])


def test_css_scoped():
    assert '.st-key-analysis_charts' in analysis_css()


def test_compact_chart_preserves_values():
    import plotly.graph_objects as go
    from finsight.analysis_layout import compact_chart
    fig = compact_chart(go.Figure(go.Bar(x=['Sep'], y=[123.456], marker_color='#426E9B')))
    assert fig.layout.height == 220
    assert fig.data[0].y[0] == 123.456
    assert fig.data[0].marker.color == '#426E9B'


def test_compact_desktop_scope():
    css = analysis_css()
    assert '@media (min-width: 1100px)' in css
    assert '.stMainBlockContainer:has(.st-key-fs_workspace_financial_analysis)' in css
