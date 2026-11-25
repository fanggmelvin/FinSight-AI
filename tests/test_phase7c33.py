import json
from types import SimpleNamespace
from finsight.deterministic_report import parse_structured_commentary

R = SimpleNamespace(records=[dict(evidence_id='E001',title='Segment: Enterprise',category='Segment Performance',values=dict(gross_profit=-10.,gross_margin=-.1))])

def parse(action='Review Enterprise unit costs.', **extra):
    item=dict(priority='High',action=action,evidence_ids=['E001'],**extra)
    return parse_structured_commentary(json.dumps(dict(items=[item])),R,action_only=True)

def test_action_only_observation():
    text,err=parse()
    assert not err and '-10.00%' in text and 'Review Enterprise unit costs.' in text

def test_untrusted_observation_discarded():
    text,err=parse(observation='Highest profit $999999')
    assert not err and '999999' not in text and 'Highest' not in text

def test_action_numbers_rejected():
    assert not parse('Increase revenue by 99%.')[0]

def test_action_ranking_rejected():
    assert not parse('Invest in the highest margin group.')[0]

def test_action_unsupported_metric_rejected():
    assert not parse('Review net income.')[0]
