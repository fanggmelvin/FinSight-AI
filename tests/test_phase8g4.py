import pytest
from finsight.conversation import resolve_followup
from finsight.question_router import route_question

MONTHS = ['2013-09', '2014-01']

def prior(q):
    return {'route': route_question(q, MONTHS), 'effective_question': q}

@pytest.mark.parametrize('follow,dim,metric,year,ascending', [
    ('What about in 2014?', 'product','gross_margin','2014',False),
    ('What about countries?', 'country','gross_margin','2013',False),
    ('What about revenue?', 'product','revenue','2013',False),
    ('And the lowest?', 'product','gross_margin','2013',True),
    ('What about all reporting periods?', 'product','gross_margin','',False),
    ('What about segments in 2014?', 'segment','gross_margin','2014',False),
])
def test_inheritance(follow,dim,metric,year,ascending):
    q, err = resolve_followup(follow, prior('Which product has the highest gross margin in 2013?'))
    assert not err
    r = route_question(q, MONTHS)
    assert (r['dimension'],r['metric'],r['ascending']) == (dim,metric,ascending)
    assert (year in q) if year else ('2013' not in q and '2014' not in q)

def test_chain():
    q, err = resolve_followup('What about in 2014?', prior('Which product has the highest gross margin?'))
    assert not err
    q, err = resolve_followup('What about countries?', prior(q))
    assert not err and '2014' in q and route_question(q,MONTHS)['dimension']=='country'

@pytest.mark.parametrize('q', ['Which one?', 'What about countries and segments?', 'What about countries in March?', 'What about COGS?'])
def test_ambiguous(q):
    assert resolve_followup(q, prior('Which product has the highest gross margin?'))[1]

def test_reset():
    assert resolve_followup('What about countries?', None)[1]
