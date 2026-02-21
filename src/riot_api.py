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
