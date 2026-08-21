import json
from pathlib import Path

import pytest

from krypton.adapters import MockPKAdapter
from krypton.registry import ModelRegistry, ModelRegistryError


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
ENTRY_POINT = "krypton.adapters.mock:MockPKAdapter"


def registry() -> ModelRegistry:
    result = ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter})
    result.load_directory(RESOURCE_ROOT / "registry" / "models")
    return result


def test_flat_file_registry_resolves_contract_and_allowlisted_adapter() -> None:
    result = registry()

    contract = result.get_contract("contract:mock-pk", "1.0.0")
    adapter = result.get_adapter("contract:mock-pk", "1.0.0")

    assert contract.metadata.model_name == "Krypton Mock PK"
    assert isinstance(adapter, MockPKAdapter)
    assert adapter.contract == contract


def test_list_by_mechanism_filters_without_ranking() -> None:
    result = registry()

    assert [item.id for item in result.list_by_mechanism("mock_pk")] == [
        "contract:mock-pk"
    ]
    assert result.list_by_mechanism("unknown") == ()


def test_unknown_contract_is_actionable() -> None:
    result = registry()

    with pytest.raises(ModelRegistryError, match="not registered"):
        result.get_contract("contract:missing", "1.0.0")
    with pytest.raises(ModelRegistryError, match="not registered"):
        result.get_adapter("contract:missing", "1.0.0")


def test_unallowlisted_adapter_fixture_is_rejected(tmp_path: Path) -> None:
    fixture = RESOURCE_ROOT / "fixtures" / "invalid" / "model_registry_unknown_adapter_v0.json"
    (tmp_path / fixture.name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")

    with pytest.raises(ModelRegistryError, match="not allowlisted project code"):
        ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter}).load_directory(tmp_path)


def test_duplicate_flat_file_registration_is_rejected(tmp_path: Path) -> None:
    fixture = RESOURCE_ROOT / "registry" / "models" / "mock_pk_v1.json"
    content = fixture.read_text(encoding="utf-8")
    (tmp_path / "one.json").write_text(content, encoding="utf-8")
    (tmp_path / "two.json").write_text(content, encoding="utf-8")

    with pytest.raises(ModelRegistryError, match="duplicate model contract"):
        ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter}).load_directory(tmp_path)


def test_registry_checks_adapter_implementation_pin_independently(tmp_path: Path) -> None:
    fixture = RESOURCE_ROOT / "registry" / "models" / "mock_pk_v1.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))
    payload["adapter"]["artifact_digest"] = "a" * 64
    (tmp_path / "mismatch.json").write_text(json.dumps(payload), encoding="utf-8")

    result = ModelRegistry(adapter_factories={ENTRY_POINT: MockPKAdapter})
    result.load_directory(tmp_path)
    with pytest.raises(ModelRegistryError, match="adapter artifact digest"):
        result.get_adapter("contract:mock-pk", "1.0.0")


def test_registry_does_not_scan_or_automatically_select_models() -> None:
    result = registry()

    assert not hasattr(result, "rank")
    assert not hasattr(result, "select_best")
