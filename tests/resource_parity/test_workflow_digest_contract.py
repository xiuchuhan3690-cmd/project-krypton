from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from krypton.orchestration import C0MockWorkflowResult, build_c0_mock_workflow


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"


def _result() -> C0MockWorkflowResult:
    return build_c0_mock_workflow(RESOURCE_ROOT).run()


def test_semantic_digest_is_canonical_and_deterministic() -> None:
    result = _result()
    assert result.semantic_digest() == result.semantic_digest()
    assert result.semantic_digest() == (
        "a2784df7b4f5d0e559e20d9e299f81859825557c42ac9a8e0c9d4059a811eee9"
    )
    assert '"provenance"' not in result.semantic_canonical_json()
    assert '"provenance_reference"' not in result.semantic_canonical_json()


def test_semantic_digest_ignores_execution_only_provenance_differences() -> None:
    result = _result()
    changed_provenance = result.provenance.model_copy(
        update={
            "git_commit": "unknown",
            "dirty_worktree": not result.provenance.dirty_worktree,
            "python_version": "3.12.different-runtime",
            "timestamp": datetime(2030, 1, 1, tzinfo=UTC),
        }
    )
    changed_consequence = result.consequence.model_copy(
        update={"provenance_reference": f"sha256:{changed_provenance.digest()}"}
    )
    changed = result.model_copy(
        update={"provenance": changed_provenance, "consequence": changed_consequence}
    )

    assert changed.semantic_digest() == result.semantic_digest()
    assert changed.digest() != result.digest()


def test_semantic_digest_changes_for_meaningful_result_difference() -> None:
    result = _result()
    changed = result.model_copy(
        update={
            "consequence": result.consequence.model_copy(
                update={"endpoint": "different_mock_endpoint"}
            )
        }
    )
    assert changed.semantic_digest() != result.semantic_digest()
