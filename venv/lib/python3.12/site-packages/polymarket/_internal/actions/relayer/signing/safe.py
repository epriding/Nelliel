from __future__ import annotations

from typing import Any, cast

from eth_account.messages import encode_defunct, encode_typed_data
from eth_account.signers.local import LocalAccount
from eth_utils.crypto import keccak
from eth_utils.hexadecimal import decode_hex

from polymarket.errors import SigningError
from polymarket.types import EvmAddress, HexString

_ZERO_ADDRESS: EvmAddress = EvmAddress("0x0000000000000000000000000000000000000000")

_SAFE_TX_FIELDS = [
    {"name": "to", "type": "address"},
    {"name": "value", "type": "uint256"},
    {"name": "data", "type": "bytes"},
    {"name": "operation", "type": "uint8"},
    {"name": "safeTxGas", "type": "uint256"},
    {"name": "baseGas", "type": "uint256"},
    {"name": "gasPrice", "type": "uint256"},
    {"name": "gasToken", "type": "address"},
    {"name": "refundReceiver", "type": "address"},
    {"name": "nonce", "type": "uint256"},
]


def build_safe_typed_data(
    *,
    safe_address: EvmAddress,
    to: EvmAddress,
    data: HexString,
    value: int,
    operation: int,
    nonce: str,
    chain_id: int,
) -> dict[str, Any]:
    return {
        "domain": {
            "chainId": chain_id,
            "verifyingContract": str(safe_address),
        },
        "types": {
            "EIP712Domain": [
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "SafeTx": _SAFE_TX_FIELDS,
        },
        "primaryType": "SafeTx",
        "message": {
            "to": str(to),
            "value": value,
            "data": decode_hex(data),
            "operation": operation,
            "safeTxGas": 0,
            "baseGas": 0,
            "gasPrice": 0,
            "gasToken": str(_ZERO_ADDRESS),
            "refundReceiver": str(_ZERO_ADDRESS),
            "nonce": int(nonce),
        },
    }


def sign_safe_transaction(
    signer: LocalAccount,
    *,
    safe_address: EvmAddress,
    to: EvmAddress,
    data: HexString,
    value: int,
    operation: int,
    nonce: str,
    chain_id: int,
) -> HexString:
    typed = build_safe_typed_data(
        safe_address=safe_address,
        to=to,
        data=data,
        value=value,
        operation=operation,
        nonce=nonce,
        chain_id=chain_id,
    )
    try:
        signable = encode_typed_data(full_message=typed)
        digest = keccak(b"\x19" + signable.version + signable.header + signable.body)
        signed = signer.sign_message(encode_defunct(primitive=digest))
    except Exception as error:
        raise SigningError(f"Failed to sign Safe transaction: {error}") from error
    return pack_safe_signature(cast(HexString, "0x" + signed.signature.hex()))


def pack_safe_signature(signature: HexString) -> HexString:
    raw = signature[2:] if signature.startswith("0x") else signature
    if len(raw) != 130:
        raise SigningError(f"Expected 65-byte signature, got {len(raw) // 2} bytes")
    v = int(raw[128:130], 16)
    if v in (0, 1):
        packed_v = v + 31
    elif v in (27, 28):
        packed_v = v + 4
    else:
        packed_v = v
    return cast(HexString, "0x" + raw[:128] + format(packed_v, "02x"))


__all__ = ["build_safe_typed_data", "pack_safe_signature", "sign_safe_transaction"]
