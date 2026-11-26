import pandas as pd
import pytest
from finsight.annual_analytics import annual_actuals, annual_state


def sample():
    return pd.DataFrame({'Fiscal year':[2018,2019,2020], 'Period type':['Actual','Actual','Forecast'], 'Revenue':[100,110,200], 'COGS':[60,65,100], 'Currency':['USD']*3})


def test_forecast_excluded():
    assert annual_actuals(sample())['Fiscal year'].tolist()==[2018,2019]


def test_yoy():
    assert annual_actuals(sample()).iloc[-1]['Revenue YoY']==pytest.approx(.1)


def test_gap():
    f=sample(); f.loc[0,'Fiscal year']=2017
    assert pd.isna(annual_actuals(f).iloc[-1]['Revenue YoY'])


def test_unclassified():
    f=sample(); f.loc[0,'Period type']='Unclassified'
    with pytest.raises(ValueError): annual_actuals(f)


def test_state():
    s=annual_state(sample(),'test','IS','id')
    assert len(s['validated_data'])==2 and len(s['annual_data'])==3
    assert not s['scenario_demo_source']


def test_zero_revenue():
    f=sample(); f.loc[0,'Revenue']=0
    a=annual_actuals(f); assert pd.isna(a.iloc[0]['Gross margin']) and pd.isna(a.iloc[1]['Revenue YoY'])
