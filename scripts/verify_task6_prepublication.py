"""Fail closed on the Project Krypton v1.0 pre-publication freeze."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
TASK5_FROZEN = {
    "krypton_v1_task5_ci_governance_manifest.yaml": "39fcbc235bbcf0b372a74cf578243a128edd740510b6c4ee184d1648dc596ea3",
    "krypton_v1_task5_ci_verification.yaml": "3aa1cd344878ffc1d2cf7716170303336757f6491b4e1e812b7acfe6b148b4f2",
    "krypton_v1_task5_digests.yaml": "ba2f67964e7d84151b5a4bbadb050994e741884952117305d30c95eef9323338",
}
SIDECARS = {
    "krypton_v1_task6_pre_task6_inventory.yaml",
    "krypton_v1_task6_prepublication_manifest.yaml",
    "krypton_v1_task6_repository_inventory.yaml",
    "krypton_v1_task6_release_asset_manifest.yaml",
    "krypton_v1_task6_verification.yaml",
    "krypton_v1_task6_digests.yaml",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def main() -> None:
    failures: list[str] = []
    for name in SIDECARS:
        if not (ROOT / name).is_file():
            failures.append(f"missing Task-6 sidecar: {name}")
    for name, expected in TASK5_FROZEN.items():
        if sha256(ROOT / name) != expected:
            failures.append(f"historical Task-5 artifact changed: {name}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    release = (ROOT / "krypton_v1_release_metadata.yaml").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    for required in ("family-names: Xiu", "given-names: Chuhan", "version: 1.0.0"):
        if required not in citation:
            failures.append(f"CFF identity/version missing: {required}")
    for prohibited in ("orcid:", "doi:", "repository-code:", "email:", "affiliation:"):
        if prohibited in citation.lower():
            failures.append(f"unresolved CFF field fabricated: {prohibited}")
    if 'authors = [{ name = "XIU CHUHAN" }]' not in pyproject:
        failures.append("pyproject author not frozen")
    if "Copyright 2026 XIU CHUHAN" not in notice:
        failures.append("NOTICE copyright holder not frozen")
    for required in ("public_attribution: XIU CHUHAN", "C3B: RESTRICTED_COMPLETE", "route_gate: USABLE_WITH_STATED_SCOPE", "validation_maturity: EXTERNAL_DESCRIPTIVE_SUPPORT", "row_30: BLOCKED", "row_31: BLOCKED", "C4: NOT_INCLUDED"):
        if required not in release:
            failures.append(f"release metadata invariant missing: {required}")

    placeholder_hits = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in {".md", ".cff", ".toml", ".yaml", ".yml", ".py"}:
            continue
        relative = path.relative_to(ROOT).as_posix()
        # The verifier contains the literal signature it is searching for.
        if relative == "scripts/verify_task6_prepublication.py":
            continue
        if "Project Krypton project owner" in path.read_text(encoding="utf-8", errors="replace"):
            placeholder_hits.append(relative)
    if placeholder_hits != ["krypton_v1_documentation_test_manifest.yaml"]:
        failures.append(f"unexpected active placeholder locations: {placeholder_hits}")

    inventory = load("krypton_v1_task6_repository_inventory.yaml")
    entries = inventory.get("files", [])
    for record in entries:
        path = ROOT / record["path"]
        if not path.is_file() or path.stat().st_size != record["size_bytes"] or sha256(path) != record["sha256"]:
            failures.append(f"source freeze mismatch: {record['path']}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != inventory.get("aggregate_sha256"):
        failures.append("source inventory aggregate mismatch")
    manifest = load("krypton_v1_task6_prepublication_manifest.yaml")
    verification = load("krypton_v1_task6_verification.yaml")
    if manifest.get("gate") != "RELEASE_TASK6_PASS_WITH_ACTIONS":
        failures.append("Task-6 gate is not frozen")
    if verification.get("public_tests") != "221 passed":
        failures.append("Task-6 public test result is not frozen")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK6_PREPUBLICATION: PASS ({len(entries)} frozen source files)")
    print("OWNER_METADATA: XIU CHUHAN")
    print("HISTORICAL_TASK5_ARTIFACTS: UNCHANGED")


if __name__ == "__main__":
    main()
