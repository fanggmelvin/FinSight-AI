import pandas as pd
import pytest
from investigation_engine import investigate

@pytest.fixture
def data():
    return pd.DataFrame({'date':['2014-10-01','2014-10-01','2014-11-01','2014-11-01'],'revenue':[100,200,150,50],'cogs':[60,100,80,40],'product':['A','B','A','B'],'country':['US','CA','US','CA'],'segment':['Retail','Retail','Retail','Other']})

def run(data): return investigate(data,'2014-10','2014-11')

def test_total(data): assert run(data)['total']['revenue_change']==-100
@pytest.mark.parametrize('dimension',['product','country','segment'])
def test_reconciliation(data,dimension): assert run(data)['dimensions'][dimension]['net_change']==-100

def test_offsets(data):
    p=run(data)['dimensions']['product']; assert (p['negative_contributions'],p['positive_contributions'])==(-150,50)

def test_profit(data): assert run(data)['total']['gross_profit_change']==-60

def test_intersection(data): assert run(data)['intersection']['net_change']==-100

def test_missing_period(data):
    with pytest.raises(ValueError): investigate(data,'2014-09','2014-11')

def test_reverse_period(data):
    with pytest.raises(ValueError): investigate(data,'2014-11','2014-10')

def test_missing_dimension(data):
    with pytest.raises(ValueError): run(data.drop(columns='country'))

def test_unknown_category(data):
    data.loc[0,'product']=None
    assert run(data)['dimensions']['product']['net_change']==-100

def test_invalid_revenue(data):
    data.loc[0,'revenue']=float('nan')
    with pytest.raises(ValueError): run(data)
