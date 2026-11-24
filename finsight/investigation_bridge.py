"""Connect deterministic investigations to the existing evidence registry."""
from finsight.investigation_engine import investigate
from finsight.evidence_engine import EvidenceRegistry, source_reference


def build_investigation_evidence(df, previous, current, source, sheet):
    dimensions = tuple(d for d in ('product', 'country', 'segment') if d in df.columns)
    if not dimensions:
        raise ValueError('No mapped business dimensions')
    result = investigate(df, previous, current, dimensions)
    registry = EvidenceRegistry()
    data = df[df['date'].dt.to_period('M').astype(str).isin([previous, current])]
    def flatten(row):
        return {**{f'previous_{k}': v for k,v in row['previous'].items()},
                **{f'current_{k}': v for k,v in row['current'].items()},
                **{k: row[k] for k in ('revenue_change','gross_profit_change','growth')}}
    def add(title, values, subset):
        registry.add(('Intersection (selected)' if title.startswith('Intersection:') else title.split(':')[0] + ' contributors' if ':' in title else title), title, {'previous_month':previous,'current_month':current, **values}, result['note'], source_reference(subset, source, sheet))
    add('Total financial change', flatten(result['total']), data)
    for dimension, breakdown in result['dimensions'].items():
        add(f'{dimension.title()} reconciliation', {k:v for k,v in breakdown.items() if k != 'rows'}, data)
        for row in breakdown['rows']:
            label = row['labels'][dimension]
            subset = data[data[dimension].astype('string').fillna('Unknown') == label]
            add(f'{dimension.title()}: {label}', flatten(row), subset)
    # Limit intersection evidence to the largest absolute changes; do not imply completeness.
    rows = sorted(result['intersection']['rows'], key=lambda r: abs(r['revenue_change']), reverse=True)[:5]
    for row in rows:
        subset = data
        for dimension, label in row['labels'].items():
            subset = subset[subset[dimension].astype('string').fillna('Unknown') == label]
        add('Intersection: ' + ' / '.join(row['labels'].values()), flatten(row), subset)
    return registry, result


def run_investigation(question, df, previous, current, source, sheet):
    from finsight.ai_engine import analyze_question
    registry, investigation = build_investigation_evidence(df, previous, current, source, sheet)
    result = analyze_question(question + '\nCompare all supplied dimensions independently. Never add changes across dimensions. Intersection evidence contains only the five largest absolute changes, or fewer if unavailable. Distinguish arithmetic attribution from causation. The selected comparison is not the entire dataset.', registry)
    result['investigation'] = investigation
    return result
