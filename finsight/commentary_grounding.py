"""Conservative ranking commentary: facts rendered locally, AI proposes tests."""
import math
import re


def ranking_rows(records, route):
    if (route or {}).get('mode') != 'ranking':
        return []
    metric = route['metric']
    rows = [r for r in records if r['category'] == route['dimension'].title() + ' Performance'
            and isinstance(r['values'].get(metric), (int, float)) and math.isfinite(r['values'][metric])]
    return sorted(rows, key=lambda r: r['values'][metric], reverse=not route.get('ascending', False))


def terminology_diagnostic(text):
    # Conservative for the current dataset: external market and net income data are absent.
    if re.search(r'\b(?:market share|competitors?)\b', text, re.I):
        return 'External market share is not established by internal revenue share'
    if re.search(r'\b(?:net profitability|net profit(?: margin)?|net income|operating margin|operating loss|operational loss|operating profit|EBITDA)\b', text, re.I):
        return 'Additional expense data required for this profitability metric'
    return None


def action_diagnostic(action, route=None):
    if (route or {}).get("metric") == "revenue" and re.search(r"\bcogs\b|cost of goods sold", action, re.I):
        return "COGS is not a direct revenue driver"
    reason = terminology_diagnostic(action)
    if reason:
        return reason
    if re.search(r'\b(?:guarantee\w*|risk[- ]free|without (?:increasing|adding) risk|will (?:increase|improve|reduce|ensure))\b', action, re.I):
        return 'Unsupported outcome in proposed action'
    if (route or {}).get('objective') != 'diversification' and re.search(r'\bdiversif\w*\b', action, re.I):
        return 'Diversification not requested'
    if re.search(r'\b(?:due to|because of|driven by|higher|lower|larger|smaller|above|below|outperform\w*)\b', action, re.I):
        return 'Comparative or causal language reserved for calculated findings'
    return None


def ranking_observation(rows, ids, metric):
    selected = [r for r in rows if r['evidence_id'] in ids]
    def fmt(r):
        v = r['values'][metric]
        return f'{v:.2%}' if metric in ('gross_margin','revenue_share') else f'{v:,.2f}'
    return '; '.join(f"{r['title'].split(':',1)[-1].strip()}: {metric.replace('_',' ')} {fmt(r)}" for r in selected) + '.'
