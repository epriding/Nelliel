"""Perps command signing.

Trading commands and owner operations are signed as EIP-712 ``Op`` payloads
whose ``data`` field commits to the msgpack encoding of the positional
command tuple.
"""

import secrets
import time
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias, cast

import msgpack  # pyright: ignore[reportMissingTypeStubs]
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_utils.crypto import keccak

from polymarket.errors import SigningError
from polymarket.types import HexString

PerpsSignableValue: TypeAlias = (
    "bool | int | str | None | Sequence[PerpsSignableValue] | Mapping[str, PerpsSignableValue]"
)
PerpsSignedOp: TypeAlias = Sequence[PerpsSignableValue]

_EIP712_DOMAIN_FIELDS = [
    {"name": "name", "type": "string"},
    {"name": "version", "type": "string"},
    {"name": "chainId", "type": "uint256"},
]
_OP_FIELDS = [
    {"name": "data", "type": "bytes32"},
    {"name": "salt", "type": "uint64"},
    {"name": "ts", "type": "uint64"},
]


def compact_signable_value(value: PerpsSignableValue) -> PerpsSignableValue:
    """Drop ``None`` entries from sequences recursively, matching the server."""
    if isinstance(value, (list, tuple)):
        return [compact_signable_value(item) for item in value if item is not None]
    return value


def hash_perps_op(op: PerpsSignableValue) -> HexString:
    packed = cast(
        bytes,
        msgpack.packb(compact_signable_value(op)),  # pyright: ignore[reportUnknownMemberType]
    )
    return HexString("0x" + keccak(packed).hex())


def build_perps_op_typed_data(
    *, chain_id: int, op: PerpsSignableValue, salt: int, timestamp_ms: int
) -> dict[str, Any]:
    return {
        "types": {"EIP712Domain": _EIP712_DOMAIN_FIELDS, "Op": _OP_FIELDS},
        "primaryType": "Op",
        "domain": {"name": "Polymarket", "version": "1", "chainId": chain_id},
        "message": {"data": hash_perps_op(op), "salt": salt, "ts": timestamp_ms},
    }


def sign_perps_op(
    signer: LocalAccount,
    *,
    chain_id: int,
    op: PerpsSignableValue,
    salt: int,
    timestamp_ms: int,
) -> HexString:
    payload = build_perps_op_typed_data(
        chain_id=chain_id, op=op, salt=salt, timestamp_ms=timestamp_ms
    )
    try:
        signed = signer.sign_typed_data(full_message=payload)
    except Exception as error:
        raise SigningError(f"Could not sign the Perps command: {error}") from error
    return _to_hex_signature(bytes(signed.signature))


def sign_perps_op_with_key(
    private_key: str,
    *,
    chain_id: int,
    op: PerpsSignableValue,
    salt: int,
    timestamp_ms: int,
) -> HexString:
    try:
        signer = Account.from_key(private_key)
    except (ValueError, TypeError) as error:
        raise SigningError(f"Invalid Perps session private key: {error}") from error
    return sign_perps_op(signer, chain_id=chain_id, op=op, salt=salt, timestamp_ms=timestamp_ms)


def build_perps_create_proxy_typed_data(
    *, chain_id: int, proxy: str, expires_at_ms: int, salt: int, timestamp_ms: int
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": _EIP712_DOMAIN_FIELDS,
            "CreateProxy": [
                {"name": "addr", "type": "address"},
                {"name": "exp", "type": "uint64"},
                {"name": "salt", "type": "uint64"},
                {"name": "ts", "type": "uint64"},
            ],
        },
        "primaryType": "CreateProxy",
        "domain": {"name": "Polymarket", "version": "1", "chainId": chain_id},
        "message": {"addr": proxy, "exp": expires_at_ms, "salt": salt, "ts": timestamp_ms},
    }


def build_perps_withdraw_typed_data(
    *,
    chain_id: int,
    deposit_contract: str,
    account: str,
    token: str,
    amount: int,
    to: str,
    salt: int,
    timestamp_s: int,
) -> dict[str, Any]:
    return {
        "types": {
            "EIP712Domain": [
                *_EIP712_DOMAIN_FIELDS,
                {"name": "verifyingContract", "type": "address"},
            ],
            "Withdraw": [
                {"name": "account", "type": "address"},
                {"name": "token", "type": "address"},
                {"name": "amount", "type": "uint256"},
                {"name": "fee", "type": "uint256"},
                {"name": "to", "type": "address"},
                {"name": "salt", "type": "uint64"},
                {"name": "ts", "type": "uint64"},
            ],
        },
        "primaryType": "Withdraw",
        "domain": {
            "name": "Polymarket",
            "version": "1",
            "chainId": chain_id,
            "verifyingContract": deposit_contract,
        },
        "message": {
            "account": account,
            "token": token,
            "amount": amount,
            "fee": 0,
            "to": to,
            "salt": salt,
            "ts": timestamp_s,
        },
    }


def sign_owner_typed_data(signer: LocalAccount, payload: dict[str, Any], *, what: str) -> HexString:
    try:
        signed = signer.sign_typed_data(full_message=payload)
    except Exception as error:
        raise SigningError(f"Could not sign the {what}: {error}") from error
    return _to_hex_signature(bytes(signed.signature))


def random_perps_salt() -> int:
    return secrets.randbits(32)


def now_ms() -> int:
    return int(time.time() * 1000)


def _to_hex_signature(signature: bytes) -> HexString:
    return HexString("0x" + signature.hex())


__all__ = [
    "PerpsSignableValue",
    "PerpsSignedOp",
    "build_perps_create_proxy_typed_data",
    "build_perps_op_typed_data",
    "build_perps_withdraw_typed_data",
    "compact_signable_value",
    "hash_perps_op",
    "now_ms",
    "random_perps_salt",
    "sign_owner_typed_data",
    "sign_perps_op",
    "sign_perps_op_with_key",
]
