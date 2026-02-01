import logging
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from rococo.data import PostgreSQLAdapter

from app.config import get_settings, Settings
from app.models import Developer
from app.repositories import DeveloperRepository, UsageSnapshotRepository
from app.services.leaderboard import (
    calculate_leaderboard,
    get_developer_rankings,
    calculate_cache_rate,
)
from app.services.scheduler import fetch_usage_for_api_key
from app.api.schemas import (
    RegisterRequest,
    RegisterResponse,
    DeveloperResponse,
    LeaderboardResponse,
    DeveloperStatsResponse,
    PeriodStats,
    DailyStats,
    HealthResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_adapter():
    settings = get_settings()
    adapter = PostgreSQLAdapter(
        settings.database_host,
        settings.database_port,
        settings.database_user,
        settings.database_password,
        settings.database_name,
    )
    with adapter:
        yield adapter


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="healthy", timestamp=datetime.utcnow())


@router.post("/register", response_model=RegisterResponse)
async def register_developer(
    request: RegisterRequest,
    adapter: PostgreSQLAdapter = Depends(get_adapter),
):
    try:
        dev_repo = DeveloperRepository(adapter)

        existing = dev_repo.get_by_api_key_id(request.api_key_id)
        if existing:
            existing.name = request.name
            developer = dev_repo.save(existing)
        else:
            developer = Developer(
                api_key_id=request.api_key_id,
                name=request.name,
                registered_at=datetime.utcnow(),
            )
            developer = dev_repo.save(developer)

        # Fetch usage data immediately so leaderboard shows data right away
        try:
            fetched_count = await fetch_usage_for_api_key(request.api_key_id)
            logger.info(f"Fetched {fetched_count} usage snapshots on registration for {request.api_key_id[:10]}...")
        except Exception as e:
            # Don't fail registration if usage fetch fails
            logger.warning(f"Failed to fetch usage on registration: {e}")

        return RegisterResponse(
            success=True,
            developer=DeveloperResponse(
                entity_id=str(developer.entity_id),
                api_key_id=developer.api_key_id,
                name=developer.name,
                registered_at=developer.registered_at,
            ),
        )
    except Exception as e:
        return RegisterResponse(success=False, error=str(e))


@router.get("/models")
async def get_available_models(
    adapter: PostgreSQLAdapter = Depends(get_adapter),
):
    """Get list of models that have usage data."""
    usage_repo = UsageSnapshotRepository(adapter)
    models = usage_repo.get_distinct_models()
    return {"models": models}


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    period: str = Query("week", pattern="^(day|week|month)$"),
    api_key_id: Optional[str] = Query(None, description="Current user's API key ID for unmasking"),
    model: Optional[str] = Query(None, description="Filter by model (e.g., claude-sonnet-4-20250514)"),
    adapter: PostgreSQLAdapter = Depends(get_adapter),
):
    dev_repo = DeveloperRepository(adapter)
    usage_repo = UsageSnapshotRepository(adapter)

    categories = calculate_leaderboard(
        usage_repo=usage_repo,
        dev_repo=dev_repo,
        period=period,
        current_user_api_key_id=api_key_id,
        model=model,
    )

    return LeaderboardResponse(
        period=period,
        categories=categories,
        updated_at=datetime.utcnow(),
        model=model,
    )


@router.get("/developer/{api_key_id}/stats", response_model=DeveloperStatsResponse)
async def get_developer_stats(
    api_key_id: str,
    model: Optional[str] = Query(None, description="Filter by model (e.g., claude-sonnet-4-20250514)"),
    adapter: PostgreSQLAdapter = Depends(get_adapter),
):
    dev_repo = DeveloperRepository(adapter)
    usage_repo = UsageSnapshotRepository(adapter)

    developer = dev_repo.get_by_api_key_id(api_key_id)
    if not developer:
        raise HTTPException(status_code=404, detail="Developer not found")

    history = usage_repo.get_developer_history(api_key_id, days=30, model=model)

    daily_history = []
    for snapshot in history:
        total_tokens = (
            snapshot.uncached_input_tokens
            + snapshot.cache_read_input_tokens
            + snapshot.output_tokens
        )
        cache_rate = calculate_cache_rate(
            snapshot.cache_read_input_tokens,
            snapshot.uncached_input_tokens,
        )
        daily_history.append(DailyStats(
            date=snapshot.snapshot_date,
            total_tokens=total_tokens,
            uncached_input_tokens=snapshot.uncached_input_tokens,
            cache_read_input_tokens=snapshot.cache_read_input_tokens,
            output_tokens=snapshot.output_tokens,
            cache_rate=cache_rate,
            web_search_requests=snapshot.web_search_requests,
        ))

    def calculate_period_stats(days: int) -> PeriodStats:
        today = date.today()
        start_date = today - timedelta(days=days)
        period_snapshots = [s for s in history if s.snapshot_date >= start_date]

        total_uncached = sum(s.uncached_input_tokens for s in period_snapshots)
        total_cache_read = sum(s.cache_read_input_tokens for s in period_snapshots)
        total_output = sum(s.output_tokens for s in period_snapshots)
        total_web_search = sum(s.web_search_requests for s in period_snapshots)

        return PeriodStats(
            total_tokens=total_uncached + total_cache_read + total_output,
            uncached_input_tokens=total_uncached,
            cache_read_input_tokens=total_cache_read,
            output_tokens=total_output,
            cache_rate=calculate_cache_rate(total_cache_read, total_uncached),
            web_search_requests=total_web_search,
        )

    current_period = {
        "day": calculate_period_stats(1),
        "week": calculate_period_stats(7),
        "month": calculate_period_stats(30),
    }

    rankings = get_developer_rankings(usage_repo, dev_repo, api_key_id, "week", model=model)

    return DeveloperStatsResponse(
        api_key_id=api_key_id,
        name=developer.name,
        current_period=current_period,
        daily_history=daily_history,
        rankings=rankings,
        model=model,
    )
