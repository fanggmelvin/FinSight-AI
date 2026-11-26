import pandas as pd
import pytest
from finsight.scenario_controls import simulate_controls, target_controls

@pytest.fixture
def df():
    return pd.DataFrame({'revenue':[100.], 'cogs':[80.], 'date':pd.to_datetime(['2014-01-01'])})

def test_independent(df):
    assert simulate_controls(df,10,-5)['cases'][0]['metrics']['Gross profit']==pytest.approx(34)

def test_proportional(df):
    assert simulate_controls(df,10,-5,True)['cases'][0]['metrics']['COGS']==pytest.approx(83.6)

def test_zero_revenue(df):
    assert simulate_controls(df,-100,0,True)['cases'][0]['metrics']['Gross margin (%)'] is None

def test_reset(df):
    result=simulate_controls(df)
    assert result['baseline']==result['cases'][0]['metrics']

def test_target(df):
    assert all(c['metrics']['Gross margin (%)']==pytest.approx(30) for c in target_controls(df,30)['cases'])

def test_invalid(df):
    with pytest.raises(ValueError): simulate_controls(df,-101)
    with pytest.raises(ValueError): target_controls(df,100)
