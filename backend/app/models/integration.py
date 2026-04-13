from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Integration(Base):
    __tablename__ = "integrations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    platform = Column(String, nullable=False)  # whoop, withings, fitbod, yazio, renpho, braun, larq
    is_connected = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    # OAuth tokens
    access_token = Column(Text)
    refresh_token = Column(Text)
    token_expires_at = Column(DateTime(timezone=True))
    token_scope = Column(String)

    # Platform-specific user info
    platform_user_id = Column(String)
    platform_username = Column(String)

    # Sync settings
    last_synced_at = Column(DateTime(timezone=True))
    sync_from_date = Column(DateTime(timezone=True))
    auto_sync = Column(Boolean, default=True)

    # Credentials for platforms without OAuth (e.g., Renpho)
    credentials = Column(JSON)  # stored encrypted

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="integrations")
    sync_logs = relationship("SyncLog", back_populates="integration", cascade="all, delete-orphan")


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(Integer, ForeignKey("integrations.id"), nullable=False)

    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    status = Column(String, default="running")  # running, success, failed
    records_synced = Column(Integer, default=0)
    error_message = Column(Text)
    details = Column(JSON)

    integration = relationship("Integration", back_populates="sync_logs")
