import json
from types import SimpleNamespace
import pytest
from finsight.strategic_choices import select_plan

F=[dict(id=str(i),title=f'Theme {i}',facts=[f'Calculated fact [E00{i+1}]'],actions=[f'Review costs {i}',f'Review prices {i}']) for i in range(3)]

def run(ids,status='completed',count=3):
    calls=[]
    def create(**kw):
        calls.append(kw)
        return SimpleNamespace(output_text=json.dumps({'choices':ids}),status=status,usage=None)
    result=select_plan(SimpleNamespace(responses=SimpleNamespace(create=create)),'test','CFO',F,count)
    assert len(calls)==1
    assert calls[0]['store'] is False
    return result

def test_valid_selection():
    text,err,_=run(['A2_1','A0_0','A1_1'])
    assert err is None and text.count('AI-selected')==3 and text.startswith('**Theme 2') and '[E003]' in text

@pytest.mark.parametrize('ids',[['A0_0','A0_1','A1_0'],['A0_0','A1_0','invented'],['A0_0'],['A0_0','A1_0',{}]])
def test_invalid_selection(ids):
    text,err,_=run(ids)
    assert not text and err

def test_incomplete():
    assert not run(['A0_0','A1_0','A2_0'],'incomplete')[0]

def test_insufficient_findings_no_call():
    assert select_plan(None,'test','CFO',F[:1],3)[1]
