from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IntegrationResponse(BaseModel):
    id: int
    platform: str
    is_connected: bool
    is_active: bool
    platform_username: Optional[str]
    last_synced_at: Optional[datetime]
    auto_sync: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrationStatus(BaseModel):
    platform: str
    is_connected: bool
    is_active: bool
    platform_username: Optional[str]
    last_synced_at: Optional[datetime]
    auto_sync: bool
    auth_url: Optional[str] = None  # URL to start OAuth flow
