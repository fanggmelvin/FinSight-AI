
import json

import numpy as np
import pandas as pd
import pytest

from evidence_engine import (
    EvidenceRegistry,
    clean_value,
    source_reference,
    build_financial_evidence,
    build_driver_evidence,
    build_ai_context,
    export_ai_context
)


@pytest.fixture
def financial_data():

    return pd.DataFrame({
        "date": pd.to_datetime([
            "2014-10-01",
            "2014-10-01",
            "2014-11-01",
            "2014-11-01"
        ]),
        "revenue": [
            1000.0,
            2000.0,
            1500.0,
            500.0
        ],
        "cogs": [
            700.0,
            1400.0,
            1000.0,
            350.0
        ],
        "product": [
            "Paseo",
            "Velo",
            "Paseo",
            "Velo"
        ],
        "country": [
            "USA",
            "Canada",
            "USA",
            "Canada"
        ],
        "segment": [
            "Government",
            "Enterprise",
            "Government",
            "Enterprise"
        ],
        "source_row": [2, 3, 4, 5]
    })


@pytest.fixture
def registry():

    result = EvidenceRegistry()

    result.add(
        category="Financial Summary",
        title="Total Revenue",
        values={"revenue": 5000.0},
        methodology="Sum of revenue.",
        source={
            "file": "test.xlsx",
            "worksheet": "Raw_Data",
            "source_rows": [2, 3, 4, 5]
        }
    )

    return result


def test_clean_numpy_integer():

    assert clean_value(np.int64(100)) == 100


def test_clean_nan():

    assert clean_value(float("nan")) is None


def test_clean_infinity():

    assert clean_value(float("inf")) is None


def test_clean_timestamp():

    value = pd.Timestamp("2014-10-01")

    assert clean_value(value) == (
        "2014-10-01T00:00:00"
    )


def test_unique_evidence_ids(registry):

    second_id = registry.add(
        category="Test",
        title="Second Evidence",
        values={"value": 100},
        methodology="Test calculation.",
        source={}
    )

    assert second_id == "E002"

    ids = [
        record["evidence_id"]
        for record in registry.records
    ]

    assert len(ids) == len(set(ids))


def test_evidence_lookup(registry):

    record = registry.get("E001")

    assert record["title"] == "Total Revenue"
    assert record["values"]["revenue"] == 5000


def test_invalid_evidence_lookup(registry):

    assert registry.get("E999") is None


def test_source_traceability(financial_data):

    source = source_reference(
        financial_data,
        "test.xlsx",
        "Raw_Data"
    )

    assert source["file"] == "test.xlsx"
    assert source["worksheet"] == "Raw_Data"
    assert source["record_count"] == 4
    assert source["source_rows"] == [2, 3, 4, 5]


def test_registry_json(registry):

    result = json.loads(registry.to_json())

    assert result[0]["evidence_id"] == "E001"
    assert result[0]["values"]["revenue"] == 5000


def test_ai_context(registry):

    context = build_ai_context(registry)

    assert "instructions" in context
    assert "evidence" in context
    assert len(context["evidence"]) == 1


def test_ai_context_export(registry):

    context = json.loads(
        export_ai_context(registry)
    )

    assert context["evidence"][0][
        "evidence_id"
    ] == "E001"


def test_empty_financial_data():

    with pytest.raises(ValueError):

        build_financial_evidence(
            pd.DataFrame()
        )


def test_financial_summary(financial_data):

    result = build_financial_evidence(
        financial_data,
        "test.xlsx",
        "Raw_Data"
    )

    revenue = next(
        record for record in result.records
        if record["title"] == "Total Revenue"
    )

    assert revenue["values"]["revenue"] == (
        pytest.approx(5000)
    )

    profit = next(
        record for record in result.records
        if record["title"] == "Gross Profit"
    )

    assert profit["values"]["gross_profit"] == (
        pytest.approx(1550)
    )


def test_revenue_change_evidence(financial_data):

    result = build_driver_evidence(
        financial_data,
        dimension="product",
        current_month="2014-11",
        previous_month="2014-10",
        source_name="test.xlsx",
        sheet_name="Raw_Data"
    )

    summary = result.get("E001")["values"]

    assert summary["previous_revenue"] == (
        pytest.approx(3000)
    )

    assert summary["current_revenue"] == (
        pytest.approx(2000)
    )

    assert summary["revenue_change"] == (
        pytest.approx(-1000)
    )

    assert summary["growth"] == (
        pytest.approx(-1 / 3)
    )


def test_product_contribution_reconciliation(
    financial_data
):

    result = build_driver_evidence(
        financial_data,
        dimension="product",
        current_month="2014-11",
        previous_month="2014-10"
    )

    contributors = [
        record
        for record in result.records
        if record["category"] ==
        "Revenue Contributor"
    ]

    total_contribution = sum(
        record["values"]["revenue_change"]
        for record in contributors
    )

    assert total_contribution == (
        pytest.approx(-1000)
    )


def test_product_source_rows(financial_data):

    result = build_driver_evidence(
        financial_data,
        dimension="product",
        current_month="2014-11",
        previous_month="2014-10"
    )

    paseo = next(
        record
        for record in result.records
        if record["title"] == "Product: Paseo"
    )

    assert paseo["source"]["source_rows"] == [
        2, 4
    ]


def test_invalid_comparison_period(
    financial_data
):

    with pytest.raises(ValueError):

        build_driver_evidence(
            financial_data,
            dimension="product",
            current_month="2014-10",
            previous_month="2014-11"
        )
