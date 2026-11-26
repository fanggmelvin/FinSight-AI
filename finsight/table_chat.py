"""Aggregate a rectangular Excel table using its own headers and category values."""
import calendar
from datetime import date
import re
from collections import defaultdict
from statistics import mean

from openpyxl.utils import get_column_letter


def words(value):
    return " ".join(re.findall(r"\w+", str(value).casefold().replace("_"," ")))


def contains(text, phrase):
    return bool(phrase) and " " + phrase + " " in " " + text + " "


def period_filters(query):
    years = {int(year) for year in re.findall(r"\b(?:fy\s*)?((?:19|20)\d{2})\b", query)}
    months = {i for i in range(1, 13)
              if contains(query, calendar.month_name[i].lower())
              or contains(query, calendar.month_abbr[i].lower())}
    for quarter in re.findall(r"\bq\s*([1-4])\b", query):
        end = 3 * int(quarter)
        months.update(range(end - 2, end + 1))
    return years, months


def table_answer(ws, question, prior=None):
    query = words(question)
    rows = enumerate(ws.values, 1)
    for row_no, row in rows:
        if row_no > 30:
            return None
        headers = [(i,v.strip()) for i,v in enumerate(row) if isinstance(v,str) and v.strip()]
        if len(headers)>=2 and len(headers)==sum(v is not None for v in row) and len({words(v) for _,v in headers})==len(headers):
            break
    else:
        return None
    entries = [(n,row) for n,row in rows if any(v is not None for v in row)]
    if not entries:
        return None
    numeric, categories, dates = {}, {}, {}
    for i,name in headers:
        vals = [row[i] for _,row in entries if i<len(row) and row[i] is not None]
        if not vals:
            continue
        if all(type(v) in (float,int) for v in vals):
            numeric[name]=i
        elif all(isinstance(v,date) for v in vals):
            dates[name]=i
        elif all(isinstance(v,str) for v in vals):
            categories[name]=(i,set(vals))
    alias = {"sales": ("revenue","net revenue"), "net sales": ("revenue",),
             "cogs": ("cost of goods sold","cost of sales"), "units sold": ("units",)}
    metrics = [name for name in numeric if contains(query,words(name))]
    metrics = [m for m in metrics if not any(words(m) in words(other) for other in metrics if len(other)>len(m))]
    if not metrics:
        metrics = [name for name in numeric if any(contains(query,a) for a in alias.get(words(name),()))]
    followup = prior and re.search(r"what about|how about|instead|^and\b|same|those|them",query)
    if not metrics and followup and prior.label in numeric:
        metrics=[prior.label]
    count_rows = bool(re.search(r"\b(how many|count|number of) (rows|records|transactions|entries)\b",query))
    group = next((name for name in categories if re.search(r"\b(by|per|each|which|what|top(?: \d+)?|bottom(?: \d+)?) "+re.escape(words(name).removesuffix("y")) + (r"(?:y|ies)" if words(name).endswith("y") else "s?") + r"\b",query)),None)
    filters = {}
    for name,(i,values) in categories.items():
        matches = {v for v in values if contains(query,words(v))}
        if matches:
            filters[i]=matches
    if not metrics and not count_rows and not filters:
        return None
    years, months = period_filters(query)
    explicit_year = bool(years)
    if followup and prior.filters:
        for name,(i,_) in categories.items():
            if i not in filters and name in prior.filters.get("categories",{}) and not re.search(r"\ball\b",query):
                filters[i] = prior.filters["categories"][name]
        if not years and "all" not in query.split():
            years = prior.filters.get("years",set())
        if not months and "all" not in query.split() and not explicit_year:
            months = prior.filters.get("months",set())
    if (years or months) and len(dates)!=1:
        return "I could not identify a single date column for that period.", ""
    if years:
        for name,(i,_) in categories.items():
            if words(name) in ("year","calendar year"):
                filters.pop(i,None)
    if re.search(r"\b(for|in|where|from)\b",query) and not (filters or years or months or group):
        return "Which category or date should I filter on? Use a value from the worksheet.", ""
    date_col = next(iter(dates.values()),None)
    groups = defaultdict(list)
    for n,row in entries:
        if any(row[i] not in values for i,values in filters.items()):
            continue
        if years or months:
            d = row[date_col]
            if not isinstance(d,date) or (years and d.year not in years) or (months and d.month not in months):
                continue
        groups[str(row[categories[group][0]]) if group else ""].append(row)
    if not groups:
        return "No worksheet rows matched the requested filters.", ""
    if not metrics and not count_rows:
        shown = [(i,name) for i,name in headers if contains(query,words(name))] or headers
        lines = []
        sources = []
        for n,row in entries:
            if any(row[i] not in vals for i,vals in filters.items()):
                continue
            if years or months:
                d=row[date_col]
                if not isinstance(d,date) or (years and d.year not in years) or (months and d.month not in months):
                    continue
            cells = [(name, f"{get_column_letter(i+1)}{n}", row[i]) for i,name in shown if row[i] is not None]
            if len(lines) < 20:
                sources.extend((ws.title, cell) for _, cell, _ in cells)
            lines.append("; ".join(f"{name}: {value} ({ws.title}!{cell})" for name, cell, value in cells))
        return "\n".join(lines[:20] + ([f"Showing 20 of {len(lines)} matches."] if len(lines)>20 else [])), "", {}, tuple(sources)
    fn = sum
    for pattern,op in ((r"\b(average|mean)\b",mean),(r"\b(highest|largest|maximum|max)\b",max),(r"\b(lowest|smallest|minimum|min)\b",min)):
        if re.search(pattern,query):
            fn=op
            break
    grouped = sorted(groups.items())
    rank = re.search(r"\b(top|bottom|highest|lowest|largest|smallest|most|least)\b(?: (\d+))?",query)
    if group and rank and len(metrics)==1:
        i=numeric[metrics[0]]
        totals = {k:sum(row[i] for row in records if type(row[i]) in (int,float)) for k,records in groups.items()}
        descending = rank[1] in ("top","highest","largest","most")
        grouped = sorted(grouped,key=lambda pair:totals[pair[0]],reverse=descending)[:int(rank[2] or 1)]
        fn=sum
    lines=[]
    sources = []
    for key,records in grouped:
        prefix = f"{key}: " if group else ""
        if count_rows:
            lines.append(f"{prefix}{len(records):,} matching rows.")
        for name in metrics:
            i=numeric[name]
            vals=[r[i] for r in records if type(r[i]) in (int,float)]
            if not vals:
                continue
            op = fn
            if fn is sum and not contains(query,"sum") and re.search(r"price|rate|margin|percent",name,re.I):
                op=mean
            col=get_column_letter(i+1)
            address = f"{col}{row_no+1}:{col}{entries[-1][0]}"
            if len(lines) < 50:
                sources.append((ws.title, address))
            lines.append(f"{prefix}{name} ({op.__name__}): {op(vals):,.12g} · {len(vals):,} numeric values · {ws.title}!{address}")
    constraints = [f"{name} = {', '.join(sorted(filters[i]))}" for name,(i,_) in categories.items() if i in filters]
    constraints += [str(y) for y in sorted(years)] + [calendar.month_name[m] for m in sorted(months)]
    scope = "Filters: " + ", ".join(constraints) if constraints else "All worksheet records"
    context = {"categories": {n:filters[i] for n,(i,_) in categories.items() if i in filters},
               "years": years, "months": months}
    return "\n".join([scope,*lines[:50]] + ([f"Showing 50 of {len(lines)} results."] if len(lines)>50 else [])), metrics[0] if len(metrics)==1 else "", context, tuple(sources)
