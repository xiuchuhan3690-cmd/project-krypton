"""Fail closed on the Task-7A private GitHub candidate metadata boundary."""

from __future__ import annotations

import hashlib
import re
import tomllib
from pathlib import Path


ROOT = Path(__file__).parents[1]
REPOSITORY_URL = "https://github.com/xiuchuhan3690-cmd/project-krypton"
TASK6_FROZEN = {
    "krypton_v1_task6_pre_task6_inventory.yaml": "b9aef94c11b82e0d856ce76d2b3514d1602819eb2be7cddef15c47d2f413705c",
    "krypton_v1_task6_prepublication_manifest.yaml": "28cd2c584695643d0b7581cef06cf51060ffb2212ef8f152e54c37eb7fa93682",
    "krypton_v1_task6_repository_inventory.yaml": "da8459f131948ab23c379ac037c54d81e3f224a57119edae49df2cce27d63163",
    "krypton_v1_task6_release_asset_manifest.yaml": "8b6f8f0c5d47aba1b6ae4abc8ad82640aa9c0b4e3e4fcc45152b5a0cef6e30fe",
    "krypton_v1_task6_verification.yaml": "01c70aefd833aae4d7fc16998254a67014215b0880385aa17a49dfa154903b23",
    "krypton_v1_task6_digests.yaml": "8f38737da4549ae1ad13f03b588f6689aa49455509dd8caeae708b1b7eaf3eb9",
}
TEXT_SUFFIXES = {".cff", ".md", ".py", ".toml", ".yaml", ".yml"}
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PRIVATE_PATH = re.compile(r"(?i)(?:[a-z]:\\users\\|PC_User|\\\.codex\\|/\.codex/|OneDrive)")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    failures: list[str] = []
    for name, expected in TASK6_FROZEN.items():
        if sha256(ROOT / name) != expected:
            failures.append(f"historical Task-6 artifact changed: {name}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    release = (ROOT / "krypton_v1_release_metadata.yaml").read_text(encoding="utf-8")
    packaged_release = (ROOT / "src/krypton/resources/krypton_v1_release_metadata.yaml").read_text(encoding="utf-8")
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    if f"repository-code: {REPOSITORY_URL}" not in citation:
        failures.append("CFF repository-code is not frozen to the real repository")
    for prohibited in ("orcid:", "doi:", "email:", "affiliation:"):
        if prohibited in citation.lower():
            failures.append(f"unresolved CFF field fabricated: {prohibited}")
    if project.get("urls") != {"Repository": REPOSITORY_URL}:
        failures.append("pyproject Repository URL mismatch")
    for name, text in (("README", readme), ("release metadata", release), ("packaged release metadata", packaged_release)):
        if REPOSITORY_URL not in text:
            failures.append(f"{name} repository URL missing")
    for required in ("C3B: RESTRICTED_COMPLETE", "route_gate: USABLE_WITH_STATED_SCOPE", "validation_maturity: EXTERNAL_DESCRIPTIVE_SUPPORT", "row_30: BLOCKED", "row_31: BLOCKED", "C4: NOT_INCLUDED"):
        if required not in release:
            failures.append(f"scientific-state invariant missing: {required}")

    placeholder_hits: list[str] = []
    privacy_hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if relative in {
            "scripts/verify_distribution.py",
            "scripts/verify_public_boundary.py",
            "scripts/verify_task6_prepublication.py",
            "scripts/verify_task7a_private_candidate.py",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Project Krypton project owner" in text:
            placeholder_hits.append(relative)
        if EMAIL.search(text) or PRIVATE_PATH.search(text):
            privacy_hits.append(relative)
    if placeholder_hits != ["krypton_v1_documentation_test_manifest.yaml"]:
        failures.append(f"unexpected active placeholder locations: {placeholder_hits}")
    if privacy_hits:
        failures.append(f"personal email or private local path in source: {privacy_hits}")

    if failures:
        raise SystemExit("\n".join(failures))
    print("TASK7A_PRIVATE_CANDIDATE: PASS")
    print(f"REPOSITORY_URL: {REPOSITORY_URL}")
    print("HISTORICAL_TASK6_ARTIFACTS: UNCHANGED")
    print("RIGHTS_PRIVACY_DELTA: PASS")


if __name__ == "__main__":
    main()
