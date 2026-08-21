"""Model-independent contracts and strict adapter-boundary validation."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from math import isfinite
from typing import Protocol, runtime_checkable

import pint
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from krypton.domain import (
    ApplicabilityContext,
    CategoricalValue,
    DistributionType,
    QuantityValue,
)

_UNITS = pint.UnitRegistry()


def _dimension(unit: str) -> str:
    try:
        return str(_UNITS.Quantity(1, unit).dimensionality)
    except (pint.UndefinedUnitError, pint.DefinitionSyntaxError, TypeError) as error:
        raise ValueError(f"unit '{unit}' is not recognized by Pint") from error


class ParameterType(StrEnum):
    FLOAT = "float"
    INTEGER = "integer"


class NumericRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum: float | None = None
    maximum: float | None = None
    minimum_inclusive: bool = True
    maximum_inclusive: bool = True

    @field_validator("minimum", "maximum")
    @classmethod
    def finite_bounds(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("model parameter bounds must be finite")
        return value

    @model_validator(mode="after")
    def ordered(self) -> NumericRange:
        if self.minimum is None and self.maximum is None:
            raise ValueError("a valid range requires at least one bound")
        if (
            self.minimum is not None
            and self.maximum is not None
            and self.minimum > self.maximum
        ):
            raise ValueError("range minimum must not exceed maximum")
        return self

    def contains(self, value: float) -> bool:
        if self.minimum is not None:
            if value < self.minimum or (value == self.minimum and not self.minimum_inclusive):
                return False
        if self.maximum is not None:
            if value > self.maximum or (value == self.maximum and not self.maximum_inclusive):
                return False
        return True


class _ParameterSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    biological_meaning: str = Field(min_length=1)
    quantity_kind: str = Field(min_length=1)
    canonical_unit: str = Field(min_length=1)
    physical_dimension: str = Field(min_length=1)

    @field_validator(
        "id", "biological_meaning", "quantity_kind", "canonical_unit", "physical_dimension"
    )
    @classmethod
    def non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model parameter metadata must not be blank")
        return value

    @model_validator(mode="after")
    def unit_matches_dimension(self) -> _ParameterSpec:
        actual = _dimension(self.canonical_unit)
        if actual != self.physical_dimension:
            raise ValueError(
                f"canonical_unit '{self.canonical_unit}' has dimension '{actual}', "
                f"not '{self.physical_dimension}'"
            )
        return self


class ModelInputSpec(_ParameterSpec):
    data_type: ParameterType
    required: bool = True
    valid_range: NumericRange | None = None


class ModelOutputSpec(_ParameterSpec):
    data_type: ParameterType = ParameterType.FLOAT
    time_semantics: str = Field(min_length=1)

    @field_validator("time_semantics")
    @classmethod
    def time_semantics_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("output time_semantics must not be blank")
        return value


class ModelMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    source: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    license: str = Field(min_length=1)
    validation_scope: tuple[str, ...]
    limitations: tuple[str, ...]
    applicability: ApplicabilityContext

    @field_validator("model_name", "model_version", "source", "license")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model metadata strings must not be blank")
        return value

    @field_validator("validation_scope", "limitations")
    @classmethod
    def lists_not_blank(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not value.strip() for value in values):
            raise ValueError("validation_scope and limitations require non-blank entries")
        return values


class ModelContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "model-contract-v0"
    id: str = Field(min_length=1)
    metadata: ModelMetadata
    inputs: tuple[ModelInputSpec, ...]
    outputs: tuple[ModelOutputSpec, ...]

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != "model-contract-v0":
            raise ValueError("C0 supports only schema_version 'model-contract-v0'")
        return value

    @field_validator("id")
    @classmethod
    def id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("model contract id must not be blank")
        return value

    @model_validator(mode="after")
    def parameter_ids_unique(self) -> ModelContract:
        if not self.inputs:
            raise ValueError("model contracts require at least one input")
        if not self.outputs:
            raise ValueError("model contracts require at least one output")
        input_ids = [item.id for item in self.inputs]
        output_ids = [item.id for item in self.outputs]
        if len(input_ids) != len(set(input_ids)):
            raise ValueError("model input IDs must be unique")
        if len(output_ids) != len(set(output_ids)):
            raise ValueError("model output IDs must be unique")
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


class ModelInputBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str
    contract_version: str
    values: dict[str, QuantityValue | CategoricalValue]


class ModelOutputBundle(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    contract_id: str
    contract_version: str
    values: dict[str, QuantityValue]


class ModelContractError(ValueError):
    pass


def _check_bundle_identity(contract: ModelContract, contract_id: str, version: str) -> None:
    if contract_id != contract.id:
        raise ModelContractError(
            f"bundle contract_id '{contract_id}' does not match '{contract.id}'"
        )
    if version != contract.metadata.model_version:
        raise ModelContractError(
            f"bundle contract_version '{version}' does not match "
            f"'{contract.metadata.model_version}'"
        )


def _canonical_fixed_quantity(
    quantity: QuantityValue,
    spec: _ParameterSpec,
    data_type: ParameterType,
) -> QuantityValue:
    if quantity.distribution is not DistributionType.FIXED:
        raise ModelContractError(
            f"parameter '{spec.id}' requires a fixed value at the model boundary"
        )
    if quantity.semantic_kind != spec.quantity_kind:
        raise ModelContractError(
            f"parameter '{spec.id}' requires semantic kind '{spec.quantity_kind}', "
            f"received '{quantity.semantic_kind}'"
        )
    try:
        converted = _UNITS.Quantity(quantity.value, quantity.unit).to(spec.canonical_unit).magnitude
    except (pint.DimensionalityError, pint.UndefinedUnitError) as error:
        raise ModelContractError(
            f"parameter '{spec.id}' unit '{quantity.unit}' is incompatible with "
            f"canonical unit '{spec.canonical_unit}': {error}"
        ) from error
    value = float(converted)
    if data_type is ParameterType.INTEGER and not value.is_integer():
        raise ModelContractError(
            f"parameter '{spec.id}' requires an integer after unit conversion, received {value}"
        )
    return QuantityValue(
        distribution="fixed",
        unit=spec.canonical_unit,
        semantic_kind=spec.quantity_kind,
        value=int(value) if data_type is ParameterType.INTEGER else value,
        uncertainty=quantity.uncertainty,
        correlation_group=quantity.correlation_group,
    )


def canonicalize_inputs(contract: ModelContract, bundle: ModelInputBundle) -> ModelInputBundle:
    """Reject invalid input and convert units only at the adapter boundary."""

    _check_bundle_identity(contract, bundle.contract_id, bundle.contract_version)
    specs = {spec.id: spec for spec in contract.inputs}
    unknown = set(bundle.values) - set(specs)
    if unknown:
        raise ModelContractError(f"unknown model inputs: {sorted(unknown)}")
    missing = {spec.id for spec in contract.inputs if spec.required} - set(bundle.values)
    if missing:
        raise ModelContractError(f"missing required model inputs: {sorted(missing)}")

    canonical: dict[str, QuantityValue] = {}
    for parameter_id, quantity in bundle.values.items():
        if isinstance(quantity, CategoricalValue):
            raise ModelContractError(
                "incompatible_target_semantics: categorical values cannot be passed to "
                f"numerical Model Contract parameter '{parameter_id}'"
            )
        spec = specs[parameter_id]
        converted = _canonical_fixed_quantity(quantity, spec, spec.data_type)
        if spec.valid_range is not None and not spec.valid_range.contains(converted.value):
            raise ModelContractError(
                f"parameter '{parameter_id}' value {converted.value} {converted.unit} is outside "
                f"the declared valid range; adapters must not silently clamp values"
            )
        canonical[parameter_id] = converted
    return ModelInputBundle(
        contract_id=contract.id,
        contract_version=contract.metadata.model_version,
        values=canonical,
    )


def validate_outputs(contract: ModelContract, bundle: ModelOutputBundle) -> ModelOutputBundle:
    _check_bundle_identity(contract, bundle.contract_id, bundle.contract_version)
    specs = {spec.id: spec for spec in contract.outputs}
    unknown = set(bundle.values) - set(specs)
    missing = set(specs) - set(bundle.values)
    if unknown:
        raise ModelContractError(f"unknown model outputs: {sorted(unknown)}")
    if missing:
        raise ModelContractError(f"missing model outputs: {sorted(missing)}")
    canonical = {
        parameter_id: _canonical_fixed_quantity(quantity, specs[parameter_id], specs[parameter_id].data_type)
        for parameter_id, quantity in bundle.values.items()
    }
    return ModelOutputBundle(
        contract_id=contract.id,
        contract_version=contract.metadata.model_version,
        values=canonical,
    )


@runtime_checkable
class ModelAdapter(Protocol):
    contract: ModelContract
    artifact_digest: str

    def execute(self, inputs: ModelInputBundle) -> ModelOutputBundle: ...
