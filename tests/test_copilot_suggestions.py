from finsight.copilot_ui import suggestion_label

def test_short_suggestion_labels():
    assert suggestion_label('If you were our CFO, what are the three most important actions you would recommend?') == 'CFO recommendations'
    assert suggestion_label('Which products should we prioritize to improve profitability?') == 'Growth opportunities'

def test_manual_and_unknown_suggestions():
    assert suggestion_label('Explain the revenue change from 2014-01 to 2014-02 by product.') == 'Explain revenue change'
    assert suggestion_label('Other question') == 'Other question'
