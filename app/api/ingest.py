import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.ingest import process_feed, FeedIngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()

class IngestRequest(BaseModel):
    url: str

@router.post(
    "/",
    response_model=FeedIngestResponse,
    status_code=201,
    tags=["Ingest"],
    summary="Ingest RSS feed"
)

def ingest_feed(request: IngestRequest):
    """
    Ingest and process an RSS feed by URL
    """
    logger.info(f"Received ingest request for URL: {request.url}")
    try:
        result = process_feed(request.url)
        logger.info(f"Ingest successful: {request.url} -> {result.post_count} posts")
        return result
    except Exception as e:
        logger.exception(f"Ingest failed for URL: {request.url}")
        raise HTTPException(status_code=500, detail=f"Failed to parse feed: {e}")
