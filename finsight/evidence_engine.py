
import json
import math

import pandas as pd
import numpy as np

from finsight.finance_engine import (
    calculate_metrics,
    calculate_monthly_performance,
    calculate_breakdown,
    detect_anomalies,
    calculate_revenue_drivers
)


# ==========================================
# JSON-SAFE FINANCIAL VALUES
# ==========================================

def clean_value(value):

    if isinstance(value, dict):
        return {
            str(k): clean_value(v)
            for k, v in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [clean_value(v) for v in value]

    if isinstance(value, np.generic):
        value = value.item()

    if pd.isna(value):
        return None

    if isinstance(value, float):
        if not math.isfinite(value):
            return None

    if isinstance(value, pd.Timestamp):
        return value.isoformat()

    if isinstance(value, pd.Period):
        return str(value)

    return value


# ==========================================
# SOURCE TRACEABILITY
# ==========================================

def source_reference(df, source_name, sheet_name):

    rows = []

    if "source_row" in df.columns:

        rows = sorted(
            set(
                int(row)
                for row in df["source_row"].dropna()
            )
        )

    return {
        "file": source_name,
        "worksheet": sheet_name,
        "record_count": len(df),
        "source_rows": rows
    }


# ==========================================
# EVIDENCE REGISTRY
# ==========================================

class EvidenceRegistry:

    def __init__(self):

        self.records = []

    def add(
        self,
        category,
        title,
        values,
        methodology,
        source
    ):

        evidence_id = (
            f"E{len(self.records) + 1:03d}"
        )

        record = {
            "evidence_id": evidence_id,
            "category": category,
            "title": title,
            "values": clean_value(values),
            "methodology": methodology,
            "source": clean_value(source)
        }

        self.records.append(record)

        return evidence_id

    def get(self, evidence_id):

        for record in self.records:

            if record["evidence_id"] == evidence_id:

                return record

        return None

    def to_json(self):

        return json.dumps(
            self.records,
            indent=2,
            allow_nan=False
        )


# ==========================================
# BUILD FINANCIAL EVIDENCE
# ==========================================

def build_financial_evidence(
    df,
    source_name="Uploaded Dataset",
    sheet_name="Unknown"
):

    if df.empty:

        raise ValueError(
            "Cannot build evidence from empty data."
        )

    registry = EvidenceRegistry()

    source = source_reference(
        df,
        source_name,
        sheet_name
    )

    metrics = calculate_metrics(df)

    # --------------------------------------
    # CORE FINANCIAL METRICS
    # --------------------------------------

    registry.add(
        category="Financial Summary",
        title="Total Revenue",
        values={
            "revenue": metrics["revenue"]
        },
        methodology="Sum of validated revenue.",
        source=source
    )

    registry.add(
        category="Financial Summary",
        title="Total Cost of Goods Sold",
        values={
            "cogs": metrics["cogs"]
        },
        methodology="Sum of validated COGS.",
        source=source
    )

    registry.add(
        category="Financial Summary",
        title="Gross Profit",
        values={
            "revenue": metrics["revenue"],
            "cogs": metrics["cogs"],
            "gross_profit": metrics["gross_profit"]
        },
        methodology="Revenue minus COGS.",
        source=source
    )

    registry.add(
        category="Financial Summary",
        title="Gross Margin",
        values={
            "gross_margin": metrics["gross_margin"]
        },
        methodology="Gross profit divided by revenue.",
        source=source
    )

    # --------------------------------------
    # BUDGET VARIANCE
    # --------------------------------------

    if "budget_variance" in metrics:

        registry.add(
            category="Budget Analysis",
            title="Revenue Budget Variance",
            values={
                "actual_revenue":
                    metrics["revenue"],
                "budget_revenue":
                    metrics["budget_revenue"],
                "variance":
                    metrics["budget_variance"],
                "variance_pct":
                    metrics["budget_variance_pct"]
            },
            methodology=(
                "Actual revenue minus budget revenue. "
                "Percentage variance equals variance "
                "divided by budget revenue."
            ),
            source=source
        )

    # --------------------------------------
    # MONTHLY FINANCIAL PERFORMANCE
    # --------------------------------------

    monthly = calculate_monthly_performance(df)

    for _, row in monthly.iterrows():

        if pd.isna(row["revenue"]):
            continue

        period = row["month"].to_period("M")

        month_data = df[
            df["date"].dt.to_period("M") == period
        ]

        registry.add(
            category="Monthly Performance",
            title=f"Financial Performance: {period}",
            values=row.to_dict(),
            methodology=(
                "Monthly aggregation of validated "
                "revenue and COGS."
            ),
            source=source_reference(
                month_data,
                source_name,
                sheet_name
            )
        )

        if pd.notna(row["revenue_growth"]):

            comparison_data = df[
                df["date"].dt.to_period("M").isin(
                    [period - 1, period]
                )
            ]

            registry.add(
                category="Monthly Growth",
                title=f"Revenue Growth: {period}",
                values={
                    "month": str(period),
                    "revenue_growth":
                        row["revenue_growth"]
                },
                methodology=(
                    "Current month revenue minus "
                    "previous month revenue, divided "
                    "by previous month revenue."
                ),
                source=source_reference(
                    comparison_data,
                    source_name,
                    sheet_name
                )
            )

    # --------------------------------------
    # BUSINESS PERFORMANCE BREAKDOWNS
    # --------------------------------------

    for dimension in [
        "product",
        "country",
        "segment"
    ]:

        if dimension not in df.columns:
            continue

        breakdown = calculate_breakdown(
            df,
            dimension
        )

        category_values = (
            df[dimension]
            .astype("string")
            .fillna("Unknown")
        )

        for _, row in breakdown.iterrows():

            name = row[dimension]

            category_data = df[
                category_values == name
            ]

            registry.add(
                category=f"{dimension.title()} Performance",
                title=f"{dimension.title()}: {name}",
                values=row.to_dict(),
                methodology=(
                    "Revenue and COGS aggregated "
                    f"by {dimension}. Revenue share "
                    "uses total selected dataset revenue."
                ),
                source=source_reference(
                    df,
                    source_name,
                    sheet_name
                )
            )

    # --------------------------------------
    # FINANCIAL ANOMALIES
    # --------------------------------------

    anomalies = detect_anomalies(df)

    for anomaly in anomalies:

        period = pd.Period(
            pd.to_datetime(
                anomaly["period"],
                format="%B %Y"
            ),
            freq="M"
        )

        comparison_data = df[
            df["date"].dt.to_period("M").isin(
                [period - 1, period]
            )
        ]

        registry.add(
            category="Financial Anomaly",
            title=(
                f"{anomaly['period']} | "
                f"{anomaly['category']}"
            ),
            values=anomaly,
            methodology=(
                "Rule-based detection: revenue changes "
                "of at least 20% or margin compression "
                "of at least 3 percentage points."
            ),
            source=source_reference(
                comparison_data,
                source_name,
                sheet_name
            )
        )

    return registry


# ==========================================
# REVENUE CHANGE INVESTIGATION EVIDENCE
# ==========================================

def build_driver_evidence(
    df,
    dimension,
    current_month,
    previous_month,
    source_name="Uploaded Dataset",
    sheet_name="Unknown"
):

    current = pd.Period(
        current_month, freq="M"
    )

    previous = pd.Period(
        previous_month, freq="M"
    )

    if current <= previous:

        raise ValueError(
            "Current month must follow previous month."
        )

    registry = EvidenceRegistry()

    drivers = calculate_revenue_drivers(
        df,
        dimension,
        current_month,
        previous_month
    )

    if drivers.empty:

        raise ValueError(
            "Insufficient data for revenue attribution."
        )

    comparison_data = df[
        df["date"].dt.to_period("M").isin(
            [current, previous]
        )
    ]

    previous_revenue = float(
        drivers["previous_revenue"].sum()
    )

    current_revenue = float(
        drivers["current_revenue"].sum()
    )

    total_change = (
        current_revenue - previous_revenue
    )

    growth = (
        total_change / previous_revenue
        if previous_revenue > 0
        else None
    )

    registry.add(
        category="Revenue Investigation",
        title="Total Revenue Change",
        values={
            "previous_month": str(previous),
            "current_month": str(current),
            "previous_revenue": previous_revenue,
            "current_revenue": current_revenue,
            "revenue_change": total_change,
            "growth": growth,
            "negative_contributions": float(drivers.loc[drivers["revenue_change"] < 0, "revenue_change"].sum()),
            "positive_contributions": float(drivers.loc[drivers["revenue_change"] > 0, "revenue_change"].sum()),
            "reconciliation_difference": round(float(drivers["revenue_change"].sum()) - total_change, 2)
        },
        methodology=(
            "Current period revenue minus "
            "previous period revenue."
        ),
        source=source_reference(
            comparison_data,
            source_name,
            sheet_name
        )
    )

    for _, row in drivers.iterrows():

        name = row[dimension]

        category_values = (
            comparison_data[dimension]
            .astype("string")
            .fillna("Unknown")
        )

        evidence_data = comparison_data[
            category_values == name
        ]

        profit_values = {}
        for label, period in [('previous', previous), ('current', current)]:
            subset = evidence_data[evidence_data['date'].dt.to_period('M') == period]
            profit_values[label + '_gross_profit'] = float(subset['revenue'].sum() - subset['cogs'].sum())
        profit_values['gross_profit_change'] = profit_values['current_gross_profit'] - profit_values['previous_gross_profit']
        registry.add(
            category="Revenue Contributor",
            title=f"{dimension.title()}: {name}",
            values={
                "previous_month": str(previous),
                "current_month": str(current),
                **row.to_dict(),
                **profit_values
            },
            methodology=(
                "Current category revenue minus "
                "previous category revenue. "
                "This is an arithmetic contribution, "
                "not proof of business causation."
            ),
            source=source_reference(
                evidence_data,
                source_name,
                sheet_name
            )
        )

    return registry


# ==========================================
# AI CONTEXT GENERATION
# ==========================================

def build_ai_context(registry):

    return {
        "instructions": [
            "Use only supplied financial evidence.",
            "Cite evidence IDs for financial claims.",
            "Do not invent financial figures.",
            "Do not treat missing data as zero.",
            "Distinguish findings from hypotheses.",
            "Do not claim causation without evidence.",
            "State when evidence is insufficient.",
            "Present recommendations as proposed actions."
        ],
        "evidence": registry.records
    }


def export_ai_context(registry):

    return json.dumps(
        build_ai_context(registry),
        indent=2,
        allow_nan=False
    )
