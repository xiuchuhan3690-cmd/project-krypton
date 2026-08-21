from __future__ import annotations

import hashlib
import tomllib
from pathlib import Path

import pytest

import krypton
from krypton.evidence_pack import EvidencePackNotConfigured, open_configured_evidence_pack
from krypton.resources import public_resource


ROOT = Path(__file__).parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
RELEASE = (ROOT / "krypton_v1_release_metadata.yaml").read_text(encoding="utf-8")


def test_version_has_one_runtime_source_of_truth() -> None:
    assert krypton.__version__ == "1.0.0"
    assert PYPROJECT["project"]["dynamic"] == ["version"]
    assert PYPROJECT["tool"]["hatch"]["version"]["path"] == "src/krypton/_version.py"


def test_distribution_and_import_names_are_explicit() -> None:
    assert PYPROJECT["project"]["name"] == "project-krypton"
    assert PYPROJECT["project"]["authors"] == [{"name": "XIU CHUHAN"}]
    assert PYPROJECT["project"]["maintainers"] == [{"name": "XIU CHUHAN"}]
    assert PYPROJECT["project"]["urls"] == {
        "Repository": "https://github.com/xiuchuhan3690-cmd/project-krypton"
    }
    assert "distribution_name: project-krypton" in RELEASE
    assert "import_name: krypton" in RELEASE
    assert "public_attribution: XIU CHUHAN" in RELEASE
    assert "family_name: Xiu" in RELEASE
    assert "given_name: Chuhan" in RELEASE
    assert "repository: https://github.com/xiuchuhan3690-cmd/project-krypton" in RELEASE
    assert "Copyright 2026 XIU CHUHAN" in (ROOT / "NOTICE").read_text(encoding="utf-8")


def test_license_metadata_and_full_license_are_consistent() -> None:
    assert PYPROJECT["project"]["license"] == "Apache-2.0"
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text


def test_release_metadata_preserves_restricted_scientific_state() -> None:
    for statement in (
        "C3B: RESTRICTED_COMPLETE",
        "route_gate: USABLE_WITH_STATED_SCOPE",
        "validation_maturity: EXTERNAL_DESCRIPTIVE_SUPPORT",
        "row_30: BLOCKED",
        "row_31: BLOCKED",
        "C4: NOT_INCLUDED",
    ):
        assert statement in RELEASE


def test_private_provenance_is_not_presented_as_public_history() -> None:
    assert "type: private_research_provenance_identifier" in RELEASE
    assert "commit: 8c03ec5d129bb438dfddf4b54f974349a76bf224" in RELEASE
    assert "present_in_public_history: false" in RELEASE


def test_missing_evidence_pack_fails_closed() -> None:
    with pytest.raises(EvidencePackNotConfigured, match="KRYPTON_LOCAL_EVIDENCE_PACK"):
        open_configured_evidence_pack({})


def test_public_resource_paths_reject_traversal() -> None:
    with pytest.raises(ValueError, match="safe relative path"):
        public_resource("../private.json")


def test_runtime_resources_live_in_the_actual_package_tree() -> None:
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/krypton"]
    assert "force-include" not in wheel
    for name in (
        "fixtures/valid/keg_mock_v0.json",
        "registry/models/mock_pk_v1.json",
        "schemas/quantity-value.schema.json",
        "requirements.lock",
        "krypton_v1_release_metadata.yaml",
    ):
        assert public_resource(name).is_file()


def test_public_lock_excludes_private_scientific_dependencies() -> None:
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
    names = {line.split("==", 1)[0].lower() for line in lock if line}
    assert "numpy" not in names
    assert "scipy" not in names
    assert {"networkx", "pint", "pydantic"} <= names


def test_task1_frozen_license_digest_is_preserved() -> None:
    assert hashlib.sha256((ROOT / "LICENSE").read_bytes()).hexdigest() == (
        "0d542e0c8804e39aa7f37eb00da5a762149dc682d7829451287e11b938e94594"
    )
