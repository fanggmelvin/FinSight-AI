from finsight.evidence_ui import evidence_sections


def result(text, **kwargs):
    return dict(direct_answer=text, cited_evidence=[{'evidence_id': f'E{i:03d}', 'title': str(i)} for i in range(1, 5)], **kwargs)


def test_order_dedup_and_unknown():
    primary, all_records = evidence_sections(result('[E003] [E001] [E003] [E999]'))
    assert [r['evidence_id'] for r in primary] == ['E003', 'E001']
    assert len(all_records) == 4


def test_ranges_and_groups():
    primary, _ = evidence_sections(result('[E002–E004; E001]'))
    assert len(primary) == 4


def test_supporting_commentary_not_featured():
    primary, _ = evidence_sections(result('', local_plan=True, commentary='Action [E002]\n\n**Calculated supporting findings**\n\n[E004]'))
    assert [r['evidence_id'] for r in primary] == ['E002']


def test_no_primary_and_no_mutation():
    r = result('', commentary='[E001]')
    primary, records = evidence_sections(r)
    assert not primary and records == r['cited_evidence']
