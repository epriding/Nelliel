from decimal import Decimal, InvalidOperation

from polymarket.errors import UserInputError


def coerce_positive_decimal(name: str, value: object) -> Decimal:
    if isinstance(value, bool):
        raise UserInputError(f"{name} must be a positive number.")
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, int):
        result = Decimal(value)
    elif isinstance(value, float):
        result = Decimal(str(value))
    elif isinstance(value, str):
        try:
            result = Decimal(value)
        except (ValueError, InvalidOperation) as error:
            raise UserInputError(f"{name} must be a valid decimal number: {value!r}") from error
    else:
        raise UserInputError(f"{name} must be a number, got {type(value).__name__}.")
    if not result.is_finite() or result <= 0:
        raise UserInputError(f"{name} must be a positive number.")
    return result


__all__ = ["coerce_positive_decimal"]
