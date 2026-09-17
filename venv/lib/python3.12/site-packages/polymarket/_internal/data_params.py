from collections.abc import Mapping, Sequence

from polymarket._internal.request import QueryParamValue

DataParamValue = QueryParamValue | Sequence[str | int] | None


def build_data_params(
    values: Mapping[str, DataParamValue],
) -> dict[str, QueryParamValue]:
    out: dict[str, QueryParamValue] = {}
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, str | int | float | bool):
            out[key] = value
            continue
        items = list(value)
        if not items:
            continue
        out[key] = ",".join(str(item) for item in items)
    return out


__all__ = ["DataParamValue", "build_data_params"]
