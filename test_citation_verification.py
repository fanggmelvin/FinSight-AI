from types import SimpleNamespace
import pytest
from ai_engine import verify_citations

@pytest.fixture
def registry():
    return SimpleNamespace(records=[{'evidence_id': f'E{i:03d}'} for i in range(1, 67)])

@pytest.mark.parametrize('answer,count', [('[E001]',1),('[E001, E003, E004]',3),('[E052-E066]',15),('[E002–E007]',6),('[E002—E007]',6),('[E042-E047, E047]',6),('[E001][E001]',1),('[E001; E002]',2)])
def test_valid_formats(registry, answer, count):
    result = verify_citations(answer, registry)
    assert result['passed']
    assert result['total_citations'] == count

@pytest.mark.parametrize('answer', ['[E999]', '[E065-E068]', '[E007-E002]', '[E001, nonsense]', '[E001-E999999]', 'No citations'])
def test_invalid_formats(registry, answer):
    assert not verify_citations(answer, registry)['passed']

def test_missing_range_members():
    registry = SimpleNamespace(records=[{'evidence_id':'E001'}, {'evidence_id':'E003'}])
    assert verify_citations('[E001-E003]', registry)['invalid_citations'] == ['E002']
