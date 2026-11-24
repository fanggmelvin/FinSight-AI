import pytest
from finsight.verification_engine import verify_claim, verify_claims

class Registry:
    records = [
        {'evidence_id':'E001','category':'Summary','values':{'revenue':118730000,'growth':-0.5649}},
        {'evidence_id':'E002','category':'Segment','values':{'gross_margin':0.2169}},
        {'evidence_id':'E003','category':'Segment','values':{'gross_margin':0.731}},
        {'evidence_id':'E004','category':'Segment','values':{'gross_margin':-0.0313}},
    ]
    def get(self, key):
        return next((r for r in self.records if r['evidence_id']==key),None)

@pytest.mark.parametrize('value,unit,decimals,status',[(118.7,'million',1,'passed'),(150,'million',0,'failed'),(118730000,'raw',0,'passed'),(118.8,'million',1,'failed'),(118730,'thousand',0,'passed'),('NaN','raw',0,'unverified'),(118.7,'bad',1,'unverified')])
def test_revenue(value,unit,decimals,status):
    assert verify_claim(dict(evidence_id='E001',field='revenue',value=value,unit=unit,decimals=decimals),Registry())['status']==status

@pytest.mark.parametrize('value,status',[(-56.5,'passed'),(56.5,'failed'),(-50,'failed')])
def test_growth(value,status):
    assert verify_claim(dict(evidence_id='E001',field='growth',value=value,unit='percent',decimals=1),Registry())['status']==status

@pytest.mark.parametrize('key,direction,status',[('E002','highest','failed'),('E003','highest','passed'),('E004','lowest','passed'),('E002','lowest','failed')])
def test_ranking(key,direction,status):
    assert verify_claim(dict(evidence_id=key,field='gross_margin',kind='ranking',direction=direction),Registry())['status']==status

def test_unknown_id():
    assert verify_claim(dict(evidence_id='E999',field='revenue',value=1),Registry())['status']=='unverified'

def test_unknown_field():
    assert verify_claim(dict(evidence_id='E001',field='net_income',value=1),Registry())['status']=='unverified'

def test_summary():
    assert verify_claims([dict(evidence_id='E999')],Registry())['unverified']==1

from finsight.claim_mapping import normalize_claims, uncovered_numbers

@pytest.mark.parametrize('value', [-2.83,-2830000])
def test_million_surface_normalization(value):
    claim = dict(text='Carretera: -$2.83M', value=value, unit='million', decimals=2, field='revenue_change', evidence_id='E001')
    normalized = normalize_claims([claim], Registry())
    assert normalized[0]['value'] == -2.83
    assert not uncovered_numbers(claim['text'], normalized)

def test_no_evidence_based_scale_guess():
    claim = dict(text='Revenue $3M', value=2830000, unit='million', evidence_id='E001')
    assert normalize_claims([claim], Registry())[0]['value'] == 2830000

def test_percentage_not_ranking():
    claim = dict(text='100% decline', kind='ranking', evidence_id='E001')
    assert normalize_claims([claim], Registry())[0]['value'] == -100
