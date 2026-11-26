from pathlib import Path
import plotly.graph_objects as go
from finsight.anomaly_layout import anomaly_findings, anomaly_display, anomaly_chart, anomaly_css

FLAGS = [dict(category='Revenue Decline',period='A',severity='High',value=-.21,description='a'),dict(category='Revenue Decline',period='B',severity='High',value=-.56,description='b'),dict(category='Margin Compression',period='C',severity='High',value=-7.3,description='c'),dict(category='Revenue Increase',period='D',severity='Review',value=1.2,description='d')]

def test_findings():
    assert anomaly_findings(FLAGS) == (FLAGS[1], FLAGS[2])
    assert anomaly_findings([]) == (None,None)

def test_display_units_and_raw_preservation():
    assert anomaly_display(FLAGS).value.tolist() == ['-21.00%','-56.00%','-7.30 pp','+120.00%']
    assert FLAGS[2]['value'] == -7.3

def test_severity_filter():
    assert len(anomaly_display(FLAGS,'High')) == 3
    assert len(anomaly_display(FLAGS,'Review')) == 1
    assert anomaly_display([]).empty

def test_chart_preserves_thresholds():
    fig=go.Figure(go.Bar(y=[.2,-.3])); fig.add_hline(y=.2); fig.add_hline(y=-.2)
    anomaly_chart(fig)
    assert list(fig.data[0].y)==[.2,-.3]
    assert [s.y0 for s in fig.layout.shapes]==[.2,-.2]
    assert 'fs_workspace_anomaly_detection' in anomaly_css()

def test_workspace_register_and_engine():
    s=(Path(__file__).resolve().parents[1]/'app.py').read_text().split('elif page == "Anomaly Detection":')[1].split('elif page == "Scenario Modeling":')[0]
    assert 'detect_anomalies(df)' in s and 'pd.DataFrame(anomalies).to_csv' in s
    assert s.index('st.plotly_chart') < s.index('with st.expander(f"Anomaly register')
