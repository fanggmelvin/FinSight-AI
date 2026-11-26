"""Compare dated actual and plan rows only where both sheets have a saved value."""
import calendar
from datetime import date
import re

from openpyxl.utils import get_column_letter

from finsight.table_chat import contains, period_filters, words
from finsight.workbook_chat import Reply


MEASURES = {
    "gross margin": {"gross margin", "gross margin percent", "gross margin percentage"},
    "gross profit": {"gross profit"},
    "COGS": {"cogs", "cost of sales", "cost of goods sold"},
    "revenue": {"revenue", "net revenue", "sales", "net sales"},
}


def month_values(ws, aliases):
    headers = {}
    result = None
    for row_number, row in enumerate(ws.values, 1):
        periods = {i:(v.year,v.month) for i,v in enumerate(row) if isinstance(v,date)}
        if periods:
            headers = periods
            continue
        if not headers:
            continue
        labels = [re.sub(r"\b(actuals?|budget(?:ed)?|forecasts?|planned)\b","",words(v)).strip()
                  for v in row if isinstance(v,str)]
        if not any(label in aliases for label in labels):
            continue
        if result is not None or len(set(headers.values())) != len(headers):
            return None
        result = {period:(row[i], f"{ws.title}!{get_column_letter(i+1)}{row_number}")
                  for i,period in headers.items() if i < len(row) and type(row[i]) in (int,float)}
    return result


def role_values(wb, role, metric):
    names = [s for s in wb.sheetnames if re.search(r"\b" + role + r"(?:s|ed)?\b", words(s))]
    return month_values(wb[names[0]], MEASURES[metric]) if len(names) == 1 else None


def workbook_suggestions(data, sheet, annual):
    if annual is not None and not annual.empty:
        rows = annual.sort_values("Fiscal year").groupby("Period type").head(1)
        return [f"What was revenue in FY{year}?" for year in rows["Fiscal year"]]
    from io import BytesIO
    from openpyxl import load_workbook

    wb = load_workbook(BytesIO(data), read_only=True, data_only=True)
    try:
        actual = role_values(wb, "actual", "revenue") or {}
        budget = role_values(wb, "budget", "revenue") or {}
        common = sorted(set(actual) & set(budget))
        if common:
            year, month = common[-1]
            return [f"Compare actual and budget revenue in {calendar.month_name[month]} {year}."]
        revenue = month_values(wb[sheet], MEASURES["revenue"])
        if revenue:
            year, month = max(revenue)
            return [f"What was revenue in {calendar.month_name[month]} {year}?"]
        return ["Which worksheets are available?"] if len(wb.sheetnames) > 1 else []
    finally:
        wb.close()


def source_address(cell):
    return tuple(cell.rsplit("!", 1))


def monthly_reply(ws, question, prior):
    prompt = words(question)
    years, months = period_filters(prompt)
    followup = prior and prior.sheet == ws.title and prior.filters.get("monthly") and re.search(
        r"\b(?:what about|how about|same|instead|and in)\b", prompt)
    if not (months or years) and not followup:
        return None
    metric = next((name for name, aliases in MEASURES.items()
                   if any(contains(prompt, alias) for alias in aliases)), None)
    if not metric and followup:
        metric = prior.label
    if not metric:
        return None
    values = month_values(ws, MEASURES[metric])
    if values is None:
        return None
    if followup and not contains(prompt, "all"):
        if not years:
            years = prior.filters["years"]
        if not months:
            months = prior.filters["months"]
    matches = [(period, values[period]) for period in sorted(values)
               if (not years or period[0] in years) and (not months or period[1] in months)]
    context = {"monthly": True, "years": years, "months": months}
    if not matches:
        return Reply(f"No saved monthly {metric} values match that period on {ws.title}.",
                     ws.title, label=metric, filters=context)

    def display(value):
        return f"{value:.2%}" if metric == "gross margin" else f"{value:,.2f}"

    lines = [f"{calendar.month_abbr[month]} {year} {metric}: {display(value)} ({cell})"
             for (year, month), (value, cell) in matches]
    if metric != "gross margin" and re.search(r"\b(total|sum|average|mean)\b", prompt):
        total = sum(value for _, (value, _) in matches)
        average = bool(re.search(r"\b(average|mean)\b", prompt))
        amount = total / len(matches) if average else total
        lines.insert(0, f"{'Average' if average else 'Total'} {metric}: {display(amount)} across {len(matches)} matched month(s).")
    return Reply("\n".join(lines), ws.title, label=metric, filters=context,
                 sources=tuple(source_address(cell) for _, (_, cell) in matches))


def compare_periods(wb, question, selected, prior):
    q = words(question)
    followup = prior and prior.filters.get("comparison") and re.search(r"what about|how about|^and\b|instead",q)
    roles = [role for role in ("actual","budget","forecast") if re.search(r"\b"+role+r"(?:s|ed)?\b",q)]
    if followup and len(roles)<2:
        roles=prior.filters["comparison"]
    if len(roles)!=2:
        return None
    metric = next((m for m,aliases in MEASURES.items() if any(" "+a+" " in " "+q+" " for a in aliases)),None)
    if not metric and followup:
        metric=prior.label
    if not metric:
        return Reply("Which measure should I compare: revenue, COGS, gross profit, or gross margin?",selected,
                     filters={"comparison":roles})
    series = [role_values(wb, role, metric) for role in roles]
    if any(item is None for item in series):
        return None
    years, months = period_filters(q)
    if followup and not contains(q, "all"):
        years = years or prior.filters.get("years", set())
        months = months or prior.filters.get("months", set())
    periods = sorted(set(series[0]) & set(series[1]))
    chosen = [p for p in periods if (not years or p[0] in years) and (not months or p[1] in months)]
    context = {"comparison":roles,"years":years,"months":months}
    if not chosen:
        return Reply(f"No matching months with a saved {metric} value on both worksheets.", selected, label=metric, filters=context)
    first,second=roles
    lines = []
    sources = []
    totals = [0,0]
    for year,month in chosen:
        (left,ls),(right,rs) = (s[(year,month)] for s in series)
        sources.extend((source_address(ls), source_address(rs)))
        totals[0]+=left
        totals[1]+=right
        delta = left-right
        if metric=="gross margin":
            detail=f"{left:.2%} vs {right:.2%}; difference {100*delta:+.2f} percentage points"
        else:
            detail=f"{left:,.2f} vs {right:,.2f}; difference {delta:+,.2f}"
        lines.append(f"{calendar.month_abbr[month]} {year}: {detail} ({ls}, {rs})")
    lead = f"{metric.capitalize()}, {first} versus {second} across {len(chosen)} matched month(s)."
    if metric!="gross margin":
        a,b=totals
        lead += f" {first.capitalize()} {a:,.2f}; {second} {b:,.2f}; {first} minus {second} {a-b:+,.2f}."
        if b>0:
            lead += f" Difference as a share of {second}: {(a-b)/b:+.2%}."
    if metric == "revenue" and roles == ["actual", "budget"] and len(chosen) > 1:
        actual, budget = series
        year, month = min(chosen, key=lambda period: actual[period][0] - budget[period][0])
        shortfall = budget[(year, month)][0] - actual[(year, month)][0]
        if shortfall > 0:
            lead += f" The largest shortfall was in {calendar.month_name[month]} {year}, at {shortfall:,.2f} below budget."
    return Reply("\n".join([lead,*lines]), selected, label=metric, filters=context, sources=tuple(sources))
