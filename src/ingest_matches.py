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
