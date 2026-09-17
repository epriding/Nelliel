"""Dataframe conversion for Polymarket SDK objects. See ``docs/frames.md``."""

from polymarket.frames import _builtin_overrides as _  # noqa: F401
from polymarket.frames._arrow import to_arrow
from polymarket.frames._errors import MissingOptionalDependencyError
from polymarket.frames._pandas import to_pandas
from polymarket.frames._polars import to_polars

__all__ = [
    "MissingOptionalDependencyError",
    "to_arrow",
    "to_pandas",
    "to_polars",
]
