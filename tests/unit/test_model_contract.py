import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.domain import QuantityValue
from krypton.models import (
    ModelContract,
    ModelContractError,
    ModelInputBundle,
    ModelInputSpec,
    ModelOutputBundle,
    NumericRange,
    canonicalize_inputs,
    validate_outputs,
)
from krypton.registry import ModelRegistryRecord


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"


def mock_contract() -> ModelContract:
    record = ModelRegistryRecord.model_validate_json(
        (RESOURCE_ROOT / "registry" / "models" / "mock_pk_v1.json").read_text(encoding="utf-8")
    )
    return record.contract


def quantity(unit: str, kind: str, value: float) -> QuantityValue:
    return QuantityValue(
        distribution="fixed", unit=unit, semantic_kind=kind, value=value
    )


def valid_bundle() -> ModelInputBundle:
    return ModelInputBundle(
        contract_id="contract:mock-pk",
        contract_version="1.0.0",
        values={
            "dose": quantity("mg", "dose_amount", 100),
            "clearance": quantity("L/h", "clearance", 10),
        },
    )


def test_model_contract_metadata_semantics_and_round_trip() -> None:
    contract = mock_contract()

    assert contract.metadata.model_name == "Krypton Mock PK"
    assert contract.metadata.model_version == "1.0.0"
    assert contract.metadata.source == "internal-mock"
    assert contract.metadata.license
    assert len(contract.metadata.artifact_digest) == 64
    assert contract.metadata.applicability.experimental_system == ("internal_mock",)
    assert contract.inputs[0].biological_meaning == "Administered mock amount"
    assert contract.outputs[0].time_semantics.startswith("total exposure")
    assert ModelContract.model_validate_json(contract.canonical_json()) == contract
    assert len(contract.digest()) == 64


def test_bad_dimension_fixture_is_rejected() -> None:
    payload = (
        RESOURCE_ROOT / "fixtures" / "invalid" / "model_contract_bad_dimension_v0.json"
    ).read_text(encoding="utf-8")

    with pytest.raises(ValidationError, match="canonical_unit"):
        ModelContract.model_validate_json(payload)


def test_duplicate_input_and_output_ids_are_rejected() -> None:
    payload = mock_contract().model_dump()
    payload["inputs"] = payload["inputs"] + (payload["inputs"][0],)
    with pytest.raises(ValidationError, match="input IDs must be unique"):
        ModelContract.model_validate(payload)

    payload = mock_contract().model_dump()
    payload["outputs"] = payload["outputs"] + (payload["outputs"][0],)
    with pytest.raises(ValidationError, match="output IDs must be unique"):
        ModelContract.model_validate(payload)


def test_parameter_type_and_range_schema_validation() -> None:
    with pytest.raises(ValidationError, match="data_type"):
        ModelInputSpec(
            id="x",
            biological_meaning="X",
            quantity_kind="x",
            canonical_unit="dimensionless",
            physical_dimension="dimensionless",
            data_type="string",
        )
    with pytest.raises(ValidationError, match="minimum must not exceed"):
        NumericRange(minimum=2, maximum=1)


def test_adapter_boundary_converts_units_to_contract_units() -> None:
    bundle = valid_bundle().model_copy(
        update={
            "values": {
                "dose": quantity("g", "dose_amount", 0.1),
                "clearance": quantity("mL/min", "clearance", 100),
            }
        }
    )

    canonical = canonicalize_inputs(mock_contract(), bundle)

    assert canonical.values["dose"].unit == "mg"
    assert canonical.values["dose"].value == pytest.approx(100)
    assert canonical.values["clearance"].unit == "L/h"
    assert canonical.values["clearance"].value == pytest.approx(6)


@pytest.mark.parametrize(
    ("values", "message"),
    [
        ({"dose": quantity("mg", "dose_amount", 100)}, "missing required"),
        (
            {
                **valid_bundle().values,
                "unregistered": quantity("mg", "dose_amount", 1),
            },
            "unknown model inputs",
        ),
        (
            {
                "dose": quantity("mg", "protein_amount", 100),
                "clearance": quantity("L/h", "clearance", 10),
            },
            "semantic kind",
        ),
        (
            {
                "dose": quantity("L", "dose_amount", 1),
                "clearance": quantity("L/h", "clearance", 10),
            },
            "incompatible",
        ),
        (
            {
                "dose": quantity("mg", "dose_amount", 100),
                "clearance": quantity("L/h", "clearance", 0),
            },
            "must not silently clamp",
        ),
    ],
)
def test_invalid_input_bundles_are_actionably_rejected(
    values: dict[str, QuantityValue], message: str
) -> None:
    bundle = valid_bundle().model_copy(update={"values": values})

    with pytest.raises(ModelContractError, match=message):
        canonicalize_inputs(mock_contract(), bundle)


def test_non_fixed_model_input_is_rejected() -> None:
    values = dict(valid_bundle().values)
    values["dose"] = QuantityValue(
        distribution="interval",
        unit="mg",
        semantic_kind="dose_amount",
        lower=90,
        upper=110,
    )

    with pytest.raises(ModelContractError, match="fixed value"):
        canonicalize_inputs(mock_contract(), valid_bundle().model_copy(update={"values": values}))


@pytest.mark.parametrize(
    ("contract_id", "version", "message"),
    [
        ("contract:other", "1.0.0", "contract_id"),
        ("contract:mock-pk", "2.0.0", "contract_version"),
    ],
)
def test_bundle_identity_is_pinned(contract_id: str, version: str, message: str) -> None:
    bundle = valid_bundle().model_copy(
        update={"contract_id": contract_id, "contract_version": version}
    )

    with pytest.raises(ModelContractError, match=message):
        canonicalize_inputs(mock_contract(), bundle)


def test_outputs_are_standardized_and_complete() -> None:
    outputs = ModelOutputBundle(
        contract_id="contract:mock-pk",
        contract_version="1.0.0",
        values={"auc": quantity("g*h/L", "auc", 0.01)},
    )

    canonical = validate_outputs(mock_contract(), outputs)

    assert canonical.values["auc"].unit == "mg*h/L"
    assert canonical.values["auc"].value == pytest.approx(10)

    with pytest.raises(ModelContractError, match="missing model outputs"):
        validate_outputs(mock_contract(), outputs.model_copy(update={"values": {}}))
    with pytest.raises(ModelContractError, match="unknown model outputs"):
        validate_outputs(
            mock_contract(),
            outputs.model_copy(
                update={"values": {**outputs.values, "other": quantity("mg", "dose_amount", 1)}}
            ),
        )
