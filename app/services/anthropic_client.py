import httpx
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AnthropicAdminClient:
    BASE_URL = "https://api.anthropic.com/v1"

    def __init__(self, admin_api_key: str):
        self.admin_api_key = admin_api_key
        self.client = httpx.AsyncClient(
            headers={
                "x-api-key": admin_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=30.0,
        )

    async def get_usage_report(
        self,
        starting_at: datetime,
        ending_at: datetime,
        group_by: List[str] = None,
        bucket_width: str = "1d",
    ) -> Optional[List[Dict[str, Any]]]:
        if group_by is None:
            group_by = ["api_key_id"]

        url = f"{self.BASE_URL}/organizations/usage_report/messages"
        # Build params as list of tuples for proper array parameter handling
        params = [
            ("starting_at", starting_at.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("ending_at", ending_at.strftime("%Y-%m-%dT%H:%M:%SZ")),
            ("bucket_width", bucket_width),
        ]
        # API requires group_by[] for array parameters
        for gb in group_by:
            params.append(("group_by[]", gb))

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # API returns buckets with nested results, flatten them
            buckets = data.get("data", [])
            all_results = []
            for bucket in buckets:
                results = bucket.get("results", [])
                all_results.extend(results)
            return all_results
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching usage report: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error fetching usage report: {e}")
            return None

    async def close(self):
        await self.client.aclose()
