from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast

from pydantic import Field, model_validator

from polymarket.models.base import BaseModel
from polymarket.types import EvmAddress, TransactionHash


class RelayerTransactionType(StrEnum):
    SAFE = "SAFE"
    PROXY = "PROXY"
    SAFE_CREATE = "SAFE-CREATE"
    WALLET = "WALLET"
    WALLET_CREATE = "WALLET-CREATE"


class RelayerTransactionState(StrEnum):
    NEW = "STATE_NEW"
    EXECUTED = "STATE_EXECUTED"
    MINED = "STATE_MINED"
    CONFIRMED = "STATE_CONFIRMED"
    INVALID = "STATE_INVALID"
    FAILED = "STATE_FAILED"


class RelayerExecuteParams(BaseModel):
    address: EvmAddress
    nonce: str

    @model_validator(mode="before")
    @classmethod
    def _validate_nonce(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(cast(dict[str, Any], value))
        nonce = data.get("nonce")
        if not isinstance(nonce, str) or not nonce or not nonce.isdigit():
            raise ValueError("relayer returned a missing or non-numeric nonce")
        return data


class RelayerExecuteResponse(BaseModel):
    state: RelayerTransactionState
    transaction_hash: TransactionHash | None = Field(
        default=None, validation_alias="transactionHash"
    )
    transaction_id: str = Field(validation_alias="transactionID")

    @model_validator(mode="before")
    @classmethod
    def _normalize_hash(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(cast(dict[str, Any], value))
        h = data.get("transactionHash")
        if h == "" or h is None:
            data["transactionHash"] = None
        return data


class GaslessTransaction(BaseModel):
    state: RelayerTransactionState
    transaction_hash: TransactionHash | None = Field(
        default=None, validation_alias="transaction_hash"
    )
    transaction_id: str = Field(validation_alias="transaction_id")
    error_msg: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_hash(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(cast(dict[str, Any], value))
        if "transaction_hash" not in data:
            raise ValueError("gasless transaction response missing transaction_hash")
        h = data["transaction_hash"]
        if h == "" or h is None:
            data["transaction_hash"] = None
        return data


class RelayerDeployedResponse(BaseModel):
    deployed: bool


@dataclass(frozen=True, slots=True)
class TransactionOutcome:
    transaction_hash: TransactionHash
    transaction_id: str | None


__all__ = [
    "GaslessTransaction",
    "RelayerDeployedResponse",
    "RelayerExecuteParams",
    "RelayerExecuteResponse",
    "RelayerTransactionState",
    "RelayerTransactionType",
    "TransactionOutcome",
]
