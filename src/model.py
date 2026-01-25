"""SQLAlchemy models for awesome-audio database."""

from pathlib import Path
from typing import Optional

from sqlalchemy import Column, Date, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base

Base = declarative_base()

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent / "awesome-audio.db"


def get_engine(db_path: Optional[Path] = None, echo: bool = False):
    """Create a SQLAlchemy engine for the given database path."""
    path = db_path or DEFAULT_DB_PATH
    return create_engine(f"sqlite:///{path}", echo=echo)


class Entry(Base):
    """An entry in the awesome-audio list."""

    __tablename__ = "entry"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    category = Column(String, nullable=False)
    url = Column(String, nullable=True)
    repo = Column(String, nullable=True)
    description = Column(String, nullable=False)
    keywords = Column(String, nullable=True)
    last_updated = Column(Date, nullable=True)
    last_checked = Column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<Entry(name='{self.name}', category='{self.category}')>"

    def to_dict(self) -> dict:
        """Convert entry to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "url": self.url,
            "repo": self.repo,
            "description": self.description,
            "keywords": self.keywords,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
        }


def init_db(db_path: Optional[Path] = None, echo: bool = False) -> Session:
    """Initialize the database and return a session."""
    engine = get_engine(db_path, echo)
    Base.metadata.create_all(engine)
    return Session(engine)


def get_session(db_path: Optional[Path] = None) -> Session:
    """Get a session for the database."""
    engine = get_engine(db_path)
    return Session(engine)
