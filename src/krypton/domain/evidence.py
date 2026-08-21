"""Evidence records carried through the C0 architecture."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EvidenceClass(StrEnum):
    OBSERVED_INTERVENTIONAL_HUMAN = "observed_interventional_human"
    OBSERVED_HUMAN_FUNCTIONAL = "observed_human_functional"
    OBSERVED_MODEL_SYSTEM = "observed_model_system"
    VALIDATED_COMPUTATIONAL_PREDICTION = "validated_computational_prediction"
    ASSOCIATION = "association"
    MECHANISTIC_MODEL_ASSUMPTION = "mechanistic_model_assumption"
    SPECULATIVE_MAPPING = "speculative_mapping"


class ConfidenceLevel(StrEnum):
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"
    INDETERMINATE = "indeterminate"


class CurationMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    curator: str = Field(min_length=1)
    curated_at: datetime
    notes: str | None = None

    @field_validator("curated_at")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("curated_at must include a timezone")
        return value


class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    evidence_class: EvidenceClass
    source: str = Field(min_length=1)
    identifier: str = Field(min_length=1)
    version: str = Field(min_length=1)
    claim: str = Field(min_length=1)
    applicability_reference: str = Field(min_length=1)
    confidence: ConfidenceLevel
    limitations: tuple[str, ...] = ()
    retrieval_timestamp: datetime
    curation: CurationMetadata

    @field_validator("id", "source", "identifier", "version", "claim", "applicability_reference")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("required evidence text fields must not be blank")
        return value

    @field_validator("limitations")
    @classmethod
    def limitations_must_not_be_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not item.strip() for item in values):
            raise ValueError("limitations must not contain blank entries")
        return values

    @field_validator("retrieval_timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("retrieval_timestamp must include a timezone")
        return value
