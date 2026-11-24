"""Deterministic multi-dimensional investigation of validated financial data."""
import math
import pandas as pd


def investigate(df, previous_month, current_month, dimensions=('product','country','segment')):
    previous, current = (pd.Period(x, freq='M') for x in (previous_month,current_month))
    if current <= previous:
        raise ValueError('Current month must follow previous month')
    if not dimensions or len(set(dimensions)) != len(dimensions):
        raise ValueError('Select unique dimensions')
    required = {'date','revenue','cogs',*dimensions}
    if not required.issubset(df.columns):
        raise ValueError(f'Missing columns: {sorted(required-set(df.columns))}')
    data = df.copy()
    data['_period'] = pd.to_datetime(data['date'], errors='raise').dt.to_period('M')
    data = data[data['_period'].isin([previous,current])].copy()
    if not {previous,current}.issubset(set(data['_period'])):
        raise ValueError('Both comparison periods must contain records')
    for col in ('revenue','cogs'):
        data[col] = pd.to_numeric(data[col], errors='raise')
        if not data[col].map(math.isfinite).all():
            raise ValueError(f'Invalid {col}')
    def metrics(frame):
        r,c = float(frame.revenue.sum()),float(frame.cogs.sum())
        return {'revenue':r,'cogs':c,'gross_profit':r-c,'gross_margin':(r-c)/r if r>0 else None}
    def compare(frame):
        a,b = (metrics(frame[frame['_period']==p]) for p in (previous,current))
        return {'previous':a,'current':b,'revenue_change':b['revenue']-a['revenue'], 'gross_profit_change':b['gross_profit']-a['gross_profit'], 'growth':(b['revenue']-a['revenue'])/a['revenue'] if a['revenue']>0 else None}
    total=compare(data)
    def breakdown(cols):
        work=data.copy()
        for col in cols:
            work[col]=work[col].astype('string').fillna('Unknown')
        rows=[]
        for key,group in work.groupby(cols[0] if len(cols)==1 else list(cols),sort=True):
            keys=(key,) if len(cols)==1 else key
            rows.append({'labels':dict(zip(cols,keys)),**compare(group)})
        rows.sort(key=lambda x:x['revenue_change'])
        delta=math.fsum(x['revenue_change'] for x in rows)
        gp=math.fsum(x['gross_profit_change'] for x in rows)
        if not math.isclose(delta,total['revenue_change'],rel_tol=0,abs_tol=.005) or not math.isclose(gp,total['gross_profit_change'],rel_tol=0,abs_tol=.005):
            raise ArithmeticError('Breakdown does not reconcile')
        return {'rows':rows,'negative_contributions':math.fsum(min(0,x['revenue_change']) for x in rows),'positive_contributions':math.fsum(max(0,x['revenue_change']) for x in rows),'net_change':delta,'reconciliation_difference':delta-total['revenue_change']}
    return {'previous_month':str(previous),'current_month':str(current),'total':total,'dimensions':{d:breakdown((d,)) for d in dimensions},'intersection':breakdown(tuple(dimensions)), 'note':'Each breakdown partitions the same revenue change. Never add totals across dimensions. Contributions do not establish causation.'}
