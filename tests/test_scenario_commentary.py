import json
from types import SimpleNamespace
from finsight.scenario_commentary import interpret_scenario
from finsight.api_guard import QuotaExceeded
from finsight.scenario_presentation import format_value

S={'cases':[{'label':'COGS unchanged'}]}

def test_disabled(monkeypatch):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    assert interpret_scenario('q',S)['status']=='No AI request sent.'

def test_offline(monkeypatch):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','0')
    assert interpret_scenario('q',S,True)['status']=='No AI request sent.'

def test_live(monkeypatch):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    calls=[]
    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(status='completed',output_text=json.dumps(dict(interpretation='Compare assumptions.',risk='Demand may vary.',action='Test demand.')),usage=SimpleNamespace(total_tokens=100))
    r=interpret_scenario('q',S,True,lambda:SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert r['source']=='AI strategic interpretation' and len(calls)==1 and r['tokens']==100
    assert calls[0]['store'] is False

def test_reject_numbers(monkeypatch):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    def create(**kw): return SimpleNamespace(status='completed',output_text=json.dumps(dict(interpretation='Profit 100',risk='Risk',action='Test')))
    assert interpret_scenario('q',S,True,lambda:SimpleNamespace(responses=SimpleNamespace(create=create)))['source']=='Local recommendation'

def test_quota(monkeypatch):
    monkeypatch.setenv('FINSIGHT_LIVE_AI','1')
    def factory(): raise QuotaExceeded()
    assert 'limit reached' in interpret_scenario('q',S,True,factory)['status']

def test_zero():
    assert format_value(-1e-12,True,True)=='0.00 pp'
