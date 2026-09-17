from __future__ import annotations

from typing import Any, cast

from eth_account.messages import encode_typed_data
from eth_account.signers.local import LocalAccount
from eth_utils.hexadecimal import decode_hex

from polymarket._internal.actions.relayer.calls import TransactionCall
from polymarket.errors import SigningError
from polymarket.types import EvmAddress, HexString

_DOMAIN_NAME = "DepositWallet"
_DOMAIN_VERSION = "1"

_CALL_FIELDS = [
    {"name": "target", "type": "address"},
    {"name": "value", "type": "uint256"},
    {"name": "data", "type": "bytes"},
]

_BATCH_FIELDS = [
    {"name": "wallet", "type": "address"},
    {"name": "nonce", "type": "uint256"},
    {"name": "deadline", "type": "uint256"},
    {"name": "calls", "type": "Call[]"},
]


def build_deposit_wallet_typed_data(
    *,
    wallet: EvmAddress,
    calls: list[TransactionCall],
    nonce: str,
    deadline: str,
    chain_id: int,
) -> dict[str, Any]:
    return {
        "domain": {
            "chainId": chain_id,
            "name": _DOMAIN_NAME,
            "verifyingContract": str(wallet),
            "version": _DOMAIN_VERSION,
        },
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "version", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "Batch": _BATCH_FIELDS,
            "Call": _CALL_FIELDS,
        },
        "primaryType": "Batch",
        "message": {
            "wallet": str(wallet),
            "nonce": int(nonce),
            "deadline": int(deadline),
            "calls": [
                {
                    "target": str(call.to),
                    "value": call.value,
                    "data": decode_hex(call.data),
                }
                for call in calls
            ],
        },
    }


def sign_deposit_wallet_batch(
    signer: LocalAccount,
    *,
    wallet: EvmAddress,
    calls: list[TransactionCall],
    nonce: str,
    deadline: str,
    chain_id: int,
) -> HexString:
    typed = build_deposit_wallet_typed_data(
        wallet=wallet,
        calls=calls,
        nonce=nonce,
        deadline=deadline,
        chain_id=chain_id,
    )
    try:
        signable = encode_typed_data(full_message=typed)
        signed = signer.sign_message(signable)
    except Exception as error:
        raise SigningError(f"Failed to sign deposit-wallet batch: {error}") from error
    return cast(HexString, "0x" + signed.signature.hex())


__all__ = ["build_deposit_wallet_typed_data", "sign_deposit_wallet_batch"]
