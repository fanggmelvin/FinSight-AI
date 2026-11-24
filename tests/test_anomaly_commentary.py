import json
import pytest
from types import SimpleNamespace
from finsight.deterministic_report import parse_structured_commentary
from finsight.skill_workflow import anomaly_commentary_context

A = dict(category='Financial Anomaly', evidence_id='E044', values=dict(period='November 2014', category='Revenue Decline', severity='High', value=-.56, description='Revenue fell 56%'))
B = dict(category='Financial Anomaly', evidence_id='E045', values=dict(period='March 2014', category='Margin Compression', severity='High', value=-3.17))

def parse(observation, action='Review sales volume and pricing.', ids=None):
    return parse_structured_commentary(json.dumps({'items':[dict(observation=observation, action=action, priority='High', evidence_ids=ids or ['E044'])]}), SimpleNamespace(records=[A,B]))

def test_exact_date():
    text, error = parse('Revenue declined in November 2014.')
    # Punctuation immediately after the year is safe only when not decimal punctuation.
    assert text and not error

@pytest.mark.parametrize('observation', ['Revenue declined 56% in November 2014.', 'Revenue declined in March 2014.', 'Revenue declined in November 2015.', 'Revenue declined by $2014.', 'Revenue declined in November 2014.5.', 'Revenue declined by fifty percent.'])
def test_reject(observation):
    assert not parse(observation)[0]

def test_context():
    assert anomaly_commentary_context([A]) == [dict(evidence_id='E044', category='Revenue Decline', period='November 2014', severity='High')]
