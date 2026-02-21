# TFT Analytics Dashboard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Set up a Postgres-backed TFT data pipeline that ingests Riot API match data into Neon and is ready for Holistics dashboarding.

**Architecture:** Python scripts fetch TFT league and match data from Riot API, normalize it into 7 relational tables in Neon Postgres. GitHub Actions runs ingestion every 6h. Holistics connects to Neon as a data source.

**Tech Stack:** Python 3.14, requests, psycopg2-binary, Neon Postgres, DBML, GitHub Actions

---

### Task 1: Project Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `requirements.txt`

**Step 1: Create .gitignore**

```
__pycache__/
*.pyc
.env
.venv/
venv/
*.egg-info/
dist/
build/
.pytest_cache/
```

**Step 2: Create pyproject.toml**

```toml
[project]
name = "holistics-tft"
version = "0.1.0"
description = "TFT data pipeline for Holistics dashboard"
requires-python = ">=3.14"
dependencies = [
    "requests>=2.31.0",
    "psycopg2-binary>=2.9.9",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
]
```

**Step 3: Create requirements.txt**

```
requests>=2.31.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
```

**Step 4: Create .env.example**

```
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATABASE_URL=postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/tft?sslmode=require
```

**Step 5: Commit**

```bash
git add .gitignore pyproject.toml requirements.txt .env.example
git commit -m "chore: project scaffolding"
```

---

### Task 2: DBML Schema

**Files:**
- Create: `schema/tft.dbml`

**Step 1: Write DBML schema**

```dbml
Project tft_analytics {
  database_type: 'PostgreSQL'
  Note: 'TFT match data from Riot API for Holistics dashboard'
}

Table matches {
  match_id varchar [pk, note: 'e.g. NA1_1234567']
  data_version varchar
  game_datetime bigint [note: 'epoch ms from API']
  game_length float [note: 'seconds']
  game_version varchar [note: 'patch version']
  queue_id int
  tft_game_type varchar [note: 'standard, turbo, etc.']
  tft_set_number int
  tft_set_core_name varchar
  region varchar [note: 'americas, europe, asia']
  ingested_at timestamp [default: `now()`]
}

Table match_participants {
  id serial [pk]
  match_id varchar [ref: > matches.match_id]
  puuid varchar
  placement int [note: '1-8']
  level int
  gold_left int
  last_round int
  players_eliminated int
  time_eliminated float
  total_damage_to_players int
}

Table participant_augments {
  id serial [pk]
  participant_id int [ref: > match_participants.id]
  augment_id varchar [note: 'e.g. TFT9_Augment_CyberneticImplants']
  pick_order int [note: '1, 2, or 3']
}

Table participant_traits {
  id serial [pk]
  participant_id int [ref: > match_participants.id]
  trait_name varchar [note: 'e.g. Set9_Demacia']
  num_units int
  tier_current int
  tier_total int
  style int [note: '0=inactive, 1=bronze, 2=silver, 3=gold, 4=chromatic']
}

Table participant_units {
  id serial [pk]
  participant_id int [ref: > match_participants.id]
  character_id varchar [note: 'e.g. TFT9_Yasuo']
  tier int [note: 'star level 1-3']
  rarity int [note: 'cost tier']
}

Table unit_items {
  id serial [pk]
  unit_id int [ref: > participant_units.id]
  item_id int
  item_name varchar
}

Table league_entries {
  id serial [pk]
  summoner_id varchar
  puuid varchar
  tier varchar [note: 'CHALLENGER, GRANDMASTER, MASTER']
  rank varchar
  league_points int
  wins int
  losses int
  region varchar
  updated_at timestamp [default: `now()`]
}
```

**Step 2: Commit**

```bash
git add schema/tft.dbml
git commit -m "docs: add DBML schema for TFT data model"
```

---

### Task 3: SQL Migration Script

**Files:**
- Create: `schema/migrations/001_initial.sql`

**Step 1: Write the migration SQL**

Translate the DBML into Postgres DDL. Include indexes on frequently queried columns (match_id FKs, puuid, region, placement).

```sql
-- 001_initial.sql
-- TFT Analytics Schema

CREATE TABLE IF NOT EXISTS matches (
    match_id VARCHAR(64) PRIMARY KEY,
    data_version VARCHAR(8),
    game_datetime BIGINT,
    game_length REAL,
    game_version VARCHAR(64),
    queue_id INT,
    tft_game_type VARCHAR(32),
    tft_set_number INT,
    tft_set_core_name VARCHAR(64),
    region VARCHAR(16),
    ingested_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS match_participants (
    id SERIAL PRIMARY KEY,
    match_id VARCHAR(64) REFERENCES matches(match_id),
    puuid VARCHAR(128),
    placement INT,
    level INT,
    gold_left INT,
    last_round INT,
    players_eliminated INT,
    time_eliminated REAL,
    total_damage_to_players INT
);

CREATE TABLE IF NOT EXISTS participant_augments (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    augment_id VARCHAR(128),
    pick_order INT
);

CREATE TABLE IF NOT EXISTS participant_traits (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    trait_name VARCHAR(128),
    num_units INT,
    tier_current INT,
    tier_total INT,
    style INT
);

CREATE TABLE IF NOT EXISTS participant_units (
    id SERIAL PRIMARY KEY,
    participant_id INT REFERENCES match_participants(id),
    character_id VARCHAR(128),
    tier INT,
    rarity INT
);

CREATE TABLE IF NOT EXISTS unit_items (
    id SERIAL PRIMARY KEY,
    unit_id INT REFERENCES participant_units(id),
    item_id INT,
    item_name VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS league_entries (
    id SERIAL PRIMARY KEY,
    summoner_id VARCHAR(128),
    puuid VARCHAR(128),
    tier VARCHAR(16),
    rank VARCHAR(8),
    league_points INT,
    wins INT,
    losses INT,
    region VARCHAR(16),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_match_participants_match_id ON match_participants(match_id);
CREATE INDEX IF NOT EXISTS idx_match_participants_puuid ON match_participants(puuid);
CREATE INDEX IF NOT EXISTS idx_participant_augments_participant_id ON participant_augments(participant_id);
CREATE INDEX IF NOT EXISTS idx_participant_traits_participant_id ON participant_traits(participant_id);
CREATE INDEX IF NOT EXISTS idx_participant_units_participant_id ON participant_units(participant_id);
CREATE INDEX IF NOT EXISTS idx_unit_items_unit_id ON unit_items(unit_id);
CREATE INDEX IF NOT EXISTS idx_matches_region ON matches(region);
CREATE INDEX IF NOT EXISTS idx_matches_tft_set_number ON matches(tft_set_number);
CREATE INDEX IF NOT EXISTS idx_league_entries_puuid ON league_entries(puuid);
CREATE INDEX IF NOT EXISTS idx_league_entries_region ON league_entries(region);
```

**Step 2: Commit**

```bash
git add schema/migrations/001_initial.sql
git commit -m "feat: add initial SQL migration for TFT schema"
```

---

### Task 4: Set Up Neon Database

**This is a manual + script task.**

**Step 1: Create Neon project**

Go to https://neon.tech, create a free project named `tft-analytics`. Copy the connection string.

**Step 2: Create a .env file locally (do NOT commit)**

```
RIOT_API_KEY=<your-dev-key>
DATABASE_URL=<your-neon-connection-string>
```

**Step 3: Create a migration runner script**

Create `schema/migrate.py`:

```python
"""Run SQL migrations against the database."""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def run_migration(filepath: str) -> None:
    database_url = os.environ["DATABASE_URL"]
    with open(filepath) as f:
        sql = f.read()
    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()
        print(f"Migration applied: {filepath}")
    finally:
        conn.close()


if __name__ == "__main__":
    migration_file = sys.argv[1] if len(sys.argv) > 1 else "schema/migrations/001_initial.sql"
    run_migration(migration_file)
```

**Step 4: Run the migration**

```bash
python schema/migrate.py schema/migrations/001_initial.sql
```

Expected: `Migration applied: schema/migrations/001_initial.sql`

**Step 5: Verify tables exist**

```bash
python -c "
import os; import psycopg2; from dotenv import load_dotenv; load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema='public'\")
print([r[0] for r in cur.fetchall()])
conn.close()
"
```

Expected: list containing `matches`, `match_participants`, `participant_augments`, `participant_traits`, `participant_units`, `unit_items`, `league_entries`

**Step 6: Commit**

```bash
git add schema/migrate.py
git commit -m "feat: add migration runner script"
```

---

### Task 5: Riot API Client with Rate Limiting

**Files:**
- Create: `src/__init__.py`
- Create: `src/riot_api.py`

**Step 1: Create src package**

Empty `src/__init__.py`.

**Step 2: Write the Riot API client**

```python
"""Riot TFT API client with rate limiting."""

import os
import time
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

# Riot dev key rate limits: 20 requests per 1 second, 100 requests per 2 minutes
RATE_LIMIT_PER_SECOND = 20
RATE_LIMIT_PER_2MIN = 100

# Regional routing for match-v1
MATCH_REGIONS = ["americas", "europe", "asia"]

# Platform routing for league-v1
LEAGUE_PLATFORMS = {
    "americas": ["na1", "br1", "la1", "la2"],
    "europe": ["euw1", "eun1", "tr1", "ru"],
    "asia": ["kr", "jp1"],
}


class RiotAPIClient:
    def __init__(self) -> None:
        self.api_key = os.environ["RIOT_API_KEY"]
        self.session = requests.Session()
        self.session.headers.update({"X-Riot-Token": self.api_key})
        self._request_times: list[float] = []

    def _rate_limit(self) -> None:
        """Simple rate limiter respecting both rate limit windows."""
        now = time.time()
        # Remove timestamps older than 2 minutes
        self._request_times = [t for t in self._request_times if now - t < 120]

        # Check 2-minute window
        if len(self._request_times) >= RATE_LIMIT_PER_2MIN:
            sleep_time = 120 - (now - self._request_times[0])
            if sleep_time > 0:
                print(f"Rate limit (2min): sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)

        # Check 1-second window
        recent = [t for t in self._request_times if now - t < 1]
        if len(recent) >= RATE_LIMIT_PER_SECOND:
            time.sleep(1.0)

        self._request_times.append(time.time())

    def _get(self, url: str) -> Any:
        """Make a rate-limited GET request."""
        self._rate_limit()
        resp = self.session.get(url)
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", 10))
            print(f"429 Too Many Requests: retrying after {retry_after}s")
            time.sleep(retry_after)
            return self._get(url)
        resp.raise_for_status()
        return resp.json()

    # -- League endpoints (platform routing) --

    def get_challenger_league(self, platform: str) -> dict:
        url = f"https://{platform}.api.riotgames.com/tft/league/v1/challenger"
        return self._get(url)

    def get_grandmaster_league(self, platform: str) -> dict:
        url = f"https://{platform}.api.riotgames.com/tft/league/v1/grandmaster"
        return self._get(url)

    def get_master_league(self, platform: str) -> dict:
        url = f"https://{platform}.api.riotgames.com/tft/league/v1/master"
        return self._get(url)

    # -- Account endpoint (to get PUUID from summoner ID) --

    def get_summoner_by_id(self, platform: str, summoner_id: str) -> dict:
        url = f"https://{platform}.api.riotgames.com/tft/summoner/v1/summoners/{summoner_id}"
        return self._get(url)

    # -- Match endpoints (regional routing) --

    def get_match_ids(self, region: str, puuid: str, count: int = 20, start: int = 0) -> list[str]:
        url = (
            f"https://{region}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
            f"?count={count}&start={start}"
        )
        return self._get(url)

    def get_match(self, region: str, match_id: str) -> dict:
        url = f"https://{region}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        return self._get(url)
```

**Step 3: Write a quick smoke test**

Create `tests/test_riot_api.py`:

```python
"""Smoke tests for RiotAPIClient (requires valid API key)."""

import os
import pytest
from src.riot_api import RiotAPIClient, LEAGUE_PLATFORMS

pytestmark = pytest.mark.skipif(
    not os.environ.get("RIOT_API_KEY"),
    reason="RIOT_API_KEY not set",
)


def test_get_challenger_league():
    client = RiotAPIClient()
    data = client.get_challenger_league("na1")
    assert "entries" in data
    assert len(data["entries"]) > 0
```

**Step 4: Run the test (if you have a key)**

```bash
pip install -e ".[dev]" && pytest tests/test_riot_api.py -v
```

**Step 5: Commit**

```bash
git add src/__init__.py src/riot_api.py tests/test_riot_api.py
git commit -m "feat: add Riot API client with rate limiting"
```

---

### Task 6: League Ingestion Script

**Files:**
- Create: `src/ingest_leagues.py`

**Step 1: Write league ingestion**

```python
"""Fetch Challenger/GM/Master league entries and upsert into Postgres."""

import os

import psycopg2
from dotenv import load_dotenv

from src.riot_api import RiotAPIClient, LEAGUE_PLATFORMS

load_dotenv()

TIERS = [
    ("CHALLENGER", "get_challenger_league"),
    ("GRANDMASTER", "get_grandmaster_league"),
    ("MASTER", "get_master_league"),
]


def platform_to_region(platform: str) -> str:
    for region, platforms in LEAGUE_PLATFORMS.items():
        if platform in platforms:
            return region
    return "americas"


def ingest_leagues() -> None:
    client = RiotAPIClient()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        with conn.cursor() as cur:
            for tier_name, method_name in TIERS:
                for region, platforms in LEAGUE_PLATFORMS.items():
                    for platform in platforms:
                        print(f"Fetching {tier_name} from {platform}...")
                        try:
                            data = getattr(client, method_name)(platform)
                        except Exception as e:
                            print(f"  Error fetching {tier_name} {platform}: {e}")
                            continue

                        entries = data.get("entries", [])
                        print(f"  Found {len(entries)} entries")

                        for entry in entries:
                            summoner_id = entry["summonerId"]

                            # Get PUUID from summoner endpoint
                            try:
                                summoner = client.get_summoner_by_id(platform, summoner_id)
                                puuid = summoner["puuid"]
                            except Exception as e:
                                print(f"  Skipping summoner {summoner_id}: {e}")
                                continue

                            cur.execute(
                                """
                                INSERT INTO league_entries
                                    (summoner_id, puuid, tier, rank, league_points, wins, losses, region, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                                ON CONFLICT (id) DO NOTHING
                                """,
                                (
                                    summoner_id,
                                    puuid,
                                    tier_name,
                                    entry.get("rank", ""),
                                    entry.get("leaguePoints", 0),
                                    entry.get("wins", 0),
                                    entry.get("losses", 0),
                                    region,
                                ),
                            )

                        conn.commit()
                        print(f"  Committed {tier_name} {platform}")

    finally:
        conn.close()

    print("League ingestion complete.")


if __name__ == "__main__":
    ingest_leagues()
```

**Step 2: Commit**

```bash
git add src/ingest_leagues.py
git commit -m "feat: add league entries ingestion script"
```

---

### Task 7: Match Ingestion Script

**Files:**
- Create: `src/ingest_matches.py`

**Step 1: Write match ingestion**

```python
"""Fetch match data for known PUUIDs and insert into normalized tables."""

import os

import psycopg2
from dotenv import load_dotenv

from src.riot_api import RiotAPIClient, LEAGUE_PLATFORMS

load_dotenv()


def get_region_for_puuid(conn, puuid: str) -> str:
    """Look up which region a PUUID belongs to from league_entries."""
    with conn.cursor() as cur:
        cur.execute("SELECT region FROM league_entries WHERE puuid = %s LIMIT 1", (puuid,))
        row = cur.fetchone()
        return row[0] if row else "americas"


def match_exists(conn, match_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM matches WHERE match_id = %s", (match_id,))
        return cur.fetchone() is not None


def insert_match(conn, match_data: dict, region: str) -> None:
    """Insert a full match into all normalized tables."""
    info = match_data["info"]
    metadata = match_data["metadata"]
    match_id = metadata["match_id"]

    with conn.cursor() as cur:
        # Insert match
        cur.execute(
            """
            INSERT INTO matches
                (match_id, data_version, game_datetime, game_length, game_version,
                 queue_id, tft_game_type, tft_set_number, tft_set_core_name, region)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (match_id) DO NOTHING
            """,
            (
                match_id,
                metadata.get("data_version", ""),
                info.get("game_datetime"),
                info.get("game_length"),
                info.get("game_version", ""),
                info.get("queue_id"),
                info.get("tft_game_type", ""),
                info.get("tft_set_number"),
                info.get("tft_set_core_name", ""),
                region,
            ),
        )

        # Insert participants
        for participant in info.get("participants", []):
            cur.execute(
                """
                INSERT INTO match_participants
                    (match_id, puuid, placement, level, gold_left, last_round,
                     players_eliminated, time_eliminated, total_damage_to_players)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    match_id,
                    participant.get("puuid", ""),
                    participant.get("placement"),
                    participant.get("level"),
                    participant.get("gold_left"),
                    participant.get("last_round"),
                    participant.get("players_eliminated"),
                    participant.get("time_eliminated"),
                    participant.get("total_damage_to_players"),
                ),
            )
            participant_id = cur.fetchone()[0]

            # Insert augments
            for i, augment in enumerate(participant.get("augments", [])):
                cur.execute(
                    """
                    INSERT INTO participant_augments (participant_id, augment_id, pick_order)
                    VALUES (%s, %s, %s)
                    """,
                    (participant_id, augment, i + 1),
                )

            # Insert traits
            for trait in participant.get("traits", []):
                cur.execute(
                    """
                    INSERT INTO participant_traits
                        (participant_id, trait_name, num_units, tier_current, tier_total, style)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        participant_id,
                        trait.get("name", ""),
                        trait.get("num_units"),
                        trait.get("tier_current"),
                        trait.get("tier_total"),
                        trait.get("style"),
                    ),
                )

            # Insert units
            for unit in participant.get("units", []):
                cur.execute(
                    """
                    INSERT INTO participant_units
                        (participant_id, character_id, tier, rarity)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        participant_id,
                        unit.get("character_id", ""),
                        unit.get("tier"),
                        unit.get("rarity"),
                    ),
                )
                unit_id = cur.fetchone()[0]

                # Insert items
                item_names = unit.get("itemNames", [])
                item_ids = unit.get("items", [])
                for j in range(len(item_names)):
                    cur.execute(
                        """
                        INSERT INTO unit_items (unit_id, item_id, item_name)
                        VALUES (%s, %s, %s)
                        """,
                        (
                            unit_id,
                            item_ids[j] if j < len(item_ids) else None,
                            item_names[j],
                        ),
                    )

    conn.commit()


def ingest_matches(max_players: int = 50, matches_per_player: int = 20) -> None:
    """Fetch recent matches for known players."""
    client = RiotAPIClient()
    conn = psycopg2.connect(os.environ["DATABASE_URL"])

    try:
        # Get PUUIDs from league_entries
        with conn.cursor() as cur:
            cur.execute(
                "SELECT DISTINCT puuid, region FROM league_entries ORDER BY updated_at DESC LIMIT %s",
                (max_players,),
            )
            players = cur.fetchall()

        print(f"Processing {len(players)} players...")

        matches_inserted = 0
        matches_skipped = 0

        for puuid, region in players:
            try:
                match_ids = client.get_match_ids(region, puuid, count=matches_per_player)
            except Exception as e:
                print(f"  Error fetching match IDs for {puuid[:8]}...: {e}")
                continue

            for mid in match_ids:
                if match_exists(conn, mid):
                    matches_skipped += 1
                    continue

                try:
                    match_data = client.get_match(region, mid)
                    insert_match(conn, match_data, region)
                    matches_inserted += 1
                except Exception as e:
                    print(f"  Error inserting match {mid}: {e}")
                    conn.rollback()
                    continue

            print(f"  {puuid[:8]}...: processed {len(match_ids)} match IDs")

        print(f"Done. Inserted: {matches_inserted}, Skipped (existing): {matches_skipped}")

    finally:
        conn.close()


if __name__ == "__main__":
    ingest_matches()
```

**Step 2: Commit**

```bash
git add src/ingest_matches.py
git commit -m "feat: add match ingestion script with full normalization"
```

---

### Task 8: Main Entrypoint

**Files:**
- Create: `src/main.py`

**Step 1: Write combined entrypoint**

```python
"""Main entrypoint: run league + match ingestion."""

import argparse

from src.ingest_leagues import ingest_leagues
from src.ingest_matches import ingest_matches


def main() -> None:
    parser = argparse.ArgumentParser(description="TFT data ingestion pipeline")
    parser.add_argument("--leagues-only", action="store_true", help="Only ingest league entries")
    parser.add_argument("--matches-only", action="store_true", help="Only ingest matches")
    parser.add_argument("--max-players", type=int, default=50, help="Max players to process")
    parser.add_argument("--matches-per-player", type=int, default=20, help="Matches per player")
    args = parser.parse_args()

    if not args.matches_only:
        print("=== Ingesting league entries ===")
        ingest_leagues()

    if not args.leagues_only:
        print("=== Ingesting matches ===")
        ingest_matches(
            max_players=args.max_players,
            matches_per_player=args.matches_per_player,
        )

    print("=== Pipeline complete ===")


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add src/main.py
git commit -m "feat: add main entrypoint for ingestion pipeline"
```

---

### Task 9: GitHub Actions Workflow

**Files:**
- Create: `.github/workflows/ingest.yml`

**Step 1: Write the workflow**

```yaml
name: TFT Data Ingestion

on:
  schedule:
    # Run every 6 hours
    - cron: '0 */6 * * *'
  workflow_dispatch: # Allow manual trigger

jobs:
  ingest:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.14
        uses: actions/setup-python@v5
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run ingestion pipeline
        env:
          RIOT_API_KEY: ${{ secrets.RIOT_API_KEY }}
          DATABASE_URL: ${{ secrets.DATABASE_URL }}
        run: python -m src.main --max-players 50 --matches-per-player 20
```

**Step 2: Commit**

```bash
git add .github/workflows/ingest.yml
git commit -m "ci: add GitHub Actions cron for TFT data ingestion"
```

---

### Task 10: Deploy and Verify End-to-End

**Step 1: Create Neon database (manual)**

1. Go to https://neon.tech → Create project `tft-analytics`
2. Copy connection string into `.env`

**Step 2: Run migration**

```bash
python schema/migrate.py
```

**Step 3: Run ingestion locally to test**

```bash
python -m src.main --max-players 5 --matches-per-player 5
```

Expected: League entries populated, matches inserted, no crashes.

**Step 4: Verify data in Neon**

```bash
python -c "
import os; import psycopg2; from dotenv import load_dotenv; load_dotenv()
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
for table in ['matches','match_participants','participant_augments','participant_traits','participant_units','unit_items','league_entries']:
    cur.execute(f'SELECT COUNT(*) FROM {table}')
    print(f'{table}: {cur.fetchone()[0]} rows')
conn.close()
"
```

**Step 5: Push to GitHub and configure secrets**

1. Create GitHub repo
2. `git remote add origin <repo-url> && git push -u origin master`
3. Go to repo Settings → Secrets → Add `RIOT_API_KEY` and `DATABASE_URL`
4. Trigger workflow manually via Actions tab to verify

**Step 6: Connect Holistics to Neon**

1. In Holistics, go to Data Sources → Add PostgreSQL
2. Use Neon connection details (host, database, user, password from connection string)
3. Verify tables are visible in Holistics

**Step 7: Final commit**

```bash
git add -A
git commit -m "docs: finalize project setup and deployment"
```
