import pytest
from finsight.api_guard import reserve_request, GuardedResponses, QuotaExceeded


def test_shared_quota(tmp_path, monkeypatch):
    monkeypatch.setenv('FINSIGHT_QUOTA_DB', str(tmp_path/'quota.db'))
    monkeypatch.setenv('FINSIGHT_MINUTE_REQUESTS', '2')
    reserve_request(now=1000)
    reserve_request(now=1001)
    with pytest.raises(QuotaExceeded):
        reserve_request(now=1002)
    reserve_request(now=1062)


def test_request_caps(tmp_path, monkeypatch):
    monkeypatch.setenv('FINSIGHT_QUOTA_DB', str(tmp_path/'quota.db'))
    class Fake:
        def create(self, **kwargs):
            return kwargs
    guard = GuardedResponses(Fake())
    assert guard.create(input='test', max_output_tokens=5000)['max_output_tokens'] == 1200
    with pytest.raises(QuotaExceeded):
        guard.create(input='x'*48001)
