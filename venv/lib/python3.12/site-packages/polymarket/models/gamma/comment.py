"""Comment models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from pydantic import Field, field_validator, model_validator

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import ImageOptimization, parse_optional_datetime
from polymarket.models.types import CommentId, EventId, SeriesId, TokenId
from polymarket.types import EvmAddress


class CommentPosition(BaseModel):
    token_id: TokenId | None = Field(default=None, validation_alias="tokenId")
    position_size: int | None = Field(default=None, validation_alias="positionSize")


class CommentProfile(BaseModel):
    name: str | None = None
    pseudonym: str | None = None
    display_username_public: bool | None = Field(
        default=None,
        validation_alias="displayUsernamePublic",
    )
    bio: str | None = None
    is_mod: bool | None = Field(default=None, validation_alias="isMod")
    is_creator: bool | None = Field(default=None, validation_alias="isCreator")
    wallet: EvmAddress | None = Field(default=None, validation_alias="wallet")
    base_address: EvmAddress | None = Field(default=None, validation_alias="baseAddress")
    profile_image: str | None = Field(default=None, validation_alias="profileImage")
    profile_image_optimized: ImageOptimization | None = Field(
        default=None,
        validation_alias="profileImageOptimized",
    )
    positions: tuple[CommentPosition, ...] | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_profile(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        data = dict(cast(dict[str, Any], value))
        if "wallet" not in data:
            data["wallet"] = data.get("proxyWallet")
        return data


class Reaction(BaseModel):
    id: str
    comment_id: int | None = Field(default=None, validation_alias="commentID")
    reaction_type: str | None = Field(default=None, validation_alias="reactionType")
    icon: str | None = None
    user_address: EvmAddress | None = Field(default=None, validation_alias="userAddress")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    profile: CommentProfile | None = None

    @field_validator("created_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)


class CommentMedia(BaseModel):
    id: str
    comment_id: int | None = Field(default=None, validation_alias="commentID")
    provider: str | None = None
    provider_media_id: str | None = Field(default=None, validation_alias="providerMediaId")
    url: str | None = None
    media_type: str | None = Field(default=None, validation_alias="mediaType")
    alt_text: str | None = Field(default=None, validation_alias="altText")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")

    @field_validator("created_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)


class Comment(BaseModel):
    id: CommentId
    body: str | None = None
    parent_entity_type: str | None = Field(default=None, validation_alias="parentEntityType")
    parent_entity_id: EventId | SeriesId | None = Field(
        default=None,
        validation_alias="parentEntityID",
    )
    parent_comment_id: CommentId | None = Field(default=None, validation_alias="parentCommentID")
    user_address: EvmAddress | None = Field(default=None, validation_alias="userAddress")
    reply_address: EvmAddress | None = Field(default=None, validation_alias="replyAddress")
    created_at: datetime | None = Field(default=None, validation_alias="createdAt")
    updated_at: datetime | None = Field(default=None, validation_alias="updatedAt")
    media: tuple[CommentMedia, ...] | None = None
    profile: CommentProfile | None = None
    reactions: tuple[Reaction, ...] | None = None
    report_count: int | None = Field(default=None, validation_alias="reportCount")
    reaction_count: int | None = Field(default=None, validation_alias="reactionCount")
    trade_asset: str | None = Field(default=None, validation_alias="tradeAsset")

    @model_validator(mode="before")
    @classmethod
    def _normalize_comment(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value

        data = dict(cast(dict[str, Any], value))
        for key in ("parentEntityID", "parentCommentID"):
            if key in data and data[key] is not None:
                data[key] = str(data[key])
        return data

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def _parse_datetime(cls, value: object) -> datetime | None:
        return parse_optional_datetime(value)


__all__ = [
    "Comment",
    "CommentMedia",
    "CommentPosition",
    "CommentProfile",
    "Reaction",
]
