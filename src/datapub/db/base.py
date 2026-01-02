import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


# Prefer dedicated app database URL, fall back to generic DATABASE_URL
DATABASE_URL = os.getenv(
    "APP_DATABASE_URL",
    os.getenv(
        "DATABASE_URL",
        # Fallback to env components (prefer APP_DB_*, then DB_*)
        f"postgresql+psycopg://{os.getenv('APP_DB_USERNAME', os.getenv('DB_USERNAME','cognee'))}:{os.getenv('APP_DB_PASSWORD', os.getenv('DB_PASSWORD','cognee'))}@{os.getenv('APP_DB_HOST', os.getenv('DB_HOST','postgres'))}:{os.getenv('APP_DB_PORT', os.getenv('DB_PORT','5432'))}/{os.getenv('APP_DB_NAME', os.getenv('DB_NAME','datapub_db'))}",
    ),
)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


@contextmanager
def session_scope() -> Iterator:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
