
import pandas as pd
import numpy as np


# ==========================================
# CORE FINANCIAL METRICS
# ==========================================

def safe_divide(numerator, denominator):

    if pd.isna(denominator) or denominator == 0:
        return None

    return float(numerator / denominator)


def calculate_metrics(df):

    revenue = float(df["revenue"].sum())
    cogs = float(df["cogs"].sum())
    gross_profit = revenue - cogs

    metrics = {
        "revenue": revenue,
        "cogs": cogs,
        "gross_profit": gross_profit,
        "gross_margin": safe_divide(
            gross_profit, revenue
        ),
        "record_count": len(df)
    }

    if "budget_revenue" in df.columns:

        budget = df["budget_revenue"].sum(min_count=1)

        if pd.notna(budget) and df["budget_revenue"].notna().all():

            budget = float(budget)
            variance = revenue - budget

            metrics["budget_revenue"] = budget
            metrics["budget_variance"] = variance
            metrics["budget_variance_pct"] = safe_divide(
                variance, budget
            )

    return metrics


# ==========================================
# MONTHLY PERFORMANCE
# ==========================================

def calculate_monthly_performance(df):

    data = df.copy()

    data["month"] = (
        data["date"]
        .dt.to_period("M")
        .dt.to_timestamp()
    )

    monthly = (
        data.groupby("month", as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            records=("revenue", "size")
        )
        .sort_values("month")
    )

    monthly["gross_profit"] = (
        monthly["revenue"] - monthly["cogs"]
    )

    monthly["gross_margin"] = (
        monthly["gross_profit"]
        / monthly["revenue"].replace(0, np.nan)
    )

    # Missing months remain missing, not zero.
    monthly = monthly.set_index("month").asfreq("MS")

    previous_revenue = monthly["revenue"].shift(1)

    monthly["revenue_growth"] = (
        (monthly["revenue"] - previous_revenue)
        / previous_revenue.where(previous_revenue > 0)
    )

    monthly["margin_change_pp"] = (
        monthly["gross_margin"].diff() * 100
    )

    return monthly.reset_index()


# ==========================================
# BUSINESS PERFORMANCE BREAKDOWN
# ==========================================

def calculate_breakdown(df, dimension):

    if dimension not in df.columns:
        return pd.DataFrame()

    data = df.copy()

    data[dimension] = (
        data[dimension]
        .astype("string")
        .fillna("Unknown")
    )

    breakdown = (
        data.groupby(dimension, as_index=False)
        .agg(
            revenue=("revenue", "sum"),
            cogs=("cogs", "sum"),
            records=("revenue", "size")
        )
    )

    breakdown["gross_profit"] = (
        breakdown["revenue"] - breakdown["cogs"]
    )

    breakdown["gross_margin"] = (
        breakdown["gross_profit"]
        / breakdown["revenue"].replace(0, np.nan)
    )

    total_revenue = breakdown["revenue"].sum()

    if total_revenue > 0:

        breakdown["revenue_share"] = (
            breakdown["revenue"] / total_revenue
        )

    else:

        breakdown["revenue_share"] = np.nan

    return breakdown.sort_values(
        "revenue",
        ascending=False
    ).reset_index(drop=True)


# ==========================================
# FINANCIAL ANOMALY DETECTION
# ==========================================

def detect_anomalies(df):

    monthly = calculate_monthly_performance(df)

    anomalies = []

    for _, row in monthly.iterrows():

        month = row["month"].strftime("%B %Y")

        growth = row["revenue_growth"]

        if pd.notna(growth):

            if growth <= -0.20:

                anomalies.append({
                    "category": "Revenue Decline",
                    "period": month,
                    "severity": "High",
                    "value": float(growth),
                    "description": (
                        f"Revenue declined {abs(growth):.1%} "
                        "compared with the previous month."
                    )
                })

            elif growth >= 0.20:

                anomalies.append({
                    "category": "Revenue Increase",
                    "period": month,
                    "severity": "Review",
                    "value": float(growth),
                    "description": (
                        f"Revenue increased {growth:.1%} "
                        "compared with the previous month."
                    )
                })

        margin_change = row["margin_change_pp"]

        if pd.notna(margin_change):

            if margin_change <= -3:

                anomalies.append({
                    "category": "Margin Compression",
                    "period": month,
                    "severity": "High",
                    "value": float(margin_change),
                    "description": (
                        f"Gross margin declined "
                        f"{abs(margin_change):.2f} "
                        "percentage points."
                    )
                })

    return anomalies


# ==========================================
# REVENUE CHANGE ATTRIBUTION
# ==========================================

def calculate_revenue_drivers(
    df,
    dimension,
    current_month,
    previous_month
):

    if dimension not in df.columns:
        return pd.DataFrame()

    data = df.copy()

    data["month"] = data["date"].dt.to_period("M")

    data[dimension] = (
        data[dimension]
        .astype("string")
        .fillna("Unknown")
    )

    current_month = pd.Period(
        current_month, freq="M"
    )

    previous_month = pd.Period(
        previous_month, freq="M"
    )

    current_data = data[
        data["month"] == current_month
    ]

    previous_data = data[
        data["month"] == previous_month
    ]

    if current_data.empty or previous_data.empty:
        return pd.DataFrame()

    current = (
        current_data.groupby(dimension)["revenue"]
        .sum()
        .rename("current_revenue")
    )

    previous = (
        previous_data.groupby(dimension)["revenue"]
        .sum()
        .rename("previous_revenue")
    )

    drivers = pd.concat(
        [current, previous],
        axis=1
    ).fillna(0).reset_index()

    drivers["revenue_change"] = (
        drivers["current_revenue"]
        - drivers["previous_revenue"]
    )

    drivers["absolute_change"] = (
        drivers["revenue_change"].abs()
    )

    return drivers.sort_values(
        "absolute_change",
        ascending=False
    ).reset_index(drop=True)


# ==========================================
# SUPPORTING FINANCIAL EVIDENCE
# ==========================================

def get_source_evidence(
    df,
    dimension=None,
    value=None,
    month=None
):

    evidence = df.copy()

    if dimension is not None:

        if dimension not in evidence.columns:
            raise ValueError("Unknown financial dimension.")

        evidence = evidence[
            evidence[dimension] == value
        ]

    if month is not None:

        selected_month = pd.Period(
            month, freq="M"
        )

        evidence = evidence[
            evidence["date"].dt.to_period("M")
            == selected_month
        ]

    return evidence


# ==========================================
# COMPLETE FINANCIAL ANALYSIS
# ==========================================

def analyze_financial_data(df):

    if df.empty:
        raise ValueError("Financial dataset is empty.")

    return {
        "metrics": calculate_metrics(df),

        "monthly_performance":
            calculate_monthly_performance(df),

        "product_performance":
            calculate_breakdown(df, "product"),

        "country_performance":
            calculate_breakdown(df, "country"),

        "segment_performance":
            calculate_breakdown(df, "segment"),

        "anomalies": detect_anomalies(df)
    }
