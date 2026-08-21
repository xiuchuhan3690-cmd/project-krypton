"""Controlled baseline/edited pair construction and pre-execution invariance gate."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from krypton.domain import ApplicabilityContext, QuantityValue
from krypton.models import (
    ModelAdapter,
    ModelContract,
    ModelContractError,
    ModelInputBundle,
    ModelOutputBundle,
    canonicalize_inputs,
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


class CanonicalPairSpecMixin:
    """Canonical serialization shared by numerical and categorical pair specs."""

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    def digest(self) -> str:
        return _digest(self.model_dump(mode="json"))

    def environment_digest(self) -> str:
        return _digest(
            {
                "context": self.context.model_dump(mode="json"),
                "environment": [item.model_dump(mode="json") for item in self.environment],
                "initial_conditions": [
                    item.model_dump(mode="json") for item in self.initial_conditions
                ],
            }
        )


class PairHashReport(BaseModel):
    """Hash-only invariance report reusable across branch value types."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_full_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    edited_full_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_invariant_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    edited_invariant_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @property
    def invariant_hashes_match(self) -> bool:
        return self.baseline_invariant_hash == self.edited_invariant_hash


def _without_paths(payload: dict[str, object], authorized_paths: set[str]) -> dict[str, object]:
    result = json.loads(_canonical_json(payload))
    for path in authorized_paths:
        parts = path.split(".")
        target: object = result
        for part in parts[:-1]:
            if not isinstance(target, dict) or part not in target:
                target = None
                break
            target = target[part]
        if isinstance(target, dict):
            target.pop(parts[-1], None)
    return result


def canonical_pair_hashes(
    baseline_payload: dict[str, object],
    edited_payload: dict[str, object],
    *,
    authorized_paths: set[str],
) -> PairHashReport:
    """Hash complete branches and the same branches with authorized paths removed."""

    baseline_invariant = _without_paths(baseline_payload, authorized_paths)
    edited_invariant = _without_paths(edited_payload, authorized_paths)
    return PairHashReport(
        baseline_full_hash=_digest(baseline_payload),
        edited_full_hash=_digest(edited_payload),
        baseline_invariant_hash=_digest(baseline_invariant),
        edited_invariant_hash=_digest(edited_invariant),
    )


class NamedQuantity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parameter_id: str = Field(min_length=1)
    quantity: QuantityValue

    @field_validator("parameter_id")
    @classmethod
    def id_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("parameter_id must not be blank")
        return value


class SharedSetting(BaseModel):
    """Immutable named environment or initial-condition value."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    key: str = Field(min_length=1)
    value: QuantityValue | str | int | float | bool

    @field_validator("key")
    @classmethod
    def key_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("shared setting key must not be blank")
        return value


class EditDerivedParameterChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parameter_id: str = Field(min_length=1)
    baseline: QuantityValue
    edited: QuantityValue
    mapping_id: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    mapping_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("parameter_id", "mapping_id", "mapping_version")
    @classmethod
    def fields_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("authorized change identifiers must not be blank")
        return value

    @model_validator(mode="after")
    def values_must_differ(self) -> EditDerivedParameterChange:
        if self.baseline == self.edited:
            raise ValueError("an authorized edit-derived change must alter the parameter")
        return self


class PairRunSpec(CanonicalPairSpecMixin, BaseModel):
    """One immutable source from which both counterfactual branches are derived."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    edit_id: str = Field(min_length=1)
    model_contract_id: str = Field(min_length=1)
    model_contract_version: str = Field(min_length=1)
    adapter_id: str = Field(min_length=1)
    adapter_artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    seed: int
    context: ApplicabilityContext
    environment: tuple[SharedSetting, ...] = ()
    initial_conditions: tuple[SharedSetting, ...] = ()
    shared_inputs: tuple[NamedQuantity, ...]
    authorized_changes: tuple[EditDerivedParameterChange, ...]
    edited_input_overrides: tuple[NamedQuantity, ...] = ()

    @field_validator(
        "id", "edit_id", "model_contract_id", "model_contract_version", "adapter_id"
    )
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("pair run identifiers must not be blank")
        return value

    @model_validator(mode="after")
    def identifiers_are_unambiguous(self) -> PairRunSpec:
        if not self.authorized_changes:
            raise ValueError("PairRunSpec requires at least one edit-derived authorized change")
        for field_name in (
            "environment",
            "initial_conditions",
            "shared_inputs",
            "authorized_changes",
            "edited_input_overrides",
        ):
            values = getattr(self, field_name)
            attribute = "key" if field_name in {"environment", "initial_conditions"} else "parameter_id"
            identifiers = [getattr(item, attribute) for item in values]
            if len(identifiers) != len(set(identifiers)):
                raise ValueError(f"{field_name} identifiers must be unique")
        shared = {item.parameter_id for item in self.shared_inputs}
        authorized = {item.parameter_id for item in self.authorized_changes}
        if shared & authorized:
            raise ValueError(
                f"parameters cannot be both shared and authorized: {sorted(shared & authorized)}"
            )
        return self

class PairBranch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    model_inputs: ModelInputBundle
    context: ApplicabilityContext
    environment: tuple[SharedSetting, ...]
    initial_conditions: tuple[SharedSetting, ...]
    model_contract_id: str
    model_contract_version: str
    adapter_id: str
    adapter_artifact_digest: str
    seed: int


class DifferenceKind(StrEnum):
    AUTHORIZED = "authorized"
    UNEXPECTED = "unexpected"


class InputDifference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    parameter_id: str
    baseline: QuantityValue
    edited: QuantityValue
    kind: DifferenceKind
    authorization_mapping_id: str | None = None
    reason: str


class InputDifferenceReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    baseline_full_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    edited_full_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    baseline_invariant_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    edited_invariant_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorized: tuple[InputDifference, ...]
    unexpected: tuple[InputDifference, ...]

    @property
    def invariant_hashes_match(self) -> bool:
        return self.baseline_invariant_hash == self.edited_invariant_hash


class OutputDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    output_id: str
    baseline: QuantityValue
    edited: QuantityValue
    delta: QuantityValue


class PairRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spec_id: str
    baseline_branch: PairBranch
    edited_branch: PairBranch
    difference_report: InputDifferenceReport
    baseline_outputs: ModelOutputBundle
    edited_outputs: ModelOutputBundle
    deltas: tuple[OutputDelta, ...]


class PairRunError(ValueError):
    pass


class PairInvariantError(PairRunError):
    def __init__(self, report: InputDifferenceReport) -> None:
        self.report = report
        unexpected = [difference.parameter_id for difference in report.unexpected]
        super().__init__(
            "counterfactual invariance gate rejected the pair before adapter execution; "
            f"unexpected differences: {unexpected}; invariant hashes match: "
            f"{report.invariant_hashes_match}"
        )


def _quantity_payload(quantity: QuantityValue) -> dict[str, object]:
    return quantity.model_dump(mode="json")


def _branch_payload(branch: PairBranch) -> dict[str, object]:
    return {
        "inputs": {
            key: _quantity_payload(value)
            for key, value in sorted(branch.model_inputs.values.items())
        },
        "context": branch.context.model_dump(mode="json"),
        "environment": [item.model_dump(mode="json") for item in branch.environment],
        "initial_conditions": [
            item.model_dump(mode="json") for item in branch.initial_conditions
        ],
        "model_contract_id": branch.model_contract_id,
        "model_contract_version": branch.model_contract_version,
        "adapter_id": branch.adapter_id,
        "adapter_artifact_digest": branch.adapter_artifact_digest,
        "seed": branch.seed,
    }


class PairRunner:
    def __init__(self, contract: ModelContract, adapter: ModelAdapter) -> None:
        self.contract = contract
        self.adapter = adapter

    def _validate_pins(self, spec: PairRunSpec) -> None:
        if spec.model_contract_id != self.contract.id:
            raise PairRunError("PairRunSpec model_contract_id does not match the runner contract")
        if spec.model_contract_version != self.contract.metadata.model_version:
            raise PairRunError("PairRunSpec model_contract_version does not match the runner contract")
        if self.adapter.contract != self.contract:
            raise PairRunError("adapter and runner must share the exact same model contract")
        actual_adapter_id = (
            f"{self.adapter.__class__.__module__}:{self.adapter.__class__.__qualname__}"
        )
        if spec.adapter_id != actual_adapter_id:
            raise PairRunError(
                f"PairRunSpec adapter_id '{spec.adapter_id}' does not match '{actual_adapter_id}'"
            )
        if spec.adapter_artifact_digest != self.adapter.artifact_digest:
            raise PairRunError("PairRunSpec adapter artifact digest does not match the adapter")

    def _canonical_branches(
        self, spec: PairRunSpec
    ) -> tuple[PairBranch, PairBranch, ModelInputBundle]:
        shared = {item.parameter_id: item.quantity for item in spec.shared_inputs}
        baseline_values = dict(shared)
        edited_values = dict(shared)
        for change in spec.authorized_changes:
            baseline_values[change.parameter_id] = change.baseline
            edited_values[change.parameter_id] = change.edited

        expected_edited = canonicalize_inputs(
            self.contract,
            ModelInputBundle(
                contract_id=spec.model_contract_id,
                contract_version=spec.model_contract_version,
                values=edited_values,
            ),
        )
        for override in spec.edited_input_overrides:
            edited_values[override.parameter_id] = override.quantity

        baseline_inputs = canonicalize_inputs(
            self.contract,
            ModelInputBundle(
                contract_id=spec.model_contract_id,
                contract_version=spec.model_contract_version,
                values=baseline_values,
            ),
        )
        edited_inputs = canonicalize_inputs(
            self.contract,
            ModelInputBundle(
                contract_id=spec.model_contract_id,
                contract_version=spec.model_contract_version,
                values=edited_values,
            ),
        )
        common = {
            "context": spec.context,
            "environment": spec.environment,
            "initial_conditions": spec.initial_conditions,
            "model_contract_id": spec.model_contract_id,
            "model_contract_version": spec.model_contract_version,
            "adapter_id": spec.adapter_id,
            "adapter_artifact_digest": spec.adapter_artifact_digest,
            "seed": spec.seed,
        }
        return (
            PairBranch(name="baseline", model_inputs=baseline_inputs, **common),
            PairBranch(name="edited", model_inputs=edited_inputs, **common),
            expected_edited,
        )

    def _difference_report(
        self,
        spec: PairRunSpec,
        baseline: PairBranch,
        edited: PairBranch,
        expected_edited: ModelInputBundle,
    ) -> InputDifferenceReport:
        authorizations = {item.parameter_id: item for item in spec.authorized_changes}
        authorized: list[InputDifference] = []
        unexpected: list[InputDifference] = []
        all_ids = sorted(set(baseline.model_inputs.values) | set(edited.model_inputs.values))
        for parameter_id in all_ids:
            baseline_value = baseline.model_inputs.values[parameter_id]
            edited_value = edited.model_inputs.values[parameter_id]
            if baseline_value == edited_value:
                continue
            authorization = authorizations.get(parameter_id)
            if (
                authorization is not None
                and edited_value == expected_edited.values[parameter_id]
            ):
                authorized.append(
                    InputDifference(
                        parameter_id=parameter_id,
                        baseline=baseline_value,
                        edited=edited_value,
                        kind=DifferenceKind.AUTHORIZED,
                        authorization_mapping_id=authorization.mapping_id,
                        reason="matches the canonical edit-derived parameter change",
                    )
                )
            else:
                unexpected.append(
                    InputDifference(
                        parameter_id=parameter_id,
                        baseline=baseline_value,
                        edited=edited_value,
                        kind=DifferenceKind.UNEXPECTED,
                        authorization_mapping_id=(authorization.mapping_id if authorization else None),
                        reason=(
                            "does not match the authorized edited value"
                            if authorization
                            else "parameter is not authorized to differ"
                        ),
                    )
                )

        for parameter_id, authorization in authorizations.items():
            if baseline.model_inputs.values[parameter_id] == edited.model_inputs.values[parameter_id]:
                unexpected.append(
                    InputDifference(
                        parameter_id=parameter_id,
                        baseline=baseline.model_inputs.values[parameter_id],
                        edited=edited.model_inputs.values[parameter_id],
                        kind=DifferenceKind.UNEXPECTED,
                        authorization_mapping_id=authorization.mapping_id,
                        reason="authorized change collapses to no difference after canonicalization",
                    )
                )

        baseline_payload = _branch_payload(baseline)
        edited_payload = _branch_payload(edited)
        authorized_ids = set(authorizations)
        hashes = canonical_pair_hashes(
            baseline_payload,
            edited_payload,
            authorized_paths={f"inputs.{parameter_id}" for parameter_id in authorized_ids},
        )
        return InputDifferenceReport(
            baseline_full_hash=hashes.baseline_full_hash,
            edited_full_hash=hashes.edited_full_hash,
            baseline_invariant_hash=hashes.baseline_invariant_hash,
            edited_invariant_hash=hashes.edited_invariant_hash,
            authorized=tuple(authorized),
            unexpected=tuple(unexpected),
        )

    def run(self, spec: PairRunSpec) -> PairRunResult:
        self._validate_pins(spec)
        try:
            baseline, edited, expected_edited = self._canonical_branches(spec)
        except ModelContractError as error:
            raise PairRunError(f"branch canonicalization failed before execution: {error}") from error
        report = self._difference_report(spec, baseline, edited, expected_edited)
        if report.unexpected or not report.invariant_hashes_match:
            raise PairInvariantError(report)

        baseline_outputs = self.adapter.execute(baseline.model_inputs)
        edited_outputs = self.adapter.execute(edited.model_inputs)
        deltas = tuple(
            OutputDelta(
                output_id=output_id,
                baseline=baseline_outputs.values[output_id],
                edited=edited_outputs.values[output_id],
                delta=QuantityValue(
                    distribution="fixed",
                    unit=baseline_outputs.values[output_id].unit,
                    semantic_kind=baseline_outputs.values[output_id].semantic_kind,
                    value=(
                        edited_outputs.values[output_id].value
                        - baseline_outputs.values[output_id].value
                    ),
                ),
            )
            for output_id in sorted(baseline_outputs.values)
        )
        return PairRunResult(
            spec_id=spec.id,
            baseline_branch=baseline,
            edited_branch=edited,
            difference_report=report,
            baseline_outputs=baseline_outputs,
            edited_outputs=edited_outputs,
            deltas=deltas,
        )
