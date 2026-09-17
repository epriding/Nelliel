from __future__ import annotations

import asyncio
import time
from typing import Any, cast

from eth_account.signers.local import LocalAccount

from polymarket._internal.actions.relayer.calls import TransactionCall
from polymarket._internal.eoa.rpc import JsonRpcClient, SyncJsonRpcClient
from polymarket.errors import (
    SigningError,
    TimeoutError,
    TransactionFailedError,
    UnexpectedResponseError,
)
from polymarket.models.clob.relayer import TransactionOutcome
from polymarket.transactions import EoaTransactionHandle, SyncEoaTransactionHandle
from polymarket.types import TransactionHash


async def broadcast_eoa_call(
    *,
    rpc: JsonRpcClient,
    signer: LocalAccount,
    call: TransactionCall,
    chain_id: int,
    max_polls: int,
    poll_delay_s: float,
) -> EoaTransactionHandle:
    await rpc.verify_chain_id(chain_id)
    nonce = await rpc.eth_get_transaction_count(signer.address)
    gas_price = await rpc.eth_gas_price()
    estimate_payload = {
        "from": signer.address,
        "to": str(call.to),
        "value": hex(call.value),
        "data": call.data,
    }
    gas = await rpc.eth_estimate_gas(estimate_payload)
    tx = {
        "to": str(call.to),
        "value": call.value,
        "data": call.data,
        "gas": gas,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": chain_id,
    }
    try:
        signed = signer.sign_transaction(cast(Any, tx))
    except Exception as error:
        raise SigningError(f"Failed to sign EOA transaction: {error}") from error
    tx_hash = await rpc.eth_send_raw_transaction("0x" + signed.raw_transaction.hex())
    return EoaTransactionHandle(
        transaction_hash=tx_hash,
        _rpc=rpc,
        _max_polls=max_polls,
        _poll_delay_s=poll_delay_s,
    )


async def wait_for_receipt(
    rpc: JsonRpcClient,
    *,
    transaction_hash: str,
    max_polls: int,
    poll_delay_s: float,
) -> TransactionOutcome:
    for _ in range(max_polls):
        receipt = await rpc.eth_get_transaction_receipt(transaction_hash)
        if receipt is not None:
            status = receipt.get("status")
            if status in ("0x1", 1):
                return TransactionOutcome(
                    transaction_hash=cast(TransactionHash, transaction_hash),
                    transaction_id=None,
                )
            if status in ("0x0", 0):
                raise TransactionFailedError(f"EOA transaction {transaction_hash} reverted")
            raise UnexpectedResponseError(
                f"EOA transaction {transaction_hash} has unrecognized status {status!r}"
            )
        await asyncio.sleep(poll_delay_s)
    raise TimeoutError(
        f"Timed out waiting for EOA transaction {transaction_hash} after "
        f"{max_polls} polls ({max_polls * poll_delay_s:.0f}s)"
    )


def broadcast_eoa_call_sync(
    *,
    rpc: SyncJsonRpcClient,
    signer: LocalAccount,
    call: TransactionCall,
    chain_id: int,
    max_polls: int,
    poll_delay_s: float,
) -> SyncEoaTransactionHandle:
    rpc.verify_chain_id(chain_id)
    nonce = rpc.eth_get_transaction_count(signer.address)
    gas_price = rpc.eth_gas_price()
    estimate_payload = {
        "from": signer.address,
        "to": str(call.to),
        "value": hex(call.value),
        "data": call.data,
    }
    gas = rpc.eth_estimate_gas(estimate_payload)
    tx = {
        "to": str(call.to),
        "value": call.value,
        "data": call.data,
        "gas": gas,
        "gasPrice": gas_price,
        "nonce": nonce,
        "chainId": chain_id,
    }
    try:
        signed = signer.sign_transaction(cast(Any, tx))
    except Exception as error:
        raise SigningError(f"Failed to sign EOA transaction: {error}") from error
    tx_hash = rpc.eth_send_raw_transaction("0x" + signed.raw_transaction.hex())
    return SyncEoaTransactionHandle(
        transaction_hash=tx_hash,
        _rpc=rpc,
        _max_polls=max_polls,
        _poll_delay_s=poll_delay_s,
    )


def wait_for_receipt_sync(
    rpc: SyncJsonRpcClient,
    *,
    transaction_hash: str,
    max_polls: int,
    poll_delay_s: float,
) -> TransactionOutcome:
    for _ in range(max_polls):
        receipt = rpc.eth_get_transaction_receipt(transaction_hash)
        if receipt is not None:
            status = receipt.get("status")
            if status in ("0x1", 1):
                return TransactionOutcome(
                    transaction_hash=cast(TransactionHash, transaction_hash),
                    transaction_id=None,
                )
            if status in ("0x0", 0):
                raise TransactionFailedError(f"EOA transaction {transaction_hash} reverted")
            raise UnexpectedResponseError(
                f"EOA transaction {transaction_hash} has unrecognized status {status!r}"
            )
        time.sleep(poll_delay_s)
    raise TimeoutError(
        f"Timed out waiting for EOA transaction {transaction_hash} after "
        f"{max_polls} polls ({max_polls * poll_delay_s:.0f}s)"
    )


__all__ = [
    "broadcast_eoa_call",
    "broadcast_eoa_call_sync",
    "wait_for_receipt",
    "wait_for_receipt_sync",
]
