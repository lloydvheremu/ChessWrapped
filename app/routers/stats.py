from contextlib import contextmanager

import httpx
from fastapi import APIRouter, HTTPException

from app.models.schemas import OpeningsResponse, PlayerProfile, WrappedStats
from app.services import aggregator, lichess

router = APIRouter(prefix="/api/v1", tags=["stats"])

PLAYER_NOT_FOUND = "Player not found on Lichess"
MAX_GAMES = 50


@contextmanager
def lichess_errors():
    """Translate Lichess client failures into the API's error contract."""
    try:
        yield
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Lichess request timed out")
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
        raise HTTPException(status_code=502, detail="Lichess API error")
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Lichess API error")


@router.get("/player/{username}", response_model=PlayerProfile)
async def get_player(username: str):
    with lichess_errors():
        profile = await lichess.get_player_profile(username)
    # Closed or banned accounts come back as a stub profile flagged "disabled".
    if profile.get("disabled"):
        raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
    return profile


@router.get("/wrapped/{username}", response_model=WrappedStats)
async def get_wrapped(username: str):
    with lichess_errors():
        games = await lichess.get_recent_games(username, max_games=MAX_GAMES)
    return aggregator.compute_wrapped(games, username)


@router.get("/openings/{username}", response_model=OpeningsResponse)
async def get_openings(username: str):
    with lichess_errors():
        games = await lichess.get_recent_games(username, max_games=MAX_GAMES)
    return OpeningsResponse(
        username=username, openings=aggregator.compute_openings(games, username)
    )
