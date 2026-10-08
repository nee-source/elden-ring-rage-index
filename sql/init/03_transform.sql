-- Tables filled by transform/run.py (seeds + boss matching).

-- grain: one row per boss alias (from seeds/boss_aliases.csv)
CREATE TABLE IF NOT EXISTS staging.boss_alias (
    boss_key text NOT NULL,
    alias    text NOT NULL,
    note     text,
    PRIMARY KEY (boss_key, alias)
);

-- grain: one row per Steam achievement (from seeds/achievement_boss_map.csv)
CREATE TABLE IF NOT EXISTS staging.achievement_boss (
    achievement_code text PRIMARY KEY,
    display_name     text NOT NULL,
    is_boss          boolean NOT NULL,
    boss_key         text,
    main_path_order  integer
);

-- grain: one row per review x boss mentioned in it
CREATE TABLE IF NOT EXISTS staging.review_boss_mention (
    recommendationid text NOT NULL,
    boss_key         text NOT NULL,
    PRIMARY KEY (recommendationid, boss_key)
);

-- grain: one row per review date x boss
CREATE TABLE IF NOT EXISTS mart.boss_mentions_daily (
    review_date        date NOT NULL,
    boss_key           text NOT NULL,
    mentions           integer NOT NULL,
    negative_mentions  integer NOT NULL,
    median_playtime_h  numeric(8,1),
    PRIMARY KEY (review_date, boss_key)
);
