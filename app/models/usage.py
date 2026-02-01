from dataclasses import dataclass, field
from datetime import datetime, date
from rococo.models import BaseModel


@dataclass(kw_only=True)
class UsageSnapshot(BaseModel):
    api_key_id: str = ""
    snapshot_date: date = field(default_factory=date.today)
    model: str = "unknown"
    uncached_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_5m_tokens: int = 0
    cache_creation_1h_tokens: int = 0
    output_tokens: int = 0
    web_search_requests: int = 0
    fetched_at: datetime = field(default_factory=datetime.utcnow)
