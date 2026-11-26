"""Explicit reporting scope and deterministic management fallback."""
import re


def scope_data(question, df, route=None):
    route = route or {}
    if route.get('mode') in ('revenue_investigation','multi_investigation'):
        return df
    years = set(re.findall(r'\b(?:FY\s*)?((?:19|20)\d{2})\b', question, re.I))
    if len(years) > 1:
        raise ValueError('Multiple reporting years require an explicit comparison workflow.')
    if years:
        year = int(next(iter(years)))
        df = df.loc[df['date'].dt.year == year].copy()
    from finsight.question_router import MONTHS, MONTH_PATTERN
    named = re.findall(rf'\b(?:in|for|during|of)\s+({MONTH_PATTERN})\b|\b({MONTH_PATTERN})\s+(?:19|20)\d{{2}}\b', question, re.I)
    month_numbers = {next(i for i, month in enumerate(MONTHS, 1) if month.startswith((a or b).lower())) for a, b in named}
    quarters = {int(q) for q in re.findall(r"\bQ([1-4])\b", question, re.I)}
    if len(month_numbers) > 1 or len(quarters) > 1 or (month_numbers and quarters):
        raise ValueError('Specify a single reporting month or quarter, or ask for an explicit period comparison.')
    if quarters:
        df = df.loc[df['date'].dt.quarter.isin(quarters)].copy()
        if df['date'].dt.year.nunique() > 1:
            raise ValueError('Specify the year for that quarter.')
    if len(month_numbers) == 1:
        df = df.loc[df['date'].dt.month.isin(month_numbers)].copy()
        if df['date'].dt.year.nunique() > 1:
            raise ValueError('Specify the year for that month.')
    if df.empty:
        raise ValueError('Requested reporting period has no selected data.')
    return df


def period_label(df):
    months = sorted(df['date'].dt.to_period('M').dropna().astype(str).unique())
    return ', '.join(months) if months else 'No dated records'


def fallback_commentary(records):
    from finsight.deterministic_report import deterministic_insights
    from finsight.skill_workflow import anomaly_rows
    flags = anomaly_rows(records)
    if flags:
        return '\n\n'.join(f"- **{r['Severity']} flag:** {r['Period']} — {r['Anomaly']}. Proposed review: investigate the relevant sales, pricing and cost drivers. [{r['Evidence']}]" for r in flags)
    return deterministic_insights(records) or 'Review the calculated evidence and investigate material changes before making decisions.'
