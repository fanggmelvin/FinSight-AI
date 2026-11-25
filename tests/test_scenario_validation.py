import pytest
from finsight.scenario_validation import rejection_reason

@pytest.mark.parametrize('text', ['Margin reaches twenty percent.', 'Profit rises by ⅓.', 'Save ₹500.', 'This guarantees returns.', 'The change reflects pricing power.', 'Growth is driven by better efficiency.', 'Net income will rise.', 'Net profit increases.'])
def test_reject(text):
    assert rejection_reason(text)

@pytest.mark.parametrize('text', ['Test pricing power before changing prices.', 'Gross margin percentage remains constant.', 'Assess potential effects on net income.', 'Demand may vary.', 'Compare fixed and proportional COGS.'])
def test_allow(text):
    assert rejection_reason(text) is None
