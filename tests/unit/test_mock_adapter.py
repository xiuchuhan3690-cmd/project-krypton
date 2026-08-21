from pathlib import Path

import pytest

from krypton.adapters import MockPKAdapter, MockPKAdapterB
from krypton.domain import QuantityValue
from krypton.models import ModelAdapter, ModelContractError, ModelInputBundle
from krypton.registry import ModelRegistry


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
ENTRY_POINT = "krypton.adapters.mock:MockPKAdapter"


def adapter() -> MockPKAdapter:
    registry = ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter})
    registry.load_directory(RESOURCE_ROOT / "registry" / "models")
    resolved = registry.get_adapter("contract:mock-pk", "1.0.0")
    assert isinstance(resolved, MockPKAdapter)
    return resolved


def q(unit: str, kind: str, value: float) -> QuantityValue:
    return QuantityValue(distribution="fixed", unit=unit, semantic_kind=kind, value=value)


def inputs(**changes: QuantityValue) -> ModelInputBundle:
    values = {
        "dose": q("mg", "dose_amount", 100),
        "clearance": q("L/h", "clearance", 10),
    }
    values.update(changes)
    return ModelInputBundle(
        contract_id="contract:mock-pk", contract_version="1.0.0", values=values
    )


def test_mock_adapter_satisfies_protocol_and_equation() -> None:
    model = adapter()

    assert isinstance(model, ModelAdapter)
    result = model.execute(inputs())

    assert result.values["auc"].value == pytest.approx(10)
    assert result.values["auc"].unit == "mg*h/L"
    assert result.values["auc"].semantic_kind == "auc"
    assert model.execution_count == 1


def test_mock_adapter_converts_units_only_at_boundary() -> None:
    model = adapter()

    result = model.execute(
        inputs(
            dose=q("g", "dose_amount", 0.1),
            clearance=q("mL/min", "clearance", 100),
        )
    )

    assert result.values["auc"].value == pytest.approx(100 / 6)


@pytest.mark.parametrize(
    ("bundle", "message"),
    [
        (
            ModelInputBundle(
                contract_id="contract:mock-pk",
                contract_version="1.0.0",
                values={"dose": q("mg", "dose_amount", 100)},
            ),
            "missing required",
        ),
        (
            inputs(extra=q("mg", "dose_amount", 1)),
            "unknown model inputs",
        ),
        (
            inputs(clearance=q("L/h", "clearance", 0)),
            "must not silently clamp",
        ),
        (
            inputs(clearance=q("mg/h", "clearance", 10)),
            "incompatible",
        ),
    ],
)
def test_invalid_inputs_fail_before_execution(bundle: ModelInputBundle, message: str) -> None:
    model = adapter()

    with pytest.raises(ModelContractError, match=message):
        model.execute(bundle)

    assert model.execution_count == 0


def test_replaceable_adapters_share_model_contract_but_have_distinct_artifact_pins() -> None:
    contract = adapter().contract
    first = MockPKAdapter(contract)
    second = MockPKAdapterB(contract)

    assert first.contract is second.contract
    assert first.artifact_digest != second.artifact_digest
    assert first.execute(inputs()).values["auc"].value == 10
    assert second.execute(inputs()).values["auc"].value == 10
