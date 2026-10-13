"""PostgreSQL-backed cache for computed WrappedStats, with TTL expiry."""

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import CachedWrapped
from app.models.schemas import WrappedStats

DEFAULT_CACHE_TTL_SECONDS = 3600


def _ttl() -> timedelta:
    return timedelta(seconds=int(os.getenv("CACHE_TTL_SECONDS", DEFAULT_CACHE_TTL_SECONDS)))


def _matches(username: str):
    # Lichess usernames are case-insensitive, so the cache key is too.
    return func.lower(CachedWrapped.username) == username.lower()


async def get_cached(db: AsyncSession, username: str) -> WrappedStats | None:
    row = await db.scalar(select(CachedWrapped).where(_matches(username)))
    if row is None:
        return None

    if datetime.now(timezone.utc) - row.cached_at > _ttl():
        await db.execute(delete(CachedWrapped).where(CachedWrapped.id == row.id))
        await db.commit()
        return None

    return WrappedStats.model_validate({**row.data, "cached_at": row.cached_at})


async def set_cached(db: AsyncSession, username: str, stats: WrappedStats) -> None:
    await db.execute(delete(CachedWrapped).where(_matches(username)))
    db.add(
        CachedWrapped(
            username=username.lower(),
            data=stats.model_dump(mode="json", exclude={"cached_at"}),
            cached_at=datetime.now(timezone.utc),
        )
    )
    try:
        await db.commit()
    except IntegrityError:
        # A concurrent request cached the same player first; its row is just as fresh.
        await db.rollback()
