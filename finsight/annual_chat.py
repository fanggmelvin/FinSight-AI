"""Answer questions from confirmed annual periods in normalized source units."""
import re
from decimal import Decimal, ROUND_HALF_UP, localcontext

import pandas as pd
from openpyxl.utils import get_column_letter

from finsight.workbook_chat import LookupDetails, Reply, cell_references
from finsight.statement_normalization import SOURCE_UNITS
from finsight.table_chat import period_filters, words


METRIC_NAMES = {
    "Gross margin": r"gross margin|profit margin|\bmargin\b",
    "Gross profit": r"gross profit",
    "COGS": r"\bcogs\b|cost of (goods sold|sales)",
    "Revenue": r"\brevenue\b|\bsales\b",
}


def sheet_coordinates(address):
    coordinates = re.fullmatch(r"row (\d+), column (\d+)", str(address))
    if coordinates:
        row, column = map(int, coordinates.groups())
        return get_column_letter(column), row
    return None


def plain_number(value):
    number = f"{Decimal(str(value)):,f}"
    return number.rstrip("0").rstrip(".") if "." in number else number


def headline_amount(value, usd):
    if not usd:
        return plain_number(value) + " in source units"
    exact = Decimal(str(value))
    for scale, name in ((10**12, "trillion"), (10**9, "billion"), (10**6, "million"), (10**3, "thousand")):
        if abs(exact) >= scale:
            scaled = exact / scale
            with localcontext() as context:
                context.prec = max(context.prec, scaled.adjusted() + 5)
                rounded = scaled.quantize(Decimal(".001"), rounding=ROUND_HALF_UP)
            qualifier = "about " if rounded != scaled else ""
            return f"{qualifier}${plain_number(rounded)} {name}"
    return f"${plain_number(exact)}"


def annual_lookup(ordered, row, metric, sheet, usd):
    coordinates = sheet_coordinates(row.get(f"{metric} cell"))
    if not coordinates or pd.isna(row[metric]):
        return None
    column, row_number = coordinates
    cell = f"{column}{row_number}"
    year = int(row["Fiscal year"])
    classification = row["Period type"]
    period = f"FY{year}" + (f" ({classification.lower()})" if classification != "Unclassified" else "")
    note = f"The workbook doesn’t identify FY{year} as an actual or a forecast." if classification == "Unclassified" else ""
    label = row.get(f"{metric} label", metric)
    units = row.get("Source units", SOURCE_UNITS)
    unit_text = f" in {units}" if units != SOURCE_UNITS else " (units unspecified)"
    source_value = f"{sheet}!{cell} · Source value {plain_number(row.get(f'Source {metric}', row[metric]))}{unit_text}"
    available = set(ordered.loc[ordered[metric].notna() & ordered[f"{metric} cell"].notna(), "Fiscal year"])
    peer = next((candidate for candidate in (year + 1, year - 1) if candidate in available), None)
    question = f"Compare {metric.lower()} in FY{year} and FY{peer}." if peer is not None else ""
    header = row.get("Fiscal year row")
    lookup = LookupDetails(source_value, note, f"A{row_number}",
                           f"{column}{int(header)}" if pd.notna(header) else "", peer, question)
    return Reply(f"{label} for {period} was {headline_amount(row[metric], usd)}.",
                 sheet, label=metric, sources=((sheet, cell),), lookup=lookup)


def annual_reply(frame, sheet, question, prior=None):
    q = question.lower()
    if cell_references(question) or re.search(r"\b(cell|range|formula|sheets|worksheets|tabs)\b", q):
        return None
    metrics = [metric for metric, pattern in METRIC_NAMES.items() if re.search(pattern, q)]
    if "COGS" in metrics and "cost of sales" in q and "revenue" not in q:
        metrics = [m for m in metrics if m != "Revenue"]
    if not metrics and prior and prior.label in METRIC_NAMES and re.search(r"what about|how about|and (in |for )?(fy)?\d|instead", q):
        metrics = [prior.label]
    if not metrics and re.search(r"summary|summarize|overview|performance", q):
        metrics = list(reversed(METRIC_NAMES))
    if not metrics:
        return None
    if period_filters(words(question))[1]:
        return Reply(f"{sheet} reports annual figures. Ask for a fiscal year or select a worksheet with monthly data.", sheet)
    requested = sorted({int(y) for y in re.findall(r"\b(?:fy\s*)?((?:19|20)\d{2})\b", q)})
    ordered = frame.sort_values("Fiscal year")
    unclassified = ordered["Period type"].eq("Unclassified").all()
    if unclassified and re.search(r"\b(?:actuals?|forecast(?:s|ed)?)\b", q):
        return Reply("This workbook does not label its fiscal years as actuals or forecasts.", sheet)
    periods = ordered if requested or unclassified else ordered.loc[ordered["Period type"].eq("Forecast" if "forecast" in q else "Actual")]
    usd = ordered["Currency"].eq("USD").all()
    if requested:
        periods = periods[periods["Fiscal year"].isin(requested)]
        missing = set(requested) - set(periods["Fiscal year"])
        if missing:
            return Reply("No complete financial statement for FY " + ", ".join(map(str, sorted(missing))) + ".", sheet)
    if periods.empty:
        return Reply("There are no confirmed periods matching that question.", sheet)
    trend = re.search(r"chang|growth|grew|declin|compar|versus|\bvs\b|increase|decrease|trend", q)
    rank = re.search(r"highest|largest|peak|maximum|lowest|minimum|smallest", q)
    total = re.search(r"\b(sum|total|average|mean)\b", q)
    if trend and len(periods) == 1:
        year = int(periods.iloc[0]["Fiscal year"])
        previous = ordered[ordered["Fiscal year"].eq(year-1)]
        if previous.empty:
            return Reply(f"FY{year} has no consecutive prior year in the uploaded statement.", sheet, label=metrics[0])
        periods = pd.concat([previous, periods])
    elif not (requested or trend or rank or total or "each" in q or "all" in q):
        periods = periods.tail(1)
    if len(periods) == len(metrics) == 1 and metrics[0] in ("Revenue", "COGS") and not (trend or rank or total):
        lookup = annual_lookup(ordered, periods.iloc[0], metrics[0], sheet, usd)
        if lookup:
            return lookup
    def fmt(metric, number):
        if pd.isna(number):
            return "undefined"
        if metric == "Gross margin":
            return f"{number:.2%}"
        return f"${number:,.2f}" if usd else f"{number:,.2f} in source units"
    lines = []
    sources = []
    has_unclassified = False
    for metric in metrics:
        selected = periods
        if rank:
            values = selected[metric].dropna()
            if values.empty:
                lines.append(f"{metric} is undefined for these periods.")
                continue
            extreme = values.min() if rank[0] in ("lowest","minimum","smallest") else values.max()
            selected = selected[selected[metric].eq(extreme)]
        if total and len(selected)>1 and not trend and not rank:
            if "margin" in metric.lower():
                revenue = selected["Revenue"].sum()
                amount = selected["Gross profit"].sum()/revenue if revenue else float("nan")
                lines.append(f"Revenue-weighted gross margin: {fmt(metric,amount)}.")
            else:
                average = total[0] in ("average","mean")
                value = selected[metric].mean() if average else selected[metric].sum()
                lines.append(f"{'Average' if average else 'Total'} {metric.lower()}: {fmt(metric,value)}.")
        if trend and len(selected)>1:
            first,last = selected.iloc[0],selected.iloc[-1]
            delta = last[metric] - first[metric]
            if metric == "Gross margin":
                change = "undefined" if pd.isna(delta) else f"{100*delta:+.2f} percentage points"
            else:
                change = fmt(metric, delta)
                if first[metric] > 0:
                    change += f" ({delta/first[metric]:+.2%})"
            label = first.get(f"{metric} label", metric)
            lines.append(f"FY{first['Fiscal year']} to FY{last['Fiscal year']} {label.lower()} change: {change}.")
        for _, row in selected.iterrows():
            keys = [metric] if metric in ("Revenue","COGS") else ["Revenue","COGS"]
            evidence = []
            for address in (row[key + " cell"] for key in keys):
                coordinates = sheet_coordinates(address)
                if coordinates:
                    column, row_num = coordinates
                    cell = f"{column}{row_num}"
                    sources.append((sheet, cell))
                    evidence.append(f"{sheet}!{cell}")
            classification = row["Period type"]
            has_unclassified |= classification == "Unclassified"
            period = f"FY{row['Fiscal year']}" + (f" ({classification.lower()})" if classification != "Unclassified" else "")
            label = row.get(f"{metric} label", metric)
            lines.append(f"{period} {label}: {fmt(metric, row[metric])}" + (" · " + ", ".join(evidence) if evidence else ""))
    if has_unclassified:
        lines.append("The workbook doesn’t identify these fiscal years as actuals or forecasts.")
    return Reply("\n".join(lines), sheet, label=metrics[0] if len(metrics)==1 else "", sources=tuple(sources))
