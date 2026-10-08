"""Daily snapshot of the global Steam achievement percentages for Elden Ring.

Steam only returns the current percentages, so the history only exists if we
store one snapshot per day. Running the script twice on the same day
overwrites that day's file, so re-runs are safe.

Output: <data-dir>/achievements/<YYYY-MM-DD>/achievements.json
"""

import argparse
import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/?gameid={app_id}"
MAX_TRIES = 4

log = logging.getLogger("snapshot_achievements")


def fetch(url):
    """Get the JSON response, retrying with back-off (2, 4, 8 s) on errors."""
    for attempt in range(1, MAX_TRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "deng-hs26-rage-index"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception as err:
            if attempt == MAX_TRIES:
                raise
            wait = 2 ** attempt
            log.warning("attempt %d failed (%s), retrying in %d s", attempt, err, wait)
            time.sleep(wait)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    parser.add_argument("--app-id", default=os.getenv("STEAM_APP_ID", "1245620"))
    args = parser.parse_args()

    url = URL.format(app_id=args.app_id)
    fetched_at = datetime.now(timezone.utc)

    response = fetch(url)
    achievements = response.get("achievementpercentages", {}).get("achievements", [])
    if not achievements:
        # fail loudly so the scheduler shows a failed run instead of saving an empty day
        log.error("no achievements in response: %s", str(response)[:200])
        sys.exit(1)

    snapshot_date = fetched_at.date().isoformat()
    out_file = Path(args.data_dir) / "achievements" / snapshot_date / "achievements.json"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "snapshot_date": snapshot_date,
        "fetched_at": fetched_at.isoformat(timespec="seconds"),
        "app_id": args.app_id,
        "source_url": url,
        "response": response,
    }
    out_file.write_text(json.dumps(record, indent=2), encoding="utf-8")

    log.info("saved %d achievements to %s", len(achievements), out_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
