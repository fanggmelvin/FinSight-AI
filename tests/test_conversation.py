from finsight.conversation import resolve_followup
from finsight.question_router import route_question

PREV = {'route': {'mode':'ranking','dimension':'product','metric':'gross_profit','ascending':False}, 'question':'Rank products by gross profit in 2014'}

def test_metric_followup():
    q, error = resolve_followup('What about their margins?', PREV)
    assert not error and '2014' in q
    route = route_question(q, ['2014-01'])
    assert route['dimension']=='product' and route['metric']=='gross_margin'

def test_direction_followup():
    q, error = resolve_followup('And the weakest?', PREV)
    assert not error and route_question(q,['2014-01'])['ascending']

def test_new_topic():
    q = 'Which countries have the weakest gross margins?'
    assert resolve_followup(q, PREV)==(q,None)

def test_no_context():
    assert resolve_followup('What about their margins?')[1]

def test_ordinal_clarification():
    assert resolve_followup('What about the second one?', PREV)[1]

def test_new_year():
    q, error = resolve_followup('What about margins in 2013?', PREV)
    assert not error and '2013' in q and '2014' not in q

def test_all_years():
    q, error = resolve_followup('What about margins across all years?', PREV)
    assert not error and '2014' not in q
