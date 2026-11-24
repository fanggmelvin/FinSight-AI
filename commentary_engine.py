"""Controlled commentary: local facts and allowlisted, conditional actions."""
import re
import json
from deterministic_report import deterministic_insights
from skill_workflow import anomaly_rows

ACTIONS = {
    'pricing': 'Evaluate pricing and discount sensitivity before changing commercial terms.',
    'cost': 'Review unit costs and cost allocation to identify potential margin improvements.',
    'volume': 'Investigate sales volume and product mix using transaction-level detail where available.',
    'scenario': 'Model downside demand scenarios and assess potential exposure.',
    'monitor': 'Track the relevant metric in subsequent periods before making resource decisions.',
    'reconcile': 'Reconcile the movement against source transactions and investigate unusual entries.',
}

def findings_for(records, skill, direction=None):
    findings = []
    def add(text, priority, choices):
        findings.append(dict(id=f'F{len(findings)+1:03}', text=text, priority=priority, choices=choices))
    if skill != 'anomaly-detection':
        for line in deterministic_insights(records, direction).split('\n\n'):
            if not line: continue
            # Keep calculated observation and evidence, replace generic review with selected action.
            ids = re.findall(r'\[E\d+\]', line)
            fact = re.split(r'\. (?:Review|Investigate|Assess)\b', line, maxsplit=1)[0].removeprefix('- ')
            fact = re.sub(r'\s*\[E\d+\]', '', fact).rstrip('.') + '. ' + ' '.join(ids)
            concentration = 'concentration' in fact.lower()
            high = 'negative revenue contribution' in fact or 'gross profit decline' in fact or bool(re.search(r'\(-\d+\.\d+%\)',fact))
            if 'Segment combined concentration' in fact:
                match = re.search(r'(\d+\.\d+)%', fact)
                high = bool(match and float(match[1]) >= 75)
            add(fact, 'High' if high else 'Medium', ['scenario','monitor'] if concentration else ['pricing','cost','volume','monitor'])
    if skill in ('anomaly-detection','executive-reporting','financial-performance'):
        for row in anomaly_rows(records):
            add(f"{row['Period']} — {row['Anomaly']}: {row['Change']}. [{row['Evidence']}]", 'High' if row['Severity']=='High' else 'Medium', ['reconcile','volume','monitor'] if row['Anomaly']!='Margin Compression' else ['cost','pricing','monitor'])
    if skill == 'variance-analysis':
        for r in records:
            v=r['values']; change=v.get('revenue_change')
            if r['title'].startswith(('Product:','Country:','Segment:','Intersection:')) and isinstance(change,(int,float)) and change>0:
                add(f"{r['title']} contributed a positive revenue change of {change:,.2f}. [{r['evidence_id']}]", 'Medium', ['volume','monitor'])
    return sorted(findings,key=lambda f:f['priority']!='High')

def render_findings(findings, raw=None):
    selected={}; diagnostic=None
    if raw is not None:
        try:
            data=json.loads(raw)
            if not isinstance(data,dict) or not isinstance(data.get('items'),list): raise ValueError()
            known={f['id']:f for f in findings}
            for item in data['items']:
                if not isinstance(item,dict): raise ValueError()
                fid=item.get('finding_id'); action=item.get('action_id')
                if not isinstance(fid,str) or not isinstance(action,str) or fid not in known or action not in known[fid]['choices'] or fid in selected: raise ValueError()
                selected[fid]=action
        except (ValueError,TypeError):
            selected={}; diagnostic='Invalid recommendation selection; local recommendations used.'
    lines=[]
    for f in findings:
        ai=f['id'] in selected
        action=selected.get(f['id'],f['choices'][0])
        lines.append(f"- **{f['priority']} priority:** {f['text']} **Proposed action ({'AI-selected' if ai else 'rule-based'}):** {ACTIONS[action]}")
    return '\n\n'.join(lines) or 'No findings under the current rules. Review the calculated evidence.', len(selected), diagnostic
