from finsight.copilot_ui import compact_period, ranking_lead, action_cards


def test_period_preserves_selected_count():
    assert compact_period('2014-01, 2014-03') == 'Jan 2014 – Mar 2014 · 2 selected months'
    assert compact_period('No dated records') == 'No dated records'


def test_ranking_lead():
    assert ranking_lead('**Product ranking by gross margin (descending)**\n\n- **A:** 15% [E001]') == '**A:** 15% [E001]'
    assert ranking_lead('Leading groups account for 80%') is None


def test_cards_preserve_text_and_provenance():
    assert action_cards('- **Margin (local):** Loss [E001] **Proposed action:** Review costs.') == [('Margin (local)', 'Loss [E001]', 'Review costs.')]
    assert action_cards('Unstructured text') == []


def test_ranking_card_preserves_exact_values():
    from finsight.copilot_ui import ranking_card
    assert ranking_card('**Product ranking by gross margin (descending)**\n\n- **Amarilla:** gross margin 15.86%; gross profit 2,814,104.06 [E039]') == ('Highest product gross margin', 'Amarilla', '15.86%', 'gross profit 2,814,104.06', '[E039]')


def test_ranking_card_lowest_and_unrecognized():
    from finsight.copilot_ui import ranking_card
    assert ranking_card('**Segment ranking by gross margin (ascending)**\n\n- **Enterprise:** gross margin -3.13% [E049]')[0:3] == ('Lowest segment gross margin', 'Enterprise', '-3.13%')
    assert ranking_card('Other answer') is None


def test_offline_status_preserves_real_failures():
    from finsight.copilot_ui import plan_status
    note = 'Local recommendations used; no live AI request for this analysis.'
    incomplete = 'AI count incomplete; local plan used.'
    assert plan_status(note, incomplete, True) == note
    assert plan_status('Rejected', incomplete, False) == 'Rejected; ' + incomplete
    assert 'Insufficient' in plan_status(note, 'Insufficient distinct findings', True)
