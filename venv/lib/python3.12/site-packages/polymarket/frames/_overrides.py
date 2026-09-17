"""Per-type override registry for the Arrow conversion engine. Lookup walks the MRO."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pyarrow as pa


_REGISTRY: dict[type, Callable[[object], pa.Table]] = {}


def register_override(
    cls: type,
) -> Callable[[Callable[[object], pa.Table]], Callable[[object], pa.Table]]:
    def decorator(
        fn: Callable[[object], pa.Table],
    ) -> Callable[[object], pa.Table]:
        _REGISTRY[cls] = fn
        return fn

    return decorator


def lookup_override(cls: type) -> Callable[[object], pa.Table] | None:
    for ancestor in cls.__mro__:
        converter = _REGISTRY.get(ancestor)
        if converter is not None:
            return converter
    return None


def clear_overrides() -> None:
    _REGISTRY.clear()


def registered_types() -> tuple[type, ...]:
    return tuple(_REGISTRY.keys())


__all__ = [
    "clear_overrides",
    "lookup_override",
    "register_override",
    "registered_types",
]
