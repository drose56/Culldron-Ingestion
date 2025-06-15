from fastapi import FastAPI
from app.api.ingest import router as ingest_router
from app.db.database import init_db
from app.services.scheduler import start_scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from app.api.themes import router as themes_router
import atexit
import multiprocessing.util

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Culldron Insight Extractor")

@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized.")
    start_scheduler()

@atexit.register
def cleanup_multiprocessing():
    try:
        multiprocessing.util._cleanup()
    except Exception:
        pass

@app.get("/")
def root():
    return {"message": "Culldron Insight Extractor is running."}

app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])

app.include_router(themes_router, tags=["Themes"])

