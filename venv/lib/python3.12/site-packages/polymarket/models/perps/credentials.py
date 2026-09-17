"""Delegated Perps session credentials."""

from datetime import datetime

from pydantic import Field

from polymarket.models.base import BaseModel


class PerpsCredentials(BaseModel):
    """Delegated credentials that authorize one Perps session key.

    Store these to resume a session later without a new wallet signature.
    Treat ``private_key`` and ``secret`` as secrets.
    """

    proxy: str
    """Address of the delegated session key."""
    private_key: str = Field(repr=False)
    """Private key of the delegated session key."""
    secret: str = Field(repr=False)
    """Shared secret that authenticates the session."""
    expires_at: datetime
    """When the delegated credentials expire."""

    def __repr__(self) -> str:
        return (
            f"PerpsCredentials(proxy={self.proxy!r}, private_key=<redacted>, "
            f"secret=<redacted>, expires_at={self.expires_at!r})"
        )

    def _repr_html_(self) -> str:
        from polymarket._jupyter import card

        return card(
            "PerpsCredentials  ·  redacted",
            rows=[
                ("proxy", self.proxy),
                ("private_key", "***"),
                ("secret", "***"),
                ("expires_at", str(self.expires_at)),
            ],
        )


__all__ = ["PerpsCredentials"]
