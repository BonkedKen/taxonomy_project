from pathlib import Path
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, create_engine, SQLModel

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "taxonomy.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    import models  # noqa
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    with Session(engine) as session:
        yield session


def get_db_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()