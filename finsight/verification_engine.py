"""Deterministic checks of structured financial claims; not prose entailment."""
from decimal import Decimal, InvalidOperation


def number(value):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a financial number')
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError('Nonfinite number')
    return result


def verify_claim(claim, registry):
    result = {'claim': claim, 'status': 'unverified'}
    try:
        record = registry.get(claim['evidence_id'])
        if record is None:
            return dict(result, reason='Unknown evidence ID')
        field = claim['field']
        actual = number(record['values'][field])
        if claim.get('kind', 'numeric') == 'ranking':
            direction = claim['direction']
            if direction not in ('highest', 'lowest'):
                raise ValueError('Unknown ranking direction')
            peers = [number(r['values'][field]) for r in registry.records
                     if r['category'] == record['category'] and field in r['values']]
            if len(peers) < 2:
                return dict(result, reason='Insufficient comparable records')
            expected = (max if direction == 'highest' else min)(peers)
            return dict(result, status='passed' if actual == expected else 'failed',
                        actual=str(actual), expected=str(expected), reason='Ranking within evidence category')
        if claim.get('kind', 'numeric') != 'numeric':
            return dict(result, reason='Unsupported claim type')
        unit = claim.get('unit', 'raw')
        factors = {'raw': 1, 'thousand': 1000, 'million': 1000000, 'percent': Decimal('0.01'), 'percentage_points': Decimal('0.01')}
        factor = number(factors[unit])
        decimals = claim.get('decimals', 0)
        if type(decimals) is not int or not 0 <= decimals <= 8:
            raise ValueError('Invalid precision')
        reported = number(claim['value']) * factor
        tolerance = factor * Decimal('0.5') * Decimal(10) ** -decimals
        return dict(result, status='passed' if abs(actual-reported) <= tolerance else 'failed',
                    actual=str(actual), reported=str(reported), tolerance=str(tolerance), reason='Compared with cited field')
    except (KeyError, TypeError, ValueError, InvalidOperation, AttributeError):
        return dict(result, reason='Missing or invalid claim or evidence field')


def verify_claims(claims, registry):
    results = [verify_claim(c, registry) for c in claims]
    return {'results': results, **{s: sum(r['status'] == s for r in results) for s in ('passed','failed','unverified')}}
