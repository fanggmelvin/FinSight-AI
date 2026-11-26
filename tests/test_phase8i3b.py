import pytest
import pandas as pd
from test_phase8i3 import sample
from finsight.annual_analytics import annual_actuals, annual_variance, annual_cagr, annual_figures, growth_figure

def test_variance_bridge():
    v=annual_variance(annual_actuals(sample()),2019)
    assert v['Revenue']-v['COGS']==v['Gross profit']==5

def test_no_prior():
    assert annual_variance(annual_actuals(sample()),2018) is None

def test_cagr():
    assert annual_cagr(annual_actuals(sample()),'Revenue')==pytest.approx(.1)

def test_single_cagr():
    assert pd.isna(annual_cagr(annual_actuals(sample()).iloc[:1],'Revenue'))

def test_growth():
    a=annual_actuals(sample()); assert a.iloc[-1]['COGS YoY']==pytest.approx(5/60)
    assert len(growth_figure(a).data)==3

def test_billions():
    f=sample(); f[['Revenue','COGS']]*=10**9
    bars,_=annual_figures(annual_actuals(f)); assert '$100B' in bars.layout.yaxis.ticktext or all('G' not in x for x in bars.layout.yaxis.ticktext)
