from typing import Dict, List, Optional
from datetime import date, timedelta
from collections import defaultdict
from app.models import UsageSnapshot, Developer
from app.repositories import UsageSnapshotRepository, DeveloperRepository


def mask_api_key(api_key_id: str) -> str:
    if len(api_key_id) <= 8:
        return api_key_id[:2] + "..." + api_key_id[-2:]
    return api_key_id[:4] + "..." + api_key_id[-2:]


def calculate_cache_rate(cache_read: int, uncached_input: int) -> float:
    total_input = cache_read + uncached_input
    if total_input == 0:
        return 0.0
    return round((cache_read / total_input) * 100, 2)


def aggregate_snapshots(snapshots: List[UsageSnapshot]) -> Dict[str, Dict]:
    aggregated = defaultdict(lambda: {
        "uncached_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_5m_tokens": 0,
        "cache_creation_1h_tokens": 0,
        "output_tokens": 0,
        "web_search_requests": 0,
    })

    for snapshot in snapshots:
        agg = aggregated[snapshot.api_key_id]
        agg["uncached_input_tokens"] += snapshot.uncached_input_tokens
        agg["cache_read_input_tokens"] += snapshot.cache_read_input_tokens
        agg["cache_creation_5m_tokens"] += snapshot.cache_creation_5m_tokens
        agg["cache_creation_1h_tokens"] += snapshot.cache_creation_1h_tokens
        agg["output_tokens"] += snapshot.output_tokens
        agg["web_search_requests"] += snapshot.web_search_requests

    return aggregated


def calculate_leaderboard(
    usage_repo: UsageSnapshotRepository,
    dev_repo: DeveloperRepository,
    period: str,
    current_user_api_key_id: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, List[Dict]]:
    today = date.today()

    if period == "day":
        start_date = today
    elif period == "week":
        start_date = today - timedelta(days=7)
    else:  # month
        start_date = today - timedelta(days=30)

    snapshots = usage_repo.get_snapshots_for_period(start_date, today, model=model)
    aggregated = aggregate_snapshots(snapshots)

    developers = {dev.api_key_id: dev for dev in dev_repo.get_all_active()}

    categories = {
        "efficient_user": [],
        "cache_champion": [],
        "wordsmith": [],
        "tool_master": [],
    }

    for api_key_id, data in aggregated.items():
        total_input = data["uncached_input_tokens"] + data["cache_read_input_tokens"]
        efficiency = round((data["output_tokens"] / total_input) * 100, 2) if total_input > 0 else 0
        cache_rate = calculate_cache_rate(
            data["cache_read_input_tokens"],
            data["uncached_input_tokens"]
        )

        dev = developers.get(api_key_id)
        is_self = api_key_id == current_user_api_key_id
        display_name = dev.name if (dev and is_self) else mask_api_key(api_key_id)

        # Mask api_key_id for privacy - only show full ID to self
        masked_api_key = api_key_id if is_self else mask_api_key(api_key_id)

        base_entry = {
            "api_key_id": masked_api_key,
            "display_name": display_name,
            "is_self": is_self,
        }

        categories["efficient_user"].append({**base_entry, "value": efficiency})
        categories["cache_champion"].append({**base_entry, "value": cache_rate})
        categories["wordsmith"].append({**base_entry, "value": data["output_tokens"]})
        categories["tool_master"].append({**base_entry, "value": data["web_search_requests"]})

    for category in categories:
        categories[category].sort(key=lambda x: x["value"], reverse=True)
        for rank, entry in enumerate(categories[category], 1):
            entry["rank"] = rank

    return categories


def get_developer_rankings(
    usage_repo: UsageSnapshotRepository,
    dev_repo: DeveloperRepository,
    api_key_id: str,
    period: str = "week",
    model: Optional[str] = None,
) -> Dict[str, int]:
    # Pass api_key_id as current_user so their entry won't be masked
    leaderboard = calculate_leaderboard(usage_repo, dev_repo, period, current_user_api_key_id=api_key_id, model=model)
    rankings = {}

    for category, entries in leaderboard.items():
        for entry in entries:
            if entry["is_self"]:
                rankings[category] = entry["rank"]
                break
        if category not in rankings:
            rankings[category] = 0

    return rankings
