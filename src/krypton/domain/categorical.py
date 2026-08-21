"""Generic categorical values whose vocabularies are supplied by the caller."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoricalValue(BaseModel):
    """A non-numerical value identified by an external or project vocabulary.

    The public core deliberately contains no biological vocabulary members. A
    local evidence pack is responsible for validating values against its pinned
    vocabulary before constructing this object.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["categorical"]
    vocabulary_id: str = Field(min_length=1)
    value: str = Field(min_length=1)

    @field_validator("vocabulary_id", "value")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("categorical vocabulary and value must not be blank")
        return value

