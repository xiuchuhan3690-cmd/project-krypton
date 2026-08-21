"""Verify Task-4R remediation and resource-parity artifact digests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
DIGESTS = ROOT / "krypton_v1_task4r_artifact_digests.yaml"
REMEDIATION = ROOT / "krypton_v1_task4r_remediation_manifest.yaml"
TESTS = ROOT / "krypton_v1_resource_parity_test_manifest.yaml"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def candidate_paths() -> list[str]:
    explicit = {
        "Dockerfile",
        "README.md",
        "docs/packaging.md",
        "docs/release-notes-v1.0.0.md",
        "examples/c0_mock/run.py",
        "krypton_v1_documentation_test_manifest.yaml",
        "krypton_v1_package_contents_manifest.yaml",
        "krypton_v1_release_metadata.yaml",
        "krypton_v1_resource_parity_test_manifest.yaml",
        "krypton_v1_task4r_remediation_manifest.yaml",
        "pyproject.toml",
        "scripts/export_public_schemas.py",
        "scripts/verify_public_boundary.py",
        "scripts/verify_task4r_artifact_digests.py",
        "tests/contract/test_adapter_replaceability.py",
        "tests/documentation/test_public_documentation.py",
        "tests/e2e/test_mock_e2e.py",
        "tests/packaging/test_release_metadata.py",
        "tests/resource_parity/test_public_resource_parity.py",
        "tests/unit/test_edit_object.py",
        "tests/unit/test_keg.py",
        "tests/unit/test_model_contract.py",
        "tests/unit/test_model_registry.py",
        "tests/unit/test_mock_adapter.py",
        "tests/unit/test_mpt.py",
        "tests/unit/test_pair_runner.py",
        "tests/unit/test_phenotype_consequence.py",
        "tests/unit/test_provenance.py",
    }
    explicit.update(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src" / "krypton" / "resources").rglob("*")
        if path.is_file()
    )
    return sorted(explicit)


def write_manifest() -> None:
    entries = {relative: digest(ROOT / relative) for relative in candidate_paths()}
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "schema_version": "krypton-v1-task4r-artifact-digests-1",
        "algorithm": "sha256",
        "task3_provenance": {
            "wheel_sha256": "5398ef06bf072c6d6903d09baa20d054aba7a9c779bc79f5952fbcc7bb4125c9",
            "sdist_sha256": "21ee24680b710486badc3d671c262e6667a5ca6bcc15fd16b2cfe2e944579ac0",
            "status": "immutable historical snapshot",
        },
        "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "artifacts": entries,
    }
    DIGESTS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE_TASK4R_ARTIFACT_DIGESTS: {len(entries)} artifacts")


def main() -> None:
    if sys.argv[1:] == ["--write"]:
        write_manifest()
        return
    manifest = load(DIGESTS)
    failures: list[str] = []
    entries = manifest.get("artifacts", {})
    for relative, expected in sorted(entries.items()):
        path = ROOT / relative
        actual = digest(path) if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")

    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != manifest.get("inventory_sha256"):
        failures.append("digest inventory checksum mismatch")

    remediation = load(REMEDIATION)
    tests = load(TESTS)
    if remediation.get("gate") not in {
        "RELEASE_TASK4R_PASS",
        "RELEASE_TASK4R_PASS_WITH_RESTRICTIONS",
    }:
        failures.append("remediation gate is not passing")
    if tests.get("counts", {}).get("PUBLIC_TOTAL_TESTS") != 211:
        failures.append("resource-parity test manifest total is not 211")
    for kind in ("wheel", "sdist"):
        record = remediation.get("task4r_artifacts", {}).get(kind, {})
        path = ROOT / "dist" / record.get("filename", "")
        actual = digest(path) if path.is_file() else "missing"
        if actual != record.get("sha256"):
            failures.append(f"{kind} archive digest mismatch")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK4R_ARTIFACT_DIGESTS: PASS ({len(entries)} artifacts)")
    print("RESOURCE_PARITY_MANIFEST: PASS (4 tests; 211 public total)")


if __name__ == "__main__":
    main()
