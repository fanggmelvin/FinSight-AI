
import pandas as pd
import pytest

from finsight.finance_engine import (
    safe_divide,
    calculate_metrics,
    calculate_monthly_performance,
    calculate_breakdown,
    detect_anomalies,
    calculate_revenue_drivers,
    get_source_evidence,
    analyze_financial_data
)

from finsight.data_validator import (
    detect_columns,
    validate_financial_data
)


# ==========================================
# CONTROLLED FINANCIAL DATASET
# ==========================================

@pytest.fixture
def sample_data():

    return pd.DataFrame({
        "source_row": [2, 3, 4, 5],
        "date": pd.to_datetime([
            "2024-01-01",
            "2024-01-01",
            "2024-02-01",
            "2024-02-01"
        ]),
        "revenue": [
            100000,
            50000,
            70000,
            40000
        ],
        "cogs": [
            70000,
            30000,
            55000,
            30000
        ],
        "product": [
            "Product A",
            "Product B",
            "Product A",
            "Product B"
        ],
        "country": [
            "USA",
            "Canada",
            "USA",
            "Canada"
        ],
        "segment": [
            "Enterprise",
            "Retail",
            "Enterprise",
            "Retail"
        ],
        "budget_revenue": [
            110000,
            55000,
            80000,
            45000
        ]
    })


# ==========================================
# TEST 1: TOTAL REVENUE
# ==========================================

def test_total_revenue(sample_data):

    result = calculate_metrics(sample_data)

    assert result["revenue"] == 260000


# ==========================================
# TEST 2: TOTAL COGS
# ==========================================

def test_total_cogs(sample_data):

    result = calculate_metrics(sample_data)

    assert result["cogs"] == 185000


# ==========================================
# TEST 3: GROSS PROFIT
# ==========================================

def test_gross_profit(sample_data):

    result = calculate_metrics(sample_data)

    assert result["gross_profit"] == 75000


# ==========================================
# TEST 4: GROSS MARGIN
# ==========================================

def test_gross_margin(sample_data):

    result = calculate_metrics(sample_data)

    assert result["gross_margin"] == pytest.approx(
        75000 / 260000
    )


# ==========================================
# TEST 5: BUDGET VARIANCE
# ==========================================

def test_budget_variance(sample_data):

    result = calculate_metrics(sample_data)

    assert result["budget_revenue"] == 290000

    assert result["budget_variance"] == -30000

    assert result["budget_variance_pct"] == pytest.approx(
        -30000 / 290000
    )


# ==========================================
# TEST 6: DIVISION BY ZERO
# ==========================================

def test_zero_division():

    assert safe_divide(100, 0) is None


# ==========================================
# TEST 7: MONTHLY REVENUE
# ==========================================

def test_monthly_revenue(sample_data):

    monthly = calculate_monthly_performance(
        sample_data
    )

    assert len(monthly) == 2

    assert monthly.iloc[0]["revenue"] == 150000

    assert monthly.iloc[1]["revenue"] == 110000


# ==========================================
# TEST 8: MONTH-OVER-MONTH GROWTH
# ==========================================

def test_monthly_growth(sample_data):

    monthly = calculate_monthly_performance(
        sample_data
    )

    expected_growth = (
        110000 - 150000
    ) / 150000

    assert monthly.iloc[1][
        "revenue_growth"
    ] == pytest.approx(expected_growth)


# ==========================================
# TEST 9: PRODUCT PERFORMANCE
# ==========================================

def test_product_breakdown(sample_data):

    result = calculate_breakdown(
        sample_data,
        "product"
    )

    product_a = result[
        result["product"] == "Product A"
    ].iloc[0]

    assert product_a["revenue"] == 170000

    assert product_a["gross_profit"] == 45000


# ==========================================
# TEST 10: REVENUE CONCENTRATION
# ==========================================

def test_revenue_concentration(sample_data):

    result = calculate_breakdown(
        sample_data,
        "product"
    )

    assert result["revenue_share"].sum() == pytest.approx(
        1.0
    )


# ==========================================
# TEST 11: REVENUE ANOMALY DETECTION
# ==========================================

def test_anomaly_detection(sample_data):

    anomalies = detect_anomalies(sample_data)

    declines = [
        item for item in anomalies
        if item["category"] == "Revenue Decline"
    ]

    assert len(declines) == 1

    assert declines[0]["severity"] == "High"

    assert declines[0]["value"] == pytest.approx(
        -40000 / 150000
    )


# ==========================================
# TEST 12: REVENUE DRIVER ATTRIBUTION
# ==========================================

def test_revenue_drivers(sample_data):

    drivers = calculate_revenue_drivers(
        sample_data,
        "product",
        "2024-02",
        "2024-01"
    )

    product_a = drivers[
        drivers["product"] == "Product A"
    ].iloc[0]

    product_b = drivers[
        drivers["product"] == "Product B"
    ].iloc[0]

    assert product_a["revenue_change"] == -30000

    assert product_b["revenue_change"] == -10000

    assert drivers["revenue_change"].sum() == -40000


# ==========================================
# TEST 13: SOURCE EVIDENCE
# ==========================================

def test_source_evidence(sample_data):

    evidence = get_source_evidence(
        sample_data,
        dimension="product",
        value="Product A",
        month="2024-02"
    )

    assert len(evidence) == 1

    assert evidence.iloc[0]["source_row"] == 4

    assert evidence.iloc[0]["revenue"] == 70000


# ==========================================
# TEST 14: AUTOMATIC COLUMN DETECTION
# ==========================================

def test_column_detection():

    raw_data = pd.DataFrame({
        "Sales": [1000],
        "COGS": [700],
        "Profit": [300],
        "Date": ["2024-01-01"]
    })

    mapping = detect_columns(raw_data)

    assert mapping["revenue"] == "Sales"

    assert mapping["cogs"] == "COGS"

    assert mapping["date"] == "Date"

    assert mapping["reported_profit"] == "Profit"


# ==========================================
# TEST 15: VALID FINANCIAL DATA
# ==========================================

def test_valid_financial_data():

    raw_data = pd.DataFrame({
        "Sales": [1000],
        "COGS": [700],
        "Profit": [300],
        "Date": ["2024-01-01"]
    })

    result = validate_financial_data(raw_data)

    assert result["valid"] is True

    assert len(result["errors"]) == 0

    assert result["data"].iloc[0][
        "gross_profit"
    ] == 300


# ==========================================
# TEST 16: INVALID FINANCIAL DATA
# ==========================================

def test_invalid_financial_data():

    raw_data = pd.DataFrame({
        "Sales": ["invalid"],
        "COGS": [700],
        "Date": ["2024-01-01"]
    })

    result = validate_financial_data(raw_data)

    assert result["valid"] is False

    assert len(result["errors"]) > 0


# ==========================================
# TEST 17: COMPLETE ANALYSIS PIPELINE
# ==========================================

def test_complete_analysis(sample_data):

    result = analyze_financial_data(sample_data)

    assert result["metrics"]["revenue"] == 260000

    assert len(result["monthly_performance"]) == 2

    assert len(result["product_performance"]) == 2

    assert len(result["country_performance"]) == 2

    assert len(result["segment_performance"]) == 2

    assert len(result["anomalies"]) > 0


# ==========================================
# TEST 18: MISSING MONTH HANDLING
# ==========================================

def test_missing_month(sample_data):

    data = sample_data.copy()

    data.loc[2:3, "date"] = pd.Timestamp(
        "2024-03-01"
    )

    monthly = calculate_monthly_performance(data)

    assert len(monthly) == 3

    assert pd.isna(monthly.iloc[1]["revenue"])

    assert pd.isna(monthly.iloc[2]["revenue_growth"])


# ==========================================
# TEST 19: PROFIT RECONCILIATION
# ==========================================

def test_profit_reconciliation():

    raw_data = pd.DataFrame({
        "Sales": [1000],
        "COGS": [700],
        "Profit": [500],
        "Date": ["2024-01-01"]
    })

    result = validate_financial_data(raw_data)

    assert any(
        "reconciliation" in warning.lower()
        for warning in result["warnings"]
    )


# ==========================================
# TEST 20: INCOMPLETE BUDGET DATA
# ==========================================

def test_incomplete_budget(sample_data):

    data = sample_data.copy()

    data.loc[0, "budget_revenue"] = float("nan")

    result = calculate_metrics(data)

    assert "budget_variance" not in result
