"""
Database engine and session management with seamless PostGIS / SQLite fallback.
"""

import logging
import socket
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger("bhudrishti.db")

SQLITE_FALLBACK_URL = "sqlite:///./bhudrishti_fallback.db"


def _create_database_engine():
    target_url = settings.DATABASE_URL or SQLITE_FALLBACK_URL

    # Normalize async driver to sync driver for SQLAlchemy standard session
    if target_url.startswith("postgresql+asyncpg://"):
        target_url = target_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    if "sqlite" not in target_url:
        try:
            parsed = urlparse(target_url)
            host = parsed.hostname
            port = parsed.port or 5432
            # Quick 0.3s socket probe so unreachable container hosts don't block tests/startup
            if host:
                s = socket.create_connection((host, port), timeout=0.3)
                s.close()

            candidate_engine = create_engine(
                target_url,
                pool_pre_ping=True,
                connect_args={"connect_timeout": 2} if "postgres" in target_url else {},
            )
            with candidate_engine.connect() as conn:
                conn.execute("SELECT 1")
            logger.info("Connected to PostGIS/PostgreSQL database successfully.")
            return candidate_engine
        except Exception as exc:
            logger.info(
                f"PostgreSQL at {target_url} not reachable: {exc}. "
                f"Active on SQLite + GeoPandas fallback ({SQLITE_FALLBACK_URL})."
            )

    # SQLite fallback engine
    return create_engine(
        SQLITE_FALLBACK_URL,
        connect_args={"check_same_thread": False},
    )


engine = _create_database_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for obtaining transactional SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
