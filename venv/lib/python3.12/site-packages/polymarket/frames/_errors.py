"""Errors raised by :mod:`polymarket.frames`."""

from __future__ import annotations


class MissingOptionalDependencyError(ImportError):
    """An optional dependency required by a frames operation is not installed."""


__all__ = ["MissingOptionalDependencyError"]
