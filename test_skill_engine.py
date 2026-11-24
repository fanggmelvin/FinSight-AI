import pytest
from skill_engine import select_skills, load_skills, ALLOWED

@pytest.mark.parametrize('question,records,route,expected', [
 ('Summarize performance', [], {}, 'financial-performance'),
 ('Rank profitability', [], {'metric':'gross_margin'}, 'profitability-analysis'),
 ('Rank concentration and profitability', [], {'metric':'revenue_share'}, 'concentration-risk'),
 ('What should management investigate?', [{'category':'Revenue Investigation'}], {}, 'variance-analysis'),
 ('Explain changes', [{'category':'Total financial change'}], {}, 'variance-analysis'),
 ('Prepare executive financial report', [], {}, 'executive-reporting'),
 ('Identify unusual results', [], {}, 'anomaly-detection'),
 ('Gross margin risks', [], {}, 'profitability-analysis'),
 ('Revenue dependency', [], {}, 'concentration-risk'),
])
def test_selection(question, records, route, expected):
    assert select_skills(question, records, route) == (expected,'evidence-verification')

@pytest.mark.parametrize('name', sorted(ALLOWED))
def test_bundled(name):
    assert load_skills((name,'evidence-verification'))

def test_missing(tmp_path):
    with pytest.raises(FileNotFoundError): load_skills(('evidence-verification',),tmp_path)

def test_unknown():
    with pytest.raises(ValueError): load_skills(('../secret','evidence-verification'))

def test_required():
    with pytest.raises(ValueError): load_skills(('financial-performance',))

def test_malformed(tmp_path):
    folder=tmp_path/'evidence-verification'; folder.mkdir()
    (folder/'SKILL.md').write_text('invalid')
    with pytest.raises(ValueError): load_skills(('evidence-verification',),tmp_path)
