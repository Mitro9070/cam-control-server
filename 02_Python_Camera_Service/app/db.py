from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


engine_kwargs: dict = {"pool_pre_ping": True}
if settings.sqlalchemy_url.startswith("postgresql"):
    # Keep DB outages from blocking API handlers for tens of seconds.
    engine_kwargs.update(
        {
            "pool_timeout": 3,
            "connect_args": {"connect_timeout": 3},
        }
    )

engine = create_engine(settings.sqlalchemy_url, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
