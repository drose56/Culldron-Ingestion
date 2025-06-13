from fastapi import APIRouter, HTTPException, Query
from sqlmodel import Session, select, func
from app.db.models import Theme, Post
from app.db.database import engine
from pydantic import BaseModel
from typing import List

router = APIRouter()

class ThemeSummary(BaseModel):
    id: int
    post_count: int

class ThemePost(BaseModel):
    title: str
    url: str
    published_at: str
    ingested_at: str
    thesis: str

@router.get("/themes", response_model=List[ThemeSummary])
def list_themes(
    limit: int = Query(10000, description="Max number of results to return (pagination placeholder)"),
    offset: int = Query(0, description="Number of results to skip (pagination placeholder)")
): # Boilerplate limit/offset for future pagination
    with Session(engine) as session:
        results = session.exec(
            select(Post.theme_id, func.count())
            .group_by(Post.theme_id)
            .order_by(func.count().desc())
        ).all()
        return [{"id": theme_id, "post_count": count} for theme_id, count in results]


@router.get("/themes/{theme_id}", response_model=List[ThemePost])
def get_theme_timeline(
    theme_id: int,
    limit: int = Query(1000, description="Max number of posts to return (pagination placeholder)"),
    offset: int = Query(0, description="Number of posts to skip (pagination placeholder)")
): # Boilerplate limit/offset for future pagination
    with Session(engine) as session:
        posts = session.exec(
            select(Post)
            .where(Post.theme_id == theme_id)
            .order_by(Post.published_at)
        ).all()

        if not posts:
            raise HTTPException(status_code=404, detail="Theme not found")

        return [
            ThemePost(
                title=p.title,
                url=p.url,
                published_at=p.published_at.isoformat(),
                ingested_at=p.ingested_at.isoformat(),
                thesis=p.thesis
            )
            for p in posts
        ]
