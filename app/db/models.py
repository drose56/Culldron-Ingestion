from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Theme(SQLModel, table=True):
    """
    A theme is just an auto-incrementing ID and the time it was created.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Post(SQLModel, table=True):
    """
    Each thesis links to a theme and stores metadata about the post it came from.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    theme_id: int = Field(foreign_key="theme.id", index=True)
    post_title: str
    post_url: str
    published_at: datetime
    ingested_at: datetime = Field(default_factory=datetime.utcnow)
    thesis: str
