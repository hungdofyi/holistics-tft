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
