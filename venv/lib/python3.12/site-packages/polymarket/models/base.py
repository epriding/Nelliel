"""Base model configuration for SDK objects."""

from typing import Self, cast

from pydantic import BaseModel as PydanticBaseModel
from pydantic import ConfigDict, ValidationError

from polymarket.errors import UnexpectedResponseError


class BaseModel(PydanticBaseModel):
    """Base model for immutable SDK objects."""

    model_config = ConfigDict(
        extra="ignore",
        frozen=True,
        populate_by_name=True,
    )

    @classmethod
    def parse_response(cls, data: object) -> Self:
        """Parse response data into this SDK object."""
        try:
            return cls.model_validate(data)
        except ValidationError as error:
            raise UnexpectedResponseError(
                f"{cls.__name__} response did not match expected shape"
            ) from error

    @classmethod
    def parse_response_list(cls, data: object) -> tuple[Self, ...]:
        """Parse response data into a tuple of SDK objects."""
        if not isinstance(data, list):
            raise UnexpectedResponseError(f"{cls.__name__} response did not match expected shape")

        items = cast(list[object], data)
        return tuple(cls.parse_response(item) for item in items)


__all__ = ["BaseModel"]
