"""Render financial values from evidence, never from model prose."""
import re
from decimal import Decimal


def build_facts(registry):
    facts = {}
    for record in registry.records:
        eid = record['evidence_id']
        for field, value in record['values'].items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            n = Decimal(str(value))
            if not n.is_finite():
                continue
            if record.get('category') == 'Financial Anomaly' and field == 'value':
                facts[f'{eid}.{field}'] = f'{n:+.2f} pp' if record['values'].get('category') == 'Margin Compression' else f'{n:+.2%}'
                continue
            percent = field in {'growth','variance_pct','revenue_share'} or 'margin' in field or field.endswith(('_pct','_growth'))
            if percent:
                shown = f'{n*100:,.2f}' + (' pp' if 'change' in field else '%')
            else:
                shown = f'{n:,.2f}'
            facts[f'{eid}.{field}'] = shown
    return facts


def render_report(registry, commentary):
    facts = build_facts(registry)
    # No free-form model numbers or rankings are admitted into financial facts.
    lines = ['### Calculated financial evidence', 'Values below are calculated from the selected evidence. Monetary values use source currency units.']
    for r in registry.records:
        eid = r['evidence_id']
        fields = [(k.split('.',1)[1], v) for k,v in facts.items() if k.startswith(eid+'.')]
        if fields:
            title = str(r['title']).replace('\n',' ').replace('|','\\|')
            lines.append(f"- **{title}** [{eid}]: " + '; '.join(f'{k.replace("_"," ")}: {v}' for k,v in fields))
    lines += ['### AI interpretation and proposed actions', commentary or 'Commentary unavailable; review the calculated evidence above.', '### Limitations', 'Financial figures are rendered from the evidence registry. AI commentary is not independently verified. Contributions do not establish causation.']
    return '\n\n'.join(lines), len(facts)


def commentary_diagnostic(text, registry):
    if not isinstance(text, str) or not text.strip():
        return 'Empty commentary'
    known = {r['evidence_id'] for r in registry.records}
    ids = re.findall(r'\[(E\d+)\]', text)
    stripped = re.sub(r'\[E\d+\]', '', text)
    if any(i not in known for i in ids):
        return 'Unknown evidence reference'
    if not ids:
        return 'No evidence references'
    if re.search(r'\d|[$€£%]', stripped):
        return 'Digits or financial symbols outside evidence references'
    if re.search(r'\b(?:one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|billion|percent|half|double|triple)\b', stripped, re.I):
        return 'Possible spelled-out numerical claim'
    if re.search(r'\[|\]|<|>|https?://', stripped):
        return 'Unexpected markup or citation format'
    return None


def validate_commentary(text, registry):
    # Convert only explicit list markers, never financial values.
    if not isinstance(text, str):
        return ''
    text = re.sub(r'(?m)^\s*\d+[.)]\s+', '- ', text)
    return '' if commentary_diagnostic(text, registry) else text.strip()


def report_groups(records):
    groups = {}
    for record in records:
        title = str(record['title'])
        group = title.split(':', 1)[0] if ':' in title else 'Other evidence'
        groups.setdefault(group, []).append(record)
    return groups


def parse_structured_commentary(raw, registry, route=None, action_only=False):
    import json
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return '', 'Invalid commentary JSON'
    if not isinstance(data, dict) or not isinstance(data.get('items'), list) or not data['items']:
        return '', 'Missing commentary items'
    from finsight.commentary_grounding import ranking_rows, ranking_observation, action_diagnostic
    ranked = ranking_rows(registry.records, route)
    lines = []
    errors = []
    known = {r['evidence_id'] for r in registry.records}
    for index, item in enumerate(data['items'], 1):
        if not isinstance(item, dict):
            errors.append('Invalid item'); continue
        ids = item.get('evidence_ids')
        if not isinstance(ids, list) or not ids or any(not isinstance(i, str) or i not in known for i in ids):
            errors.append('Missing or unknown evidence reference'); continue
        priority = item.get('priority')
        observation, action = item.get('observation'), item.get('action')
        if ranked:
            observation = ''  # Discard model observations before any validation.
            observation = ranking_observation(ranked, ids, route['metric'])
        if action_only and not ranked:
            # Financial observations are generated solely from cited evidence.
            facts = build_facts(registry)
            parts = []
            for r in registry.records:
                if r['evidence_id'] not in ids:
                    continue
                fields = [f"{k.replace('_', ' ')} {facts[r['evidence_id']+'.'+k]}" for k in ('gross_profit','gross_margin','revenue_share','revenue','value') if r['evidence_id']+'.'+k in facts]
                parts.append(str(r['title']).replace('\n',' ') + (': ' + '; '.join(fields) if fields else ''))
            observation = '; '.join(parts) + '.'
        if priority not in ('High', 'Medium', 'Low') or any(not isinstance(t, str) or not t.strip() or '\n' in t or '[' in t or ']' in t for t in (observation, action)):
            errors.append('Invalid commentary fields'); continue
        line = f'- **{priority} priority:** {observation} **Proposed action:** {action} ' + ' '.join(f'[{i}]' for i in dict.fromkeys(ids))
        from finsight.skill_workflow import qualitative_diagnostic, mask_cited_anomaly_dates
        cited = [r for r in registry.records if r['evidence_id'] in ids]
        error = commentary_diagnostic(mask_cited_anomaly_dates(line, cited), registry) or qualitative_diagnostic(observation, cited)
        if not ranked and not error:
            from finsight.commentary_grounding import terminology_diagnostic
            error = terminology_diagnostic(observation + " " + action)
        if ranked:
            # Model observations are discarded, not treated as verified claims.
            error = commentary_diagnostic(action + ' ' + ' '.join(f'[{i}]' for i in ids), registry) or action_diagnostic(action, route)
            if error:
                error = f'Item {index}, action: {error}'
            if any(i not in {r['evidence_id'] for r in ranked} for i in ids):
                error = 'Evidence outside requested ranking'
            if not error:
                observation = ranking_observation(ranked, ids, route['metric'])
                line = f'- **{priority} priority:** {observation} **Proposed action:** {action} ' + ' '.join(f'[{i}]' for i in dict.fromkeys(ids))
        if action_only and not ranked:
            error = commentary_diagnostic(action + ' ' + ' '.join(f'[{i}]' for i in ids), registry) or action_diagnostic(action, route) or qualitative_diagnostic(action, cited)
            if error:
                error = f'Item {index}, action: {error}'
        if error:
            errors.append(error); continue
        if action_only and any(action == previous.split(' **Proposed action:** ',1)[-1].split(' [E',1)[0] for previous in lines):
            errors.append('Duplicate strategic action'); continue
        lines.append(line)
    lines.sort(key=lambda line: next((i for i,p in enumerate(('High','Medium','Low')) if line.startswith(f'- **{p} priority:')), 3))
    if ranked and lines and not any('[' + ranked[0]['evidence_id'] + ']' in line for line in lines):
        return '', 'Ranking leader not addressed; local recommendations used.'
    if ranked and lines and route.get('ambiguous_profitability'):
        profits = [r for r in ranked if isinstance(r['values'].get('gross_profit'), (int, float))]
        if profits:
            leader = max(profits, key=lambda r:r['values']['gross_profit'])
            eid = leader['evidence_id']
            if not any(f'[{eid}]' in line for line in lines):
                lines.append(f"- **Local action:** {ranking_observation([leader], [eid], 'gross_profit')} Review volume, pricing and incremental COGS before allocating resources. [{eid}]")
    if ranked:
        seen = set()
        for i, line in enumerate(lines):
            if ' **Proposed action:** ' not in line:
                continue
            prefix, action = line.split(' **Proposed action:** ', 1)
            observation = prefix.split(' priority:** ', 1)[-1]
            if observation in seen:
                lines[i] = prefix.split(' priority:** ', 1)[0] + ' priority:** **Proposed action:** ' + action
            seen.add(observation)
    return '\n\n'.join(lines), '; '.join(dict.fromkeys(errors)) or None


def key_tables(records):
    """Deterministic tables, independent of AI output."""
    tables = {}
    for group, rows in report_groups(records).items():
        if group not in ('Product','Country','Segment','Intersection','Financial Performance'):
            continue
        fields = ('revenue_change','gross_profit_change','previous_revenue','current_revenue','previous_gross_profit','current_gross_profit','gross_margin','revenue_share','revenue','gross_profit')
        data = [{'Name': r['title'].split(':',1)[-1].strip(), 'Evidence': r['evidence_id'], **{f:r['values'][f] for f in fields if f in r['values']}} for r in rows]
        if data:
            tables[group] = data
    return tables


def deterministic_insights(records, direction=None):
    """Evidence-backed findings; recommendations are hypotheses, not causal claims."""
    lines = []
    for group, rows in report_groups(records).items():
        if group not in ('Product', 'Country', 'Segment', 'Intersection', 'Financial Performance'):
            continue
        def eligible(field):
            return [r for r in rows if isinstance(r['values'].get(field), (int,float)) and Decimal(str(r['values'][field])).is_finite()]
        def name(r):
            return r['title'].split(':',1)[-1].strip()
        def cite(r):
            return '[' + r['evidence_id'] + ']'
        changes = eligible('revenue_change')
        if changes:
            if direction == 'growth':
                for field, label in [('revenue_change','revenue'), ('gross_profit_change','gross profit')]:
                    candidates = eligible(field)
                    if candidates:
                        top = max(candidates,key=lambda r:r['values'][field])
                        if top['values'][field] > 0:
                            lines.append(f"- **{group} growth priority:** {name(top)} had the largest positive {label} contribution ({top['values'][field]:,.2f}). Review opportunities to sustain performance. {cite(top)}")
            r = min(changes,key=lambda r:r['values']['revenue_change'])
            if r['values']['revenue_change'] < 0:
                lines.append(f"- **{group} revenue priority:** {name(r)} had the largest negative revenue contribution ({r['values']['revenue_change']:,.2f}). Investigate sales volume, pricing and mix where data permits. {cite(r)}")
            gp = eligible('gross_profit_change')
            if gp:
                r = min(gp,key=lambda r:r['values']['gross_profit_change'])
                if r['values']['gross_profit_change'] < 0:
                    lines.append(f"- **{group} profit priority:** {name(r)} had the largest gross profit decline ({r['values']['gross_profit_change']:,.2f}). Review cost and sales drivers. {cite(r)}")
            for row in rows:
                v = row['values']
                if all(isinstance(v.get(k),(int,float)) for k in ('previous_revenue','current_revenue','previous_gross_profit','current_gross_profit')) and v['previous_revenue'] > 0 and v['current_revenue'] > 0:
                    before = v['previous_gross_profit']/v['previous_revenue']
                    after = v['current_gross_profit']/v['current_revenue']
                    if direction == 'growth' and v['revenue_change'] > 0 and after < before:
                        lines.append(f"- **{group} margin pressure:** {name(row)} gross margin fell from {before:.2%} to {after:.2%} despite revenue growth. {cite(row)}")
            continue
        margins = eligible('gross_margin')
        if margins:
            r = min(margins,key=lambda r:r['values']['gross_margin'])
            lines.append(f"- **{group} margin review:** {name(r)} had the lowest gross margin ({r['values']['gross_margin']:.2%}). Review pricing, discounts and costs. {cite(r)}")
        shares = eligible('revenue_share')
        if shares:
            r = max(shares,key=lambda r:r['values']['revenue_share'])
            lines.append(f"- **{group} concentration:** {name(r)} had the largest revenue share ({r['values']['revenue_share']:.2%}). Assess exposure before allocating resources. {cite(r)}")
            if len(shares) >= 2:
                top = sorted(shares,key=lambda r:r['values']['revenue_share'],reverse=True)[:2]
                lines.append(f"- **{group} combined concentration:** {name(top[0])} and {name(top[1])} represent {sum(r['values']['revenue_share'] for r in top):.2%} of revenue. {cite(top[0])} {cite(top[1])}")
        if group == 'Financial Performance':
            rev = eligible('revenue')
            if rev:
                lo=min(rev,key=lambda r:r['values']['revenue']); hi=max(rev,key=lambda r:r['values']['revenue'])
                lines.append(f"- **Monthly revenue range:** {name(lo)} ({lo['values']['revenue']:,.2f}) to {name(hi)} ({hi['values']['revenue']:,.2f}). Review monthly variability before forecasting. {cite(lo)} {cite(hi)}")
    return '\n\n'.join(lines)
