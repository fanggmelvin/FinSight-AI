"""Answer-first facts and explicitly labelled local action plans."""
import re
import math

def requested_count(question):
    q = question.lower()
    m = re.search(
        r'\b(\d+|one|two|three|four|five)\s+(?:(?:most important|most impactful|strategic|key|specific|concrete)\s+)*'
        r'(?:recommendations?|changes?|actions?|priorit(?:y|ies)|steps?|areas?\s+(?:for|of)\s+improvement)\b', q)
    if not m:
        if re.search(r'\b(?:pick|choose|target|focus on)\s+(?:just\s+)?(?:one|1)(?:\s+of\s+(?:these|those))?[?!.\s]*$', q):
            return 1
        return None
    return {'one':1,'two':2,'three':3,'four':4,'five':5}.get(m[1],int(m[1]) if m[1].isdigit() else 0)


def recommendation_count(question):
    count = requested_count(question)
    if count is not None:
        return count
    if re.search(r'\b(?:areas? (?:for|of) improvement|improvement priorities)\b', question, re.I):
        return 3
    return None

def direct_answer(records, route, question=""):
    if not route or route.get('mode')!='ranking':return ''
    metric=route['metric']; dim=route['dimension']
    rows=[r for r in records if r['category']==dim.title()+' Performance' and isinstance(r['values'].get(metric),(int,float)) and math.isfinite(r['values'][metric])]
    rows.sort(key=lambda r:r['values'][metric],reverse=not route.get('ascending',False))
    def name(r):return r['title'].split(':',1)[-1].strip()
    def fmt(k,v):return f'{v:.2%}' if k in ('gross_margin','revenue_share') else f'{v:,.2f}'
    def row(r):
        v=r['values']; return f"- **{name(r)}:** "+'; '.join(f"{k.replace('_',' ')} {fmt(k,v[k])}" for k in dict.fromkeys([metric,'gross_profit','gross_margin','revenue_share']) if isinstance(v.get(k),(int,float)) and math.isfinite(v[k]))+f" [{r['evidence_id']}]"
    if not rows:return 'No valid values for the requested metric.'
    if route.get('objective')=='diversification':
        shares=sorted([r for r in rows if isinstance(r['values'].get('revenue_share'),(int,float))],key=lambda r:r['values']['revenue_share'],reverse=True)
        dominant=shares[:2]; candidates=[r for r in shares[2:] if (r['values'].get('gross_profit') or 0)>0 and (r['values'].get('gross_margin') or 0)>0]
        candidates.sort(key=lambda r:r['values']['gross_margin'],reverse=True)
        lines=[]
        if dominant:lines.append('Leading groups account for '+f"{sum(r['values']['revenue_share'] for r in dominant):.2%}"+' of revenue: '+', '.join(name(r)+f" [{r['evidence_id']}]" for r in dominant)+'.')
        lines.append('Retain profitable dominant business without increasing relative dependence; test expansion of smaller profitable groups.')
        lines+= [row(r) for r in candidates] or ['No smaller profitable group identified in available evidence.']
        lines+=['Review losses before scaling: '+row(r)[2:] for r in rows if (r['values'].get('gross_profit') or 0)<0]
        return '\n\n'.join(lines)
    label=metric.replace('_',' '); direction='ascending' if route.get('ascending') else 'descending'
    distinction = ''
    if metric == 'gross_margin' and route.get('ambiguous_profitability'):
        profits = [r for r in rows if isinstance(r['values'].get('gross_profit'), (int,float)) and math.isfinite(r['values']['gross_profit'])]
        if profits:
            leader = max(profits,key=lambda r:r['values']['gross_profit'])
            distinction = f"\n\nGross profit leader: {name(leader)} ({leader['values']['gross_profit']:,.2f}) [{leader['evidence_id']}]. Gross margin and absolute gross profit measure different aspects of profitability."
    correction = ''
    if re.search(r'\b(?:prove|confirm|show)\s+that\b', question, re.I) and re.search(r'\b(?:most profitable|highest|lowest)\b', question, re.I):
        named = [r for r in rows if re.search(r'(?<!\w)' + re.escape(name(r)) + r'(?!\w)', question, re.I)]
        if len(named) == 1 and named[0]['values'][metric] != rows[0]['values'][metric]:
            r = named[0]
            correction = f'\n\nThe calculated {label} ranking does not support the premise about {name(r)}: {fmt(metric,r["values"][metric])} [{r["evidence_id"]}].'
    return f'**{dim.title()} ranking by {label} ({direction})**\n\n'+'\n'.join(row(r) for r in rows)+ ('\n\nHistorical gross profit is not a forecast of incremental returns; test demand, capacity and marginal costs before scaling.' if metric=='gross_profit' else '') + distinction + correction

def complete_plan(synthesis, findings, count):
    if count is None:return synthesis, None
    if not 1<=count<=5:return synthesis,'Requested count outside supported range (one to five).'
    # Use a coherent local plan rather than silently mixing duplicate AI and local actions.
    if len(synthesis.split('\n\n'))==count and synthesis:return synthesis,None
    lines=[]
    for t in findings[:count]:
        lines.append(f"- **{t['title']} (local):** {t['facts'][0]} **Proposed action:** {t['actions'][0]}")
    return '\n\n'.join(lines), 'AI count incomplete; local plan used.' if len(lines)==count else 'Insufficient distinct findings for requested count; local plan used.'
