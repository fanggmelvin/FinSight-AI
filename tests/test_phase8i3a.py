import pandas as pd
import pytest
from finsight.annual_analytics import annual_figures, compact_money, annual_actuals
from test_phase8i3 import sample

@pytest.mark.parametrize('value,expected', [(110225000000,'$110.23B'),(-1250000,'-$1.25M'),(0,'$0.00')])
def test_compact(value,expected):
    assert compact_money(value)==expected

def test_grouped_bars():
    a=annual_actuals(sample()); bars,_=annual_figures(a)
    assert bars.layout.barmode=='group'
    assert [t.name for t in bars.data]==['Revenue','COGS','Gross profit']
    assert list(bars.data[0].y)==[100,110]
    assert list(bars.data[0].x)==['2018','2019']

def test_single_year_margin():
    _,fig=annual_figures(annual_actuals(sample()).iloc[:1])
    assert fig.data[0].mode=='lines+markers'
    assert fig.layout.yaxis.tickformat=='.1%'
    assert '%{y:.2%}' in fig.data[0].hovertemplate
    assert list(fig.data[0].y)==[.4]

def test_missing_margin():
    f=sample(); f.loc[0,'Revenue']=0
    _,fig=annual_figures(annual_actuals(f))
    assert pd.isna(fig.data[0].y[0])
    assert fig.data[0].connectgaps is False
