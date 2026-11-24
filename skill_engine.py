"""Deterministic selection of trusted, bundled financial skill instructions."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "skills"
ALLOWED = frozenset(('financial-performance','variance-analysis','profitability-analysis','concentration-risk','anomaly-detection','executive-reporting','evidence-verification'))

def select_skills(question, records, route=None):
    q = question.lower()
    route = route or {}
    categories = {r.get('category') for r in records}
    if route.get('mode') in ('multi_investigation','revenue_investigation') or categories & {'Revenue Investigation','Total financial change'}:
        primary = 'variance-analysis'
    elif route.get('metric') == 'revenue_share':
        primary = 'concentration-risk'
    elif route.get('metric') == 'gross_margin':
        primary = 'profitability-analysis'
    elif re.search(r'\b(executive|board|cfo|management)\b.*\breport\b|\breport\b.*\b(executive|board|cfo|management)\b', q):
        primary = 'executive-reporting'
    elif re.search(r'\b(anomal\w*|unusual|exception\w*|flags?)\b', q):
        primary = 'anomaly-detection'
    elif re.search(r'concentrat|revenue share|dependen|exposure', q):
        primary = 'concentration-risk'
    elif re.search(r'profitab|gross margin|margin compression', q):
        primary = 'profitability-analysis'
    else:
        primary = 'financial-performance'
    return (primary, 'evidence-verification')

def load_skills(names, root=None):
    root = Path(root) if root is not None else ROOT
    if 'evidence-verification' not in names:
        raise ValueError('Mandatory evidence skill missing')
    sections = []
    for name in names:
        if name not in ALLOWED:
            raise ValueError('Unknown skill')
        path = root / name / 'SKILL.md'
        raw = path.read_text(encoding='utf-8')
        parts = raw.split('---', 2)
        if len(raw) > 12000 or len(parts) != 3 or parts[0].strip() or not re.search(r'^name: '+re.escape(name)+r'$', parts[1], re.M) or not parts[2].strip():
            raise ValueError('Invalid bundled skill: '+name)
        sections.append(parts[2].strip())
    return '\n\n'.join(sections)
