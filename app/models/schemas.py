"""Pydantic response models."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict


def _round2(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


# Every float in a response is rounded to 2 decimal places.
Rate = Annotated[float, AfterValidator(_round2)]
OptionalRate = Annotated[float | None, AfterValidator(_round2)]


class PlayerProfile(BaseModel):
    id: str
    username: str
    title: str | None = None
    patron: bool = False
    perfs: dict  # raw per-time-control ratings, as Lichess returns them
    createdAt: int
    seenAt: int | None = None
    playTime: dict | None = None
    url: str
    count: dict | None = None
    profile: dict | None = None  # bio fields, including the country flag


class OpeningStat(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    eco: str
    name: str | None
    games_played: int
    win_rate: Rate


class BestGame(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    game_id: str
    accuracy: OptionalRate
    opponent: str
    result: str  # "win" | "draw" | "loss"
    url: str


class WrappedStats(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    period: str  # always "last_50_games" for now
    total_games: int
    win_rate: Rate
    draw_rate: Rate
    loss_rate: Rate
    best_streak: int
    favourite_time_control: str
    favourite_opening: OpeningStat | None
    best_accuracy_game: BestGame | None
    cached_at: datetime | None = None


class OpeningsResponse(BaseModel):
    username: str
    openings: list[OpeningStat]  # top 5, sorted by games_played desc
