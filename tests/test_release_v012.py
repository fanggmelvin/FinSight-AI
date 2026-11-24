from question_router import route_question
from deterministic_report import key_tables
import pytest

@pytest.mark.parametrize('question,mode,metric',[
 ('Which products had the weakest gross margins in 2014?', 'ranking','gross_margin'),
 ('Which business segments have the highest revenue concentration?', 'ranking','revenue_share'),
 ('Analyze revenue performance in 2025','clarify',None),
 ('What was actual net income in 2014?','clarify',None),
])
def test_special_routes(question,mode,metric):
    route=route_question(question,['2014-10','2014-11'])
    assert route['mode']==mode and route.get('metric')==metric

def test_table():
    records=[{'title':'Product: A','evidence_id':'E001','values':{'gross_margin':-.1,'revenue':100}}]
    assert key_tables(records)['Product'][0]['gross_margin']==-.1
