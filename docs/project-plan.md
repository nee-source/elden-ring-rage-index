# Project plan & backlog

Deadlines (Europe/Zurich):

- **01.10.2026** (W3): pitch, Architecture v0.1
- **22.10.2026 15:30** (W6): midterm repo submission on ILIAS (link + commit hash or tag)
- **29.10.2026** (W7): midterm defence
- **12.11.2026**: midterm peer reviews due
- **10.12.2026 20:00** (W13): final repo submission on ILIAS
- **17.12.2026** (W14): final defence
- **31.12.2026**: final peer reviews due

## Milestone 1: Pitch (W3)

- [x] Choose the sources and the use case
- [x] Write the README, dataset doc, use case and Architecture v0.1
- [ ] Prepare the pitch slides and rehearse: 5 min pitch + 4 min Q&A

## Milestone 2: Midterm (W4–W6)

- [x] Daily achievement snapshot job, **first**, because its history can't be backfilled (B). It runs on GitHub Actions and writes to the `snapshots` branch
- [x] Load the snapshot files from the `snapshots` branch into PostgreSQL (B)
- [x] Review ingestion: cursor pagination, retries, high-water mark, run log (A)
- [ ] Full review backfill (a few hours because of the rate limit; resumable) (A)
- [x] Docker Compose with PostgreSQL + pgAdmin on a shared network (B)
- [x] Pipeline image (`Dockerfile`) as a `pipeline` service in Docker Compose on `rage-net` (B)
- [x] PostgreSQL raw/staging/mart schemas (B)
- [x] First transformation: boss matching → `staging.review_boss_mention` → `mart.boss_mentions_daily` (A)
- [ ] Check matching precision on a sample of reviews (A)
- [ ] Orchestrator: daily schedule, retries, backfill by date range (A)
- [ ] Architecture v0.2, plus setup/run/verification steps in the README (A + B)
- [ ] Tag `v0.2-midterm` and submit on ILIAS (A + B)

## Milestone 3: Final (W7–W13)

- [ ] Terraform: GCS bucket + BigQuery dataset (B)
- [ ] Ingestion writes straight to GCS (A)
- [ ] Load from the lake into BigQuery staging and curated tables, with partitioning (B)
- [ ] Funnel, mentions and rage ranking tables, each with its grain documented (A + B)
- [ ] Data-quality checks: row counts, duplicates, freshness (A)
- [ ] Measure matching precision on 200 labelled reviews (A + B)
- [ ] Final architecture, verification queries, limitations (A + B)
- [ ] Tag `v1.0-final` and submit on ILIAS (A + B)
