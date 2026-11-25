import json
from types import SimpleNamespace
from finsight.deterministic_report import parse_structured_commentary
from finsight.scenario_commentary import local_commentary
from finsight.answer_reliability import direct_answer

R = SimpleNamespace(records=[dict(evidence_id='E001',category='Product Performance',title='Product: Amarilla',values=dict(gross_margin=.16,gross_profit=20)),dict(evidence_id='E002',category='Product Performance',title='Product: Montana',values=dict(gross_margin=.13,gross_profit=10)),dict(evidence_id='E003',category='Product Performance',title='Product: Paseo',values=dict(gross_margin=.14,gross_profit=30))])
ROUTE=dict(mode='ranking',dimension='product',metric='gross_margin',objective='profitability')
def parse(ids,observation='Montana has higher gross profit.',action='Test demand.'):
    return parse_structured_commentary(json.dumps(dict(items=[dict(priority='High',observation=observation,action=action,evidence_ids=ids)])),R,ROUTE)
def test_wrong_observation_replaced():
    text,err=parse(['E001','E002']); assert not err and 'higher gross profit' not in text and 'Amarilla: gross margin 16.00%' in text

def test_leader_required():
    assert not parse(['E002'])[0]

def test_diversification_not_requested():
    assert not parse(['E001'],action='Maintain diversification.')[0]

def test_comparative_action_rejected():
    assert not parse(['E001'],action='Invest because of higher profits.')[0]

def test_guarantee_rejected():
    assert not parse(['E001'],action='This will increase profit.')[0]

def test_distinction():
    assert 'Gross profit leader: Paseo' in direct_answer(R.records,dict(ROUTE,ambiguous_profitability=True))

def test_zero_revenue():
    assert 'business continuity' in local_commentary(dict(baseline={'Revenue':100,'COGS':80},cases=[dict(label='COGS unchanged',metrics={'Revenue':0,'COGS':80})]))

def test_decline():
    assert 'cost flexibility' in local_commentary(dict(baseline={'Revenue':100,'COGS':80},cases=[dict(label='COGS unchanged',metrics={'Revenue':80,'COGS':80})]))

def test_cost_increase():
    assert 'margin protection' in local_commentary(dict(baseline={'Revenue':100,'COGS':80},cases=[dict(label='Explicit changes',metrics={'Revenue':100,'COGS':90})]))
