"""Load achievement snapshot files into Postgres.

1. raw: one row per snapshot file (the whole JSON), upsert on snapshot_date
2. staging: sql/staging/achievement_snapshot.sql turns the JSON into one row
   per day x achievement

Both steps upsert, so loading the same files again changes nothing.
"""

import argparse
import json
import logging
import os
from pathlib import Path

from psycopg.types.json import Jsonb

from ingestion.db import connect

STAGING_SQL = Path(__file__).parent.parent / "sql" / "staging" / "achievement_snapshot.sql"

UPSERT_RAW = """
    INSERT INTO raw.achievement_snapshots (snapshot_date, fetched_at, payload)
    VALUES (%s, %s, %s)
    ON CONFLICT (snapshot_date) DO UPDATE
    SET fetched_at = EXCLUDED.fetched_at,
        payload    = EXCLUDED.payload,
        loaded_at  = now()
"""

log = logging.getLogger("load_achievements")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    args = parser.parse_args()

    files = sorted(Path(args.data_dir).glob("achievements/*/achievements.json"))
    if not files:
        log.error("no snapshot files in %s/achievements, run sync_snapshots first", args.data_dir)
        raise SystemExit(1)

    with connect() as conn:
        for f in files:
            record = json.loads(f.read_text(encoding="utf-8"))
            conn.execute(UPSERT_RAW, (record["snapshot_date"], record["fetched_at"], Jsonb(record)))
        staged = conn.execute(STAGING_SQL.read_text(encoding="utf-8")).rowcount
        # leaving the with-block commits; any error above rolls everything back

    log.info("loaded %d snapshot files into raw, upserted %d staging rows", len(files), staged)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
