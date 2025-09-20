import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    # Fallback to env components
    f"postgresql+psycopg://{os.getenv('DB_USERNAME','cognee')}:{os.getenv('DB_PASSWORD','cognee')}@{os.getenv('DB_HOST','postgres')}:{os.getenv('DB_PORT','5432')}/{os.getenv('DB_NAME','cognee_db')}",
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

