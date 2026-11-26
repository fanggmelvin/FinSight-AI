"""Deterministic routing for monthly revenue investigations."""
import re
from datetime import date

MONTHS = 'january february march april may june july august september october november december'.split()
MONTH_PATTERN = '|'.join(MONTHS + [m[:3] for m in MONTHS])

def route_question(question, available_months):
    q = question.lower().strip()
    available = {str(m)[:7] for m in available_months}
    dimensions = [d for d, pattern in [('product', r'\bproducts?\b'), ('country', r'\b(countries|country|geographic)\b'), ('segment', r'\bsegments?\b')] if re.search(pattern,q)]
    investigation = bool(re.search(r'\b(declin\w*|drop\w*|fell|fall|increas\w*|growth|chang\w*|compar\w*|drivers?|drove|contributors?|attribution)\b',q) and re.search(r'\b(revenue|sales)\b',q))
    years_requested = set(re.findall(r'\b(?:fy\s*)?((?:19|20)\d{2})\b', q))
    if years_requested - {m[:4] for m in available}:
        return {'mode':'clarify','reason':'Requested year is not available in selected data.'}
    from finsight.request_policy import missing_metrics
    missing = missing_metrics(q)
    if missing:
        return {'mode':'clarify','reason':missing}
    if not investigation and len(years_requested)>1:
        return {'mode':'clarify','reason':'Specify a single reporting year; annual comparisons are not supported.'}
    if not investigation and len(dimensions)==1:
        rank_clause = re.split(r'[,;]|\band\b', q, maxsplit=1)[0]
        metric = 'revenue_share' if re.search(r'concentrat|revenue share',rank_clause) else 'gross_margin' if re.search(r'profitab|gross margin',rank_clause) else 'revenue_share' if re.search(r'concentrat|revenue share',q) else 'gross_margin' if re.search(r'profitab|gross margin',q) else None
        if re.search(r'\bgross profits?\b', q) and not re.search(r'concentrat|revenue share', rank_clause):
            metric = 'gross_profit'
        if not metric and re.search(r'\b(revenue|sales)\b', q):
            metric = 'revenue'
        if metric:
            return {'mode':'ranking','dimension':dimensions[0],'metric':metric,'ambiguous_profitability':bool(re.search(r'profitab',q) and not re.search(r'gross margin|gross profit',q)),'ascending':bool(re.search(r'\b(lowest|weakest|smallest|least|worst|minimum)\b', q)),'objective':'diversification' if re.search(r'diversif|concentrat|dependence',q) else 'profitability' if metric in ('gross_profit','gross_margin') else 'revenue','reason':'Deterministic ranking by requested metric.'}
    if not investigation:
        return {'mode':'summary','reason':'No explicit revenue change investigation detected.'}
    def clarify(reason):
        return {'mode':'clarify','reason':reason}
    if re.search(r'\b(year.over.year|yoy|quarter\w*|annual|yearly)\b',q):
        return clarify('This router currently supports monthly comparisons only.')
    pattern = rf'\b({MONTH_PATTERN})\b\s*(?:,\s*)?(\d{{4}})?|\b(\d{{4}})-(0[1-9]|1[0-2])\b'
    matches = list(re.finditer(pattern,q))
    years = set(re.findall(r'\b(?:19|20)\d{2}\b',q))
    periods=[]
    for match in matches:
        name,year,iso_year,iso_month=match.groups()
        if iso_year:
            year,month=iso_year,int(iso_month)
        else:
            month=next(i+1 for i,m in enumerate(MONTHS) if m.startswith(name))
            if not year:
                if len(years)==1: year=next(iter(years))
                elif not years:
                    candidates=[p for p in available if p.endswith(f'-{month:02d}')]
                    if len(candidates)==1: year=candidates[0][:4]
                if not year: return clarify('Specify the year for each month.')
        periods.append(f'{year}-{month:02d}')
    periods=sorted(set(periods))
    if not periods or len(periods)>2:
        return clarify('Specify one target month or two comparison months.')
    current=periods[-1]
    if len(periods)==2: previous=periods[0]
    else:
        y,m=map(int,current.split('-'))
        previous=f'{y if m>1 else y-1:04d}-{m-1 if m>1 else 12:02d}'
    if previous not in available or current not in available:
        return clarify('Both comparison months must exist in the selected data.')
    return {'mode':'multi_investigation' if len(dimensions)>1 else 'revenue_investigation','dimension':'all' if len(dimensions)>1 else dimensions[0] if dimensions else 'product','direction':'growth' if re.search(r'\b(increas\w*|growth|grew|rose)\b',q) and not re.search(r'\b(declin\w*|drop\w*|fell|fall)\b',q) else 'decline','previous_month':previous,'current_month':current,'reason':'Monthly revenue comparison; product is the default dimension.' if not dimensions else 'Monthly revenue comparison using requested dimension.'}
