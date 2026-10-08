"""Copy the daily achievement snapshots from the `snapshots` branch to data/raw.

GitHub Actions commits one file per day to that branch. This script fetches the
branch and extracts the files without switching branches, so it can run from main.

Output: <data-dir>/achievements/<YYYY-MM-DD>/achievements.json
"""

import argparse
import io
import logging
import os
import subprocess
import tarfile

log = logging.getLogger("sync_snapshots")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    args = parser.parse_args()

    subprocess.run(["git", "fetch", "origin", "snapshots"], check=True)
    archive = subprocess.run(
        ["git", "archive", "--format=tar", "origin/snapshots", "achievements"],
        check=True,
        capture_output=True,
    ).stdout

    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        files = [m for m in tar.getmembers() if m.isfile()]
        tar.extractall(args.data_dir, members=files, filter="data")

    log.info("synced %d snapshot files to %s/achievements", len(files), args.data_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
