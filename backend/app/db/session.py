from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite fallback — swap this one line for the PostGIS URL later, nothing else changes
SQLALCHEMY_DATABASE_URL = "sqlite:///./bhudrishti_fallback.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False
    },  # SQLite-only quirk, harmless to leave in
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
