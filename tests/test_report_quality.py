from types import SimpleNamespace
from finsight.deterministic_report import build_facts, render_report
from finsight.workspace_ui import evidence_rows, report_kpi_lines
import pytest

@pytest.mark.parametrize('value,expected', [(0.8047,'+0.80 pp'),(-7.3005,'-7.30 pp'),(-3.7488,'-3.75 pp'),(5.654,'+5.65 pp')])
def test_margin_points(value, expected):
    values = {'margin_change_pp':value, 'gross_margin':.1423, 'records':700}
    registry = SimpleNamespace(records=[{'evidence_id':'E001','title':'Monthly','values':values}])
    assert build_facts(registry)['E001.margin_change_pp'] == expected
    assert evidence_rows(values)[0]['Value'] == expected
    report,_ = render_report(registry,'Local review',ai_used=False)
    assert expected in report and 'records: 700' in report and 'AI interpretation' not in report
    assert values['margin_change_pp'] == value

def test_kpis():
    text = report_kpi_lines({'revenue':118726350.25999999,'gross_margin':.142291,'record_count':700,'budget_variance_pct':None})
    assert '118,726,350.26' in text and '14.23%' in text and 'Record Count: 700' in text and 'N/A' in text

def test_anomaly_display():
    assert evidence_rows({'category':'Margin Compression','value':-3.17},'Financial Anomaly')[1]['Value'] == '-3.17 pp'
    assert evidence_rows({'category':'Revenue Decline','value':-.5649},'Financial Anomaly')[1]['Value'] == '-56.49%'
