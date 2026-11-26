"""Build a dated, reproducible growth outlook from eligible financial data."""
import re
from math import isfinite

import pandas as pd


def is_outlook(question, *, workbook=False):
    q = question.casefold()
    if re.search(r"\b(?:actuals?\s+(?:vs\.?|versus|and)\s+forecast|forecast\s+(?:vs\.?|versus|and)\s+actuals?)\b", q):
        return False
    projections = r"\bpredict\b|\bproject\s+(?:next|revenue|sales|gross profit|growth)\b"
    next_year = r"\bnext (?:fiscal )?year(?:s\b|'s\b|\b)"
    metrics = r"\b(?:forecast|growth|revenue|sales|profit|numbers)\b"
    return bool(((re.search(projections, q) or re.search(next_year, q)) and re.search(metrics, q)) or
                (not workbook and re.search(r"\bforecast\b", q)))


def _outlook_text(periods, question, *, currency="", fiscal=False):
    periods = periods.sort_index()
    latest = int(periods.index.max())
    years = {int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", question)}
    future = years - set(periods.index)
    target = min(future) if future else latest + 1
    if len(future) > 1 or (years and not future) or target != latest + 1:
        raise ValueError(f"The available baseline supports a one-year outlook for {latest + 1}.")
    if re.search(r"\b(?:quarter|monthly|next month|q[1-4])\b", question, re.I):
        raise ValueError("A subannual forecast needs a separate period model. Ask for a full-year outlook.")

    baseline = periods.loc[latest]
    revenue, cogs = float(baseline["revenue"]), float(baseline["cogs"])
    if not isfinite(revenue) or not isfinite(cogs) or revenue <= 0:
        raise ValueError("A growth-rate outlook requires finite baseline costs and positive revenue.")
    margin = 1 - cogs / revenue
    prefix = "FY" if fiscal else ""
    assumption = re.search(
        r"\b(?:at|assum(?:e|ing))\s+([+-]?\d+(?:\.\d+)?)\s*%(?:\s*(?:revenue\s+)?(growth|increase|decline|decrease)\b)?",
        question, re.I,
    )
    if assumption:
        growth = float(assumption[1]) / 100
        if assumption[2] and assumption[2].lower() in ("decline", "decrease"):
            growth = -abs(growth)
        if not isfinite(growth) or growth < -1:
            raise ValueError("Enter a finite revenue growth rate. A decline cannot exceed 100%.")
        cases = (("User assumption", growth),)
        basis = "Revenue growth uses the rate you supplied."
    elif latest - 1 in periods.index and periods.loc[latest - 1, "revenue"] > 0:
        previous = float(periods.loc[latest - 1, "revenue"])
        rate = revenue / previous - 1
        cases = (("Run-rate projection", rate),)
        basis = f"Applies the observed {prefix}{latest - 1} to {prefix}{latest} revenue growth rate for one more year."
    else:
        cases = (("Downside", -0.05), ("Flat baseline", 0.0), ("Upside", 0.05))
        basis = "Only one comparable year is available, so these are illustrative sensitivity cases. The growth rates are assumptions."

    def amount(value):
        return f"{currency}{value:,.2f}"

    lines = [f"**{prefix}{target} revenue and gross-profit outlook**",
             f"Baseline {prefix}{latest}: revenue {amount(revenue)}, gross profit {amount(revenue - cogs)}, gross margin {margin:.2%}.",
             basis + " Gross margin is held at the baseline rate."]
    for label, rate in cases:
        projected = revenue * (1 + rate)
        if not isfinite(projected) or not isfinite(projected * margin):
            raise ValueError("The calculated outlook exceeds the supported financial range.")
        lines.append(f"- **{label} ({rate:+.2%}):** Revenue {amount(projected)} · Gross profit {amount(projected * margin)}")
    return "\n\n".join(lines)


def monthly_outlook(frame, question):
    dates = frame["date"].dt
    months_per_year = frame.groupby(dates.year)["date"].agg(lambda values: values.dt.month.nunique())
    if months_per_year.empty or months_per_year.iloc[-1] != 12:
        raise ValueError("A full-year outlook needs all twelve months in the latest selected year.")
    complete = months_per_year[months_per_year.eq(12)].index
    totals = frame.groupby(dates.year)[["revenue", "cogs"]].sum(min_count=1)
    return _outlook_text(totals.loc[complete], question)


def annual_outlook(frame, question):
    actuals = frame.loc[frame["Period type"].eq("Actual")].set_index("Fiscal year")
    if actuals.empty:
        raise ValueError("Identify the last actual fiscal year under Change dataset to project growth from actuals.")
    currency = "$" if actuals["Currency"].eq("USD").all() else ""
    return _outlook_text(actuals.rename(columns={"Revenue": "revenue", "COGS": "cogs"}), question,
                         currency=currency, fiscal=True)
