# Phase 1: shared API request guard
Defaults: 5 requests per rolling minute, 50 per rolling day, 300 per rolling 30 days. Set FINSIGHT_MINUTE_REQUESTS, FINSIGHT_DAILY_REQUESTS, FINSIGHT_MONTHLY_REQUESTS in server secrets to change. Requests over 48,000 serialized UTF-8 bytes fall back locally; output capped at 1,200 tokens. SDK retries disabled. Failed calls consume reservations. No API key is included.

SQLite quota file defaults to ~/.finsight-api-quota.sqlite3; FINSIGHT_QUOTA_DB can point to a persistent shared local volume. All workers must share the same database. Streamlit Community Cloud storage may reset on redeployment or restart; separate replicas do not share local files. This is not a guaranteed monetary cap. Use a durable shared external quota store before relying on it for public spending enforcement. Monitor provider usage. Keep live AI disabled if strict spending enforcement is required.

Run python -m pytest -q before deployment. This phase does not change conversation behavior.
