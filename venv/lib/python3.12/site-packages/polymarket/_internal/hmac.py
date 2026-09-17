import base64
import binascii
import hashlib
import hmac as _hmac

from polymarket.errors import SigningError


def build_hmac_signature(
    *,
    secret: str,
    timestamp: int,
    method: str,
    path: str,
    body: str | None = None,
) -> str:
    message = f"{timestamp}{method}{path}"
    if body is not None:
        message += body

    try:
        raw_secret = base64.urlsafe_b64decode(_pad_base64(secret))
        digest = _hmac.new(raw_secret, message.encode("utf-8"), hashlib.sha256).digest()
    except (binascii.Error, TypeError, ValueError) as error:
        raise SigningError(f"Failed to compute HMAC signature: {error}") from error
    return base64.urlsafe_b64encode(digest).decode("ascii")


def _pad_base64(value: str) -> str:
    padding = (-len(value)) % 4
    return value + ("=" * padding)


__all__ = ["build_hmac_signature"]
