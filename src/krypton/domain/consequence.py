"""Standardized C0 phenotype consequence and simple confidence ceilings."""

from __future__ import annotations

from enum import StrEnum
from math import isclose

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from krypton.domain.applicability import ApplicabilityResult
from krypton.domain.evidence import ConfidenceLevel, EvidenceClass
from krypton.domain.quantity import DistributionType, QuantityValue


class PredictedDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    NO_CHANGE = "no_change"
    INDETERMINATE = "indeterminate"


class EvidencePathEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evidence_id: str = Field(min_length=1)
    evidence_class: EvidenceClass
    keg_edge_ids: tuple[str, ...] = ()
    mapping_id: str | None = None

    @field_validator("evidence_id", "mapping_id")
    @classmethod
    def id_not_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("evidence path IDs must not be blank")
        return value

    @field_validator("keg_edge_ids")
    @classmethod
    def edge_ids_valid(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("KEG edge IDs in an evidence path must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("KEG edge IDs in an evidence path must be unique")
        return values


class ModelVersionReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    contract_id: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("model_name", "model_version", "contract_id")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model version references must not be blank")
        return value


_CONFIDENCE_RANK = {
    ConfidenceLevel.INDETERMINATE: 0,
    ConfidenceLevel.LOW: 1,
    ConfidenceLevel.MODERATE: 2,
    ConfidenceLevel.HIGH: 3,
}


class PhenotypeConsequence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "phenotype-consequence-v0"
    id: str = Field(min_length=1)
    endpoint: str = Field(min_length=1)
    baseline: QuantityValue
    edited: QuantityValue
    delta: QuantityValue | None
    delta_propagated: bool = True
    predicted_direction: PredictedDirection
    time_horizon: str = Field(min_length=1)
    confidence: ConfidenceLevel
    applicability_assessment: ApplicabilityResult
    major_uncertainties: tuple[str, ...]
    evidence_path: tuple[EvidencePathEntry, ...]
    model_versions: tuple[ModelVersionReference, ...]
    out_of_domain_flags: tuple[str, ...] = ()
    provenance_reference: str = Field(min_length=1)
    confidence_ceiling_reasons: tuple[str, ...] = ()

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != "phenotype-consequence-v0":
            raise ValueError("C0 supports only schema_version 'phenotype-consequence-v0'")
        return value

    @field_validator("id", "endpoint", "time_horizon", "provenance_reference")
    @classmethod
    def required_text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("consequence identifiers and descriptions must not be blank")
        return value

    @field_validator("major_uncertainties", "out_of_domain_flags")
    @classmethod
    def text_lists_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("consequence text lists must not contain blank entries")
        return values

    @model_validator(mode="after")
    def validate_result_and_apply_ceilings(self) -> PhenotypeConsequence:
        if not self.major_uncertainties:
            raise ValueError("PhenotypeConsequence requires at least one major uncertainty")
        if not self.evidence_path:
            raise ValueError("PhenotypeConsequence requires a non-empty evidence path")
        if not self.model_versions:
            raise ValueError("PhenotypeConsequence requires at least one model version")
        if self.baseline.unit != self.edited.unit:
            raise ValueError("baseline and edited consequence units must be canonical and identical")

        reasons: list[str] = []
        final_confidence = self.confidence
        final_direction = self.predicted_direction
        if not self.delta_propagated:
            if self.delta is not None:
                raise ValueError("unpropagated delta must be represented as null")
            final_confidence = ConfidenceLevel.INDETERMINATE
            final_direction = PredictedDirection.INDETERMINATE
            reasons.append("delta was not propagated to the endpoint")
        else:
            if self.delta is None:
                raise ValueError("a propagated endpoint requires delta")
            if self.delta.unit != self.baseline.unit:
                raise ValueError("delta unit must match baseline and edited units")
            if (
                self.baseline.distribution is DistributionType.FIXED
                and self.edited.distribution is DistributionType.FIXED
                and self.delta.distribution is DistributionType.FIXED
            ):
                expected = self.edited.value - self.baseline.value
                if not isclose(self.delta.value, expected, rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(
                        f"delta value {self.delta.value} does not equal edited-baseline {expected}"
                    )
                expected_direction = (
                    PredictedDirection.INCREASE
                    if expected > 0
                    else PredictedDirection.DECREASE
                    if expected < 0
                    else PredictedDirection.NO_CHANGE
                )
                if self.predicted_direction is not expected_direction:
                    raise ValueError(
                        f"predicted_direction must be '{expected_direction.value}' for delta {expected}"
                    )

        low_ceiling_reasons: list[str] = []
        if (
            self.applicability_assessment is ApplicabilityResult.OUT_OF_DOMAIN
            or self.out_of_domain_flags
        ):
            low_ceiling_reasons.append("out-of-domain result")
        if self.applicability_assessment is ApplicabilityResult.UNKNOWN:
            low_ceiling_reasons.append("applicability is unresolved")
        if all(
            entry.evidence_class is EvidenceClass.SPECULATIVE_MAPPING
            for entry in self.evidence_path
        ):
            low_ceiling_reasons.append("evidence path is speculative-only")
        if low_ceiling_reasons and _CONFIDENCE_RANK[final_confidence] > _CONFIDENCE_RANK[ConfidenceLevel.LOW]:
            final_confidence = ConfidenceLevel.LOW
        reasons.extend(low_ceiling_reasons)
        object.__setattr__(self, "confidence", final_confidence)
        object.__setattr__(self, "predicted_direction", final_direction)
        object.__setattr__(self, "confidence_ceiling_reasons", tuple(reasons))
        return self
