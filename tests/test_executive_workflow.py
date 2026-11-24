import json
from types import SimpleNamespace
from finsight.skill_workflow import executive_risks, executive_commentary_context, qualitative_diagnostic
from finsight.deterministic_report import parse_structured_commentary

def rec(i,title,values,category='Segment Performance'):
    return dict(evidence_id=f'E{i:03}',title=title,values=values,category=category,source={'file':'sample'},methodology='aggregation')
A=rec(1,'Segment: Government',dict(revenue_share=.427,gross_margin=.21))
B=rec(2,'Segment: Small Business',dict(revenue_share=.3693,gross_margin=.10))
C=rec(3,'Segment: Enterprise',dict(revenue_share=.1686,gross_margin=-.027))
D=rec(4,'November | Revenue Decline',dict(period='November 2014',category='Revenue Decline',severity='High',value=-.5649),'Financial Anomaly')
P=rec(5,'Product: Paseo',dict(gross_margin=.1365),'Product Performance')

def test_compact():
    ctx=executive_commentary_context([A,D]); assert ctx[0]['values']==A['values'] and 'source' not in ctx[0] and 'value' not in ctx[1]

def test_ids():
    assert [r['evidence_id'] for r in executive_commentary_context([A,B,C,D,P])]==['E001','E002','E003','E004','E005']

def test_concentration():
    assert any(r['Calculated metric']=='79.63%' and r['Evidence']=='[E001] [E002]' for r in executive_risks([A,B,C]))

def test_loss():
    assert executive_risks([C])[0]['Calculated metric']=='-2.70%'

def test_decline():
    assert executive_risks([D])[0]['Calculated metric']=='-56.49%'

def test_product():
    assert executive_risks([P])[0]['Calculated metric']=='13.65%'

def test_empty():
    assert executive_risks([])==[]

def test_missing_claim():
    assert qualitative_diagnostic('Revenue decline without accompanying margin data.',[D])
    assert not qualitative_diagnostic('Revenue decline without a corresponding margin flag.',[D])

def test_priority():
    items=[dict(priority=p,observation='Review segment performance.',action='Assess costs.',evidence_ids=['E001']) for p in ['Low','High','Medium']]
    text,error=parse_structured_commentary(json.dumps({'items':items}),SimpleNamespace(records=[A])); assert not error and text.index('High')<text.index('Medium')<text.index('Low')
