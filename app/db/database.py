import os
from sqlmodel import SQLModel, create_engine, Session
import logging
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/data.db")

connect_args = (
    {"check_same_thread": False}
    if DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)

def init_db() -> None:
    """
    Create all tables. Call this once at application startup.
    """
    try:
        from app.db.models import Theme, Post
        SQLModel.metadata.create_all(engine)
        logger.info("Database tables created.")
    except Exception as e:
        logger.exception("Failed to create database tables.")
        raise
