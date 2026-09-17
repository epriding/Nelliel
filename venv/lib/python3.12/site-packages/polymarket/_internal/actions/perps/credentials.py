"""Perps delegated credentials lifecycle."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

from eth_account import Account
from eth_account.signers.local import LocalAccount

from polymarket._internal.actions.perps.paging import as_json_dict
from polymarket._internal.actions.perps.signing import (
    build_perps_create_proxy_typed_data,
    now_ms,
    random_perps_salt,
    sign_owner_typed_data,
    sign_perps_op,
)
from polymarket.clients._transport import AsyncTransport
from polymarket.errors import (
    RequestRejectedError,
    UnexpectedResponseError,
    UserInputError,
)
from polymarket.models.perps.account import PerpsCredentialsInfo
from polymarket.models.perps.credentials import PerpsCredentials

DEFAULT_CREDENTIAL_TTL = timedelta(days=7)


def credential_headers(credentials: PerpsCredentials) -> dict[str, str]:
    return {
        "POLYMARKET-PROXY": credentials.proxy,
        "POLYMARKET-SECRET": credentials.secret,
    }


async def create_credentials(
    perps: AsyncTransport,
    *,
    signer: LocalAccount,
    chain_id: int,
    expires_in: timedelta,
    label: str | None,
) -> PerpsCredentials:
    if expires_in <= timedelta(0):
        raise UserInputError("expires_in must be positive")
    if label is not None and not label:
        raise UserInputError("label must be non-empty when provided")
    private_key = "0x" + secrets.token_bytes(32).hex()
    proxy = cast(LocalAccount, Account.from_key(private_key)).address
    timestamp = now_ms()
    expires_at_ms = timestamp + int(expires_in.total_seconds() * 1000)
    salt = random_perps_salt()
    signature = sign_owner_typed_data(
        signer,
        build_perps_create_proxy_typed_data(
            chain_id=chain_id,
            proxy=proxy,
            expires_at_ms=expires_at_ms,
            salt=salt,
            timestamp_ms=timestamp,
        ),
        what="Perps proxy credentials request",
    )
    body: dict[str, object] = {
        "op": {
            "type": "createProxy",
            "args": {"expiry": expires_at_ms, "owner": signer.address, "proxy": proxy},
        },
        "salt": salt,
        "sig": signature,
        "ts": timestamp,
    }
    if label is not None:
        body["label"] = label
    response = as_json_dict(await perps.post_json("/v1/account/proxy", json=body))
    secret = response.get("secret") if response is not None else None
    if not isinstance(secret, str) or not secret:
        raise UnexpectedResponseError("Perps credentials response did not match expected shape")
    credentials = PerpsCredentials(
        proxy=proxy,
        private_key=private_key,
        secret=secret,
        expires_at=datetime.fromtimestamp(expires_at_ms / 1000, tz=UTC),
    )
    return await validate_credentials(perps, signer_address=signer.address, credentials=credentials)


async def resume_credentials(
    perps: AsyncTransport,
    *,
    signer_address: str,
    credentials: PerpsCredentials,
) -> PerpsCredentials:
    try:
        derived = cast(LocalAccount, Account.from_key(credentials.private_key)).address
    except (ValueError, TypeError) as error:
        raise UserInputError(f"Invalid Perps credentials private key: {error}") from error
    if derived.lower() != credentials.proxy.lower():
        raise UserInputError("Perps credentials private key does not match the proxy address.")
    return await validate_credentials(perps, signer_address=signer_address, credentials=credentials)


async def validate_credentials(
    perps: AsyncTransport,
    *,
    signer_address: str,
    credentials: PerpsCredentials,
) -> PerpsCredentials:
    response = PerpsCredentialsInfo.parse_response(
        await perps.get_json("/v1/account/credentials", headers=credential_headers(credentials))
    )
    if response.address.lower() != signer_address.lower():
        raise UnexpectedResponseError("Perps credentials belong to a different signer account.")
    proxy_key = next(
        (key for key in response.keys if key.proxy.lower() == credentials.proxy.lower()),
        None,
    )
    if proxy_key is None:
        raise UnexpectedResponseError("Perps credentials were not returned by the API.")
    if proxy_key.expires_at <= datetime.now(tz=UTC):
        raise UnexpectedResponseError("Perps credentials are expired.")
    return credentials.model_copy(update={"expires_at": proxy_key.expires_at})


async def revoke_credentials(
    perps: AsyncTransport,
    *,
    signer: LocalAccount,
    chain_id: int,
    proxy: str,
) -> None:
    if not isinstance(proxy, str) or not proxy.startswith("0x") or len(proxy) != 42:  # pyright: ignore[reportUnnecessaryIsInstance]
        raise UserInputError(f"proxy must be an EVM address, got {proxy!r}")
    salt = random_perps_salt()
    timestamp = now_ms()
    signature = sign_perps_op(
        signer,
        chain_id=chain_id,
        op=["deleteProxy", [proxy]],
        salt=salt,
        timestamp_ms=timestamp,
    )
    response = as_json_dict(
        await perps.delete_json(
            "/v1/account/proxy",
            json={
                "op": {"type": "deleteProxy", "args": {"proxy": proxy}},
                "salt": salt,
                "sig": signature,
                "ts": timestamp,
            },
        )
    )
    if response is None or response.get("status") not in ("ok", "err"):
        raise UnexpectedResponseError(
            "Perps credentials revocation response did not match expected shape"
        )
    if response["status"] == "err":
        error = response.get("error")
        raise RequestRejectedError(
            str(error) if error else "Perps credentials revocation was rejected.",
            status=200,
        )


__all__ = [
    "DEFAULT_CREDENTIAL_TTL",
    "create_credentials",
    "credential_headers",
    "resume_credentials",
    "revoke_credentials",
    "validate_credentials",
]
