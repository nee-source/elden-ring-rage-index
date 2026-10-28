"""Incremental load of English Steam reviews for Elden Ring.

How it works:
- Steam's IUserReviewsService/GetAppReviews returns reviews newest-updated first
  (filter 2 = updated), 100 per page, with a cursor for the next page. It replaced
  the old store.steampowered.com/appreviews endpoint, which Valve retired on
  2026-10-22 (it now redirects to the store homepage).
- The high-water mark is the highest timestamp_updated we had after the last
  successful run. We page until a whole page is older than the mark (the order
  is only roughly sorted, so one old review is not enough to stop).
- Every page is saved as a raw file and upserted into raw.reviews, then
  sql/staging/reviews.sql updates staging.reviews.
- Each run is logged in raw.ingestion_runs, including the cursor of the last
  finished page. Only a successful run moves the mark. A failed run can be
  continued with --resume; without it, the next run simply fetches the same
  range again and the upserts remove the duplicates.
- Steam rate-limits (HTTP 429) after roughly 150 quick requests and unblocks
  after a few minutes, so on a 429 we wait a minute and try again.

Usage:
    python -m ingestion.load_reviews                      # incremental (first run = full backfill)
    python -m ingestion.load_reviews --since 2026-10-01   # backfill everything updated since a date
    python -m ingestion.load_reviews --full               # reload all reviews
    python -m ingestion.load_reviews --resume             # continue the last failed or killed run
    python -m ingestion.load_reviews --max-pages 3        # test run, does not move the mark
"""

import argparse
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from psycopg.types.json import Jsonb

from ingestion.db import connect

URL = "https://api.steampowered.com/IUserReviewsService/GetAppReviews/v1/?{query}"
STAGING_SQL = Path(__file__).parent.parent / "sql" / "staging" / "reviews.sql"
MAX_TRIES = 4             # other errors: retry after 2, 4, 8 s
RATE_LIMIT_WAIT = 60      # HTTP 429: wait this many seconds ...
RATE_LIMIT_TRIES = 10     # ... up to this many times

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
    """One page of up to 100 reviews. Waits on rate limits, retries other errors."""
    # the parameters go as one JSON object; the options are numbers (enums) now
    params = {
        "appid": int(app_id),
        "filter": 2,               # 2 = sort by last update
        "languages": [language],
        "num_per_page": 100,
        "purchase_type": 1,        # 1 = all, also keys not bought on Steam
        "review_type": 0,          # 0 = positive and negative
        "cursor": cursor,
    }
    query = urllib.parse.urlencode({"input_json": json.dumps(params)})
    req = urllib.request.Request(URL.format(query=query),
                                 headers={"User-Agent": "deng-hs26-rage-index"})
    errors = rate_limits = 0
    while True:
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)["response"]
        except urllib.error.HTTPError as err:
            if err.code != 429:
                errors += 1
                if errors == MAX_TRIES:
                    raise
                wait = 2 ** errors
            else:
                rate_limits += 1
                if rate_limits == RATE_LIMIT_TRIES:
                    raise
                wait = RATE_LIMIT_WAIT
            log.warning("%s, waiting %d s", err, wait)
            time.sleep(wait)
        except Exception as err:  # network errors, timeouts
            errors += 1
            if errors == MAX_TRIES:
                raise
            wait = 2 ** errors
            log.warning("%s, waiting %d s", err, wait)
            time.sleep(wait)


def main():
    parser = argparse.ArgumentParser()
    # REVIEWS_SINCE lets the orchestrator pass a backfill date; empty = incremental
    parser.add_argument("--since", default=os.getenv("REVIEWS_SINCE") or None,
                        help="load everything updated since this date (YYYY-MM-DD)")
    parser.add_argument("--full", action="store_true", help="ignore the high-water mark")
    parser.add_argument("--resume", action="store_true", help="continue the last failed run")
    parser.add_argument("--max-pages", type=int, help="stop after N pages (test run)")
    parser.add_argument("--sleep", type=float, default=1.0, help="pause between pages in seconds")
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    parser.add_argument("--app-id", default=os.getenv("STEAM_APP_ID", "1245620"))
    parser.add_argument("--language", default=os.getenv("REVIEW_LANGUAGE", "english"))
    args = parser.parse_args()

    with connect() as conn:
        # where to start: mark = only reviews updated after it, cursor = first page to fetch
        last_success = conn.execute("""
            SELECT high_water_mark, finished_at FROM raw.ingestion_runs
            WHERE source = 'reviews' AND status = 'success'
            ORDER BY run_id DESC LIMIT 1
        """).fetchone()
        previous_mark, last_success_at = last_success or (0, datetime(1970, 1, 1, tzinfo=timezone.utc))

        cursor, note = "*", ""
        if args.resume:
            # "running" = the process was killed or the laptop shut down mid-run
            failed = conn.execute("""
                SELECT run_id, mark_from, last_cursor FROM raw.ingestion_runs
                WHERE source = 'reviews' AND status IN ('failed', 'running')
                  AND last_cursor IS NOT NULL
                ORDER BY run_id DESC LIMIT 1
            """).fetchone()
            if failed is None:
                raise SystemExit("no failed run with a saved cursor to resume")
            failed_id, mark, cursor = failed
            note = f"resumes run {failed_id}, "
        elif args.full:
            mark = 0
        elif args.since:
            mark = int(datetime.fromisoformat(args.since).replace(tzinfo=timezone.utc).timestamp())
        else:
            mark = previous_mark

        run_id, started_at = conn.execute("""
            INSERT INTO raw.ingestion_runs (source, mark_from) VALUES ('reviews', %s)
            RETURNING run_id, started_at
        """, (mark,)).fetchone()
        conn.commit()
        log.info("run %d: %sloading reviews updated after %s", run_id, note,
                 datetime.fromtimestamp(mark, timezone.utc).isoformat() if mark else "the beginning")

        page_dir = Path(args.data_dir) / "reviews" / started_at.date().isoformat() / f"run_{run_id}"
        page_dir.mkdir(parents=True, exist_ok=True)

        page = loaded = 0
        try:
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
                    # remember where the next page starts, so a failed run can be resumed
                    cur.execute("UPDATE raw.ingestion_runs SET last_cursor = %s WHERE run_id = %s",
                                (data["cursor"], run_id))
                conn.commit()
                loaded += len(new)

                if page % 50 == 0:
                    log.info("page %d, %d reviews loaded so far", page, loaded)
                if not new:
                    break  # the whole page is older than the mark
                if data["cursor"] == cursor or (args.max_pages and page >= args.max_pages):
                    break
                cursor = data["cursor"]
                time.sleep(args.sleep)

            # everything loaded since the last successful run, so rows of failed runs are included
            staged = conn.execute(STAGING_SQL.read_text(encoding="utf-8"),
                                  {"since": last_success_at}).rowcount

            # a successful run has everything from its mark up to now, so the newest
            # timestamp in the table is a safe new mark. A test run may stop early.
            status = "partial" if args.max_pages else "success"
            conn.execute("""
                UPDATE raw.ingestion_runs
                SET finished_at = now(), status = %s, rows_loaded = %s, note = %s,
                    high_water_mark = (SELECT max(timestamp_updated) FROM raw.reviews)
                WHERE run_id = %s
            """, (status, loaded, f"{note}{page} pages", run_id))
            conn.commit()
        except BaseException:  # also Ctrl+C, so the run is never left as "running"
            conn.rollback()
            conn.execute("UPDATE raw.ingestion_runs SET finished_at = now(), status = 'failed', "
                         "rows_loaded = %s, note = %s WHERE run_id = %s",
                         (loaded, f"{note}{page} pages", run_id))
            conn.commit()
            raise

    log.info("run %d %s: %d pages, %d reviews loaded, %d staging rows upserted",
             run_id, status, page, loaded, staged)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
