"""Fail-closed, process-independent quotas on a shared local SQLite file.
Reservations are never refunded, including failed requests. Not a billing cap.
"""
import os
import sqlite3
import time
from pathlib import Path


class QuotaExceeded(RuntimeError):
    pass


def quota_config():
    dev = os.getenv('FINSIGHT_ENV', 'production') == 'development'
    prefix = 'FINSIGHT_DEV_' if dev else 'FINSIGHT_'
    path = Path(os.getenv(prefix + 'QUOTA_DB', str(Path.home() / ('.finsight-api-quota-dev.sqlite3' if dev else '.finsight-api-quota.sqlite3'))))
    windows = [(name, seconds, int(os.getenv(prefix + name.upper() + '_REQUESTS', str(default)))) for name, seconds, default in [('minute',60,5),('daily',86400,50),('monthly',2592000,300)]]
    return path, windows


def quota_status(now=None):
    now = time.time() if now is None else now
    path, windows = quota_config()
    rows = []
    if path.exists():
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            timestamps = [r[0] for r in db.execute('SELECT ts FROM requests WHERE ts > ? ORDER BY ts', (now-2592000,))]
    else:
        timestamps = []
    for name, seconds, limit in windows:
        active = [t for t in timestamps if t > now-seconds]
        remaining = max(0, limit-len(active))
        reset = max(0, active[len(active)-limit]+seconds-now) if limit > 0 and len(active)>=limit else None
        rows.append(dict(window=name, limit=limit, used=len(active), remaining=remaining, retry_seconds=reset))
    return rows


def reserve_request(*, now=None):
    now = time.time() if now is None else now
    path, windows = quota_config()
    if any(limit < 1 for _, _, limit in windows):
        raise QuotaExceeded('Live AI quota disabled')
    with sqlite3.connect(path, timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS requests (ts REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM requests WHERE ts <= ?', (now - 30*86400,))
        for name, window, limit in windows:
            count = db.execute('SELECT COUNT(*) FROM requests WHERE ts > ?', (now-window,)).fetchone()[0]
            if count >= limit:
                raise QuotaExceeded(f'Shared live AI {name} request quota reached')
        db.execute('INSERT INTO requests VALUES (?)', (now,))


class GuardedResponses:
    def __init__(self, responses):
        self._responses = responses

    def create(self, **kwargs):
        # Bound the complete serialized request, including instructions and schema.
        import json
        if len(json.dumps(kwargs, ensure_ascii=False).encode('utf-8')) > 48000:
            raise QuotaExceeded('Live AI request exceeds input size limit')
        kwargs['max_output_tokens'] = min(int(kwargs.get('max_output_tokens', 1200)), 1200)
        kwargs['store'] = False
        reserve_request()
        return self._responses.create(**kwargs)


class GuardedClient:
    def __init__(self, client):
        self.responses = GuardedResponses(client.responses)
