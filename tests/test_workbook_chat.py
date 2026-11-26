from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from finsight.workbook_chat import answer, preview_cells


@pytest.fixture
def book():
    stream = BytesIO()
    wb = Workbook()
    raw = wb.active
    raw.title = "Transactions"
    raw.append(["Country", "Sales", "Date"])
    raw.append(["Canada", 30, datetime(2024, 2, 1)])
    raw.append(["Canada", 20, datetime(2023, 2, 1)])
    raw.append(["France", 10, datetime(2024, 3, 1)])
    plan = wb.create_sheet("Plan")
    plan.append(["Year", 2023, 2024])
    plan.append(["Net revenue", 100, 125])
    plan.append(["Change", None, "=C2-B2"])
    actuals = wb.create_sheet("Monthly_Actuals")
    actuals.append(["Metric", datetime(2024, 2, 1), datetime(2024, 3, 1), datetime(2024, 4, 1)])
    actuals.append(["Revenue", 30, 10, 40])
    budget = wb.create_sheet("Budget")
    budget.append(["Metric", datetime(2024, 2, 1), datetime(2024, 3, 1), datetime(2024, 4, 1)])
    budget.append(["Revenue Budget", 20, 15, 25])
    wb.create_sheet("Revenue")
    wb.save(stream)
    return stream.getvalue()


def test_filters_and_provenance(book):
    result = answer(book, "What was revenue in Canada in 2024?", "Transactions")
    assert "Sales (sum): 30" in result.text
    assert "Transactions!B2:B4" in result.text


def test_cell_chat_context(book):
    first = answer(book, "Sum Plan!B2:C2", "Transactions")
    assert "225" in first.text
    second = answer(book, "Average that range instead", "Transactions", first)
    assert "112.5" in second.text and second.sheet == "Plan"


def test_cached_values_and_formula_text(book):
    assert "No saved value" in answer(book, "Read C3", "Plan").text
    assert "=C2-B2" in answer(book, "Show formula in C3", "Plan").text
    assert "outside" in answer(book, "Read XFE1", "Plan").text


def test_metric_by_fiscal_year(book):
    first = answer(book, "Revenue for FY2023", "Plan")
    assert "B2 = 100" in first.text and "125" not in first.text
    assert "C2 = 125" in answer(book, "What about 2024?", "Plan", first).text


def test_monthly_lookup_and_conversational_scope(book):
    february = answer(book, "What was revenue in February FY2024 on Monthly Actuals?", "Transactions")
    assert february.text == "Feb 2024 revenue: 30.00 (Monthly_Actuals!B2)"
    march = answer(book, "What about March?", "Transactions", february)
    assert march.text == "Mar 2024 revenue: 10.00 (Monthly_Actuals!C2)"
    quarter = answer(book, "Total revenue for Q1 FY2024", "Transactions", march)
    assert quarter.sheet == "Transactions"
    assert "Sales (sum): 40" in quarter.text


def test_comparison_keeps_requested_quarter(book):
    result = answer(book, "Compare actual and budget revenue for Q1 FY2024", "Transactions")
    assert "across 2 matched month(s)" in result.text
    assert "actual minus budget +5.00" in result.text
    assert "largest shortfall was in March 2024, at 5.00 below budget" in result.text
    assert "Apr" not in result.text
    assert result.sources == (("Monthly_Actuals", "B2"), ("Budget", "B2"),
                              ("Monthly_Actuals", "C2"), ("Budget", "C2"))
    assert answer(book, "Read 'Monthly_Actuals'!C2", "Transactions").text.endswith("C2: 10")
    assert "couldn't find that worksheet" in answer(book, "Read Missing!C2", "Transactions").text


def test_sheet_preview_preserves_excel_coordinates(book):
    rows, columns, first_row, displayed, cropped = preview_cells(book, "Budget", "B2:C2")
    assert rows == [(20, 15)]
    assert (columns, first_row, displayed, cropped) == (["B", "C"], 2, "B2:C2", False)
