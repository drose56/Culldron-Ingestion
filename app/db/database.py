import os
from sqlmodel import SQLModel, create_engine, Session

# 1) Read the DB URL from env, default to a local file
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data.db")

# 2) SQLite needs this arg to allow multiple threads
connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

# 3) Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=True, connect_args=connect_args)


def init_db() -> None:
    """
    Create all tables.  Call this once at application startup.
    """
    from app.db.models import Theme, Post
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    FastAPI dependency to yield a database session.
    Use it like:
        @app.post(...)
        def ingest(..., session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session
