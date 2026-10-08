# Dataset description

Numbers were checked against the live endpoints on **2026-09-25**. Elden Ring's Steam app id is `1245620`. Neither endpoint needs an API key.

## 1. Steam reviews (main fact source)

| | |
|---|---|
| **Provenance** | User reviews on the Steam store, published by Valve |
| **Access** | `GET https://store.steampowered.com/appreviews/1245620?json=1&filter=updated&language=english&num_per_page=100&purchase_type=all&review_type=all&cursor=<cursor>` (`filter=updated` sorts by last update, newest first; `purchase_type=all` also includes reviews from keys not bought on Steam) |
| **Format** | JSON: `query_summary`, `reviews[]`, and a `cursor` for the next page |
| **Update frequency** | Continuous. New reviews arrive every day, and existing ones can be edited or deleted |
| **Volume** | 831,957 reviews in all languages (2026-09-25). **English: 573,286** (34,908 negative = 6.1 %) on 2026-10-08. About 1.1 KB per review as JSON, so a full English load is ~600 MB raw |
| **Change rate** | About 100 English reviews are created or edited per day, so the daily incremental run is 1–2 pages. In our sample, 25–33 % of reviews had been edited after creation |
| **Speed** | About 0.45 s per page of 100 reviews. A full backfill takes ~5,700 pages, about 1 hour with a 0.5 s pause between pages |

**Fields we use**

| Field | Type | Notes |
|---|---|---|
| `recommendationid` | string | unique review id, used as the primary key |
| `review` | string | free text |
| `voted_up` | bool | `true` = recommended, `false` = not recommended |
| `language` | string | we keep `english` only |
| `timestamp_created` | unix int | |
| `timestamp_updated` | unix int | changes when the author edits the review; used as our high-water mark |
| `author.playtime_at_review` | int (minutes) | how long they had played when they wrote it |

All other fields stay in the raw JSON and are not used. That includes `author.steamid`, which is personal data we don't need.

**Sample record (trimmed, illustrative values)**

```json
{
  "recommendationid": "123456789",
  "author": { "playtime_at_review": 5230 },
  "language": "english",
  "review": "Malenia made me uninstall. 10/10.",
  "timestamp_created": 1788000000,
  "timestamp_updated": 1788000000,
  "voted_up": true
}
```

**Data-quality risks**

- **Mutable reviews:** reviews can be edited or deleted, so staging upserts on `recommendationid` rather than appending.
- **Sarcasm:** a thumbs-up review can still complain. `voted_up` does not always match the tone of the text.
- **Noise:** spam, memes, and empty or one-word reviews.
- **Only roughly sorted:** the first page was not strictly in `timestamp_updated` order, so the loader stops only once a whole page is older than the high-water mark.
- **Deletions are invisible** to incremental loads. A deleted review stays in our tables until a full reload.
- **Rate limits:** they are undocumented, so we back off and retry. The one-time full backfill needs many requests.

## 2. Steam global achievement percentages (fact, daily snapshot)

| | |
|---|---|
| **Access** | `GET https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/?gameid=1245620` |
| **Format** | JSON: `achievementpercentages.achievements[] = {name, percent}` |
| **Update frequency** | Steam updates it continuously, but only the **current** value is available |
| **Volume** | 42 rows per snapshot |

**Example (2026-09-25):** `ACH25` (Margit) 71.0 %, `ACH04` (Godrick) 65.1 %, `ACH06` (Morgott) 49.6 %, `ACH11` (Hoarah Loux) 40.5 %.

**Data-quality risks**

- **Percent is a string:** the API returns `percent` as text (`"75.0"`), so staging casts it to a number.
- **Code names only:** the API returns codes like `ACH25`, not boss names. `seeds/achievement_boss_map.csv` maps each code to a boss.
- **No history:** a missed daily snapshot is lost for good.
- **All owners count:** the percentage is a share of *all owners*, including people who never really played.
- **Rounding:** values are rounded to 0.1 %.

## Seed tables (ours)

| File | Content |
|---|---|
| `seeds/achievement_boss_map.csv` | achievement code → display name → boss, plus the main-path order |
| `seeds/boss_aliases.csv` | boss → the names and nicknames players write in reviews |

## Terms & ethics

- We call public endpoints only, at a low request rate.
- We don't keep personal data: Steam IDs are dropped in staging.
- Raw data is not redistributed in the repo. The pipeline fetches it.
