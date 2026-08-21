"""Verify the Task-5 CI/governance boundary and post-Task-5 digest freeze."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
DIGESTS = ROOT / "krypton_v1_task5_digests.yaml"
IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "build",
    "dist",
    "post_task5_dist",
}
FROZEN_RIGHTS = {
    "krypton_v1_independent_rights_audit.yaml": "a119a9c3323e24528856c242821dcbfdf77d78ef822792eda8cf61f7e640b588",
    "krypton_v1_file_rights_inventory.yaml": "b6ccb0a07856d7abad0bdd7cf34bc1975ab225dd352fee8a44c951d5b0bba9c5",
    "krypton_v1_dependency_license_audit.yaml": "d077d9bcaf8ec681b5df951f6afef731f1404df72662dc87a64500ccb64aa2fa",
    "krypton_v1_rights_audit_digests.yaml": "8c309f5c66881112cd44416f226946a30cabdeed01b740a3b5eeb40493bdea58",
}
FROZEN_DISTRIBUTIONS = {
    "dist/project_krypton-1.0.0-py3-none-any.whl": "351fd4d7a3232234dbdb40ca6c0001c4edf13cacf2ccf634269a2f0fa6120469",
    "dist/project_krypton-1.0.0.tar.gz": "3ed9a075c88fbda86c52d13a21ed8616be80c1693fb952dde65e6a354c8eacc8",
}
REQUIRED_FILES = {
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/documentation.yml",
    ".github/ISSUE_TEMPLATE/scientific_scope.yml",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "GOVERNANCE.md",
    "krypton_v1_task5_ci_governance_manifest.yaml",
    "krypton_v1_task5_ci_verification.yaml",
    "krypton_v1_task5_digests.yaml",
}
ALLOWED_ACTIONS = {
    "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_candidates() -> list[Path]:
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path != DIGESTS
            and not any(part in IGNORED_PARTS or part.startswith(".venv") for part in path.parts)
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def write_digest_manifest() -> None:
    entries = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in source_candidates()
    }
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    post = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in sorted((ROOT / "post_task5_dist").glob("*"))
        if path.is_file()
    }
    payload = {
        "schema_version": "krypton-v1-task5-digests-1",
        "algorithm": "sha256",
        "source_inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "source_artifacts": entries,
        "post_task5_distributions": post,
        "historical_distributions_unchanged": FROZEN_DISTRIBUTIONS,
        "self_digest_policy": "This file is excluded from its source inventory and the archives to avoid self-reference.",
    }
    DIGESTS.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"WROTE_TASK5_DIGESTS: {len(entries)} source artifacts, {len(post)} post-Task-5 artifacts")


def main() -> None:
    if sys.argv[1:] == ["--write"]:
        write_digest_manifest()
        return
    failures: list[str] = []
    for relative in sorted(REQUIRED_FILES):
        if not (ROOT / relative).is_file():
            failures.append(f"missing required governance file: {relative}")

    workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for required in (
        "pull_request:",
        "branches: [main]",
        "permissions:\n  contents: read",
        "python-version: \"3.12\"",
        "python -m pip check",
        "python -m pytest -q",
        "python scripts/verify_public_boundary.py",
        "python scripts/verify_task5_ci_governance.py",
        "python scripts/verify_distribution.py",
        "cffconvert --validate --infile CITATION.cff",
        "docker build --tag project-krypton-ci:1.0.0 .",
    ):
        if required not in workflow:
            failures.append(f"workflow invariant missing: {required}")
    for prohibited in (
        "pull_request_target",
        "contents: write",
        "${{ secrets.",
        "upload-artifact",
        "docker push",
        "twine upload",
    ):
        if prohibited in workflow:
            failures.append(f"prohibited workflow capability: {prohibited}")
    actions = set(re.findall(r"uses:\s*([^\s#]+)", workflow))
    if actions != ALLOWED_ACTIONS:
        failures.append(f"unexpected or missing Actions references: {sorted(actions)}")

    for relative, expected in {**FROZEN_RIGHTS, **FROZEN_DISTRIBUTIONS}.items():
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"frozen baseline changed: {relative}: {actual}")

    external_files = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "external_data").rglob("*")
        if path.is_file()
    }
    expected_external = {
        "external_data/.gitignore",
        "external_data/DO_NOT_COMMIT_EXTERNAL_SCIENTIFIC_DATA.md",
    }
    if external_files != expected_external:
        failures.append(f"external_data boundary changed: {sorted(external_files)}")

    governance = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
    for state in (
        "C3B RESTRICTED_COMPLETE",
        "USABLE_WITH_STATED_SCOPE",
        "EXTERNAL_DESCRIPTIVE_SUPPORT",
        "Rows 30 and 31 BLOCKED",
        "C4 NOT_INCLUDED",
    ):
        if state not in governance:
            failures.append(f"scientific-state guard missing: {state}")

    manifest = load(ROOT / "krypton_v1_task5_ci_governance_manifest.yaml")
    verification = load(ROOT / "krypton_v1_task5_ci_verification.yaml")
    digest_manifest = load(DIGESTS)
    if manifest.get("gate") != "RELEASE_TASK5_PASS_WITH_RESTRICTIONS":
        failures.append("Task-5 governance gate is not frozen")
    if verification.get("local_ci_simulation", {}).get("status") != "LOCAL_COMMAND_VERIFIED":
        failures.append("local CI simulation is not verified")
    if verification.get("github_actions", {}).get("status") != "GITHUB_ACTIONS_NOT_YET_EXECUTED":
        failures.append("GitHub execution status is misleading")

    entries = digest_manifest.get("source_artifacts", {})
    expected_entries = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in source_candidates()
    }
    if entries != expected_entries:
        failures.append("Task-5 source digest inventory differs from current source")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != digest_manifest.get("source_inventory_sha256"):
        failures.append("Task-5 source inventory checksum mismatch")
    for relative, expected in digest_manifest.get("post_task5_distributions", {}).items():
        path = ROOT / relative
        actual = sha256(path) if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"post-Task-5 distribution mismatch: {relative}: {actual}")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK5_CI_GOVERNANCE: PASS ({len(entries)} source artifacts)")
    print("PRE_TASK5_RIGHTS_BASELINE: UNCHANGED")
    print("GITHUB_ACTIONS: NOT_YET_EXECUTED")


if __name__ == "__main__":
    main()
