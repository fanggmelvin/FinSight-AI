import json
from types import SimpleNamespace
import pytest
from finsight.scenario_commentary import calculated_interpretation, interpret_scenario
from finsight.commentary_grounding import action_diagnostic

S = {'baseline': {'Revenue':100,'COGS':80,'Gross profit':20,'Gross margin (%)':20}, 'cases':[{'label':'Proportional COGS','metrics':{'Revenue':110,'COGS':88,'Gross profit':22,'Gross margin (%)':20}}]}

def test_proportional():
    assert 'gross profit increases; gross margin is unchanged' in calculated_interpretation(S)

def test_zero():
    s = {**S,'cases':[{'label':'Zero revenue','metrics':{'Revenue':0,'COGS':80,'Gross profit':-80,'Gross margin (%)':None}}]}
    assert 'gross profit decreases; gross margin is undefined' in calculated_interpretation(s)

@pytest.mark.parametrize('text', ['Assess net profitability from gross profit.', 'Review market share.'])
def test_terminology(text):
    assert action_diagnostic(text)

def test_revenue_share():
    assert action_diagnostic('Review internal revenue share.') is None

@pytest.mark.parametrize('risk,action,expected', [('Demand may vary.','Profit 100','Risk (AI)'),('Costs rise by ten percent.','Test demand.','Action (AI)'),('Demand may vary.','Test demand.','AI response accepted')])
def test_fields(monkeypatch,risk,action,expected):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    calls=[]
    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(status='completed',output_text=json.dumps({'risk':risk,'action':action,'interpretation':'Gross profit stays unchanged.'}))
    r=interpret_scenario('q',S,True,lambda:SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert expected in r['text'] or expected in r['status']
    assert 'gross profit increases; gross margin is unchanged' in r['text']
    assert 'Gross profit stays unchanged.' not in r['text']
    assert len(calls)==1 and calls[0]['max_output_tokens']==250
    assert set(calls[0]['text']['format']['schema']['required'])=={'risk','action'}
