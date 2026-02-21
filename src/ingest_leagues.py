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
                            puuid = entry["puuid"]

                            cur.execute(
                                """
                                INSERT INTO league_entries
                                    (puuid, tier, rank, league_points, wins, losses, region, updated_at)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                                ON CONFLICT (puuid, region) DO UPDATE SET
                                    tier = EXCLUDED.tier,
                                    rank = EXCLUDED.rank,
                                    league_points = EXCLUDED.league_points,
                                    wins = EXCLUDED.wins,
                                    losses = EXCLUDED.losses,
                                    updated_at = NOW()
                                """,
                                (
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
