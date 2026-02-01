from typing import Optional, List
from datetime import date, timedelta
from rococo.repositories.postgresql import PostgreSQLRepository
from rococo.data import PostgreSQLAdapter
from app.models import UsageSnapshot


class UsageSnapshotRepository(PostgreSQLRepository):
    def __init__(self, adapter: PostgreSQLAdapter):
        super().__init__(adapter, UsageSnapshot, None, None)

    def get_by_api_key_date_model(self, api_key_id: str, snapshot_date: date, model: str) -> Optional[UsageSnapshot]:
        results = self.get_many({"api_key_id": api_key_id, "snapshot_date": snapshot_date, "model": model})
        return results[0] if results else None

    def get_snapshots_for_period(self, start_date: date, end_date: date, model: Optional[str] = None) -> List[UsageSnapshot]:
        if model:
            query = """
                SELECT * FROM usage_snapshot
                WHERE snapshot_date >= %s AND snapshot_date <= %s AND model = %s AND active = true
            """
            results = self._execute_within_context(
                self.adapter.execute_query, query, (start_date, end_date, model)
            )
        else:
            query = """
                SELECT * FROM usage_snapshot
                WHERE snapshot_date >= %s AND snapshot_date <= %s AND active = true
            """
            results = self._execute_within_context(
                self.adapter.execute_query, query, (start_date, end_date)
            )
        return [UsageSnapshot.from_dict(row) for row in results] if results else []

    def get_developer_history(self, api_key_id: str, days: int = 30, model: Optional[str] = None) -> List[UsageSnapshot]:
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        if model:
            query = """
                SELECT * FROM usage_snapshot
                WHERE api_key_id = %s AND snapshot_date >= %s AND snapshot_date <= %s AND model = %s AND active = true
                ORDER BY snapshot_date DESC
            """
            results = self._execute_within_context(
                self.adapter.execute_query, query, (api_key_id, start_date, end_date, model)
            )
        else:
            query = """
                SELECT * FROM usage_snapshot
                WHERE api_key_id = %s AND snapshot_date >= %s AND snapshot_date <= %s AND active = true
                ORDER BY snapshot_date DESC
            """
            results = self._execute_within_context(
                self.adapter.execute_query, query, (api_key_id, start_date, end_date)
            )
        return [UsageSnapshot.from_dict(row) for row in results] if results else []

    def get_distinct_models(self) -> List[str]:
        query = "SELECT DISTINCT model FROM usage_snapshot WHERE active = true ORDER BY model"
        results = self._execute_within_context(
            self.adapter.execute_query, query, ()
        )
        return [row["model"] for row in results] if results else []

    def upsert_snapshot(self, snapshot: UsageSnapshot) -> UsageSnapshot:
        existing = self.get_by_api_key_date_model(snapshot.api_key_id, snapshot.snapshot_date, snapshot.model)
        if existing:
            existing.uncached_input_tokens = snapshot.uncached_input_tokens
            existing.cache_read_input_tokens = snapshot.cache_read_input_tokens
            existing.cache_creation_5m_tokens = snapshot.cache_creation_5m_tokens
            existing.cache_creation_1h_tokens = snapshot.cache_creation_1h_tokens
            existing.output_tokens = snapshot.output_tokens
            existing.web_search_requests = snapshot.web_search_requests
            existing.fetched_at = snapshot.fetched_at
            return self.save(existing)
        return self.save(snapshot)
