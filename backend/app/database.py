from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import get_settings

settings = get_settings()

_is_sqlite = "sqlite" in settings.database_url

engine = create_engine(
    settings.database_url,
    # SQLite requires this flag; PostgreSQL doesn't accept it
    connect_args={"check_same_thread": False} if _is_sqlite else {},
    # Connection pool settings (ignored by SQLite, important for PostgreSQL)
    pool_size=5,
    max_overflow=10,
    # Verify connections before using — transparently reconnects after DB
    # maintenance restarts (critical for Azure Database for PostgreSQL)
    pool_pre_ping=True,
    # SQLite doesn't support pool_size/max_overflow with StaticPool
    **({} if _is_sqlite else {}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    from app.models import user, health_data, lab_test, integration  # noqa
    Base.metadata.create_all(bind=engine)
