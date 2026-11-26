"""Read-only evidence navigation for a single stored answer."""
import re


def evidence_sections(result):
    records = {r['evidence_id']: r for r in result.get('cited_evidence', []) if r}
    primary = result.get('direct_answer') or ''
    if result.get('local_plan') or result.get('numerical_verification', {}).get('generated_synthesis'):
        primary += '\n' + result.get('commentary', '').split('\n\n**Calculated supporting findings**', 1)[0]
    ids = []
    for group in re.findall(r'\[([^\[\]]+)\]', primary):
        for part in re.split(r'[,;]', group):
            m = re.fullmatch(r'E(\d{1,9})(?:\s*[-–—]\s*E(\d{1,9}))?', part.strip(), re.I)
            if not m:
                continue
            first, last = int(m[1]), int(m[2] or m[1])
            if 0 <= last-first <= 1000:
                ids.extend(f'E{i:03d}' for i in range(first, last+1))
    featured = [records[i] for i in dict.fromkeys(ids) if i in records]
    return featured, list(records.values())
