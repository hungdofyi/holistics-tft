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
