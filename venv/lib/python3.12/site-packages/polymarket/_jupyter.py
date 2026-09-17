"""Internal HTML helpers for ``_repr_html_`` on SDK models and containers."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import wraps
from html import escape
from typing import Any, TypeVar

_CARD_STYLE = (
    "font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;"
    "font-size: 12px;"
    "border: 1px solid #d0d7de;"
    "border-radius: 4px;"
    "padding: 6px 10px;"
    "display: inline-block;"
    "background: #f6f8fa;"
    "color: #1f2328;"
)
_TITLE_STYLE = "font-weight: 600; margin-bottom: 4px;"
_TABLE_STYLE = "border-collapse: collapse;"
_KEY_STYLE = "color: #57606a; padding-right: 8px; vertical-align: top;"
_VALUE_STYLE = "vertical-align: top;"
_HINT_STYLE = "color: #57606a; margin-top: 4px; font-style: italic;"


def card(
    title: str,
    rows: Iterable[tuple[str, str]] | None = None,
    *,
    hint: str | None = None,
) -> str:
    """Render a small HTML card; all strings are HTML-escaped here."""
    title_html = f'<div style="{_TITLE_STYLE}">{escape(title)}</div>'
    rows_html = ""
    if rows:
        cells = "".join(
            f'<tr><td style="{_KEY_STYLE}">{escape(k)}</td>'
            f'<td style="{_VALUE_STYLE}">{escape(v)}</td></tr>'
            for k, v in rows
        )
        if cells:
            rows_html = f'<table style="{_TABLE_STYLE}">{cells}</table>'
    hint_html = f'<div style="{_HINT_STYLE}">{escape(hint)}</div>' if hint else ""
    return f'<div style="{_CARD_STYLE}">{title_html}{rows_html}{hint_html}</div>'


def truncate_mid(s: str | None, *, head: int = 6, tail: int = 4) -> str:
    if s is None:
        return "—"
    if len(s) <= head + tail + 1:
        return s
    return f"{s[:head]}…{s[-tail:]}"


F = TypeVar("F", bound=Callable[..., str])


def safe_html_repr(fn: F) -> F:
    """Decorator: on exception, fall back to ``repr(self)`` so cells never crash."""

    @wraps(fn)
    def wrapper(self: Any) -> str:
        try:
            return fn(self)
        except Exception:  # noqa: BLE001
            return escape(repr(self))

    return wrapper  # type: ignore[return-value]


__all__ = ["card", "safe_html_repr", "truncate_mid"]
