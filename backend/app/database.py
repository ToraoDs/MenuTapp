from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


BASE_DIR = settings.base_dir
DATABASE_URL = settings.database_url

connect_args = (
    {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


@event.listens_for(engine, "connect")
def configurar_sqlite(dbapi_connection, _connection_record):
    if not DATABASE_URL.startswith("sqlite"):
        return

    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    if settings.sqlite_busy_timeout_ms > 0:
        cursor.execute(f"PRAGMA busy_timeout={settings.sqlite_busy_timeout_ms}")
    if settings.sqlite_wal and ":memory:" not in DATABASE_URL:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def sesion_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
