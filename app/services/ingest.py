import feedparser
from bs4 import BeautifulSoup
import nltk
from sentence_transformers import SentenceTransformer, util
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from typing import List, Optional, Any, Tuple
import re
from fastapi import HTTPException

from sqlmodel import Session, select
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from app.db.models import Post, Theme
from app.db.database import engine
import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

nltk.download("punkt_tab", quiet=True)

_model = SentenceTransformer("all-MiniLM-L6-v2")

# Constants for processing logic
MAX_SENTENCES = 2
SIMILARITY_THRESHOLD = 0.60
THEME_MATCH_THRESHOLD = float(os.getenv("THEME_MATCH_THRESHOLD", "0.60"))


@dataclass
class PostCandidate:
    """
    Represents a candidate post during ingestion, including title, content, embedding, and matched theme.
    """
    title: str
    url: str
    published: datetime
    thesis: str
    content: str
    embedding: Any
    theme_id: Optional[int] = None


class PostOut(BaseModel):
    """
    Schema for a single processed post returned from ingestion.
    """
    title: str
    url: str
    published: str
    thesis: List[str]
    content: str


class FeedIngestResponse(BaseModel):
    """
    Response schema for an ingested feed.
    """
    feed_title: str
    post_count: int
    posts: List[PostOut]


def _extract_thesis(text: str) -> list[str]:
    """
    Extracts the key thesis sentence(s) from the input text using sentence transformers and similarity checks.
    Returns up to MAX_SENTENCES (2), or 1 if the two sentences have similarity above SIMILARITY_THRESHOLD (0.6).
    """
    sentences = nltk.sent_tokenize(text)
    if not sentences:
        return []

    if len(sentences) <= MAX_SENTENCES:
        if len(sentences) == MAX_SENTENCES:
            sim = util.cos_sim(
                _model.encode(sentences[0], convert_to_tensor=True, show_progress_bar=False),
                _model.encode(sentences[1], convert_to_tensor=True, show_progress_bar=False),
            ).item()
            if sim > SIMILARITY_THRESHOLD:
                return [sentences[0]]
        return sentences

    doc_emb = _model.encode(text, convert_to_tensor=True, show_progress_bar=False)
    sent_embs = _model.encode(sentences, convert_to_tensor=True, show_progress_bar=False)
    sims = util.cos_sim(doc_emb, sent_embs)[0].cpu().numpy()
    top_idxs = np.argsort(-sims)[:MAX_SENTENCES].tolist()
    picks = [sentences[i] for i in top_idxs]

    if len(picks) == MAX_SENTENCES:
        sim = util.cos_sim(
            _model.encode(picks[0], convert_to_tensor=True, show_progress_bar=False),
            _model.encode(picks[1], convert_to_tensor=True, show_progress_bar=False),
        ).item()
        if sim > SIMILARITY_THRESHOLD:
            return [picks[0]]

    return picks


def _extract_main_text(entry: dict) -> str:
    """
    Extracts readable text content from an RSS entry. Falls back to summary or title if content is missing.
    """
    html = ""
    if "content" in entry and entry["content"]:
        html = entry["content"][0].get("value", "")
    if html == "" and "summary" in entry:
        html = entry.summary
    if html == "":
        return entry.get("title", "")
    soup = BeautifulSoup(html, "html.parser")
    return re.sub(r'\s+', ' ', soup.get_text(separator=" ", strip=True))


def _parse_date(entry) -> datetime:
    """
    Extracts the published date from an RSS entry. Falls back to current UTC time if none found.
    """
    if "published_parsed" in entry and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    if "updated_parsed" in entry and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.utcnow()


def _generate_embedding(title: str, thesis: str):
    """
    Combines the title and thesis and returns a sentence embedding.
    """
    return _model.encode(f"{title}. {thesis}", convert_to_tensor=True, show_progress_bar=False)


def _match_theme(cand_emb, embeddings):
    """
    Matches a candidate post against a list of embeddings to find the most similar theme.
    Returns the best theme_id and its similarity score.
    """
    best_theme = None
    best_score = 0.0
    for emb, theme_id in embeddings:
        sim = util.cos_sim(cand_emb, emb).item()
        if sim > best_score:
            best_score = sim
            best_theme = theme_id
    return best_theme, best_score


def process_feed(feed_url: str) -> FeedIngestResponse:
    """
    Parses and ingests an RSS feed, extracts thesis sentences from each post, assigns themes using embeddings,
    and stores results in the database. Returns a structured summary of all processed posts.
    """
    logger.info(f"Processing feed: {feed_url}")
    try:
        parsed = feedparser.parse(feed_url)
    except Exception as e:
        logger.error(f"Feed parsing failed: {e}")
        raise HTTPException(status_code=400, detail="Unable to parse feed URL.")

    if parsed.bozo:
        logger.error(f"Feedparser bozo error: {parsed.bozo_exception}")
        raise HTTPException(status_code=422, detail="Invalid or unreadable feed format.")

    if not parsed.entries:
        logger.info(f"No entries found in feed: {feed_url}")
        return {
            "feed_title": parsed.feed.get("title", ""),
            "post_count": 0,
            "posts": []
        }
    posts: List[dict] = []

    with Session(engine) as session:
        existing_posts = session.exec(select(Post.title, Post.thesis, Post.theme_id)).all()
        existing_embeddings = [
            (_generate_embedding(title, thesis), theme_id)
            for title, thesis, theme_id in existing_posts
        ]

        existing_keys = set(
            session.exec(select(Post.url, Post.published_at, Post.title)).all()
        )
        seen_keys = set(existing_keys)

        candidates = []
        for entry in parsed.entries:
            title = entry.get("title", "")
            post_url = entry.get("link")
            content = _extract_main_text(entry)
            published_at = _parse_date(entry)
            key = (post_url, published_at, title)
            if key in seen_keys:
                continue
            seen_keys.add(key)
            thesis_sentences = _extract_thesis(content)
            if not thesis_sentences:
                continue
            full_thesis = " ".join(thesis_sentences)
            emb = _generate_embedding(title, full_thesis)

            candidates.append(PostCandidate(
                title=title,
                url=post_url,
                published=published_at,
                thesis=full_thesis,
                content=content,
                embedding=emb
            ))

        new_embeddings: List[Tuple[Any, int]] = []
        for cand in candidates:
            found_theme = None
            best_theme, best_score = _match_theme(cand.embedding, existing_embeddings + new_embeddings)

            if best_score >= THEME_MATCH_THRESHOLD:
                found_theme = best_theme
            else:
                new_theme = Theme()
                session.add(new_theme)
                session.commit()
                session.refresh(new_theme)
                found_theme = new_theme.id

            cand.theme_id = found_theme
            new_embeddings.append((cand.embedding, found_theme))

        for cand in candidates:
            try:
                session.add(Post(
                    title=cand.title,
                    url=cand.url,
                    published_at=cand.published,
                    thesis=cand.thesis,
                    theme_id=cand.theme_id,
                ))
                posts.append({
                    "title": cand.title,
                    "url": cand.url,
                    "published": cand.published.isoformat(),
                    "thesis": [cand.thesis],
                    "content": cand.content
                })
            except IntegrityError:
                session.rollback()
                logger.warning(f"Skipped duplicate post possibly due to race condition: {cand.url} @ {cand.published} [{cand.title}]")

        session.commit()
        logger.info(f"Inserted {len(posts)} new posts from feed: {feed_url}")

    return FeedIngestResponse(
        feed_title=parsed.feed.get("title", ""),
        post_count=len(posts),
        posts=posts
    )
