"""Incremental load of English Steam reviews for Elden Ring.

How it works:
- Steam returns reviews newest-updated first (filter=updated), 100 per page,
  with a cursor for the next page.
- The high-water mark is the highest timestamp_updated of the last successful
  run. We page until a whole page is older than the mark (the order is only
  roughly sorted, so one old review is not enough to stop).
- Every page is saved as a raw file and upserted into raw.reviews, then
  sql/staging/reviews.sql updates staging.reviews.
- Each run is logged in raw.ingestion_runs. Only a successful full run moves
  the mark, so after a crash the next run fetches the same range again and the
  upserts remove the duplicates.

Usage:
    python -m ingestion.load_reviews                      # incremental (first run = full backfill)
    python -m ingestion.load_reviews --since 2026-10-01   # backfill everything updated since a date
    python -m ingestion.load_reviews --full               # reload all reviews
    python -m ingestion.load_reviews --max-pages 3        # test run, does not move the mark
"""

import argparse
import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from ingestion.db import connect

URL = "https://store.steampowered.com/appreviews/{app_id}?{query}"
STAGING_SQL = Path(__file__).parent.parent / "sql" / "staging" / "reviews.sql"
MAX_TRIES = 4

UPSERT_RAW = """
    INSERT INTO raw.reviews (recommendationid, timestamp_updated, payload)
    VALUES (%s, %s, %s)
    ON CONFLICT (recommendationid) DO UPDATE
    SET timestamp_updated = EXCLUDED.timestamp_updated,
        payload           = EXCLUDED.payload,
        loaded_at         = now()
"""

log = logging.getLogger("load_reviews")


def fetch_page(app_id, language, cursor):
    """One page of up to 100 reviews, retrying with back-off (2, 4, 8 s) on errors."""
    query = urllib.parse.urlencode({
        "json": 1,
        "filter": "updated",
        "language": language,
        "num_per_page": 100,
        "purchase_type": "all",
        "review_type": "all",
        "cursor": cursor,
    })
    req = urllib.request.Request(URL.format(app_id=app_id, query=query),
                                 headers={"User-Agent": "deng-hs26-rage-index"})
    for attempt in range(1, MAX_TRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as err:
            if attempt == MAX_TRIES:
                raise
            wait = 2 ** attempt
            log.warning("attempt %d failed (%s), retrying in %d s", attempt, err, wait)
            time.sleep(wait)


def last_high_water_mark(conn):
    row = conn.execute("""
        SELECT coalesce(max(high_water_mark), 0)
        FROM raw.ingestion_runs
        WHERE source = 'reviews' AND status = 'success'
    """).fetchone()
    return row[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="load everything updated since this date (YYYY-MM-DD)")
    parser.add_argument("--full", action="store_true", help="ignore the high-water mark")
    parser.add_argument("--max-pages", type=int, help="stop after N pages (test run)")
    parser.add_argument("--sleep", type=float, default=0.5, help="pause between pages in seconds")
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    parser.add_argument("--app-id", default=os.getenv("STEAM_APP_ID", "1245620"))
    parser.add_argument("--language", default=os.getenv("REVIEW_LANGUAGE", "english"))
    args = parser.parse_args()

    with connect() as conn:
        run_id, started_at = conn.execute(
            "INSERT INTO raw.ingestion_runs (source) VALUES ('reviews') RETURNING run_id, started_at"
        ).fetchone()
        conn.commit()

        previous_mark = last_high_water_mark(conn)
        if args.full:
            mark = 0
        elif args.since:
            mark = int(datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc).timestamp())
        else:
            mark = previous_mark
        log.info("run %d: loading reviews updated after %s", run_id,
                 datetime.fromtimestamp(mark, timezone.utc).isoformat() if mark else "the beginning")

        page_dir = Path(args.data_dir) / "reviews" / started_at.date().isoformat() / f"run_{run_id}"
        page_dir.mkdir(parents=True, exist_ok=True)

        try:
            cursor, page, loaded, newest = "*", 0, 0, mark
            while True:
                data = fetch_page(args.app_id, args.language, cursor)
                reviews = data.get("reviews", [])
                if not reviews:
                    break
                page += 1
                (page_dir / f"page_{page:05d}.json").write_text(json.dumps(data), encoding="utf-8")

                new = [r for r in reviews if r["timestamp_updated"] > mark]
                with conn.cursor() as cur:
                    cur.executemany(UPSERT_RAW, [
                        (r["recommendationid"], r["timestamp_updated"], Jsonb(r)) for r in new
                    ])
                conn.commit()  # keep progress of long backfills
                loaded += len(new)
                newest = max([newest] + [r["timestamp_updated"] for r in new])

                if page % 50 == 0:
                    log.info("page %d, %d reviews loaded so far", page, loaded)
                if not new:
                    break  # the whole page is older than the mark
                if data["cursor"] == cursor or (args.max_pages and page >= args.max_pages):
                    break
                cursor = data["cursor"]
                time.sleep(args.sleep)

            staged = conn.execute(STAGING_SQL.read_text(encoding="utf-8"),
                                  {"since": started_at}).rowcount

            # a test run with --max-pages may stop early, so it must not move the mark
            status = "partial" if args.max_pages else "success"
            conn.execute("""
                UPDATE raw.ingestion_runs
                SET finished_at = now(), status = %s, high_water_mark = %s, rows_loaded = %s, note = %s
                WHERE run_id = %s
            """, (status, max(previous_mark, newest), loaded, f"{page} pages", run_id))
            conn.commit()
        except Exception:
            conn.rollback()
            conn.execute("UPDATE raw.ingestion_runs SET finished_at = now(), status = 'failed' WHERE run_id = %s",
                         (run_id,))
            conn.commit()
            raise

    log.info("run %d %s: %d pages, %d reviews loaded, %d staging rows upserted",
             run_id, status, page, loaded, staged)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
