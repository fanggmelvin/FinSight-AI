from finsight.claim_mapping import normalize_claims, uncovered_numbers
import pytest
class Registry:
    def get(self, key):
        return {'category':'Revenue Investigation','title':'Total Revenue Change','values':{'growth':-.565,'revenue_change':-6991605.72}} if key=='E001' else {'category':'Revenue Contributor','title':'Product: Paseo','values':{'revenue_change':2840879.54}} if key=='E002' else None
@pytest.mark.parametrize('key,field,expected',[('E001','total_revenue_change','revenue_change'),('E001','revenue_growth_pct','growth'),('E002','paseo_revenue_change','revenue_change'),('E002','velo_revenue_change','velo_revenue_change'),('E999','total_revenue_change','total_revenue_change')])
def test_alias(key,field,expected):
    assert normalize_claims([{'evidence_id':key,'field':field}],Registry())[0]['field']==expected

def test_missing_total():
    assert len(uncovered_numbers('Loss $9,532,485', []))==1

def test_multiple_numbers():
    text='Revenue fell $100 (5%)'
    assert [c['text'] for c in uncovered_numbers(text,[{'text':text,'value':-100,'unit':'raw'}])]==['5%']
