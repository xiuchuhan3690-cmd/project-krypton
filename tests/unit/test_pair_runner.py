from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.adapters import MockPKAdapter
from krypton.domain import QuantityValue
from krypton.orchestration import (
    DifferenceKind,
    EditDerivedParameterChange,
    NamedQuantity,
    PairInvariantError,
    PairRunError,
    PairRunResult,
    PairRunSpec,
    PairRunner,
)
from krypton.registry import ModelRegistry


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
ENTRY_POINT = "krypton.adapters.mock:MockPKAdapter"


def valid_spec() -> PairRunSpec:
    return PairRunSpec.model_validate_json(
        (RESOURCE_ROOT / "fixtures" / "valid" / "pair_run_spec_mock_v0.json").read_text(
            encoding="utf-8"
        )
    )


def runner_and_adapter() -> tuple[PairRunner, MockPKAdapter]:
    registry = ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter})
    registry.load_directory(RESOURCE_ROOT / "registry" / "models")
    contract = registry.get_contract("contract:mock-pk", "1.0.0")
    adapter = registry.get_adapter("contract:mock-pk", "1.0.0")
    assert isinstance(adapter, MockPKAdapter)
    return PairRunner(contract, adapter), adapter


def q(unit: str, kind: str, value: float) -> QuantityValue:
    return QuantityValue(distribution="fixed", unit=unit, semantic_kind=kind, value=value)


def test_positive_pair_is_derived_from_one_spec_and_produces_expected_delta() -> None:
    pair_runner, adapter = runner_and_adapter()

    result = pair_runner.run(valid_spec())

    assert result.baseline_outputs.values["auc"].value == pytest.approx(10.0)
    assert result.edited_outputs.values["auc"].value == pytest.approx(25.0)
    assert result.deltas[0].output_id == "auc"
    assert result.deltas[0].delta.value == pytest.approx(15.0)
    assert result.deltas[0].delta.unit == "mg*h/L"
    assert adapter.execution_count == 2


def test_only_clearance_is_an_authorized_branch_difference() -> None:
    pair_runner, _ = runner_and_adapter()

    result = pair_runner.run(valid_spec())
    report = result.difference_report

    assert [item.parameter_id for item in report.authorized] == ["clearance"]
    assert report.authorized[0].kind is DifferenceKind.AUTHORIZED
    assert report.authorized[0].authorization_mapping_id == "mapping:activity-clearance"
    assert report.unexpected == ()
    assert report.baseline_full_hash != report.edited_full_hash
    assert report.invariant_hashes_match


def test_context_environment_initial_state_model_adapter_and_seed_are_shared() -> None:
    pair_runner, _ = runner_and_adapter()

    result = pair_runner.run(valid_spec())
    baseline = result.baseline_branch
    edited = result.edited_branch

    assert baseline.context == edited.context
    assert baseline.environment == edited.environment
    assert baseline.initial_conditions == edited.initial_conditions
    assert baseline.model_contract_id == edited.model_contract_id
    assert baseline.model_contract_version == edited.model_contract_version
    assert baseline.adapter_id == edited.adapter_id
    assert baseline.adapter_artifact_digest == edited.adapter_artifact_digest
    assert baseline.seed == edited.seed == 42
    assert baseline.model_inputs.values["dose"] == edited.model_inputs.values["dose"]


def test_pair_result_serialization_round_trip() -> None:
    pair_runner, _ = runner_and_adapter()
    result = pair_runner.run(valid_spec())

    assert PairRunResult.model_validate_json(result.model_dump_json()) == result


def test_unauthorized_dose_change_100_to_120_fails_before_execution() -> None:
    spec = PairRunSpec.model_validate_json(
        (
            RESOURCE_ROOT
            / "fixtures"
            / "invalid"
            / "pair_run_spec_unauthorized_dose_v0.json"
        ).read_text(encoding="utf-8")
    )
    pair_runner, adapter = runner_and_adapter()

    with pytest.raises(PairInvariantError) as error:
        pair_runner.run(spec)

    report = error.value.report
    assert adapter.execution_count == 0
    assert [item.parameter_id for item in report.unexpected] == ["dose"]
    assert report.unexpected[0].baseline.value == 100
    assert report.unexpected[0].edited.value == 120
    assert report.unexpected[0].reason == "parameter is not authorized to differ"
    assert not report.invariant_hashes_match


def test_unit_equivalent_shared_override_is_not_a_difference() -> None:
    spec = valid_spec().model_copy(
        update={
            "edited_input_overrides": (
                NamedQuantity(
                    parameter_id="dose",
                    quantity=q("g", "dose_amount", 0.1),
                ),
            )
        }
    )
    pair_runner, adapter = runner_and_adapter()

    result = pair_runner.run(spec)

    assert result.difference_report.unexpected == ()
    assert result.difference_report.invariant_hashes_match
    assert adapter.execution_count == 2


def test_override_of_authorized_parameter_must_match_authorized_value() -> None:
    spec = valid_spec().model_copy(
        update={
            "edited_input_overrides": (
                NamedQuantity(
                    parameter_id="clearance",
                    quantity=q("L/h", "clearance", 5),
                ),
            )
        }
    )
    pair_runner, adapter = runner_and_adapter()

    with pytest.raises(PairInvariantError) as error:
        pair_runner.run(spec)

    assert adapter.execution_count == 0
    assert error.value.report.unexpected[0].parameter_id == "clearance"
    assert error.value.report.unexpected[0].reason == "does not match the authorized edited value"


def test_unknown_override_fails_during_canonicalization_before_execution() -> None:
    spec = valid_spec().model_copy(
        update={
            "edited_input_overrides": (
                NamedQuantity(
                    parameter_id="unknown",
                    quantity=q("mg", "dose_amount", 1),
                ),
            )
        }
    )
    pair_runner, adapter = runner_and_adapter()

    with pytest.raises(PairRunError, match="canonicalization failed.*unknown model inputs"):
        pair_runner.run(spec)

    assert adapter.execution_count == 0


def test_authorized_change_must_survive_canonicalization() -> None:
    change = EditDerivedParameterChange(
        parameter_id="clearance",
        baseline=q("L/h", "clearance", 1),
        edited=q("mL/h", "clearance", 1000),
        mapping_id="mapping:equivalent",
        mapping_version="1.0.0",
        mapping_digest="c" * 64,
    )
    spec = valid_spec().model_copy(update={"authorized_changes": (change,)})
    pair_runner, adapter = runner_and_adapter()

    with pytest.raises(PairInvariantError) as error:
        pair_runner.run(spec)

    assert adapter.execution_count == 0
    assert "collapses to no difference" in error.value.report.unexpected[0].reason


@pytest.mark.parametrize(
    ("update", "message"),
    [
        ({"model_contract_id": "contract:other"}, "model_contract_id"),
        ({"model_contract_version": "2.0.0"}, "model_contract_version"),
        ({"adapter_id": "untrusted.module:Adapter"}, "adapter_id"),
        ({"adapter_artifact_digest": "a" * 64}, "artifact digest"),
    ],
)
def test_model_and_adapter_pins_are_checked_before_execution(
    update: dict[str, object], message: str
) -> None:
    pair_runner, adapter = runner_and_adapter()

    with pytest.raises(PairRunError, match=message):
        pair_runner.run(valid_spec().model_copy(update=update))

    assert adapter.execution_count == 0


def test_pair_run_spec_is_immutable() -> None:
    spec = valid_spec()

    with pytest.raises(ValidationError, match="frozen"):
        spec.seed = 99
    with pytest.raises(ValidationError, match="frozen"):
        spec.shared_inputs[0].parameter_id = "other"


def test_pair_spec_and_environment_digests_are_canonical_and_sensitive() -> None:
    spec = valid_spec()
    restored = PairRunSpec.model_validate_json(spec.canonical_json())

    assert restored == spec
    assert restored.digest() == spec.digest()
    assert restored.environment_digest() == spec.environment_digest()
    changed_seed = spec.model_copy(update={"seed": 99})
    assert changed_seed.digest() != spec.digest()
    assert changed_seed.environment_digest() == spec.environment_digest()
    changed_environment = spec.model_copy(
        update={
            "environment": (
                spec.environment[0].model_copy(update={"value": "stochastic"}),
            )
        }
    )
    assert changed_environment.environment_digest() != spec.environment_digest()


def test_spec_rejects_ambiguous_or_missing_authorizations() -> None:
    payload = valid_spec().model_dump()
    payload["authorized_changes"] = ()
    with pytest.raises(ValidationError, match="at least one"):
        PairRunSpec.model_validate(payload)

    payload = valid_spec().model_dump()
    payload["shared_inputs"] = payload["shared_inputs"] + (payload["shared_inputs"][0],)
    with pytest.raises(ValidationError, match="shared_inputs identifiers must be unique"):
        PairRunSpec.model_validate(payload)

    payload = valid_spec().model_dump()
    payload["shared_inputs"] = payload["shared_inputs"] + (
        {
            "parameter_id": "clearance",
            "quantity": q("L/h", "clearance", 10).model_dump(),
        },
    )
    with pytest.raises(ValidationError, match="both shared and authorized"):
        PairRunSpec.model_validate(payload)
