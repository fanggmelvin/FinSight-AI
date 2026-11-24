"""Conservative field aliases and surface-level coverage warnings."""
import re


def normalize_claims(claims, registry):
    output = []
    for original in claims:
        claim = dict(original)
        record = registry.get(claim.get('evidence_id'))
        if record:
            field = claim.get('field')
            values = record['values']
            aliases = {}
            if record['category'] == 'Revenue Investigation':
                aliases = {'total_revenue_change': 'revenue_change', 'revenue_growth_pct': 'growth'}
            elif record['category'] == 'Revenue Contributor':
                name = record['title'].partition(': ')[2].lower()
                aliases = {name + '_revenue_change': 'revenue_change'}
            if isinstance(field, str) and field not in values and aliases.get(field) in values:
                claim['field'] = aliases[field]
        output.append(claim)
    return output


AMOUNT = re.compile(r'\$\s*\d[\d,]*(?:\.\d+)?(?:\s*(?:million|thousand|[MK])\b)?|\b\d+(?:\.\d+)?\s*(?:%|percentage points)', re.I)


def uncovered_numbers(answer, claims):
    # Surface check only: matching a number does not establish semantic coverage.
    from decimal import Decimal, InvalidOperation
    output = []
    for match in AMOUNT.finditer(answer):
        token = match.group()
        magnitude = Decimal(re.search(r'\d[\d,]*(?:\.\d+)?', token).group().replace(',', ''))
        unit = 'percent' if '%' in token else 'percentage_points' if 'percentage points' in token.lower() else 'million' if re.search(r'million|m$', token, re.I) else 'thousand' if re.search(r'thousand|k$', token, re.I) else 'raw'
        covered = False
        for c in claims:
            try:
                if token in (c.get('text') or '') and c.get('unit') == unit and abs(Decimal(str(c.get('value')))) == magnitude:
                    covered = True
                    break
            except (InvalidOperation, TypeError, ValueError):
                pass
        if not covered:
            output.append({'text': token, 'kind': 'coverage_warning', 'evidence_id': None, 'field': None})
    return output

# Normalize only when the literal report token independently confirms the scale.
_original_normalize = normalize_claims

def normalize_claims(claims, registry):
    from decimal import Decimal, InvalidOperation
    output = _original_normalize(claims, registry)
    for c in output:
        text = c.get('text') or ''
        record = registry.get(c.get('evidence_id'))
        values = record['values'] if record else {}
        if c.get('field') == 'revenue_change' and 'revenue_change' not in values and 'net_change' in values:
            c['field'] = 'net_change'
        if c.get('kind') == 'ranking' and re.search(r'100\s*%\s*decline', text, re.I) and not re.search(r'largest|smallest|highest|lowest', text, re.I):
            c.update(kind='numeric', field='growth', value=-100, unit='percent', decimals=0)
        factor = {'million':1000000, 'thousand':1000}.get(c.get('unit'))
        if factor:
            try:
                v = Decimal(str(c.get('value')))
                tokens = [Decimal(re.search(r'\d[\d,]*(?:\.\d+)?', m.group()).group().replace(',','')) for m in AMOUNT.finditer(text) if re.search(r'(?:million|m)$' if factor==1000000 else r'(?:thousand|k)$', m.group(), re.I)]
                if abs(v) not in tokens and abs(v)/factor in tokens:
                    c['value'] = float(v/factor)
            except (InvalidOperation, ValueError, TypeError):
                pass
        if c.get('field') == 'gross_margin' and 'gross_margin' not in values:
            match = re.search(r'from\s+(-?\d+(?:\.\d+)?)%\s+to\s+(?:negative\s+)?(-?\d+(?:\.\d+)?)%', text, re.I)
            if match:
                try:
                    v = Decimal(str(c.get('value')))
                    candidates = [field for field, token in zip(('previous_gross_margin','current_gross_margin'),match.groups()) if v == Decimal(token) and field in values]
                    if len(candidates)==1:
                        c['field']=candidates[0]
                except (InvalidOperation, ValueError):
                    pass
    return output
