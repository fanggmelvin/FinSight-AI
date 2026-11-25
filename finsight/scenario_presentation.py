"""Local presentation and bounded scenario follow-ups."""
import re
from finsight.scenario import run_scenario


def resolve_scenario_followup(question, previous):
    q=question.strip().rstrip('?.')
    m=re.fullmatch(r'(?:what if |and )?(?:we )?(?:increase|decrease|change|raise|reduce)?\s*(?:it )?\s*to\s+(\d+(?:\.\d+)?)\s*%\s*(?:instead)?',q,re.I)
    if not m:
        return question, None
    old=(previous or {}).get('effective_question') or (previous or {}).get('question','')
    if not (previous or {}).get('scenario') or len(re.findall(r'\d+(?:\.\d+)?\s*%',old))!=1:
        return question,'Specify the metric and percentage to change.'
    return re.sub(r'\d+(?:\.\d+)?\s*%',m[1]+'%',old,count=1),None


def format_value(value, margin=False, delta=False):
    if value is None: return 'N/A'
    value = round(value, 2) or 0.0
    return format(value, '+,.2f' if delta and value else ',.2f') + (' pp' if margin and delta else '%' if margin else '')


def executive_summary(baseline, projected):
    delta=projected['Gross profit']-baseline['Gross profit']
    direction='increases' if delta>0 else 'decreases' if delta<0 else 'is unchanged'
    text=f'Gross profit {direction}' + (f' by {abs(delta):,.2f}' if delta else '') + '.'
    b,p=baseline['Gross margin (%)'],projected['Gross margin (%)']
    if b is not None and p is not None:
        text+=f' Gross margin moves from {b:.2f}% to {p:.2f}% ({format_value(p-b, delta=True)} percentage points).'
    else: text+=' Gross margin is undefined when revenue is zero.'
    return text


def sensitivity(question, df):
    matches=list(re.finditer(r'\d+(?:\.\d+)?\s*%',question))
    if len(matches)!=1 or re.search(r'\b(?:target|achieve|discontinue)\b',question,re.I): return []
    m=matches[0]; center=float(m.group().rstrip('%').strip())
    values=sorted(set([0,max(0,center-5),center,min(100,center+5)]))
    rows=[]
    for v in values:
        try: result=run_scenario(question[:m.start()]+f'{v:g}%'+question[m.end():],df)
        except ValueError: continue
        for case in result['cases']:
            rows.append({'Assumption magnitude (%)':v,'Cost assumption':case['label'],'Gross profit':case['metrics']['Gross profit']})
    return rows
