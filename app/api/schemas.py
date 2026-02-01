from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date


class RegisterRequest(BaseModel):
    api_key_id: str = Field(..., min_length=1, description="Anthropic API key ID")
    name: str = Field(..., min_length=1, max_length=100, description="Developer display name")


class DeveloperResponse(BaseModel):
    entity_id: str
    api_key_id: str
    name: str
    registered_at: datetime


class RegisterResponse(BaseModel):
    success: bool
    developer: Optional[DeveloperResponse] = None
    error: Optional[str] = None


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    api_key_id: str
    value: float
    is_self: bool


class LeaderboardResponse(BaseModel):
    period: str
    categories: Dict[str, List[LeaderboardEntry]]
    updated_at: datetime
    model: Optional[str] = None


class DailyStats(BaseModel):
    date: date
    total_tokens: int
    uncached_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    cache_rate: float
    web_search_requests: int


class PeriodStats(BaseModel):
    total_tokens: int
    uncached_input_tokens: int
    cache_read_input_tokens: int
    output_tokens: int
    cache_rate: float
    web_search_requests: int


class DeveloperStatsResponse(BaseModel):
    api_key_id: str
    name: str
    current_period: Dict[str, PeriodStats]
    daily_history: List[DailyStats]
    rankings: Dict[str, int]
    model: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
