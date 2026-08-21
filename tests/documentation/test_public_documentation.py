from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")
METADATA = (ROOT / "krypton_v1_release_metadata.yaml").read_text(encoding="utf-8")
CITATION = (ROOT / "CITATION.cff").read_text(encoding="utf-8")


def test_readme_version_matches_release_and_citation() -> None:
    assert README.startswith("# Project Krypton 1.0.0")
    assert "software_version: 1.0.0" in METADATA
    assert "version: 1.0.0" in CITATION


def test_readme_exposes_every_frozen_scientific_state() -> None:
    for value in (
        "C0 | COMPLETE",
        "C1 | COMPLETE",
        "C2 | COMPLETE",
        "C3A | COMPLETE",
        "C3B | RESTRICTED_COMPLETE",
        "USABLE_WITH_STATED_SCOPE",
        "EXTERNAL_DESCRIPTIVE_SUPPORT",
        "NOT_INCLUDED",
    ):
        assert value in README


def test_rows_30_and_31_are_visible_blocked_debt() -> None:
    assert "Validation Row 30 | **BLOCKED**" in README
    assert "Validation Row 31 | **BLOCKED**" in README
    assert "visible, accepted validation debt" in README


def test_public_and_private_test_counts_are_not_conflated() -> None:
    assert "Public distribution test suite:       221" in README
    assert "Documentation tests:                  12" in README
    assert "Resource parity tests:                  4" in README
    assert "CI/governance tests:                   10" in README
    assert "Private canonical scientific reference suite: 1184" in README
    assert "public_total_after_task_3: 207" in METADATA
    assert "public_total_after_task_4r: 211" in METADATA
    assert "public_total_after_task_5: 221" in METADATA


def test_external_data_and_pack_policy_are_prominent() -> None:
    assert "It does not include:" in README
    assert "paper-derived numerical datasets" in README
    assert "KRYPTON_LOCAL_EVIDENCE_PACK" in README
    assert "Pack access is fail-closed" in README


def test_research_and_clinical_limitations_are_prominent() -> None:
    assert "Research-use and safety boundary" in README
    assert "not clinical decision-support" in README
    assert "not a CYP2C19 scientific result" in README
    assert "not independent quantitative external validation" in README


def test_prohibited_positive_overclaims_are_absent() -> None:
    lowered = README.lower()
    for phrase in (
        "a general dna modification prediction system",
        "an arbitrary genotype-to-phenotype predictor",
        "a clinically validated system",
        "a clinical decision-support software platform",
        "a generalized whole-body prediction platform",
    ):
        assert phrase not in lowered


def test_platform_and_docker_status_match_metadata() -> None:
    assert "Windows x86-64 CPU: **VERIFIED**" in README
    assert "Linux amd64 Docker: **UNVERIFIED**" in README
    assert "macOS: **UNVERIFIED**" in README
    assert "ARM platforms: **UNVERIFIED**" in README
    assert "UNVERIFIED_DOCKER_NOT_AVAILABLE_ON_TASK2_HOST" in METADATA


def test_citation_is_versioned_with_real_repository_and_no_invented_doi() -> None:
    assert "title: Project Krypton" in CITATION
    assert "family-names: Xiu" in CITATION
    assert "given-names: Chuhan" in CITATION
    assert "license: Apache-2.0" in CITATION
    assert "doi:" not in CITATION.lower()
    assert "repository-code: https://github.com/xiuchuhan3690-cmd/project-krypton" in CITATION
    assert "https://github.com/xiuchuhan3690-cmd/project-krypton" in README


def test_release_notes_and_changelog_are_consistent() -> None:
    notes = (ROOT / "docs" / "release-notes-v1.0.0.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "Project Krypton 1.0.0 draft release notes" in notes
    assert "## 1.0.0 — release candidate" in changelog
    assert "publication checksums will be rebuilt and frozen" in notes


def test_representative_demo_is_documented_as_synthetic_and_stable() -> None:
    demo = (ROOT / "docs" / "representative-demo.md").read_text(encoding="utf-8")
    for value in ("baseline AUC: 10", "edited AUC:   25", "delta:        +15"):
        assert value in demo
    assert "not a CYP2C19 result" in demo
    assert "No evidence pack is required" in demo


def test_all_local_markdown_links_resolve() -> None:
    markdown_files = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md", ROOT / "CHANGELOG.md"]
    markdown_files.extend(sorted((ROOT / "docs").glob("*.md")))
    missing: list[str] = []
    for document in markdown_files:
        text = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if target.startswith(("http://", "https://", "#")):
                continue
            relative = target.split("#", 1)[0]
            if relative and not (document.parent / relative).resolve().exists():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert not missing
