-- raw.achievement_snapshots -> staging.achievement_snapshot
-- grain: one row per snapshot day x achievement
-- percent arrives as text ("75.0"), cast to numeric here
-- upsert, so re-running it is safe

INSERT INTO staging.achievement_snapshot (snapshot_date, achievement_code, unlock_pct)
SELECT
    s.snapshot_date,
    a ->> 'name',
    (a ->> 'percent')::numeric(4,1)
FROM raw.achievement_snapshots s
CROSS JOIN LATERAL jsonb_array_elements(
    s.payload -> 'response' -> 'achievementpercentages' -> 'achievements'
) AS a
ON CONFLICT (snapshot_date, achievement_code) DO UPDATE
SET unlock_pct = EXCLUDED.unlock_pct;
