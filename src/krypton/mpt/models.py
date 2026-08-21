"""Versioned, JSON-backed MPT request, mapping, and result models."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from math import isfinite
from typing import Any, Literal, TypeAlias

import pint
from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator, model_validator

from krypton.domain import (
    ApplicabilityContext,
    ApplicabilityResult,
    CategoricalValue,
    EvidenceRecord,
    QuantityValue,
)

_UNITS = pint.UnitRegistry()


def unit_dimension(unit: str) -> str:
    try:
        return str(_UNITS.Quantity(1, unit).dimensionality)
    except (pint.UndefinedUnitError, pint.DefinitionSyntaxError, TypeError) as error:
        raise ValueError(f"unit '{unit}' is not recognized by Pint") from error


class MappingType(StrEnum):
    IDENTITY = "identity"
    SCALE = "scale"
    LOOKUP = "lookup"
    CALLABLE = "callable"


class ParameterRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum: float | None = None
    maximum: float | None = None

    @field_validator("minimum", "maximum")
    @classmethod
    def bounds_must_be_finite(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("parameter range bounds must be finite")
        return value

    @model_validator(mode="after")
    def range_must_be_ordered(self) -> ParameterRange:
        if self.minimum is None and self.maximum is None:
            raise ValueError("parameter range requires at least one bound")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("parameter range minimum must not exceed maximum")
        return self


class TargetParameterReference(BaseModel):
    """MPT's narrow boundary reference to a future model contract parameter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str = Field(min_length=1)
    contract_version: str = Field(min_length=1)
    parameter_id: str = Field(min_length=1)
    biological_meaning: str = Field(min_length=1)
    quantity_kind: str = Field(min_length=1)
    canonical_unit: str = Field(min_length=1)
    physical_dimension: str = Field(min_length=1)
    valid_range: ParameterRange | None = None

    @field_validator(
        "contract_id",
        "contract_version",
        "parameter_id",
        "biological_meaning",
        "quantity_kind",
        "canonical_unit",
        "physical_dimension",
    )
    @classmethod
    def strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("target parameter strings must not be blank")
        return value

    @model_validator(mode="after")
    def unit_must_match_declared_dimension(self) -> TargetParameterReference:
        actual = unit_dimension(self.canonical_unit)
        if actual != self.physical_dimension:
            raise ValueError(
                f"canonical_unit '{self.canonical_unit}' has dimension '{actual}', "
                f"not declared physical_dimension '{self.physical_dimension}'"
            )
        return self


class LookupEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_value: float
    target_value: float

    @field_validator("source_value", "target_value")
    @classmethod
    def values_must_be_finite(cls, value: float) -> float:
        if not isfinite(value):
            raise ValueError("lookup values must be finite")
        return value


class MPTMappingDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    mapping_type: MappingType
    source_quantity_kind: str = Field(min_length=1)
    source_unit: str = Field(min_length=1)
    target: TargetParameterReference
    evidence_ids: tuple[str, ...]
    applicability: ApplicabilityContext
    scale_factor: float | None = None
    lookup_entries: tuple[LookupEntry, ...] = ()
    callable_name: str | None = None

    @field_validator("id", "version", "source_quantity_kind", "source_unit", "callable_name")
    @classmethod
    def strings_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("mapping identifiers and units must not be blank")
        return value

    @field_validator("source_unit")
    @classmethod
    def source_unit_must_be_known(cls, value: str) -> str:
        unit_dimension(value)
        return value

    @field_validator("evidence_ids")
    @classmethod
    def evidence_required_and_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("MPT mappings require at least one evidence_id")
        if any(not value.strip() for value in values):
            raise ValueError("mapping evidence_ids must not contain blank identifiers")
        if len(values) != len(set(values)):
            raise ValueError("mapping evidence_ids must be unique")
        return values

    @field_validator("scale_factor")
    @classmethod
    def scale_must_be_finite_and_nonzero(cls, value: float | None) -> float | None:
        if value is not None and (not isfinite(value) or value == 0):
            raise ValueError("scale_factor must be finite and non-zero")
        return value

    @model_validator(mode="after")
    def configuration_must_match_mapping_type(self) -> MPTMappingDefinition:
        configured = {
            "scale": self.scale_factor is not None,
            "lookup": bool(self.lookup_entries),
            "callable": self.callable_name is not None,
        }
        required = {
            MappingType.IDENTITY: set(),
            MappingType.SCALE: {"scale"},
            MappingType.LOOKUP: {"lookup"},
            MappingType.CALLABLE: {"callable"},
        }[self.mapping_type]
        supplied = {name for name, present in configured.items() if present}
        if supplied != required:
            raise ValueError(
                f"mapping_type '{self.mapping_type.value}' requires configuration {sorted(required)}; "
                f"received {sorted(supplied)}"
            )
        if self.mapping_type is MappingType.LOOKUP:
            keys = [entry.source_value for entry in self.lookup_entries]
            if len(keys) != len(set(keys)):
                raise ValueError("lookup source_value entries must be unique")
        if self.mapping_type is MappingType.IDENTITY:
            source_dimension = unit_dimension(self.source_unit)
            if source_dimension != self.target.physical_dimension:
                raise ValueError(
                    "identity mapping source and target units must be dimensionally compatible"
                )
        return self

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class MPTRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mapping_id: str = Field(min_length=1)
    baseline: QuantityValue
    edited: QuantityValue
    context: ApplicabilityContext
    evidence: tuple[EvidenceRecord, ...]

    @field_validator("mapping_id")
    @classmethod
    def mapping_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("mapping_id must not be blank")
        return value


class BiologicalQuantityTarget(BaseModel):
    """A model-independent biological target; never a Model Contract parameter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    target_type: Literal["biological_quantity"]
    biological_quantity_kind: str = Field(min_length=1)
    unit: str = Field(min_length=1)

    @field_validator("biological_quantity_kind", "unit")
    @classmethod
    def target_strings_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("biological target fields must not be blank")
        return value


class BiologicalMPTRequest(BaseModel):
    """Sibling request for biological mappings that require no model adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    request_type: Literal["biological_quantity"]
    mapping_id: str = Field(min_length=1)
    target: BiologicalQuantityTarget
    baseline: QuantityValue
    edited: QuantityValue
    context: ApplicabilityContext
    evidence: tuple[EvidenceRecord, ...]

    @field_validator("mapping_id")
    @classmethod
    def biological_mapping_id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("mapping_id must not be blank")
        return value


class MPTResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    mapping_id: str
    mapping_version: str
    mapping_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_ids: tuple[str, ...]
    applicability_result: ApplicabilityResult
    target: TargetParameterReference
    baseline: QuantityValue
    edited: QuantityValue
    warnings: tuple[str, ...] = ()


# The completed C0 numerical result is the ParameterEffect contract.  The alias
# deliberately preserves its class and serialized representation byte-for-byte.
ParameterEffect = MPTResult


class CategoricalDirection(StrEnum):
    INCREASED = "increased"
    DECREASED = "decreased"
    UNCHANGED = "unchanged"
    INDETERMINATE = "indeterminate"


class CategoricalEffect(BaseModel):
    """A qualitative comparison; direction is never numerical subtraction."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_type: Literal["categorical_effect"]
    target_semantic_kind: str = Field(min_length=1)
    baseline: CategoricalValue
    edited: CategoricalValue
    direction: CategoricalDirection
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]
    applicability: ApplicabilityContext
    warnings: tuple[str, ...]
    reason_code: str | None = None

    @field_validator("target_semantic_kind", "mapping_id", "mapping_version")
    @classmethod
    def identifiers_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("categorical effect identifiers must not be blank")
        return value

    @field_validator("reason_code")
    @classmethod
    def reason_code_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("categorical effect reason_code must not be blank")
        return value

    @field_validator("evidence_ids", "warnings")
    @classmethod
    def text_lists_must_be_valid(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("categorical effect lists must not contain blank strings")
        if len(values) != len(set(values)):
            raise ValueError("categorical effect lists must not contain duplicates")
        return values


class QuantitativeResultSemantics(BaseModel):
    """Closed semantics for the approved non-distribution biological interval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    interval_semantics: Literal[
        "between_study_normalized_group_mean_envelope"
    ]
    population_distribution: Literal["not_estimated"]
    individual_prediction_distribution: Literal["not_estimated"]
    confidence_interval: Literal["not_estimated"]


class QuantitativeBiologicalEffect(BaseModel):
    """A model-independent quantitative biological comparison."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    result_type: Literal["quantitative_biological_effect"]
    target_biological_quantity_kind: str = Field(min_length=1)
    baseline: QuantityValue
    edited: QuantityValue
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    evidence_ids: tuple[str, ...]
    applicability_result: ApplicabilityResult
    applicability_reference: str = Field(min_length=1)
    quantitative_semantics: QuantitativeResultSemantics
    warnings: tuple[str, ...]

    @field_validator(
        "target_biological_quantity_kind",
        "mapping_id",
        "mapping_version",
        "applicability_reference",
    )
    @classmethod
    def quantitative_identifiers_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("quantitative biological identifiers must not be blank")
        return value

    @field_validator("evidence_ids", "warnings")
    @classmethod
    def quantitative_text_lists_must_be_valid(
        cls, values: tuple[str, ...]
    ) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("quantitative biological lists must not contain blanks")
        if len(values) != len(set(values)):
            raise ValueError("quantitative biological lists must not contain duplicates")
        return values

    @model_validator(mode="after")
    def quantities_must_match_biological_target(self) -> QuantitativeBiologicalEffect:
        supported = {"fixed", "interval"}
        if (
            self.baseline.distribution.value not in supported
            or self.edited.distribution.value not in supported
        ):
            raise ValueError(
                "quantitative biological effects support only fixed or interval values"
            )
        if self.baseline.unit != self.edited.unit:
            raise ValueError(
                "baseline and edited biological quantities must use the same unit"
            )
        if (
            self.baseline.semantic_kind != self.target_biological_quantity_kind
            or self.edited.semantic_kind != self.target_biological_quantity_kind
        ):
            raise ValueError(
                "baseline and edited semantic_kind must match "
                "target_biological_quantity_kind"
            )
        return self


MPTResultValue: TypeAlias = (
    ParameterEffect | CategoricalEffect | QuantitativeBiologicalEffect
)


class MPTResultUnion(RootModel[MPTResultValue]):
    """Validation wrapper for the backward-compatible MPT result union."""

    model_config = ConfigDict(frozen=True)


class UnsupportedResultTypeError(ValueError):
    """Raised when a consumer cannot handle an explicit MPT result type."""


def parse_mpt_result(value: Any) -> MPTResultValue:
    """Route tagged biological results and untagged legacy parameter results."""

    if isinstance(value, (MPTResult, CategoricalEffect, QuantitativeBiologicalEffect)):
        return value
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise TypeError("MPT result must be a mapping, JSON string, or result model")
    result_type = value.get("result_type")
    if result_type is None:
        return MPTResultUnion.model_validate(value).root
    if result_type in {"categorical_effect", "quantitative_biological_effect"}:
        return MPTResultUnion.model_validate(value).root
    raise UnsupportedResultTypeError(
        f"unsupported_result_type: consumer does not support '{result_type}'"
    )


def require_parameter_effect(result: MPTResultValue) -> ParameterEffect:
    """Guard a model-parameter consumer against implicit biological coercion."""

    if isinstance(result, CategoricalEffect):
        raise UnsupportedResultTypeError(
            "unsupported_result_type: numerical consumer does not support "
            "'categorical_effect'"
        )
    if isinstance(result, QuantitativeBiologicalEffect):
        raise UnsupportedResultTypeError(
            "adapter_required_for_model_parameter: a quantitative biological "
            "effect cannot be used as a Model Contract parameter without an adapter"
        )
    return result
