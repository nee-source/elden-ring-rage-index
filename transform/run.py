"""Run the transformations: load the seed CSVs, then every file in sql/transform/ in order.

Everything runs in one transaction, so a failing step leaves the previous
results untouched. All steps are full rebuilds, so re-running is safe.
"""

import csv
import logging
from pathlib import Path

from ingestion.db import connect

ROOT = Path(__file__).parent.parent
SEEDS = ROOT / "seeds"
TRANSFORM_SQL = ROOT / "sql" / "transform"

log = logging.getLogger("transform")


def read_csv(name):
    with open(SEEDS / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_seeds(conn):
    aliases = read_csv("boss_aliases.csv")
    achievements = read_csv("achievement_boss_map.csv")

    conn.execute("TRUNCATE staging.boss_alias, staging.achievement_boss")
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO staging.boss_alias (boss_key, alias, note) VALUES (%s, %s, %s)",
            [(a["boss_key"], a["alias"].lower(), a["note"] or None) for a in aliases],
        )
        cur.executemany(
            """INSERT INTO staging.achievement_boss
               (achievement_code, display_name, is_boss, boss_key, main_path_order)
               VALUES (%s, %s, %s, %s, %s)""",
            [(a["achievement_code"], a["display_name"], a["is_boss"] == "true",
              a["boss_key"] or None, int(a["main_path_order"]) if a["main_path_order"] else None)
             for a in achievements],
        )
    log.info("seeds: %d aliases, %d achievements", len(aliases), len(achievements))


def main():
    with connect() as conn:
        load_seeds(conn)
        for sql_file in sorted(TRANSFORM_SQL.glob("*.sql")):
            # a file may hold several statements (TRUNCATE + INSERT): log the rows of the last one
            cur = conn.execute(sql_file.read_text(encoding="utf-8"))
            rows = cur.rowcount
            while cur.nextset():
                rows = cur.rowcount
            log.info("%s: %d rows", sql_file.name, rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
