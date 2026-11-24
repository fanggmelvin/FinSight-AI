from types import SimpleNamespace
import json
from finsight.skill_workflow import select_evidence, anomaly_rows, qualitative_diagnostic
from finsight.deterministic_report import parse_structured_commentary, build_facts

A=dict(category='Financial Anomaly', title='November | Revenue Decline', evidence_id='E001', values=dict(category='Revenue Decline', severity='High', period='November', value=-.56))
B=dict(category='Financial Anomaly', title='March | Margin Compression', evidence_id='E002', values=dict(category='Margin Compression', severity='High', period='March', value=-3.17))
C=dict(category='Financial Summary', title='Total Revenue', evidence_id='E003', values=dict(revenue=100))

def test_select():
    assert select_evidence([C,A,B],'anomaly-detection') == [A,B]
    assert select_evidence([C,A,B],'executive-reporting') == [C,A,B]

def test_no_flags():
    assert select_evidence([C],'anomaly-detection') == []

def test_units():
    assert [r['Change'] for r in anomaly_rows([A,B])] == ['-56.00%','-3.17 pp']
    assert build_facts(SimpleNamespace(records=[A,B])) == {'E001.value':'-56.00%','E002.value':'-3.17 pp'}

def test_annual_claim():
    assert qualitative_diagnostic('Total annual revenue showed positive growth.',[C])
    assert not qualitative_diagnostic('Revenue declined in November.',[A])

def test_reject_annual():
    item=dict(observation='Annual revenue grew.', action='Review sales.', priority='High', evidence_ids=['E003'])
    text,error=parse_structured_commentary(json.dumps({'items':[item]}),SimpleNamespace(records=[C]))
    assert not text and 'Annual comparison' in error
