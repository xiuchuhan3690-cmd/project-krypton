from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).parents[2]
WORKFLOW = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
GOVERNANCE = (ROOT / "GOVERNANCE.md").read_text(encoding="utf-8")
DOCKERFILE = (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_ci_events_and_permissions_are_minimal() -> None:
    assert "pull_request:" in WORKFLOW
    assert "branches: [main]" in WORKFLOW
    assert "permissions:\n  contents: read" in WORKFLOW
    assert "pull_request_target" not in WORKFLOW
    assert "contents: write" not in WORKFLOW
    assert "${{ secrets." not in WORKFLOW


def test_ci_covers_declared_python_only() -> None:
    assert set(re.findall(r'python-version: "([^"]+)"', WORKFLOW)) == {"3.12"}
    assert 'requires-python = ">=3.12,<3.13"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_actions_are_official_and_immutable() -> None:
    actions = set(re.findall(r"uses:\s*([^\s#]+)", WORKFLOW))
    assert actions == {
        "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    }


def test_ci_has_source_distribution_wheel_citation_and_docker_jobs() -> None:
    for job in ("source:", "distribution:", "installed-wheel:", "citation:", "docker-build:"):
        assert job in WORKFLOW
    assert "python -m pytest -q" in WORKFLOW
    assert "python -m pip check" in WORKFLOW
    assert "python scripts/verify_distribution.py" in WORKFLOW
    assert "python scripts/verify_task7a_private_candidate.py" in WORKFLOW
    assert "python -m krypton.demo" in WORKFLOW


def test_concurrency_does_not_cancel_main() -> None:
    assert "cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}" in WORKFLOW


def test_dependabot_is_weekly_without_auto_merge() -> None:
    policy = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
    assert "package-ecosystem: pip" in policy
    assert "package-ecosystem: github-actions" in policy
    assert policy.count("interval: weekly") == 2
    assert "auto-merge" not in policy


def test_issue_and_pr_templates_reject_sensitive_data() -> None:
    template_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / ".github").rglob("*"))
        if path.is_file() and path.name != "ci.yml" and path.name != "dependabot.yml"
    ).lower()
    for term in ("patient data", "genotype", "private evidence", "credential"):
        assert term in template_text


def test_governance_defines_change_classes_and_single_owner() -> None:
    assert "single-owner" in GOVERNANCE
    for label in ("| A |", "| B |", "| C |", "| D |"):
        assert label in GOVERNANCE
    assert "CODEOWNERS` is deferred" in GOVERNANCE
    assert "Code of Conduct is deferred" in GOVERNANCE


def test_governance_preserves_frozen_scientific_state() -> None:
    for state in (
        "C0/C1/C2/C3A COMPLETE",
        "C3B RESTRICTED_COMPLETE",
        "USABLE_WITH_STATED_SCOPE",
        "EXTERNAL_DESCRIPTIVE_SUPPORT",
        "Rows 30 and 31 BLOCKED",
        "C4 NOT_INCLUDED",
    ):
        assert state in GOVERNANCE


def test_contribution_and_security_policies_publish_actionable_routes() -> None:
    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    assert "No CLA or DCO is required" in contributing
    assert "AI-assisted work" in contributing
    assert "python scripts/verify_public_boundary.py" in contributing
    assert "python scripts/verify_task7a_private_candidate.py" in contributing
    assert "python scripts/verify_distribution.py" in contributing
    assert "python scripts/verify_task6_prepublication.py" not in contributing
    assert "canonical public repository" in contributing
    assert "remains private during pre-publication" not in contributing
    assert "Report a vulnerability" in security
    assert "GitHub Private Vulnerability Reporting" in security
    assert "SECURITY_REPORTING_ACTIVATION_REQUIRED_BEFORE_PUBLIC_READER_ACCESS" not in security


def test_docker_uses_an_explicit_full_test_stage_and_minimal_runtime_stage() -> None:
    assert "FROM package AS test" in DOCKERFILE
    assert "FROM package AS runtime" in DOCKERFILE
    for resource in (
        "COPY tests ./tests",
        "COPY scripts/verify_distribution.py ./scripts/verify_distribution.py",
        "COPY examples ./examples",
        "COPY CITATION.cff CONTRIBUTING.md SECURITY.md CHANGELOG.md GOVERNANCE.md ./",
        "COPY docs ./docs",
        "COPY .github ./.github",
    ):
        assert resource in DOCKERFILE
    assert "docker build --target test" in WORKFLOW
