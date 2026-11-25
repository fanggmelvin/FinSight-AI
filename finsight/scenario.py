"""Deterministic what-if models on selected historical records."""
import re
import math
from finsight.reliability import scope_data, period_label


def is_scenario(question):
    return bool(re.search(r'\b(?:what if|what happens if|scenario|simulate|target gross margin|achieve a?\s*\d+(?:\.\d+)?%\s*gross margin|discontinue|increase revenue|reduce cogs)\b', question, re.I))


def _metrics(r, c):
    return {'Revenue': r, 'COGS': c, 'Gross profit': r-c, 'Gross margin (%)': (r-c)/r*100 if r else None}


def run_scenario(question, df):
    q = question.lower().strip().rstrip('?.')
    q = re.sub(r'\b(?:in|for)\s+((?:19|20)\d{2})\b', '', q).strip()
    df = scope_data(question, df)
    if df[['revenue','cogs']].isna().any().any():
        raise ValueError('Scenario requires complete revenue and COGS data.')
    r, c = (float(df[k].sum()) for k in ('revenue','cogs'))
    if not all(map(math.isfinite,(r,c))) or r <= 0 or c < 0:
        raise ValueError('Scenario requires positive revenue and nonnegative COGS.')
    rows = []
    def add(label, rr, cc):
        if not all(map(math.isfinite,(rr,cc))) or rr < 0 or cc < 0:
            raise ValueError('Scenario produces invalid revenue or COGS.')
        rows.append({'label':label,'metrics':_metrics(rr,cc)})
    prefix = r'(?:(?:what happens if|what if|simulate|scenario:?)\s+)?(?:we\s+)?'
    target = re.fullmatch(r'(?:target gross margin(?: of)?|(?:how much (?:additional )?revenue do we need to )?achieve)\s+(?:a\s+)?(\d+(?:\.\d+)?)\s*%\s*(?:gross margin)?',q)
    if target:
        t = float(target[1])/100
        if not 0 <= t < 1: raise ValueError('Target margin must be at least zero and below 100%.')
        if c == 0: raise ValueError('Revenue-only target is undefined with zero COGS.')
        add('Target via revenue; COGS unchanged',c/(1-t),c)
        add('Target via COGS; revenue unchanged',r,r*(1-t))
    else:
        stop = re.fullmatch(prefix+r'discontinue\s+(?:the\s+)?(.+?)(?:\s+segment)?',q)
        if stop:
            if 'segment' not in df: raise ValueError('Segment column is unavailable.')
            part=df[df.segment.astype(str).str.lower()==stop[1].strip()]
            if part.empty: raise ValueError('Named segment not found in selected data.')
            add('Remove segment revenue and all recorded segment COGS',r-float(part.revenue.sum()),c-float(part.cogs.sum()))
        else:
            # Strict grammar: do not silently ignore unparsed clauses.
            q=re.sub(r'^'+prefix,'',q).strip()
            q=re.sub(r'\b(?:increase|raise|grow)\s+(revenue|cogs)\b',r'\1 increases',q)
            q=re.sub(r'\b(?:reduce|decrease|cut)\s+(revenue|cogs)\b',r'\1 decreases',q)
            clauses=re.split(r'\s+and\s+',q)
            changes={}; segment=None
            for clause in clauses:
                m=re.fullmatch(r'(?:(.+?)\s+)?(revenue|cogs)\s+(increases?|grows?|rises?|decreases?|declines?|falls?|drops?|reduces?)\s+(?:by\s+)?(\d+(?:\.\d+)?)\s*%',clause.strip())
                if not m or m[2] in changes: raise ValueError('Use explicit percentage changes, e.g. revenue increases by 10% and COGS decreases by 5%.')
                if m[1]:
                    if segment and segment != m[1]: raise ValueError('Use one segment per scenario.')
                    segment=m[1].strip()
                change=float(m[4])/100 * (1 if m[3].startswith(('increase','grow','rise')) else -1)
                if change < -1 or not math.isfinite(change): raise ValueError('Decrease cannot exceed 100%.')
                changes[m[2]]=change
            if segment and len(changes)>1: raise ValueError('Combined segment changes are not supported; specify one change.')
            sr,sc=r,c
            if segment:
                if 'segment' not in df: raise ValueError('Segment column is unavailable.')
                part=df[df.segment.astype(str).str.lower()==segment]
                if part.empty: raise ValueError('Named segment not found in selected data.')
                sr,sc=float(part.revenue.sum()),float(part.cogs.sum())
            rr=r+sr*changes.get('revenue',0)
            if 'cogs' in changes:
                add('Explicit changes; percentages applied to baseline',rr,c+sc*changes['cogs'])
            else:
                add('COGS unchanged',rr,c)
                add('Affected COGS changes proportionally with revenue',rr,c+sc*changes['revenue'])
    return {'baseline':_metrics(r,c),'cases':rows,'period':period_label(df),'records':len(df)}
