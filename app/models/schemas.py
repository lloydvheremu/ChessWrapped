"""Pydantic response models."""

from pydantic import BaseModel


class PlayerProfile(BaseModel):
    id: str
    username: str
    title: str | None = None
    patron: bool = False
    perfs: dict  # keep as raw dict for now — refined in M3
    createdAt: int
    seenAt: int
    playTime: dict | None = None
    url: str
    count: dict | None = None
