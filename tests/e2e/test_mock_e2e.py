import json
import subprocess
import sys
from pathlib import Path

import networkx as nx
import pytest

from krypton.domain import ApplicabilityResult, QuantityValue, digest_model
from krypton.keg import KEGValidationContext, validate_keg
from krypton.orchestration import (
    C0MockWorkflowResult,
    PairInvariantError,
    build_c0_mock_workflow,
)


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
EXPECTED = json.loads(
    (RESOURCE_ROOT / "fixtures" / "reference" / "c0_mock_expected_v0.json").read_text(
        encoding="utf-8"
    )
)


def run_workflow() -> C0MockWorkflowResult:
    return build_c0_mock_workflow(RESOURCE_ROOT).run()


def test_full_mock_chain_matches_reference_fixture() -> None:
    result = run_workflow()

    assert result.edit.id == EXPECTED["edit_id"]
    assert result.evidence.id == EXPECTED["evidence_id"]
    assert result.mpt_result.baseline.value == EXPECTED["baseline_clearance_L_per_h"]
    assert result.mpt_result.edited.value == EXPECTED["edited_clearance_L_per_h"]
    assert result.pair_result.baseline_branch.model_inputs.values["dose"].value == EXPECTED[
        "dose_mg"
    ]
    assert result.consequence.baseline.value == EXPECTED["baseline_auc_mg_h_per_L"]
    assert result.consequence.edited.value == EXPECTED["edited_auc_mg_h_per_L"]
    assert result.consequence.delta.value == EXPECTED["delta_auc_mg_h_per_L"]
    assert result.keg_path_node_ids == tuple(EXPECTED["keg_path_node_ids"])
    assert result.keg_path_edge_ids == tuple(EXPECTED["keg_path_edge_ids"])


def test_activity_to_mpt_to_clearance_values_are_exact() -> None:
    workflow = build_c0_mock_workflow(RESOURCE_ROOT)
    result = workflow.run()

    assert workflow.mpt_request.baseline.value == EXPECTED["baseline_activity"]
    assert workflow.mpt_request.edited.value == EXPECTED["edited_activity"]
    assert result.mpt_result.baseline.unit == result.mpt_result.edited.unit == "L/h"
    assert result.mpt_result.baseline.value == 10.0
    assert result.mpt_result.edited.value == 4.0
    assert result.mpt_result.applicability_result is ApplicabilityResult.IN_DOMAIN


def test_keg_is_valid_dag_with_resolved_units_and_references() -> None:
    workflow = build_c0_mock_workflow(RESOURCE_ROOT)
    context = KEGValidationContext(
        mapping_ids=frozenset(
            {
                "mapping:edit-activity",
                "mapping:activity-clearance",
                "mapping:clearance-auc",
            }
        ),
        model_parameters=frozenset(
            {("contract:mock-pk", "1.0.0", "clearance")}
        ),
    )

    assert validate_keg(workflow.keg, context) is None
    assert nx.is_directed_acyclic_graph(workflow.keg.to_multidigraph())
    assert workflow.keg.nodes[2].quantity.unit == "L/h"
    assert workflow.keg.nodes[3].quantity.unit == "mg*h/L"


def test_pair_has_only_the_edit_derived_clearance_difference() -> None:
    result = run_workflow()
    report = result.pair_result.difference_report

    assert [item.parameter_id for item in report.authorized] == EXPECTED[
        "authorized_differences"
    ]
    assert [item.parameter_id for item in report.unexpected] == EXPECTED[
        "unexpected_differences"
    ]
    assert report.invariant_hashes_match
    assert result.pair_result.baseline_branch.seed == result.pair_result.edited_branch.seed == 42


def test_final_consequence_traces_to_every_upstream_artifact() -> None:
    result = run_workflow()
    evidence_path = result.consequence.evidence_path[0]

    assert evidence_path.evidence_id == result.evidence.id
    assert evidence_path.evidence_class == result.evidence.evidence_class
    assert evidence_path.keg_edge_ids == result.keg_path_edge_ids
    assert evidence_path.mapping_id == result.mpt_mapping.id == result.mpt_result.mapping_id
    assert result.mpt_mapping.evidence_ids == (result.evidence.id,)
    assert result.keg.edit == result.edit
    assert result.provenance.edit_object.id == result.edit.id
    assert result.provenance.edit_object.digest == digest_model(result.edit)
    assert result.provenance.keg.id == result.keg.id
    assert result.provenance.keg.digest == result.keg.digest()
    assert result.provenance.mpt.id == result.mpt_mapping.id
    assert result.provenance.mpt.digest == result.mpt_mapping.digest()
    assert result.provenance.model_artifact.id == result.model_contract.id
    assert (
        result.provenance.model_artifact.digest
        == result.model_contract.metadata.artifact_digest
        == result.consequence.model_versions[0].artifact_digest
    )
    assert result.provenance.pair_run_spec.id == result.pair_result.spec_id
    assert result.provenance.pair_run_spec.id == result.pair_run_spec.id
    assert result.provenance.pair_run_spec.digest == result.pair_run_spec.digest()
    assert result.provenance.environment_digest == result.pair_run_spec.environment_digest()
    assert result.consequence.provenance_reference == f"sha256:{result.provenance.digest()}"


def test_full_workflow_serialization_and_canonical_digest_round_trip() -> None:
    result = run_workflow()
    canonical = result.canonical_json()
    restored = C0MockWorkflowResult.model_validate_json(canonical)

    assert "\n" not in canonical
    assert restored == result
    assert restored.canonical_json() == canonical
    assert restored.digest() == result.digest()
    assert len(result.digest()) == 64


def test_full_workflow_is_deterministic_for_fixed_inputs_seed_and_timestamp() -> None:
    first = run_workflow()
    second = run_workflow()

    assert first.canonical_json() == second.canonical_json()
    assert first.digest() == second.digest()
    assert first.consequence == second.consequence


def test_unauthorized_full_e2e_dose_change_is_rejected_before_adapter_execution() -> None:
    workflow = build_c0_mock_workflow(RESOURCE_ROOT)
    unauthorized_dose = QuantityValue(
        distribution="fixed",
        unit="mg",
        semantic_kind="dose_amount",
        value=120,
    )

    with pytest.raises(PairInvariantError) as error:
        workflow.run(unauthorized_edited_dose=unauthorized_dose)

    assert workflow.adapter.execution_count == 0
    assert [item.parameter_id for item in error.value.report.unexpected] == ["dose"]
    assert error.value.report.unexpected[0].baseline.value == 100
    assert error.value.report.unexpected[0].edited.value == 120
    assert not error.value.report.invariant_hashes_match


def test_c0_mock_example_executes_with_expected_output() -> None:
    process = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "c0_mock" / "run.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    summary = json.loads(process.stdout)

    assert summary["clearance"] == {
        "baseline_L_per_h": 10.0,
        "edited_L_per_h": 4.0,
    }
    assert summary["auc"] == {
        "baseline_mg_h_per_L": 10.0,
        "edited_mg_h_per_L": 25.0,
        "delta_mg_h_per_L": 15.0,
    }
    assert summary["authorized_differences"] == ["clearance"]
    assert summary["unexpected_differences"] == []
    assert "not biological evidence" in summary["warning"]
