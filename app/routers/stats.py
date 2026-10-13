from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["stats"])


@router.get("/player/{username}")
async def get_player(username: str):
    return {}


@router.get("/wrapped/{username}")
async def get_wrapped(username: str):
    return {}


@router.get("/openings/{username}")
async def get_openings(username: str):
    return {}
