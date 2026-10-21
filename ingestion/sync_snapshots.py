"""Copy the daily achievement snapshots from the `snapshots` branch to data/raw.

GitHub Actions commits one file per day to that branch. The repo is public, so we
download the branch as a tar.gz over HTTPS. No git and no login are needed, which
means the same step runs on a laptop, in a container and in Kestra.

Output: <data-dir>/achievements/<YYYY-MM-DD>/achievements.json
"""

import argparse
import logging
import os
import tarfile
import urllib.request

URL = "https://codeload.github.com/{repo}/tar.gz/refs/heads/snapshots"

log = logging.getLogger("sync_snapshots")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=os.getenv("RAW_DATA_DIR", "data/raw"))
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPO", "nee-source/elden-ring-rage-index"))
    args = parser.parse_args()

    req = urllib.request.Request(URL.format(repo=args.repo),
                                 headers={"User-Agent": "deng-hs26-rage-index"})
    with urllib.request.urlopen(req, timeout=60) as resp, tarfile.open(fileobj=resp, mode="r|gz") as tar:
        count = 0
        for member in tar:
            # names look like "<repo>-snapshots/achievements/<date>/achievements.json"
            parts = member.name.split("/", 1)
            if not member.isfile() or len(parts) < 2 or not parts[1].startswith("achievements/"):
                continue
            member.name = parts[1]
            tar.extract(member, args.data_dir, filter="data")
            count += 1

    log.info("synced %d snapshot files to %s/achievements", count, args.data_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
