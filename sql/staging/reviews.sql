-- raw.reviews -> staging.reviews
-- grain: one row per review (latest version), English only, no Steam IDs
-- only rows loaded by the current run are processed (the since parameter)
-- upsert, so re-running it is safe

INSERT INTO staging.reviews (
    recommendationid, review, voted_up, created_at, updated_at, playtime_at_review_min
)
SELECT
    r.recommendationid,
    r.payload ->> 'review',
    (r.payload ->> 'voted_up')::boolean,
    to_timestamp((r.payload ->> 'timestamp_created')::bigint),
    to_timestamp(r.timestamp_updated),
    (r.payload -> 'author' ->> 'playtime_at_review')::integer
FROM raw.reviews r
WHERE r.loaded_at >= %(since)s
  AND r.payload ->> 'language' = 'english'
ON CONFLICT (recommendationid) DO UPDATE
SET review                 = EXCLUDED.review,
    voted_up               = EXCLUDED.voted_up,
    updated_at             = EXCLUDED.updated_at,
    playtime_at_review_min = EXCLUDED.playtime_at_review_min;
