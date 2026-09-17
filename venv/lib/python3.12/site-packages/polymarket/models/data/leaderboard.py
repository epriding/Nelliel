from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_optional_datetime, parse_optional_decimal
from polymarket.types import EvmAddress

BuilderVolumeTimePeriod = Literal["DAY", "WEEK", "MONTH", "ALL"]
LeaderboardTimePeriod = Literal["DAY", "WEEK", "MONTH", "ALL"]
LeaderboardCategory = Literal[
    "OVERALL",
    "POLITICS",
    "SPORTS",
    "CRYPTO",
    "CULTURE",
    "MENTIONS",
    "WEATHER",
    "ECONOMICS",
    "TECH",
    "FINANCE",
]
LeaderboardOrderBy = Literal["PNL", "VOL"]


class BuilderVolumeEntry(BaseModel):
    bucket_at: datetime | None = Field(default=None, validation_alias="dt")
    builder: str | None = None
    builder_logo: str | None = Field(default=None, validation_alias="builderLogo")
    verified: bool | None = None
    volume: Decimal | None = None
    active_users: int | None = Field(default=None, validation_alias="activeUsers")
    rank: str | None = None

    @field_validator("bucket_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)

    @field_validator("volume", mode="before")
    @classmethod
    def _parse_volume(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class LeaderboardEntry(BaseModel):
    rank: str | None = None
    builder: str | None = None
    volume: Decimal | None = None
    active_users: int | None = Field(default=None, validation_alias="activeUsers")
    verified: bool | None = None
    builder_logo: str | None = Field(default=None, validation_alias="builderLogo")

    @field_validator("volume", mode="before")
    @classmethod
    def _parse_volume(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class TraderLeaderboardEntry(BaseModel):
    rank: str | None = None
    wallet: EvmAddress | None = Field(default=None, validation_alias="proxyWallet")
    user_name: str | None = Field(default=None, validation_alias="userName")
    vol: Decimal | None = None
    pnl: Decimal | None = None
    profile_image: str | None = Field(default=None, validation_alias="profileImage")
    x_username: str | None = Field(default=None, validation_alias="xUsername")
    verified_badge: bool | None = Field(default=None, validation_alias="verifiedBadge")

    @field_validator("vol", "pnl", mode="before")
    @classmethod
    def _parse_decimal(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


__all__ = [
    "BuilderVolumeEntry",
    "BuilderVolumeTimePeriod",
    "LeaderboardCategory",
    "LeaderboardEntry",
    "LeaderboardOrderBy",
    "LeaderboardTimePeriod",
    "TraderLeaderboardEntry",
]
