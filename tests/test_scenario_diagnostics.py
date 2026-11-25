import json
from types import SimpleNamespace
import pytest
from finsight.scenario_commentary import interpret_scenario, local_commentary

@pytest.mark.parametrize('label,metrics,expected', [
 ('Explicit changes', {'Revenue':100,'COGS':70}, 'supplier contracts'),
 ('Explicit changes', {'Revenue':110,'COGS':70}, 'can coexist'),
 ('Affected COGS changes proportionally with revenue', {}, 'capacity'),
 ('Remove segment revenue', {}, 'stranded costs'),
 ('Target via revenue', {}, 'margin target'),
])
def test_fallback(label,metrics,expected):
    assert expected in local_commentary({'baseline':{'Revenue':100,'COGS':80},'cases':[{'label':label,'metrics':metrics}]})

@pytest.mark.parametrize('bad,reason', [('Profit rises by twenty percent.', 'Numerical'),('This guarantees returns.', 'Guarantee'),('The change reflects pricing power.', 'causal')])
def test_diagnostic(monkeypatch,bad,reason):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    calls=[]
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(status='completed',output_text=json.dumps({'interpretation':bad,'risk':'Demand may vary.','action':'Test demand.'}))
    result=interpret_scenario('q',{'cases':[{'label':'COGS unchanged'}]},True,lambda:SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert reason in result['diagnostic'] and bad not in result['text'] and len(calls)==1
    assert result['source']=='Local recommendation'
