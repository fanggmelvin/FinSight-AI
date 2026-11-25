"""Answer-first facts and explicitly labelled local action plans."""
import re
import math

def requested_count(question):
    m=re.search(r'\b(\d+|one|two|three|four|five)\s+(?:most important\s+|strategic\s+|key\s+)*(?:recommendations|changes|actions|priorities|steps)\b',question.lower())
    if not m:return None
    return {'one':1,'two':2,'three':3,'four':4,'five':5}.get(m[1],int(m[1]) if m[1].isdigit() else 0)

def direct_answer(records, route):
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
        lines=['Retain profitable dominant business without increasing relative dependence; test expansion of smaller profitable groups.']
        if dominant:lines.append('Leading groups account for '+f"{sum(r['values']['revenue_share'] for r in dominant):.2%}"+' of revenue: '+', '.join(name(r)+f" [{r['evidence_id']}]" for r in dominant)+'.')
        lines+= [row(r) for r in candidates] or ['No smaller profitable group identified in available evidence.']
        lines+=['Review losses before scaling: '+row(r)[2:] for r in rows if (r['values'].get('gross_profit') or 0)<0]
        return '\n\n'.join(lines)
    label=metric.replace('_',' '); direction='ascending' if route.get('ascending') else 'descending'
    return f'**{dim.title()} ranking by {label} ({direction})**\n\n'+'\n'.join(row(r) for r in rows)+ ('\n\nHistorical gross profit is not a forecast of incremental returns; test demand, capacity and marginal costs before scaling.' if metric=='gross_profit' else '')

def complete_plan(synthesis, findings, count):
    if count is None:return synthesis, None
    if not 1<=count<=5:return synthesis,'Requested count outside supported range (one to five).'
    # Use a coherent local plan rather than silently mixing duplicate AI and local actions.
    if len(synthesis.split('\n\n'))==count and synthesis:return synthesis,None
    lines=[]
    for t in findings[:count]:
        lines.append(f"- **{t['title']} (local):** {t['facts'][0]} **Proposed action:** {t['actions'][0]}")
    return '\n\n'.join(lines), 'AI count incomplete; local plan used.' if len(lines)==count else 'Insufficient distinct findings for requested count; local plan used.'
