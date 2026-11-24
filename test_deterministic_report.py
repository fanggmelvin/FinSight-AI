from deterministic_report import build_facts, render_report, validate_commentary
class Registry:
    records=[{'evidence_id':'E001','title':'Total','values':{'revenue_change':-2830217.95,'previous_gross_margin':.144,'current_gross_margin':.112,'growth':None}}]

def test_money():
    assert build_facts(Registry())['E001.revenue_change']=='-2,830,217.95'
def test_periods():
    f=build_facts(Registry()); assert f['E001.previous_gross_margin']=='14.40%' and f['E001.current_gross_margin']=='11.20%'
def test_missing():
    assert 'E001.growth' not in build_facts(Registry())
def test_reject_number():
    assert not validate_commentary('Revenue fell $3M [E001]',Registry())
def test_reject_unknown():
    assert not validate_commentary('Review sales [E999]',Registry())
def test_render():
    c=validate_commentary('Review sales [E001]',Registry()); report,n=render_report(Registry(),c); assert n==3 and c in report and '-2,830,217.95' in report


def test_numbered_list():
    assert validate_commentary('1. Review sales [E001]', Registry()) == '- Review sales [E001]'

def test_spelled_number():
    assert not validate_commentary('Revenue fell three million [E001]', Registry())

def test_diagnostics():
    from deterministic_report import commentary_diagnostic
    assert commentary_diagnostic('Review [E999]', Registry()) == 'Unknown evidence reference'
    assert commentary_diagnostic('Review [E001]', Registry()) is None

def test_grouping():
    from deterministic_report import report_groups
    assert report_groups(Registry.records)['Other evidence'] == Registry.records


def test_structured_commentary():
    import json
    from deterministic_report import parse_structured_commentary
    item = dict(observation='Revenue declined.', action='Review contracts.', priority='High', evidence_ids=['E001'])
    text, error = parse_structured_commentary(json.dumps({'items':[item]}), Registry())
    assert '[E001]' in text and error is None
    for change in ({'evidence_ids':[]}, {'evidence_ids':['E999']}, {'observation':'Revenue fell $3M'}):
        text, error = parse_structured_commentary(json.dumps({'items':[dict(item, **change)]}), Registry())
        assert not text and error
    text, error = parse_structured_commentary(json.dumps({'items':[item,dict(item,evidence_ids=[])]}), Registry())
    assert '[E001]' in text and error


def test_invalid_json():
    from deterministic_report import parse_structured_commentary
    assert parse_structured_commentary('not json', Registry())[0] == ''
