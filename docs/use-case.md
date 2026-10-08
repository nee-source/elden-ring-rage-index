# Use case

## Stakeholder

A content creator (guide writer / YouTuber) covering Elden Ring. They have limited time and want to spend it on the guides that help the most players: the bosses where people get stuck or quit.

## Questions

1. **Where do players stop?** Which main-path boss has the biggest drop in achievement unlock rate compared with the boss before it?
2. **Who do players complain about?** Which bosses are mentioned in negative reviews more often than average?
3. **When?** At what playtime (hours) are those reviews written?

## Data product

The guide writer gets **one table**:

| Table | One row per … | Main columns |
|---|---|---|
| `boss_rage_ranking` | boss (current state) | `dropoff_pct`, `negative_lift`, `mentions_total`, `median_playtime_h`, `rage_index`, `rank` |

## Intermediate tables

The ranking is built from two daily tables. They stay separate because they have different grains and come from different sources. They also keep the daily history, which lets us show trends over time. Steam does not give us the achievement history, so it only exists if we keep it.

| Table | One row per … | Main columns |
|---|---|---|
| `boss_funnel_daily` | snapshot date × boss | `unlock_pct`, `dropoff_pct` |
| `boss_mentions_daily` | review date × boss | `mentions`, `negative_mentions`, `median_playtime_h` |

## Rage-Quit Index (draft v0.1)

- **Drop-off**, from achievements, main-path bosses only:
  `dropoff = 1 − unlock_pct(boss) / unlock_pct(previous main-path boss)`
  Example: Godrick has 65.1 %, and Margit before him 71.0 %. That gives 1 − 65.1/71.0 ≈ **8.3 %**: of the players who beat Margit, 8.3 % never beat Godrick.
- **Negative lift**, from reviews:
  `negative_lift = share of negative reviews among those mentioning the boss / share of negative reviews overall`
  Today the overall share is about 6.8 % across all languages. A lift above 1 means the boss appears more than usual in negative reviews. We only rank bosses with at least 30 mentions.
- **`rage_index`:** convert both signals to a percentile rank from 0 to 1, then take the average. Optional bosses have no main-path drop-off, so they get a review-only score and a flag.

We will refine the definition once we see the real distributions.

## Success criteria

- The guide writer can open one ranked table and see both signals, plus the playtime at which frustration peaks.
- Re-running the pipeline for the same dates gives the same result.
- Each day's data is ready by 08:00 Europe/Zurich.
- On a hand-labelled sample of 200 reviews, boss matching reaches a precision of at least 0.8.
