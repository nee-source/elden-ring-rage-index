# ADR 0001: Data source selection

- Status: accepted (Week 3)
- Date: 2026-09-25

## Context

The course requires a batch source that **changes over time**, so that incremental loads, reruns and backfills make sense. Peer reviewers must be able to access it too. We wanted a fantasy RPG topic, either D&D or Elden Ring.

## Options considered

| Option | Changes over time? | Reproducible access? | Verdict |
|---|---|---|---|
| D&D Beyond | yes | **no**: no public API, `robots.txt` disallows `/api/`, licensed content | rejected |
| D&D 5e SRD API | no, the rules are static | yes | rejected |
| Elden Ring Fan API | no | yes, but incomplete (e.g. no Margit, Rennala, Morgott or DLC bosses) | rejected; a small seed table does the job better |
| **Steam reviews + achievement %** | yes: reviews daily, achievements drift | yes: public, no key | **chosen** |

## Decision

We use **two** Steam sources, reviews (incremental) and global achievement % (daily snapshot), plus two small seed tables that we maintain in git.

## Consequences

**Benefits**
- The use case rests on two signals: what players *do* and what they *say*.
- The pipeline shows two load patterns: backfill plus incremental, and snapshot.
- No API key is needed, so peer reviewers can run the pipeline straight away.

**Costs**
- Achievement history can't be backfilled, so we have to start snapshotting early.
- We maintain the seed tables by hand.
