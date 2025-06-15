# app/scheduler.py
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from app.services.ingest import process_feed
import logging
logger = logging.getLogger(__name__)

load_dotenv()

FEED_URLS = os.getenv("FEED_URLS", "").split(",")
FEED_URLS = [url.strip() for url in FEED_URLS if url.strip()]
SCHEDULER_INTERVAL_SECONDS = int(os.getenv("INGEST_INTERVAL_SECONDS", "3600"))

if not FEED_URLS:
    logger.warning("No feed URLs configured in FEED_URLS env variable.")

def scheduled_ingest():
    for url in FEED_URLS:
        try:
            logger.info(f"Ingesting {url}")
            process_feed(url)
        except Exception as e:
            logger.exception(f"Error ingesting {url}")

def start_scheduler():
    if not FEED_URLS or SCHEDULER_INTERVAL_SECONDS <= 0:
        logger.warning("Scheduler not started: FEED_URLS is empty or INGEST_INTERVAL_SECONDS is invalid/missing.")
        return

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=scheduled_ingest,
        trigger="interval",
        seconds=SCHEDULER_INTERVAL_SECONDS,
        id="scheduled_feed_ingest",
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Scheduler started: ingesting every {SCHEDULER_INTERVAL_SECONDS} seconds.")

