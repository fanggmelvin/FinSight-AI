from finsight.overview_layout import reporting_label, overview_css


def test_reporting_range():
    assert reporting_label(['2014-12', '2013-09']) == 'Sep 2013 – Dec 2014'


def test_single_month():
    assert reporting_label(['2014-01']) == 'Jan 2014'


def test_empty_period():
    assert reporting_label([]) == 'Reporting period unavailable'


def test_chart_style_scoped():
    assert '.st-key-overview_charts [data-testid="stPlotlyChart"]' in overview_css()
