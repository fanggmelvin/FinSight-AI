import pandas as pd
import pytest
from reliability import scope_data, period_label, fallback_commentary
from question_router import route_question
from skill_workflow import qualitative_diagnostic

@pytest.fixture
def data():
    return pd.DataFrame({'date':pd.to_datetime(['2013-12-01','2014-01-01','2014-11-01']), 'revenue':[900,100,200]})

@pytest.mark.parametrize('question',['Rank products by gross margin in 2014','Analyze revenue concentration across segments in 2014','Summarize financial performance in 2014'])
def test_scope(data,question):
    route=route_question(question,['2013-12','2014-01','2014-11'])
    assert scope_data(question,data,route).revenue.sum()==300

def test_cross_year(data):
    assert len(scope_data('January 2014',data,{'mode':'revenue_investigation'}))==3

def test_missing(data):
    with pytest.raises(ValueError): scope_data('Summarize 2025',data)

def test_multi_year(data):
    with pytest.raises(ValueError): scope_data('Summarize 2013 and 2014',data)

def test_period(data):
    assert period_label(scope_data('2014',data))=='2014-01, 2014-11'

def test_ranking_guard():
    assert qualitative_diagnostic('Small Business has the lowest margin.',[])

def test_consistency_guard():
    assert qualitative_diagnostic('Revenue contributions were consistent and occurred consistently.',[])

def test_fallback():
    r=dict(title='Segment: Enterprise',evidence_id='E001',values={'gross_margin':-.027})
    assert '-2.70%' in fallback_commentary([r])
