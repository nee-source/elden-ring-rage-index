-- staging.review_boss_mention + staging.reviews -> mart.boss_mentions_daily
-- grain: one row per review date x boss
-- review_date = the day the review was written (created_at, UTC)
-- Full rebuild, like the step before.

TRUNCATE mart.boss_mentions_daily;

INSERT INTO mart.boss_mentions_daily
    (review_date, boss_key, mentions, negative_mentions, median_playtime_h)
SELECT
    r.created_at::date,
    m.boss_key,
    count(*),
    count(*) FILTER (WHERE NOT r.voted_up),
    round((percentile_cont(0.5) WITHIN GROUP (ORDER BY r.playtime_at_review_min) / 60.0)::numeric, 1)
FROM staging.review_boss_mention m
JOIN staging.reviews r USING (recommendationid)
GROUP BY 1, 2;
