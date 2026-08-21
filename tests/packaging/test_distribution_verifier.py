from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[2]
SPEC = importlib.util.spec_from_file_location(
    "krypton_verify_distribution", ROOT / "scripts" / "verify_distribution.py"
)
assert SPEC is not None and SPEC.loader is not None
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)
inspect_names = VERIFIER.inspect_names
member_set_digest = VERIFIER.member_set_digest
member_set_matches = VERIFIER.member_set_matches


def test_authorized_expected_member_set_passes() -> None:
    expected = {"README.md", "src/krypton/__init__.py"}
    assert member_set_matches(
        expected,
        expected_count=2,
        expected_digest=member_set_digest(expected),
    )


def test_unexpected_sdist_member_fails_classification() -> None:
    expected = {"README.md", "src/krypton/__init__.py"}
    actual = expected | {"unreviewed-notes.txt"}
    assert not member_set_matches(
        actual,
        expected_count=2,
        expected_digest=member_set_digest(expected),
    )


def test_existing_rights_and_private_data_exclusions_remain_fail_closed() -> None:
    payload = b"unapproved external evidence\n"
    findings = inspect_names(
        ["evidence/unapproved-source.yaml"],
        lambda _name: payload,
    )
    assert {finding["kind"] for finding in findings} == {"forbidden-path"}
