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
    _apply_migrations(engine)


def _apply_migrations(engine):
    """Idempotently apply lightweight schema migrations for existing tables."""
    try:
        import logging
        from sqlalchemy import inspect, text

        def _column_missing(table: str, column: str) -> bool:
            cols = {c["name"] for c in inspect(engine).get_columns(table)}
            return column not in cols

        inspector = inspect(engine)
        with engine.begin() as conn:
            # transportation_problems.restricted_cells (restricted route state)
            if inspector.has_table("transportation_problems"):
                if _column_missing("transportation_problems", "restricted_cells"):
                    conn.execute(text(
                        "ALTER TABLE transportation_problems "
                        "ADD COLUMN restricted_cells JSON NULL"
                    ))
                    logging.getLogger("database.connection").warning(
                        "applied migration: transportation_problems.restricted_cells"
                    )
            # assignment_problems.restricted_cells (restricted worker-job state)
            if inspector.has_table("assignment_problems"):
                if _column_missing("assignment_problems", "restricted_cells"):
                    conn.execute(text(
                        "ALTER TABLE assignment_problems "
                        "ADD COLUMN restricted_cells JSON NULL"
                    ))
                    logging.getLogger("database.connection").warning(
                        "applied migration: assignment_problems.restricted_cells"
                    )
    except Exception:
        # Migrations are best-effort; a running app must not crash on them.
        import logging
        logging.getLogger("database.connection").exception(
            "schema migration failed (continuing without it)"
        )


def close_session(session):
    """Close a database session safely."""
    try:
        session.close()
    except Exception:
        pass
