from fastapi import FastAPI
from app.api.ingest import router as ingest_router
from app.db.database import init_db
from app.services.scheduler import start_scheduler
from apscheduler.schedulers.background import BackgroundScheduler

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Culldron Insight Extractor")

@app.on_event("startup")
def on_startup():
    try:
        init_db()
        logger.info("Database initialized.")
    except Exception as e:
        logger.exception("Failed to initialize database.")

    try:
        start_scheduler()
        logger.info("Scheduler started.")
    except Exception as e:
        logger.exception("Failed to start scheduler.")

@app.get("/")
def root():
    return {"message": "Culldron Insight Extractor is running."}

app.include_router(ingest_router, prefix="/ingest", tags=["Ingest"])
