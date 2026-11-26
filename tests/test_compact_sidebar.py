from finsight.workspace_ui import compact_sidebar_css, dataset_card_markup


def test_demo_card_shows_full_name_and_validation():
    card = dataset_card_markup({"name": "Microsoft Financial Sample (demo)", "validated": True, "records": 700})
    assert "Microsoft Financial Sample (demo)" in card
    assert "Ready · 700 records" in card


def test_long_name_is_complete_and_escaped():
    name = "a" * 50
    card = dataset_card_markup({"name": name + " & <budget>.xlsx", "validated": False, "records": 1})
    assert name + " &amp; &lt;budget&gt;.xlsx" in card
    assert "Column details needed · 1 record" in card


def test_annual_card_labels_fiscal_years():
    card = dataset_card_markup({"name": "Annual.xlsx", "validated": True, "records": 2}, annual=True)
    assert "Ready · 2 fiscal years" in card


def test_css_preserves_scroll_and_focus():
    css = compact_sidebar_css()
    assert 'overflow: hidden' not in css
    assert ':focus-visible' in css
    assert 'border-color: transparent' in css
