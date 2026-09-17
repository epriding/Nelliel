from polymarket.errors import UnexpectedResponseError, UserInputError

END_CURSOR = "LTE="


def validate_cursor(value: str | None) -> str | None:
    if value is None:
        return None
    if not value:
        raise UserInputError("cursor must be a non-empty string when provided.")
    return value


def next_cursor_or_none(raw: object) -> str | None:
    if raw is None:
        return None
    if not isinstance(raw, str):
        raise UnexpectedResponseError(
            f"expected next_cursor to be a string, got {type(raw).__name__}"
        )
    if raw == END_CURSOR:
        return None
    if not raw:
        raise UnexpectedResponseError(
            "expected next_cursor to be non-empty or the END_CURSOR sentinel"
        )
    return raw


def optional_int(payload: dict[str, object], key: str) -> int | None:
    if key not in payload:
        return None
    value = payload[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise UnexpectedResponseError(f"expected '{key}' to be an int, got {type(value).__name__}")
    return value


__all__ = ["END_CURSOR", "next_cursor_or_none", "optional_int", "validate_cursor"]
