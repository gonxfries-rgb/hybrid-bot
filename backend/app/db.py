from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from .config import settings


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if not database_url.startswith('sqlite:///'):
        return
    db_path = database_url.replace('sqlite:///', '', 1)
    parent = Path(db_path).expanduser().resolve().parent
    parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_parent_dir(settings.database_url)
connect_args = {'check_same_thread': False} if settings.database_url.startswith('sqlite') else {}
engine = create_engine(settings.database_url, connect_args=connect_args)


def init_db() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
