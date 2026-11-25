import pytest

@pytest.fixture(autouse=True)
def isolated_quota(monkeypatch,tmp_path):
    monkeypatch.setenv('FINSIGHT_ENV','production')
    for prefix in ('FINSIGHT_', 'FINSIGHT_DEV_'):
        monkeypatch.setenv(prefix+'QUOTA_DB',str(tmp_path/(prefix+'quota.db')))
        for name,value in [('MINUTE',5),('DAILY',50),('MONTHLY',300)]:
            monkeypatch.setenv(prefix+name+'_REQUESTS',str(value))
