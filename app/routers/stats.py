from contextlib import contextmanager

import httpx
from fastapi import APIRouter, HTTPException

from app.services import lichess

router = APIRouter(prefix="/api/v1", tags=["stats"])

PLAYER_NOT_FOUND = "Player not found on Lichess"


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


@router.get("/player/{username}")
async def get_player(username: str):
    with lichess_errors():
        profile = await lichess.get_player_profile(username)
    # Closed or banned accounts come back as a stub profile flagged "disabled".
    if profile.get("disabled"):
        raise HTTPException(status_code=404, detail=PLAYER_NOT_FOUND)
    return profile


@router.get("/wrapped/{username}")
async def get_wrapped(username: str):
    return {}


@router.get("/openings/{username}")
async def get_openings(username: str):
    return {}
