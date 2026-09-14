"""ClickHouse connection, isolated from the rest of the logic.

Isolating this makes it possible, later on, to switch to a real connection pool
without touching any other part of the code (llm_service, analysis, etc. only
call run_sql, without knowing how the connection is managed underneath).
"""
import clickhouse_connect
from app.config import ENV

_client = None


def get_client():
    global _client
    if _client is None:
        _client = clickhouse_connect.get_client(
            host=ENV["CLICKHOUSE_HOST"],
            port=int(ENV["CLICKHOUSE_PORT"]),
            username=ENV["CLICKHOUSE_USER"],
            password=ENV["CLICKHOUSE_PASSWORD"],
            database=ENV["CLICKHOUSE_DATABASE"],
        )
    return _client


def run_sql(sql: str):
    result = get_client().query(sql)
    return result.result_rows, result.column_names
