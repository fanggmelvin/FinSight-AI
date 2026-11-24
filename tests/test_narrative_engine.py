import json
from finsight.narrative_engine import build_themes, render_themes
from test_controlled_commentary import R

def test_grouped_concentration():
    t=build_themes(R,'concentration-risk'); assert len(t)==2
    text,n,e=render_themes(t); assert '79.63%' in text and '-2.70%' in text and '42.70%' in text and n==0

def test_distinct_contextual_actions():
    t=build_themes(R,'concentration-risk'); assert len({x['actions'][0] for x in t})==len(t)

def test_valid_selection():
    t=build_themes(R,'concentration-risk'); text,n,e=render_themes(t,json.dumps({'items':[{'finding_id':x['id'],'action_id':'b'} for x in t]})); assert n==2 and not e and 'AI-selected' in text

def test_invalid_selection():
    t=build_themes(R,'concentration-risk'); text,n,e=render_themes(t,'{"items":[{"finding_id":"segment_margin","action_id":"invented"}]}'); assert n==0 and e and '79.63%' in text

def test_positive_margin_no_loss_claim():
    t=build_themes(R[:2],'concentration-risk'); assert 'do not establish losses' in render_themes(t)[0]

def test_anomaly_magnitude():
    rows=[dict(evidence_id=f'E00{i}',title='Anomaly',category='Financial Anomaly',values=dict(period=month,category='Revenue Decline',severity='High',value=value)) for i,(month,value) in enumerate([('March 2014',-.23),('November 2014',-.56)],1)]
    t=build_themes(rows,'anomaly-detection'); assert len(t)==1 and 'November' in t[0]['facts'][0] and 'March' in t[0]['facts'][1]
