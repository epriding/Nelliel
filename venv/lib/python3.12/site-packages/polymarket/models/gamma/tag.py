"""Tag models."""

from __future__ import annotations

from pydantic import Field

from polymarket.models.base import BaseModel
from polymarket.models.gamma.common import TagReference, TemplateReference


class Tag(TagReference):
    templates: tuple[TemplateReference, ...] | None = None


class RelatedTag(BaseModel):
    id: str
    tag_id: int | None = Field(default=None, validation_alias="tagID")
    related_tag_id: int | None = Field(default=None, validation_alias="relatedTagID")
    rank: int | None = None


__all__ = ["RelatedTag", "Tag"]
