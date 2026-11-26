from finsight.workspace_ui import evidence_label, registry_display, scenario_delta_color, evidence_rows


def test_acronym_labels():
    assert evidence_label('current_cogs') == 'Current COGS'
    assert evidence_rows({'cogs': 10}) == [{'Field': 'COGS', 'Value': '10.00'}]


def test_registry_counts_only():
    assert registry_display('records', '1,234.00') == '1,234'
    assert registry_display('revenue', '1,234.00') == '1,234.00'
    assert registry_display('records', '1.50') == '1.50'


def test_delta_semantics():
    assert scenario_delta_color('COGS', -10) == 'inverse'
    assert scenario_delta_color('COGS', 10) == 'inverse'
    assert scenario_delta_color('Revenue', 10) == 'normal'
    assert scenario_delta_color('Gross profit', -10) == 'normal'
    assert scenario_delta_color('Gross margin (%)', 0) == 'off'
    assert scenario_delta_color('Revenue', None) == 'off'
