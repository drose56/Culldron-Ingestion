# Culldron Insight Extractor

This is a lightweight NLP-powered service that ingests RSS feeds, extracts key thesis statements from each post, and groups similar ones into recurring “themes” of discourse. Built as part of the Culldron founding engineer take-home challenge.

---

## Features

- **Scheduled + Manual Ingestion**  
  RSS feeds can be ingested on a schedule (via `.env`) or on demand via `POST /ingest`.

- **NLP Thesis Extraction**  
  Extracts the most important 1 or 2 sentences (depending on the similarity of the top 2 sentences) from each post using `sentence-transformers` (`all-MiniLM-L6-v2`). If no thesis can be extracted, the post is skipped.

- **Theme Clustering by Similarity**  
  Posts are grouped by cosine similarity of their `[title] + [thesis]` embeddings. Posts with similarity ≥ `THEME_MATCH_THRESHOLD` (configurable via .env, default 0.60) are assigned to an existing theme; otherwise a new theme is created.

- **Deduplication & Idempotency**  
  Posts are uniquely identified by `(url, title, published date)` to avoid re-insertion. This guards against duplicates even if the scheduler and API ingest the same feed at the same time.

- **Simple Read API**  
  - `GET /themes`: lists all themes with post counts (sorted by count)
  - `GET /themes/{id}`: timeline of posts in a theme (sorted by published date)

- **Auto-generated API docs** at  
   [`http://localhost:8000/docs#/`](http://localhost:8000/docs#/)

---

## Tech Stack

| Component        | Implementation                   |
|------------------|-----------------------------------|
| Language         | Python 3.11                       |
| Framework        | FastAPI                          |
| NLP              | SentenceTransformers              |
| Database         | SQLite via SQLModel              |
| Scheduler        | APScheduler                      |
| Containerization | Docker        

---

## Quick Start

1. **Clone the repo**

```bash
git clone https://github.com/drose56/Culldron-Ingestion.git
cd Culldron-Ingestion
```

2. **Create a .env file**
```bash
cp .env.example .env
```

3. **Run the service**
```bash
docker-compose up
```
App will be available at: http://localhost:8000

## How It Works

- For each post, the main content is cleaned, tokenized, and the most representative 1–2 sentences are selected.

- The thesis is embedded along with the title to improve clustering accuracy.

- Embeddings are compared with prior posts to detect and reuse existing themes.


## Design Notes
- Posts with no valid thesis are excluded from the database.

- Race conditions (e.g., scheduler + Ingester API processing same feed at the same time) are handled via database-level uniqueness to ensure no duplicates.

- Embeddings are recomputed at runtime for simplicity; in a real system you'd persist them or use a vector database.

## Potential future improvements:

Persist and reuse embeddings

Use pgvector or other vector search backend

Store data on the feed such as last-seen timestamp to immediately skip unmodified content

Add tests and auth support

# License
MIT
