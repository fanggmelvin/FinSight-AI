"""Local request policy and bounded, session-owned validated response reuse."""
import re
import copy
import time

METRICS = [
    (r'\b(?:net income|net profit)\b', 'Net income requires operating expenses, interest, taxes and other income or expenses.'),
    (r'\bebitda\b', 'EBITDA requires operating profit and depreciation and amortization information.'),
    (r'\b(?:roic|return on invested capital)\b', 'ROIC requires net operating profit after tax (NOPAT) and invested capital.'),
    (r'\b(?:free cash flow|fcf)\b', 'Free cash flow requires operating cash flow and capital expenditures.'),
    (r'\bcash flow\b', 'Cash flow requires cash flow statement or cash transaction data.'),
    (r'\b(?:earnings per share|eps)\b', 'Earnings per share requires earnings attributable to common shareholders and weighted-average shares.'),
    (r'\bmarket share\b', 'External market share requires comparable total market revenue; competitor comparisons also require competitor revenue. Internal revenue share is not market share.'),
]

def missing_metrics(question):
    q=question.lower()
    messages=[message for pattern,message in METRICS if re.search(pattern,q)]
    if not messages:return None
    return 'This dataset does not establish the requested metric; gross profit is not net income. ' + ' '.join(messages)

def strategic(question):
    from finsight.answer_reliability import recommendation_count
    return recommendation_count(question) is not None or bool(re.search(r'\b(?:should|recommend\w*|prioriti\w*|strategy|strategic|cfo|why|how can|how should|interpret\w*|explain|dependence|diversif\w*)\b',question,re.I))

def allow_ai(question, route):
    return bool(question.strip()) and route.get("mode") != "clarify"

def cached_analysis(state, key, enabled, run):
    # State belongs to a single Streamlit session; never shared or persisted.
    if not enabled:return run(False)
    cache=state.setdefault('validated_ai_cache',{})
    now=time.monotonic()
    if key in cache and now-cache[key][0]<900:
        result=copy.deepcopy(cache[key][1]); result['cache_hit']=True
        return result
    attempts=state.setdefault('ai_attempt_times',[])
    attempts[:]=[t for t in attempts if now-t<60]
    if len(attempts)>=3:
        result=run(False); result['session_limited']=True; return result
    attempts.append(now)
    result=run(True)
    check=result.get('numerical_verification',{})
    commentary=result.get('scenario_commentary',{})
    interpretation = result.get("interpretation")
    valid=(check.get('generated_synthesis') and not check.get('commentary_diagnostic') and result.get('verification',{}).get('passed')) or (commentary.get('status','').startswith('AI response accepted;') and not commentary.get('diagnostic')) or bool(interpretation and interpretation.text)
    if valid:
        if len(cache)>=32:cache.pop(next(iter(cache)))
        cache[key]=(now,copy.deepcopy(result))
    return result


def closure_decision(question, df):
    from finsight.reliability import scope_data
    df=scope_data(question,df)
    if 'segment' not in df:return 'Segment data is unavailable.'
    names=[name for name in df.segment.dropna().astype(str).unique() if re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',question,re.I)]
    if len(names)!=1:return 'Specify one segment to evaluate.'
    name=names[0]
    part=df[df.segment.astype(str)==name]
    if part[['revenue','cogs']].isna().any().any():return 'Complete revenue and COGS data are required.'
    revenue=float(part.revenue.sum()); profit=revenue-float(part.cogs.sum())
    margin=f'{profit/revenue:.2%}' if revenue else 'undefined'
    return (f'**Do not decide to discontinue {name} based solely on historical gross margin.**\n\n'
            f'Calculated gross profit: {profit:,.2f}; gross margin: {margin}.\n\n'
            'Compare avoidable and stranded costs, contractual obligations, exit costs, customer dependencies and restructuring alternatives. '
            'Removing all recorded COGS is a hypothetical assumption, not proof of savings. Additional operational and financial data are required.')


def named_analysis(question, df):
    """Conservative local routes using names in the selected reporting scope."""
    from finsight.reliability import scope_data
    q = question.lower()
    share = bool(re.search(r'percentage of (?:our |total )?revenue|revenue share|share of (?:our |total )?revenue|proportion of (?:our |total )?revenue', q))
    focus = bool(re.search(r'\b(?:improve|increase|restore)\b.*\b(?:profitability|gross margin|gross profit)\b', q))
    if not (share or focus): return None
    scoped = scope_data(question, df)
    matches = {}
    for dim in ('segment', 'product', 'country'):
        if dim in scoped:
            names = [n for n in scoped[dim].dropna().astype(str).unique() if re.search(r'(?<!\w)'+re.escape(n)+r'(?!\w)', question, re.I)]
            if names: matches[dim] = names
    if not matches: return None
    if len(matches) != 1: return 'Specify named groups from a single business dimension; overlapping dimensions cannot be added.'
    dim, names = next(iter(matches.items()))
    selected = scoped[scoped[dim].astype(str).isin(names)]
    if share:
        if scoped.revenue.isna().any() or scoped.revenue.sum() <= 0: return 'Revenue share requires complete data and positive total revenue.'
        total = scoped.revenue.sum()
        return '**' + ' and '.join(names) + f' account for {selected.revenue.sum()/total:.2%} of selected revenue.**\n\n' + '\n'.join(f'- {n}: {selected.loc[selected[dim].astype(str)==n,"revenue"].sum()/total:.2%}' for n in names) + f'\n\nCombined revenue: {selected.revenue.sum():,.2f}; total revenue: {total:,.2f}. Calculated from selected records.'
    if len(names)!=1: return None
    if selected[['revenue','cogs']].isna().any().any(): return 'Complete revenue and COGS data are required.'
    rev=selected.revenue.sum(); gp=rev-selected.cogs.sum(); margin=f'{gp/rev:.2%}' if rev else 'undefined'
    return f'**{names[0]} profitability review**\n\nGross profit: {gp:,.2f}; gross margin: {margin}.\n\n- Review realized prices and discounts for this group.\n- Reconcile unit costs and product mix to identify loss-making transactions.\n- Test pricing and cost changes against demand, capacity and avoidable costs before implementation.\n\nGross profit does not establish net profitability; additional expense data are needed.'
