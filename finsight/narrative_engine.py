"""Consolidate calculated observations into contextual management themes."""
import re
from collections import OrderedDict
from finsight.commentary_engine import findings_for

PLANS = {
 'segment_margin': ('Segment profitability', 'Negative gross margin indicates sales do not cover recorded cost of goods sold; it does not establish net income.', ['Review segment-level pricing, discounts and unit costs; isolate loss-making product combinations.', 'Build a segment gross-profit bridge separating volume, price and unit-cost effects where data permits.']),
 'segment_exposure': ('Segment concentration', 'Dependence on a narrow revenue base can increase sensitivity to demand shocks.', ['Stress-test simultaneous demand declines in the leading segments and assess diversification opportunities.', 'Review segment demand scenarios and identify alternative sources of revenue before reallocating resources.']),
 'product': ('Product profitability and exposure', 'Revenue scale and margin should be evaluated together rather than treating relative margin rank as proof of underperformance.', ['Compare product-level unit economics, discounts and sales mix before changing prices.', 'Model margin improvement scenarios while testing sensitivity of sales volume.']),
 'country': ('Geographic performance', 'Regional concentration and margin differences warrant separate review of local commercial conditions.', ['Compare country-level pricing, discounts and product mix using available transaction data.', 'Assess regional demand sensitivity and investigate cost differences before reallocating sales resources.']),
 'monthly': ('Monthly performance and volatility', 'Large monthly movements may distort run-rate forecasts; their causes are not established by aggregate results.', ['Reconcile the largest movements first and test volume, pricing, mix and timing hypotheses before forecasting.', 'Compare transaction-level sales and costs across flagged months and assess whether changes are recurring.']),
 'decline': ('Revenue declines', 'Revenue contraction warrants investigation of sales drivers rather than assuming a particular cause.', ['Prioritize the largest decline and compare volume, realized prices and product mix across periods.', 'Reconcile declining months to source transactions and investigate order timing where data permits.']),
 'compression': ('Margin compression', 'Margin compression can reflect pricing, mix or cost changes; these are hypotheses to test.', ['Build a gross-margin bridge using realized prices, discounts and unit costs for flagged months.', 'Compare cost and product mix across flagged months to identify recurring margin pressure.']),
 'increase': ('Revenue increases', 'A revenue rebound should not automatically be treated as sustainable growth.', ['Test whether revenue increases reflect recurring demand or timing effects before updating forecasts.', 'Review transaction mix and repeat sales patterns where available to assess sustainability.']),
 'driver_product': ('Product contributions', 'Product contributions explain arithmetic changes, not underlying causes.', ['Compare volume and realized pricing for declining products and assess the sustainability of positive offsets.', 'Build a product-level sales and gross-profit bridge to distinguish revenue effects from margin effects.']),
 'driver_country': ('Country contributions', 'Geographic attribution identifies where the change occurred, not why.', ['Review regional sales volume, pricing and product mix; investigate order timing where data permits.', 'Compare regional demand indicators with transaction-level changes before drawing causal conclusions.']),
 'driver_segment': ('Segment contributions', 'Segment exposure helps focus investigation on the business areas affected.', ['Prioritize the affected segments and review sales activity, order timing and pricing where records permit.', 'Compare segment-level demand and cost drivers before recommending commercial changes.']),
 'driver_intersection': ('Cross-dimensional contributions', 'Intersection findings overlap with individual dimensions and must not be added to them.', ['Drill into the cited product-country-segment combinations and reconcile their source transactions.', 'Coordinate a targeted review of the cited combinations to distinguish sales and cost effects.']),
 'other': ('Additional financial findings', 'These calculated observations are investigation leads.', ['Review the underlying evidence before making management decisions.', 'Validate the relevant transactions and monitor subsequent performance.']),
}

def theme_for(text, skill):
    t=text.lower().replace('*','')
    if skill=='variance-analysis':
        for d in ('product','country','segment','intersection'):
            if t.startswith(d): return 'driver_'+d
    if skill=='anomaly-detection':
        if 'revenue decline' in t:return 'decline'
        if 'margin compression' in t:return 'compression'
        if 'revenue increase' in t:return 'increase'
    if t.startswith('segment margin'):return 'segment_margin'
    if t.startswith('segment'):return 'segment_exposure'
    if t.startswith('product'):return 'product'
    if t.startswith('country'):return 'country'
    if 'financial performance' in t or 'monthly revenue' in t or 'revenue decline' in t or 'margin compression' in t or 'revenue increase' in t:return 'monthly'
    return 'other'

def build_themes(records, skill, direction=None):
    records_by_id = {record['evidence_id']: record for record in records}
    groups=OrderedDict()
    for f in findings_for(records,skill,direction):
        key=theme_for(f['text'],skill)
        groups.setdefault(key,[]).append(f)
    out=[]
    for key,items in groups.items():
        title,implication,actions=PLANS[key]
        if key=='segment_margin' and not any(re.search(r'\(-\d',f['text']) for f in items):
            implication='Relative margin rankings help prioritize review but do not establish losses or underperformance.'
        elif key == 'segment_margin':
            source_ids = re.findall(r'\[(E\d+)\]', items[0]['text'])
            if source_ids and (record := records_by_id.get(source_ids[0])):
                segment = record['title'].partition(':')[2].strip()
                if segment:
                    actions = [
                        f"Rank {segment} transactions by gross profit. Review realized prices, discounts and unit costs on the largest losses, then track the segment’s gross margin against break-even.",
                        f"Build a gross-profit bridge for {segment} to test how realized pricing, sales mix and unit costs contributed to the loss.",
                    ]
        # Sort anomaly observations by magnitude within severity, without comparing unlike units.
        if key in ('decline','compression','increase'):
            def order(f):
                m=re.search(r'([+-]?\d+(?:\.\d+)?)\s*(?:%|pp)',f['text'])
                return (f['priority']!='High',-abs(float(m[1])) if m else 0)
            items=sorted(items,key=order)
        out.append(dict(id=key,title=title,implication=implication,priority='High' if any(f['priority']=='High' for f in items) else 'Medium',facts=[f['text'] for f in items],actions=actions))
    return sorted(out,key=lambda x:x['priority']!='High')

def render_themes(themes, raw=None):
    import json
    selected={}; diagnostic=None
    if raw is not None:
        try:
            known={t['id'] for t in themes}
            items=json.loads(raw)['items']
            if not isinstance(items,list):raise ValueError()
            for item in items:
                key=item['finding_id']; action=item['action_id']
                if key not in known or key in selected or action not in ('a','b'):raise ValueError()
                selected[key]=action
        except (ValueError,TypeError,KeyError):
            selected={};diagnostic='Invalid management plan; local recommendations used.'
    lines=[]
    for t in themes:
        action=t['actions'][selected.get(t['id'],'a')=='b']
        facts=' '.join(re.sub(r'\*\*','',f) for f in t['facts'])
        lines.append(f"**{t['priority']} priority — {t['title']}**\n\n{facts}\n\n**Business implication:** {t['implication']}\n\n**Proposed action ({'AI-selected' if t['id'] in selected else 'rule-based'}):** {action}")
    return '\n\n'.join(lines) or 'No findings under the current rules. Review the calculated evidence.',len(selected),diagnostic
