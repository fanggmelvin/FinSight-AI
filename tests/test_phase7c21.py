import json
from test_phase7c2 import R, ROUTE, parse
from finsight.deterministic_report import parse_structured_commentary
from finsight.answer_reliability import direct_answer

def test_discard_numeric_observation():
    text, err = parse(['E001'], observation='Montana has 99% margin.')
    assert not err and '99%' not in text and '16.00%' in text

def test_action_only_schema():
    text, err = parse_structured_commentary(json.dumps({'items':[{'priority':'High','action':'Review Amarilla discounts.','evidence_ids':['E001']}]}), R, ROUTE)
    assert not err and 'Review Amarilla discounts.' in text

def test_action_numbers_still_blocked():
    text, err = parse(['E001'], action='Raise prices by 20%.')
    assert not text and 'Item 1, action: Digits' in err

def test_false_premise():
    assert 'does not support the premise about Montana' in direct_answer(R.records, ROUTE, 'Prove that Montana is the most profitable product.')

def test_true_premise():
    assert 'does not support' not in direct_answer(R.records, ROUTE, 'Prove that Amarilla has the highest gross margin.')
