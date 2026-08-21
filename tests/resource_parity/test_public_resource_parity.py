from __future__ import annotations

import tomllib
from pathlib import Path

from krypton.demo import demo_summary
from krypton.resources import public_resource, public_resource_root


ROOT = Path(__file__).parents[2]


def test_supported_runtime_resources_resolve_through_package_contract() -> None:
    for relative in (
        "fixtures/valid/keg_mock_v0.json",
        "fixtures/valid/mpt_request_v0.json",
        "fixtures/valid/mpt_scale_mapping_v0.json",
        "registry/models/mock_pk_v1.json",
        "schemas/quantity-value.schema.json",
        "requirements.lock",
        "krypton_v1_release_metadata.yaml",
    ):
        resource = public_resource(relative)
        assert resource.is_file(), relative
        assert resource.read_bytes(), relative


def test_demo_uses_the_public_resource_contract_and_preserves_output() -> None:
    with public_resource_root() as root:
        assert root.name == "resources"
        assert (root / "fixtures" / "valid" / "keg_mock_v0.json").is_file()
    summary = demo_summary()
    assert summary["auc"] == {
        "baseline_mg_h_per_L": 10.0,
        "edited_mg_h_per_L": 25.0,
        "delta_mg_h_per_L": 15.0,
    }
    assert summary["workflow_digest"] == (
        "a2784df7b4f5d0e559e20d9e299f81859825557c42ac9a8e0c9d4059a811eee9"
    )
    assert len(summary["execution_digest"]) == 64
    assert summary["execution_digest"] != summary["workflow_digest"]


def test_repository_root_has_no_obsolete_runtime_resource_trees() -> None:
    for name in ("fixtures", "schemas", "registry"):
        assert not (ROOT / name).exists()
        assert (ROOT / "src" / "krypton" / "resources" / name).is_dir()


def test_build_inputs_and_runtime_copies_are_explicit_and_synchronized() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    wheel = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel == {"packages": ["src/krypton"]}
    for name in ("requirements.lock", "krypton_v1_release_metadata.yaml"):
        assert (ROOT / name).read_bytes() == public_resource(name).read_bytes()
