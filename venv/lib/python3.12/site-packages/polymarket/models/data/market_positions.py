from __future__ import annotations

from decimal import Decimal

from pydantic import Field, field_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import parse_optional_decimal
from polymarket.models.types import CtfConditionId, TokenId, validate_optional_ctf_condition_id
from polymarket.types import EvmAddress


class MarketPosition(BaseModel):
    wallet: EvmAddress | None = Field(default=None, validation_alias="proxyWallet")
    name: str | None = None
    profile_image: str | None = Field(default=None, validation_alias="profileImage")
    verified: bool | None = None
    token_id: TokenId | None = Field(default=None, validation_alias="asset")
    condition_id: CtfConditionId | None = Field(default=None, validation_alias="conditionId")
    avg_price: Decimal | None = Field(default=None, validation_alias="avgPrice")
    size: Decimal | None = None
    cur_price: Decimal | None = Field(default=None, validation_alias="currPrice")
    current_value: Decimal | None = Field(default=None, validation_alias="currentValue")
    cash_pnl: Decimal | None = Field(default=None, validation_alias="cashPnl")
    total_bought: Decimal | None = Field(default=None, validation_alias="totalBought")
    realized_pnl: Decimal | None = Field(default=None, validation_alias="realizedPnl")
    total_pnl: Decimal | None = Field(default=None, validation_alias="totalPnl")
    outcome: str | None = None
    outcome_index: int | None = Field(default=None, validation_alias="outcomeIndex")

    @field_validator("condition_id", mode="before")
    @classmethod
    def _validate_condition_id(cls, value: object) -> CtfConditionId | None:
        return validate_optional_ctf_condition_id(value)

    @field_validator(
        "avg_price",
        "size",
        "cur_price",
        "current_value",
        "cash_pnl",
        "total_bought",
        "realized_pnl",
        "total_pnl",
        mode="before",
    )
    @classmethod
    def _parse_decimal(cls, value: object) -> Decimal | None:
        return parse_optional_decimal(value)


class MetaMarketPosition(BaseModel):
    token: str | None = None
    positions: tuple[MarketPosition, ...] | None = None


__all__ = ["MarketPosition", "MetaMarketPosition"]
