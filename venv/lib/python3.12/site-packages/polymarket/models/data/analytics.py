from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_optional_decimal
from polymarket.models.types import CtfConditionId, TokenId, validate_optional_ctf_condition_id
from polymarket.types import EvmAddress

OpenInterestMarket = CtfConditionId | Literal["GLOBAL"]


class MarketVolume(BaseModel):
    market: CtfConditionId | None = None
    value: Decimal | None = None

    @field_validator("market", mode="before")
    @classmethod
    def _validate_market(cls, value: object) -> CtfConditionId | None:
        return validate_optional_ctf_condition_id(value)

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class LiveVolume(BaseModel):
    total: Decimal | None = None
    markets: tuple[MarketVolume, ...] | None = None

    @field_validator("total", mode="before")
    @classmethod
    def _parse_total(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class OpenInterest(BaseModel):
    market: OpenInterestMarket | None = None
    value: Decimal | None = None

    @field_validator("market", mode="before")
    @classmethod
    def _validate_market(cls, value: object) -> OpenInterestMarket | None:
        if value == "GLOBAL":
            return "GLOBAL"
        return validate_optional_ctf_condition_id(value)

    @field_validator("value", mode="before")
    @classmethod
    def _parse_value(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class Holder(BaseModel):
    wallet: EvmAddress | None = Field(default=None, validation_alias="proxyWallet")
    token_id: TokenId | None = Field(default=None, validation_alias="asset")
    amount: Decimal | None = None
    outcome_index: int | None = Field(default=None, validation_alias="outcomeIndex")
    name: str | None = None
    pseudonym: str | None = None
    bio: str | None = None
    display_username_public: bool | None = Field(
        default=None, validation_alias="displayUsernamePublic"
    )
    profile_image: str | None = Field(default=None, validation_alias="profileImage")
    profile_image_optimized: str | None = Field(
        default=None, validation_alias="profileImageOptimized"
    )

    @field_validator("amount", mode="before")
    @classmethod
    def _parse_amount(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class MetaHolder(BaseModel):
    token: str | None = None
    holders: tuple[Holder, ...] | None = None


__all__ = [
    "Holder",
    "LiveVolume",
    "MarketVolume",
    "MetaHolder",
    "OpenInterest",
]
