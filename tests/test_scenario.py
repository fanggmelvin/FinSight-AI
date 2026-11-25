import pandas as pd
import pytest
from finsight.scenario import run_scenario, is_scenario

@pytest.fixture
def data():
    return pd.DataFrame({'revenue':[100.,200.],'cogs':[80.,220.],'segment':['Government','Enterprise'],'date':pd.to_datetime(['2014-01-01','2013-01-01'])})

def test_revenue(data):
    x=run_scenario('What if revenue increases by 10%?',data)
    assert x['cases'][0]['metrics']['Gross profit']==pytest.approx(30)
    assert x['cases'][1]['metrics']['Gross profit']==pytest.approx(0)

def test_cost(data):
    assert run_scenario('What if we reduce COGS by 5%?',data)['cases'][0]['metrics']['Gross profit']==15

def test_segment(data):
    x=run_scenario('What if Government revenue declines by 20%?',data)
    assert x['cases'][1]['metrics']['COGS']==284

def test_remove(data):
    assert run_scenario('What if we discontinue the Enterprise segment?',data)['cases'][0]['metrics']['Gross profit']==20

def test_target(data):
    x=run_scenario('Target gross margin of 20%',data)
    assert all(y['metrics']['Gross margin (%)']==pytest.approx(20) for y in x['cases'])

def test_combined(data):
    assert run_scenario('What if revenue increases by 10% and COGS decreases by 5%?',data)['cases'][0]['metrics']['Gross profit']==45

def test_year(data):
    assert run_scenario('What if revenue increases by 10% in 2014?',data)['records']==1

@pytest.mark.parametrize('q',['What if revenue declines by 101%?','What if revenue increases by 10% and taxes fall?','Target gross margin of 100%','What if Unknown revenue declines by 20%?'])
def test_invalid(data,q):
    with pytest.raises(ValueError): run_scenario(q,data)

def test_detection():
    assert is_scenario('What if revenue increases by 10%?')
    assert not is_scenario('Which products generate the most gross profit?')
