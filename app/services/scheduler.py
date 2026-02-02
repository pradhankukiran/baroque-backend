import logging
from datetime import datetime, date, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from rococo.data import PostgreSQLAdapter

from collections import defaultdict
from app.config import get_settings
from app.models import UsageSnapshot
from app.repositories import DeveloperRepository, UsageSnapshotRepository
from app.services.anthropic_client import AnthropicAdminClient

logger = logging.getLogger(__name__)


def aggregate_hourly_to_daily(records: list) -> list:
    """Aggregate hourly usage records into daily totals by api_key_id + model + date."""
    daily_totals = defaultdict(lambda: {
        "uncached_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_5m_tokens": 0,
        "cache_creation_1h_tokens": 0,
        "output_tokens": 0,
        "web_search_requests": 0,
    })

    for record in records:
        api_key_id = record.get("api_key_id")
        model = record.get("model", "unknown")
        bucket_date = record.get("_bucket_date", "")

        if not api_key_id or not bucket_date:
            continue

        key = (api_key_id, model, bucket_date)

        # Handle nested cache_creation structure from API
        cache_creation = record.get("cache_creation", {})
        server_tool_use = record.get("server_tool_use", {})

        daily_totals[key]["uncached_input_tokens"] += record.get("uncached_input_tokens", 0)
        daily_totals[key]["cache_read_input_tokens"] += record.get("cache_read_input_tokens", 0)
        daily_totals[key]["cache_creation_5m_tokens"] += cache_creation.get("ephemeral_5m_input_tokens", 0)
        daily_totals[key]["cache_creation_1h_tokens"] += cache_creation.get("ephemeral_1h_input_tokens", 0)
        daily_totals[key]["output_tokens"] += record.get("output_tokens", 0)
        daily_totals[key]["web_search_requests"] += server_tool_use.get("web_search_requests", 0)

    # Convert back to list of records
    aggregated = []
    for (api_key_id, model, bucket_date), totals in daily_totals.items():
        aggregated.append({
            "api_key_id": api_key_id,
            "model": model,
            "_bucket_date": bucket_date,
            **totals,
        })

    return aggregated

scheduler = AsyncIOScheduler()


async def fetch_usage_for_api_key(api_key_id: str, adapter: Optional[PostgreSQLAdapter] = None) -> int:
    """
    Fetch usage data for a single API key ID.
    Returns the number of snapshots upserted.
    """
    settings = get_settings()

    if not settings.anthropic_admin_api_key:
        logger.warning("No Anthropic Admin API key configured, skipping fetch")
        return 0

    logger.info(f"Fetching usage data for API key: {api_key_id[:10]}...")

    client = AnthropicAdminClient(settings.anthropic_admin_api_key)

    # Create adapter if not provided
    owns_adapter = adapter is None
    if owns_adapter:
        adapter = PostgreSQLAdapter(
            settings.database_host,
            settings.database_port,
            settings.database_user,
            settings.database_password,
            settings.database_name,
        )

    try:
        usage_repo = UsageSnapshotRepository(adapter)

        # Fetch past 7 days to capture historical data (API returns empty for partial days)
        now_utc = datetime.utcnow()
        today_utc = now_utc.date()
        starting_at = datetime.combine(today_utc - timedelta(days=7), datetime.min.time())
        ending_at = datetime.combine(today_utc + timedelta(days=1), datetime.min.time())

        usage_data = await client.get_usage_report(
            starting_at=starting_at,
            ending_at=ending_at,
            group_by=["api_key_id", "model"],
            bucket_width="1h",  # Use hourly to capture today's incomplete data
        )

        if usage_data is None:
            logger.error("Failed to fetch usage data")
            return 0

        # Aggregate hourly data into daily totals
        daily_records = aggregate_hourly_to_daily(usage_data)
        logger.info(f"Aggregated {len(usage_data)} hourly records into {len(daily_records)} daily records")

        fetched_count = 0
        for record in daily_records:
            record_api_key_id = record.get("api_key_id")
            if record_api_key_id != api_key_id:
                continue

            model = record.get("model", "unknown")
            bucket_date_str = record.get("_bucket_date", str(today_utc))
            snapshot_date = date.fromisoformat(bucket_date_str)

            snapshot = UsageSnapshot(
                api_key_id=api_key_id,
                snapshot_date=snapshot_date,
                model=model,
                uncached_input_tokens=record.get("uncached_input_tokens", 0),
                cache_read_input_tokens=record.get("cache_read_input_tokens", 0),
                cache_creation_5m_tokens=record.get("cache_creation_5m_tokens", 0),
                cache_creation_1h_tokens=record.get("cache_creation_1h_tokens", 0),
                output_tokens=record.get("output_tokens", 0),
                web_search_requests=record.get("web_search_requests", 0),
                fetched_at=datetime.utcnow(),
            )

            usage_repo.upsert_snapshot(snapshot)
            fetched_count += 1

        logger.info(f"Fetched {fetched_count} usage snapshots for {api_key_id[:10]}...")
        return fetched_count

    except Exception as e:
        logger.error(f"Error fetching usage data for {api_key_id[:10]}...: {e}")
        return 0
    finally:
        if owns_adapter:
            adapter.close_connection()
        await client.close()


async def fetch_usage_data():
    settings = get_settings()

    if not settings.anthropic_admin_api_key:
        logger.warning("No Anthropic Admin API key configured, skipping fetch")
        return

    logger.info("Starting usage data fetch...")

    client = AnthropicAdminClient(settings.anthropic_admin_api_key)
    adapter = PostgreSQLAdapter(
        settings.database_host,
        settings.database_port,
        settings.database_user,
        settings.database_password,
        settings.database_name,
    )

    try:
        dev_repo = DeveloperRepository(adapter)
        usage_repo = UsageSnapshotRepository(adapter)

        registered_api_keys = set(dev_repo.get_all_api_key_ids())

        if not registered_api_keys:
            logger.info("No registered developers, skipping fetch")
            return

        # Use UTC for consistency with Anthropic API
        # Fetch past 7 days to capture historical data (API returns empty for partial days)
        now_utc = datetime.utcnow()
        today_utc = now_utc.date()
        starting_at = datetime.combine(today_utc - timedelta(days=7), datetime.min.time())
        ending_at = datetime.combine(today_utc + timedelta(days=1), datetime.min.time())

        usage_data = await client.get_usage_report(
            starting_at=starting_at,
            ending_at=ending_at,
            group_by=["api_key_id", "model"],
            bucket_width="1h",  # Use hourly to capture today's incomplete data
        )

        if usage_data is None:
            logger.error("Failed to fetch usage data")
            return

        # Aggregate hourly data into daily totals
        daily_records = aggregate_hourly_to_daily(usage_data)
        logger.info(f"Aggregated {len(usage_data)} hourly records into {len(daily_records)} daily records")

        fetched_count = 0
        for record in daily_records:
            api_key_id = record.get("api_key_id")
            if not api_key_id or api_key_id not in registered_api_keys:
                continue

            model = record.get("model", "unknown")
            bucket_date_str = record.get("_bucket_date", str(today_utc))
            snapshot_date = date.fromisoformat(bucket_date_str)

            snapshot = UsageSnapshot(
                api_key_id=api_key_id,
                snapshot_date=snapshot_date,
                model=model,
                uncached_input_tokens=record.get("uncached_input_tokens", 0),
                cache_read_input_tokens=record.get("cache_read_input_tokens", 0),
                cache_creation_5m_tokens=record.get("cache_creation_5m_tokens", 0),
                cache_creation_1h_tokens=record.get("cache_creation_1h_tokens", 0),
                output_tokens=record.get("output_tokens", 0),
                web_search_requests=record.get("web_search_requests", 0),
                fetched_at=datetime.utcnow(),
            )

            usage_repo.upsert_snapshot(snapshot)
            fetched_count += 1

        logger.info(f"Successfully fetched and stored usage data for {fetched_count} developers")

    except Exception as e:
        logger.error(f"Error during usage data fetch: {e}")
    finally:
        adapter.close_connection()
        await client.close()


def start_scheduler(interval_minutes: int = 5):
    scheduler.add_job(
        fetch_usage_data,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="fetch_usage_data",
        name="Fetch usage data from Anthropic Admin API",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started with {interval_minutes}-minute interval")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler stopped")
