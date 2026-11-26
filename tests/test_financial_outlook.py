import pandas as pd
import pytest

from finsight.financial_outlook import annual_outlook, is_outlook, monthly_outlook


def test_one_year_uses_sensitivities_and_separates_incomplete_history():
    frame = pd.DataFrame({
        "date": pd.date_range("2013-09-01", periods=16, freq="MS"),
        "revenue": [200] * 4 + [100] * 12,
        "cogs": [120] * 4 + [60] * 12,
    })
    answer = monthly_outlook(frame, "predict next years growth and numbers")
    assert "**2015 revenue and gross-profit outlook**" in answer
    assert "Baseline 2014: revenue 1,200.00" in answer
    assert "Only one comparable year" in answer
    assert "Downside (-5.00%)" in answer
    with pytest.raises(ValueError, match="twelve months"):
        monthly_outlook(frame.iloc[:-1], "predict next year's growth and numbers")


def test_annual_projection_uses_actuals_and_respects_direction():
    annual = pd.DataFrame({
        "Fiscal year": [2023, 2024, 2025],
        "Period type": ["Actual", "Actual", "Forecast"],
        "Currency": ["USD"] * 3,
        "Revenue": [100, 120, 999],
        "COGS": [70, 84, 700],
    })
    outlook = annual_outlook(annual, "predict next year's revenue")
    assert "FY2025" in outlook and "Revenue $144.00" in outlook and "999" not in outlook
    decline = annual_outlook(annual, "predict next year's revenue at 10% decline")
    assert "User assumption (-10.00%)" in decline and "Revenue $108.00" in decline


def test_workbook_forecast_lookup_and_project_owner_use_normal_lookup():
    assert not is_outlook("What is forecast revenue for FY2025?", workbook=True)
    assert not is_outlook("Who is the project owner?", workbook=True)
    assert is_outlook("predict next years growth and numbers", workbook=True)
