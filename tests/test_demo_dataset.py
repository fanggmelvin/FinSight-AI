from finsight.demo_dataset import load_demo_state
from finsight.finance_engine import calculate_metrics
import pytest


def test_demo_dataset():
    state = load_demo_state()
    df = state["validated_data"]
    assert len(df) == 700
    assert calculate_metrics(df[df.date.dt.year == 2014])["revenue"] == pytest.approx(92311094.75)


def test_demo_state_is_independent():
    a, b = load_demo_state(), load_demo_state()
    a["validated_data"].iloc[0, 0] = None
    assert b["validated_data"].iloc[0, 0] is not None


def test_offline_never_calls_client(monkeypatch):
    import finsight.ai_engine as ai_engine
    from finsight.evidence_engine import build_financial_evidence
    monkeypatch.setenv("FINSIGHT_LIVE_AI", "0")
    def forbidden():
        pytest.fail("Offline mode attempted API client creation")
    monkeypatch.setattr(ai_engine, "get_client", forbidden)
    df = load_demo_state()["validated_data"]
    result = ai_engine.analyze_financial_data("Summarize financial performance in 2014.", df, "demo", "Raw_Data")
    assert result["total_tokens"] == 0
    assert result["numerical_verification"]["selected_actions"] == 0
