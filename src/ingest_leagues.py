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
