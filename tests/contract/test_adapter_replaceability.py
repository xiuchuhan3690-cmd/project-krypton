from pathlib import Path

from krypton.adapters import MockPKAdapterB
from krypton.orchestration import build_c0_mock_workflow


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"


def test_adapter_b_replaces_a_without_upstream_rewrite() -> None:
    workflow_a = build_c0_mock_workflow(RESOURCE_ROOT)
    workflow_b = build_c0_mock_workflow(RESOURCE_ROOT)
    upstream_before = (
        workflow_b.edit,
        workflow_b.keg,
        workflow_b.evidence,
        workflow_b.applicability,
        workflow_b.mapping,
        workflow_b.mpt_request,
        workflow_b.contract,
    )
    workflow_b.adapter = MockPKAdapterB(workflow_b.contract)

    result_a = workflow_a.run()
    result_b = workflow_b.run()

    assert (
        workflow_b.edit,
        workflow_b.keg,
        workflow_b.evidence,
        workflow_b.applicability,
        workflow_b.mapping,
        workflow_b.mpt_request,
        workflow_b.contract,
    ) == upstream_before
    assert result_a.edit == result_b.edit
    assert result_a.keg == result_b.keg
    assert result_a.evidence == result_b.evidence
    assert result_a.mpt_result == result_b.mpt_result
    assert result_a.model_contract == result_b.model_contract
    assert result_a.consequence.baseline == result_b.consequence.baseline
    assert result_a.consequence.edited == result_b.consequence.edited
    assert result_a.consequence.delta == result_b.consequence.delta
    assert result_a.pair_result.baseline_outputs == result_b.pair_result.baseline_outputs
    assert result_a.pair_result.edited_outputs == result_b.pair_result.edited_outputs
    assert workflow_a.adapter.artifact_digest != workflow_b.adapter.artifact_digest
