"""Fail-closed, process-independent quotas on a shared local SQLite file.
Reservations are never refunded, including failed requests. Not a billing cap.
"""
import os
import sqlite3
import time
from pathlib import Path


class QuotaExceeded(RuntimeError):
    pass


def reserve_request(*, now=None):
    now = time.time() if now is None else now
    path = Path(os.getenv('FINSIGHT_QUOTA_DB', str(Path.home() / '.finsight-api-quota.sqlite3')))
    daily = int(os.getenv('FINSIGHT_DAILY_REQUESTS', '50'))
    monthly = int(os.getenv('FINSIGHT_MONTHLY_REQUESTS', '300'))
    minute = int(os.getenv('FINSIGHT_MINUTE_REQUESTS', '5'))
    if min(daily, monthly, minute) < 1:
        raise QuotaExceeded('Live AI quota disabled')
    with sqlite3.connect(path, timeout=5) as db:
        db.execute('CREATE TABLE IF NOT EXISTS requests (ts REAL NOT NULL)')
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM requests WHERE ts <= ?', (now - 30*86400,))
        for window, limit in ((60, minute), (86400, daily), (30*86400, monthly)):
            count = db.execute('SELECT COUNT(*) FROM requests WHERE ts > ?', (now-window,)).fetchone()[0]
            if count >= limit:
                raise QuotaExceeded('Shared live AI request quota reached')
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
