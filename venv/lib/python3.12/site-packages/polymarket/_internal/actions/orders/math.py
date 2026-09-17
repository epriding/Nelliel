from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_EVEN, Decimal

_COLLATERAL_DECIMALS = 6
_BASE_UNIT_QUANTIZER = Decimal(1)


def parse_amount(value: Decimal) -> int:
    scaled = (value * (Decimal(10) ** _COLLATERAL_DECIMALS)).quantize(
        _BASE_UNIT_QUANTIZER, rounding=ROUND_HALF_EVEN
    )
    return int(scaled)


def round_down(value: Decimal, decimals: int) -> Decimal:
    return _round(value, decimals, ROUND_FLOOR)


def round_up(value: Decimal, decimals: int) -> Decimal:
    return _round(value, decimals, ROUND_CEILING)


def round_normal(value: Decimal, decimals: int) -> Decimal:
    return _round(value, decimals, ROUND_HALF_EVEN)


def decimal_places(value: Decimal) -> int:
    normalized = value.normalize()
    sign, digits, exponent = normalized.as_tuple()
    del sign, digits
    if isinstance(exponent, str):
        return 0
    return max(0, -exponent)


def _round(value: Decimal, decimals: int, rounding: str) -> Decimal:
    if decimal_places(value) <= decimals:
        return value
    quantizer = Decimal(10) ** -decimals
    return value.quantize(quantizer, rounding=rounding)


__all__ = [
    "decimal_places",
    "parse_amount",
    "round_down",
    "round_normal",
    "round_up",
]
