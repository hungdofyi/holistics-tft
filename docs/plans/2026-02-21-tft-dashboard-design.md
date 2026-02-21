# TFT Analytics Dashboard — Design Document

**Date:** 2026-02-21
**Goal:** Build a real-time Postgres-backed TFT dashboard using Holistics, similar to MetaTFT / tactics.tools.

## Architecture

```
Riot TFT API
     │
     ▼
Python Ingestion Scripts (GitHub Actions cron, every 6h)
     │
     ▼
Neon Postgres (hosted)
     │
     ▼
Holistics (connected as data source)
     │
     ▼
Dashboard Tabs: Comps | Units | Items | Augments | Players
```

## Approach

**Normalized tables + Holistics AQL for all aggregations.** Raw match data stored in Postgres. No pre-aggregation tables — Holistics AQL handles all metric computation (comp win rates, augment tiers, unit stats, etc.).

## Data Schema

### matches
| Column | Type | Notes |
|---|---|---|
| match_id | varchar PK | e.g. "NA1_1234567" |
| data_version | varchar | |
| game_datetime | bigint | epoch ms from API |
| game_length | float | seconds |
| game_version | varchar | patch version |
| queue_id | int | |
| tft_game_type | varchar | "standard", "turbo", etc. |
| tft_set_number | int | |
| tft_set_core_name | varchar | |
| region | varchar | "americas", "europe", "asia" |
| ingested_at | timestamp | default now() |

### match_participants
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| match_id | varchar FK → matches | |
| puuid | varchar | |
| placement | int | 1-8 |
| level | int | |
| gold_left | int | |
| last_round | int | |
| players_eliminated | int | |
| time_eliminated | float | |
| total_damage_to_players | int | |

### participant_augments
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| participant_id | int FK → match_participants | |
| augment_id | varchar | e.g. "TFT9_Augment_CyberneticImplants" |
| pick_order | int | 1, 2, or 3 |

### participant_traits
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| participant_id | int FK → match_participants | |
| trait_name | varchar | e.g. "Set9_Demacia" |
| num_units | int | |
| tier_current | int | |
| tier_total | int | |
| style | int | 0=inactive, 1=bronze, 2=silver, 3=gold, 4=chromatic |

### participant_units
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| participant_id | int FK → match_participants | |
| character_id | varchar | e.g. "TFT9_Yasuo" |
| tier | int | star level 1-3 |
| rarity | int | cost tier |

### unit_items
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| unit_id | int FK → participant_units | |
| item_id | int | |
| item_name | varchar | |

### league_entries
| Column | Type | Notes |
|---|---|---|
| id | serial PK | |
| summoner_id | varchar | |
| puuid | varchar | |
| tier | varchar | CHALLENGER, GRANDMASTER, MASTER |
| rank | varchar | |
| league_points | int | |
| wins | int | |
| losses | int | |
| region | varchar | |
| updated_at | timestamp | default now() |

## Data Ingestion Pipeline

1. **ingest_leagues.py** — Calls League API for Challenger/GM/Master across all regions. Upserts into league_entries. Collects PUUIDs.
2. **ingest_matches.py** — For each PUUID, fetches recent match IDs, then match details. Deduplicates by match_id. Inserts into all normalized tables.

Rate limit handling: Dev key = 20 req/s, 100 req/2min. Simple rate limiter with backoff.

## Scheduling

GitHub Actions cron job runs every 6 hours. Secrets: `RIOT_API_KEY`, `DATABASE_URL`.

## Holistics Dashboard Tabs

| Tab | Key Metrics (via AQL) |
|---|---|
| Comps | Top comps by avg placement, play rate, top-4 rate, win rate |
| Units | Per-champion avg placement, pick rate, best items, star distribution |
| Items | Item win rates, most-used-on champions, avg placement |
| Augments | Augment tier list by avg placement, pick rate per stage |
| Players | Player lookup, match history, placement trend, most-played comps |

## Tech Stack

| Component | Choice |
|---|---|
| Database | Neon Postgres (free tier) |
| Ingestion | Python 3.14 (requests, psycopg2) |
| Schema docs | DBML |
| Scheduling | GitHub Actions cron |
| Dashboard | Holistics (AQL for metrics) |
| Region filter | Holistics filter on region columns |

## Data Sources

- [Riot TFT API](https://developer.riotgames.com/docs/tft)
- [Holistics AQL Reference](https://docs.holistics.io/as-code/reference/function)
- [Holistics Data Source Connection](https://docs.holistics.io/docs/connect)
