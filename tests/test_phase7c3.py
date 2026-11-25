import pytest
from finsight.api_guard import reserve_request, quota_status, quota_config, QuotaExceeded
from finsight.scenario_commentary import local_risk, scenario_instructions
from finsight.commentary_grounding import terminology_diagnostic
from test_phase7c2 import R, ROUTE
from finsight.deterministic_report import parse_structured_commentary
import json

@pytest.mark.parametrize('revenue,cogs,word', [(0,80,'payment obligations'),(80,80,'demand'),(100,90,'Supplier')])
def test_specific_risk(revenue,cogs,word):
    s={'baseline':{'Revenue':100,'COGS':80},'cases':[{'label':'Explicit changes','metrics':{'Revenue':revenue,'COGS':cogs}}]}
    assert word in local_risk(s) and local_risk(s) in scenario_instructions(s)

@pytest.mark.parametrize('text',['operational loss','operating loss','operating profit'])
def test_unsupported_operating_metric(text):
    assert terminology_diagnostic(text)

def test_quota_profiles(monkeypatch,tmp_path):
    monkeypatch.setenv('FINSIGHT_QUOTA_DB',str(tmp_path/'prod.db'))
    monkeypatch.setenv('FINSIGHT_DEV_QUOTA_DB',str(tmp_path/'dev.db'))
    monkeypatch.setenv('FINSIGHT_ENV','production')
    reserve_request(now=1000)
    monkeypatch.setenv('FINSIGHT_ENV','development')
    assert quota_status(now=1001)[0]['used']==0
    reserve_request(now=1001)
    monkeypatch.setenv('FINSIGHT_ENV','production')
    assert quota_status(now=1002)[0]['used']==1

def test_quota_reset(monkeypatch,tmp_path):
    monkeypatch.setenv('FINSIGHT_ENV','production')
    monkeypatch.setenv('FINSIGHT_QUOTA_DB',str(tmp_path/'q.db'))
    monkeypatch.setenv('FINSIGHT_MINUTE_REQUESTS','1')
    reserve_request(now=1000)
    assert quota_status(now=1001)[0]['retry_seconds']==59
    with pytest.raises(QuotaExceeded,match='minute'):
        reserve_request(now=1001)
    assert quota_status(now=1060)[0]['remaining']==1

def test_both_leaders():
    raw=json.dumps({'items':[{'priority':'High','action':'Review pricing.','evidence_ids':['E001']}]})
    text,err=parse_structured_commentary(raw,R,dict(ROUTE,ambiguous_profitability=True))
    assert 'Paseo: gross profit 30.00' in text and 'Local action' in text

def test_deduplicate():
    raw=json.dumps({'items':[{'priority':'High','action':a,'evidence_ids':['E001']} for a in ['Review pricing.','Review discounts.']]})
    text,err=parse_structured_commentary(raw,R,ROUTE)
    assert text.count('Amarilla: gross margin')==1 and 'Review discounts.' in text
