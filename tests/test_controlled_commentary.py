import json
from finsight.commentary_engine import findings_for, render_findings

def record(i,name,margin,share):
    return dict(evidence_id=i,title='Segment: '+name,category='Segment Performance',values=dict(gross_margin=margin,revenue_share=share))
R=[record('E001','Government',.2157,.427),record('E002','Small Business',.0997,.3693),record('E003','Enterprise',-.027,.1686)]
def test_mandatory_concentration():
    f=findings_for(R,'concentration-risk'); text,n,error=render_findings(f)
    assert '79.63%' in text and '-2.70%' in text and n==0

def test_valid_selection():
    f=findings_for(R,'concentration-risk'); text,n,error=render_findings(f,json.dumps({'items':[{'finding_id':f[0]['id'],'action_id':f[0]['choices'][0]}]}))
    assert n==1 and not error and 'AI-selected' in text and '79.63%' in text

def test_invalid_action_falls_back():
    f=findings_for(R,'concentration-risk'); text,n,error=render_findings(f,json.dumps({'items':[{'finding_id':f[0]['id'],'action_id':'Invented profit'}]}))
    assert n==0 and error and 'Invented profit' not in text and '79.63%' in text

def test_omission_keeps_findings():
    f=findings_for(R,'concentration-risk'); text,n,error=render_findings(f,'{"items":[]}'); assert '79.63%' in text and '-2.70%' in text

def test_anomaly_scope():
    r=dict(evidence_id='E004',title='August',category='Financial Anomaly',values=dict(period='August 2014',category='Revenue Decline',severity='High',value=-.25))
    f=findings_for(R+[r],'anomaly-detection'); assert len(f)==1 and '-25.00%' in f[0]['text']
