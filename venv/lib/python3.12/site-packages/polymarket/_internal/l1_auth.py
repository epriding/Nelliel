from dataclasses import dataclass
from typing import Any

from eth_account.signers.local import LocalAccount

from polymarket.errors import SigningError

_CLOB_AUTH_MESSAGE = "This message attests that I control the given wallet"


@dataclass(frozen=True, slots=True)
class ApiKeyAuthSignature:
    address: str
    nonce: int
    signature: str
    timestamp: int


def build_api_key_auth_typed_data(
    *,
    address: str,
    chain_id: int,
    timestamp: int,
    nonce: int = 0,
) -> dict[str, Any]:
    return {
        "domain": {
            "name": "ClobAuthDomain",
            "version": "1",
            "chainId": chain_id,
        },
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "ClobAuth": [
                {"name": "address", "type": "address"},
                {"name": "timestamp", "type": "string"},
                {"name": "nonce", "type": "uint256"},
                {"name": "message", "type": "string"},
            ],
        },
        "primaryType": "ClobAuth",
        "message": {
            "address": address,
            "timestamp": str(timestamp),
            "nonce": nonce,
            "message": _CLOB_AUTH_MESSAGE,
        },
    }


def sign_api_key_auth(
    signer: LocalAccount,
    *,
    chain_id: int,
    timestamp: int,
    nonce: int = 0,
) -> ApiKeyAuthSignature:
    typed_data = build_api_key_auth_typed_data(
        address=signer.address,
        chain_id=chain_id,
        timestamp=timestamp,
        nonce=nonce,
    )
    try:
        signed = signer.sign_typed_data(full_message=typed_data)
    except Exception as error:
        raise SigningError(f"Failed to sign ClobAuth message: {error}") from error
    return ApiKeyAuthSignature(
        address=signer.address,
        nonce=nonce,
        signature="0x" + signed.signature.hex(),
        timestamp=timestamp,
    )


__all__ = [
    "ApiKeyAuthSignature",
    "build_api_key_auth_typed_data",
    "sign_api_key_auth",
]
