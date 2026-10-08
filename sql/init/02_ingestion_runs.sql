-- One row per loader run. The review loader reads its high-water mark from the
-- last *successful* run, so a crashed or test run never moves the mark forward.
-- A failed run keeps the cursor of its last finished page, so it can be resumed.

CREATE TABLE IF NOT EXISTS raw.ingestion_runs (
    run_id          bigserial PRIMARY KEY,
    source          text NOT NULL,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text NOT NULL DEFAULT 'running',   -- running | success | partial | failed
    mark_from       bigint,                            -- only reviews updated after this (unix)
    last_cursor     text,                              -- Steam cursor of the next page
    high_water_mark bigint,                            -- max timestamp_updated after the run (unix)
    rows_loaded     integer,
    note            text
);
