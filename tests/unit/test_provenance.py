import hashlib
import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.domain import (
    ArtifactReference,
    EditObject,
    ProvenanceManifest,
    VersionedReference,
    collect_provenance,
    digest_model,
)


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
VALID_FIXTURE = RESOURCE_ROOT / "fixtures" / "valid" / "provenance_manifest_mock_v0.json"


def artifact(identifier: str, version: str, character: str) -> ArtifactReference:
    return ArtifactReference(id=identifier, version=version, digest=character * 64)


def collector_arguments(lock: Path) -> dict[str, object]:
    return {
        "run_id": "run:test-collector",
        "repository": ROOT,
        "dependency_lock": lock,
        "edit_object": artifact("edit:mock", "edit-object-v0", "1"),
        "keg": artifact("keg:mock", "keg-v0", "2"),
        "mpt": artifact("mapping:mock", "1.0.0", "3"),
        "model_artifact": artifact("contract:mock-pk", "1.0.0", "4"),
        "pair_run_spec": artifact("pair:mock", "pair-run-spec-v0", "5"),
        "environment_digest": "6" * 64,
        "random_seed": 42,
        "timestamp": datetime(2026, 8, 16, tzinfo=UTC),
    }


def test_valid_manifest_canonical_json_and_digest_are_stable() -> None:
    manifest = ProvenanceManifest.model_validate_json(VALID_FIXTURE.read_text(encoding="utf-8"))
    canonical = manifest.canonical_json()

    assert "\n" not in canonical
    assert list(json.loads(canonical))[0] == "container_image_digest"
    assert ProvenanceManifest.model_validate_json(canonical) == manifest
    assert manifest.digest() == ProvenanceManifest.model_validate_json(canonical).digest()
    assert len(manifest.digest()) == 64
    assert manifest.random_seed == 42


def test_invalid_manifest_fixture_rejects_timestamp_commit_and_digests() -> None:
    fixture = RESOURCE_ROOT / "fixtures" / "invalid" / "provenance_manifest_bad_digest_v0.json"

    with pytest.raises(ValidationError) as error:
        ProvenanceManifest.model_validate_json(fixture.read_text(encoding="utf-8"))

    text = str(error.value)
    assert "timestamp" in text
    assert "git_commit" in text
    assert "digest" in text


def test_collect_provenance_reads_local_environment_and_lock() -> None:
    lock = ROOT / "requirements.lock"

    manifest = collect_provenance(**collector_arguments(lock))

    assert manifest.krypton_package_version == "1.0.1"
    assert manifest.python_version.startswith("3.12")
    assert manifest.git_commit in {"unborn", "unknown"} or len(manifest.git_commit) >= 40
    git_available = shutil.which("git") is not None
    git_tree = None
    if git_available:
        git_tree = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    if git_tree is None or git_tree.returncode != 0:
        assert manifest.git_commit == "unknown"
        assert manifest.dirty_worktree is True
    else:
        git_status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert manifest.dirty_worktree == bool(git_status.stdout.strip())
    assert manifest.dependency_lock_digest == hashlib.sha256(lock.read_bytes()).hexdigest()
    assert manifest.pair_run_spec.id == "pair:mock"
    assert manifest.environment_digest == "6" * 64
    assert manifest.timestamp.tzinfo is not None


def test_lock_content_changes_provenance_digest(tmp_path: Path) -> None:
    first_lock = tmp_path / "first.lock"
    second_lock = tmp_path / "second.lock"
    first_lock.write_text("package==1\n", encoding="utf-8")
    second_lock.write_text("package==2\n", encoding="utf-8")

    first = collect_provenance(**collector_arguments(first_lock))
    second = collect_provenance(**collector_arguments(second_lock))

    assert first.dependency_lock_digest != second.dependency_lock_digest
    assert first.digest() != second.digest()


def test_missing_dependency_lock_is_actionable(tmp_path: Path) -> None:
    missing = tmp_path / "missing.lock"

    with pytest.raises(FileNotFoundError, match="dependency lock file does not exist"):
        collect_provenance(**collector_arguments(missing))


def test_model_digest_is_canonical_and_sensitive_to_edit() -> None:
    edit = EditObject(
        id="edit:test",
        assembly="GRCh38",
        sequence_id="chr1",
        start=0,
        end=1,
        reference_allele="A",
        edited_allele="G",
        edit_type="snv",
        zygosity="heterozygous",
        mode="germline",
        edited_tissues=("all",),
        cell_fraction=1.0,
    )
    other = edit.model_copy(update={"edited_allele": "T"})

    assert digest_model(edit) == digest_model(EditObject.model_validate_json(edit.model_dump_json()))
    assert digest_model(edit) != digest_model(other)
    assert len(digest_model(edit)) == 64


def test_dataset_and_container_versions_are_recorded() -> None:
    payload = ProvenanceManifest.model_validate_json(
        VALID_FIXTURE.read_text(encoding="utf-8")
    ).model_dump()
    payload["dataset_versions"] = (
        VersionedReference(id="dataset:mock", version="2026-08-16"),
    )
    payload["container_image_digest"] = "sha256:" + "a" * 64

    manifest = ProvenanceManifest.model_validate(payload)

    assert manifest.dataset_versions[0].id == "dataset:mock"
    assert manifest.container_image_digest.startswith("sha256:")


def test_manifest_is_immutable() -> None:
    manifest = ProvenanceManifest.model_validate_json(VALID_FIXTURE.read_text(encoding="utf-8"))

    with pytest.raises(ValidationError, match="frozen"):
        manifest.random_seed = 99
