from finsight.workspace_ui import NAV_GROUPS, SIM_DEFAULTS, visible_delta, evidence_rows


def test_navigation_unique():
    names = [n for _, group in NAV_GROUPS for n in group]
    assert len(names) == len(set(names)) == 8
    assert 'Scenario Modeling' in names


def test_reset_defaults():
    assert SIM_DEFAULTS == {'sim_rev': 0, 'sim_cost': 0, 'sim_target': 20, 'sim_behavior': 'Independent'}


def test_neutral_delta():
    assert visible_delta(0) is None
    assert visible_delta(0.000001, True) is None
    assert visible_delta(None) is None
    assert visible_delta(-2, True) == '-2.00 pp'


def test_evidence_display():
    values = {'gross_margin': .1585668, 'revenue': 17747116.06, 'records': 94}
    assert [r['Value'] for r in evidence_rows(values)] == ['15.86%', '17,747,116.06', '94']
    assert values['gross_margin'] == .1585668
