-- Runs once when the Postgres volume is created.
-- Layers: raw (untouched API JSON) -> staging (typed, cleaned) -> mart (for the guide writer)

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS mart;

-- raw ------------------------------------------------------------------

-- grain: one row per snapshot day (the whole API response, schema-on-read)
CREATE TABLE IF NOT EXISTS raw.achievement_snapshots (
    snapshot_date date PRIMARY KEY,
    fetched_at    timestamptz NOT NULL,
    payload       jsonb NOT NULL,
    loaded_at     timestamptz NOT NULL DEFAULT now()
);

-- grain: one row per review, latest version (upsert on recommendationid)
CREATE TABLE IF NOT EXISTS raw.reviews (
    recommendationid  text PRIMARY KEY,
    timestamp_updated bigint NOT NULL,   -- high-water mark for incremental loads
    payload           jsonb NOT NULL,
    loaded_at         timestamptz NOT NULL DEFAULT now()
);

-- staging --------------------------------------------------------------

-- grain: one row per snapshot day x achievement
CREATE TABLE IF NOT EXISTS staging.achievement_snapshot (
    snapshot_date    date NOT NULL,
    achievement_code text NOT NULL,
    unlock_pct       numeric(4,1) NOT NULL,   -- API sends it as text, cast here
    PRIMARY KEY (snapshot_date, achievement_code)
);

-- grain: one row per review (English only, no Steam IDs)
CREATE TABLE IF NOT EXISTS staging.reviews (
    recommendationid      text PRIMARY KEY,
    review                text NOT NULL,
    voted_up              boolean NOT NULL,
    created_at            timestamptz NOT NULL,
    updated_at            timestamptz NOT NULL,
    playtime_at_review_min integer
);
