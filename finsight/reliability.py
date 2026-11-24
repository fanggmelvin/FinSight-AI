"""Explicit reporting scope and deterministic management fallback."""
import re


def scope_data(question, df, route=None):
    route = route or {}
    if route.get('mode') in ('revenue_investigation','multi_investigation'):
        return df
    years = set(re.findall(r'\b(?:19|20)\d{2}\b', question))
    if len(years) > 1:
        raise ValueError('Multiple reporting years require an explicit comparison workflow.')
    if years:
        year = int(next(iter(years)))
        df = df.loc[df['date'].dt.year == year].copy()
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
