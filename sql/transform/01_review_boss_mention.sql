-- staging.reviews x staging.boss_alias -> staging.review_boss_mention
-- grain: one row per review x boss mentioned in it
--
-- A review mentions a boss when one of the boss's aliases appears as a whole
-- word (\m = start of word, \M = end of word), case-insensitive (~*).
-- "malenia" matches "Malenia's", but "mohg" does not match "mohgwyn".
-- Several aliases of the same boss in one review count once (DISTINCT).
-- Full rebuild: simple, and always consistent with the current seeds.

TRUNCATE staging.review_boss_mention;

INSERT INTO staging.review_boss_mention (recommendationid, boss_key)
SELECT DISTINCT r.recommendationid, a.boss_key
FROM staging.reviews r
JOIN staging.boss_alias a
  ON r.review ~* ('\m' || a.alias || '\M');
