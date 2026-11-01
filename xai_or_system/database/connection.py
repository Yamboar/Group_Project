import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

_engine = None
_SessionFactory = None


def get_database_url() -> str:
    """Construct database URL from environment variables."""
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "xai_or_system")
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"


def get_engine():
    """Get or create the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(url, echo=False, pool_pre_ping=True)
    return _engine


def get_session_factory():
    """Get or create the session factory."""
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory


def get_session():
    """Create a new database session."""
    factory = get_session_factory()
    return factory()


def init_database():
    """Create all tables in the database."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def close_session(session):
    """Close a database session safely."""
    try:
        session.close()
    except Exception:
        pass
