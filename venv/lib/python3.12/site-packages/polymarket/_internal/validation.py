from polymarket.errors import UserInputError
from polymarket.types import HexString

_BUILDER_CODE_LENGTH = 66


def require_nonempty(name: str, value: object) -> str:
    if not isinstance(value, str):
        raise UserInputError(f"{name} must be a string, got {type(value).__name__}.")
    if not value:
        raise UserInputError(f"{name} is required")
    return value


def validate_builder_code(value: object) -> HexString:
    if not isinstance(value, str):
        raise UserInputError(
            f"builder_code must be a 32-byte hex string, got {type(value).__name__}."
        )
    if len(value) != _BUILDER_CODE_LENGTH or not value.startswith("0x"):
        raise UserInputError("builder_code must be a 32-byte hex string (0x-prefixed, 66 chars).")
    try:
        int(value[2:], 16)
    except ValueError as error:
        raise UserInputError("builder_code must be a 32-byte hex string.") from error
    return HexString(value)


__all__ = ["require_nonempty", "validate_builder_code"]
