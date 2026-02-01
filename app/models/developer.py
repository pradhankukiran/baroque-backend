from dataclasses import dataclass, field
from datetime import datetime
from rococo.models import VersionedModel


@dataclass(kw_only=True)
class Developer(VersionedModel):
    api_key_id: str = ""
    name: str = ""
    registered_at: datetime = field(default_factory=datetime.utcnow)
