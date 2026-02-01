from typing import Optional, List
from rococo.repositories.postgresql import PostgreSQLRepository
from rococo.data import PostgreSQLAdapter
from app.models import Developer


class DeveloperRepository(PostgreSQLRepository):
    def __init__(self, adapter: PostgreSQLAdapter):
        super().__init__(adapter, Developer, None, None)

    def get_by_api_key_id(self, api_key_id: str) -> Optional[Developer]:
        results = self.get_many({"api_key_id": api_key_id, "active": True})
        return results[0] if results else None

    def get_all_active(self) -> List[Developer]:
        return self.get_many({"active": True})

    def get_all_api_key_ids(self) -> List[str]:
        developers = self.get_all_active()
        return [dev.api_key_id for dev in developers]
