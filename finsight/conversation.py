"""Bounded session follow-ups; never reuse prior financial values or citations."""
import re

DIMENSIONS = {'product': 'products', 'country': 'countries', 'segment': 'segments'}
METRICS = {'gross_margin': 'gross margins', 'gross_profit': 'gross profit', 'revenue': 'revenue', 'revenue_share': 'revenue share'}


def resolve_followup(question, previous=None):
    """Return (effective question, clarification). Explicit new topics take precedence."""
    q = question.strip()
    low = q.lower()
    if re.search(r'\b(products?|countries|country|segments?)\b', low):
        return q, None
    follow = bool(re.search(r'^(?:and\b|what about\b|how about\b|now\b|which one\b)|\b(their|those|them|same|it|that one|second one|first one)\b', low))
    if not follow:
        return q, None
    route = (previous or {}).get('route', {})
    dim = route.get('dimension')
    if route.get('mode') != 'ranking' or dim not in DIMENSIONS:
        return q, 'Which business dimension or previous finding do you mean?'
    if re.search(r'\b(first|second|third|top|bottom|that one|it|those|them|their|which one)\b', low):
        # A prior ranking can contain all groups; never silently infer a subset.
        if re.search(r'\b(first|second|third|top|bottom|that one|it|which one)\b', low):
            return q, 'Please name the group or groups you want to analyze; individual ranking references are not supported yet.'
    metric = ('gross_margin' if re.search(r'\bmargins?\b', low) else
              'gross_profit' if re.search(r'\bgross profits?\b', low) else
              'revenue_share' if re.search(r'\brevenue share\b', low) else
              'revenue' if re.search(r'\b(revenue|sales)\b', low) else None)
    if metric is None and re.search(r'\b(lowest|weakest|highest|strongest|largest|smallest|same)\b', low):
        metric = route.get('metric')
    if metric not in METRICS:
        return q, 'Please specify the financial metric for this follow-up.'
    direction = 'lowest' if re.search(r'\b(lowest|weakest|smallest|least|worst)\b', low) else 'highest' if re.search(r'\b(highest|strongest|largest|best)\b', low) else 'lowest' if route.get('ascending') else 'highest'
    years = re.findall(r'\b(?:19|20)\d{2}\b', q) or re.findall(r'\b(?:19|20)\d{2}\b', (previous or {}).get('effective_question', (previous or {}).get('question', '')))
    if re.search(r'\b(all years|all periods|entire period)\b', low):
        years = []
    if len(set(years)) > 1:
        return q, 'Please specify a single reporting year.'
    effective = f'Rank {DIMENSIONS[dim]} by {METRICS[metric]}, {direction} first.'
    if years:
        effective += f' Reporting year {years[0]}.'
    return effective, None
