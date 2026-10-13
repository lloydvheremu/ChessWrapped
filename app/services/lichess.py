import json
import os

import httpx

DEFAULT_LICHESS_BASE_URL = "https://lichess.org/api"
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_GAMES_LIMIT = 200
# Lichess answers game exports from generic client User-Agents (python-httpx, curl)
# with a 404, so every request identifies the app instead.
USER_AGENT = "ChessWrapped/0.1 (+https://github.com/lloydvheremu/ChessWrapped)"


def _base_url() -> str:
    return os.getenv("LICHESS_BASE_URL", DEFAULT_LICHESS_BASE_URL).rstrip("/")


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}
    )


async def get_player_profile(username: str) -> dict:
    """Fetch a player's public Lichess profile."""
    async with _client() as client:
        response = await client.get(f"{_base_url()}/user/{username}")
        response.raise_for_status()
        return response.json()


async def get_recent_games(username: str, max_games: int = 50) -> list[dict]:
    """Fetch a player's most recent games (newest first).

    Lichess streams games as NDJSON: one JSON object per line, not a JSON array.
    """
    max_games = min(max_games, MAX_GAMES_LIMIT)
    params = {
        "max": max_games,
        "pgnInJson": "true",
        "opening": "true",
        "accuracy": "true",
    }
    headers = {"Accept": "application/x-ndjson"}

    async with _client() as client:
        response = await client.get(
            f"{_base_url()}/games/user/{username}", params=params, headers=headers
        )
        response.raise_for_status()
        return [json.loads(line) for line in response.text.splitlines() if line.strip()]
