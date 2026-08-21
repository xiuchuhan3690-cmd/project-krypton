import json
from pathlib import Path

import networkx as nx
import pytest
from pydantic import ValidationError

from krypton.keg import (
    EdgeUnits,
    KEGDocument,
    KEGEdge,
    KEGNode,
    KEGValidationContext,
    KEGValidationError,
    NodeType,
    validate_keg,
)


FIXTURES = Path(__file__).parents[2] / "src" / "krypton" / "resources" / "fixtures"
VALID_KEG = FIXTURES / "valid" / "keg_mock_v0.json"


def validation_context() -> KEGValidationContext:
    return KEGValidationContext(
        mapping_ids=frozenset(
            {
                "mapping:edit-activity",
                "mapping:activity-clearance",
                "mapping:clearance-auc",
            }
        ),
        model_parameters=frozenset({("contract:mock-pk", "1.0.0", "clearance")}),
    )


def valid_document() -> KEGDocument:
    return KEGDocument.model_validate_json(VALID_KEG.read_text(encoding="utf-8"))


def issue_codes(error: KEGValidationError) -> set[str]:
    return {issue.code for issue in error.issues}


def test_valid_keg_fixture_passes_all_rules() -> None:
    document = valid_document()

    assert validate_keg(document, validation_context()) is None
    assert document.schema_version == "keg-v0"
    assert document.nodes[1].quantity_kind == "relative_enzyme_activity"


def test_canonical_json_is_stable_and_round_trips() -> None:
    document = valid_document()
    canonical = document.canonical_json()

    assert "\n" not in canonical
    assert canonical == KEGDocument.model_validate_json(canonical).canonical_json()
    assert document.digest() == KEGDocument.model_validate_json(canonical).digest()
    assert len(document.digest()) == 64
    assert list(json.loads(canonical))[0] == "applicability_contexts"


def test_networkx_multidigraph_is_a_runtime_view() -> None:
    document = valid_document()
    graph = document.to_multidigraph()

    assert isinstance(graph, nx.MultiDiGraph)
    assert nx.is_directed_acyclic_graph(graph)
    assert graph.number_of_nodes() == 4
    assert graph.number_of_edges() == 3
    assert graph.has_edge("node:activity", "node:clearance", key="edge:activity-clearance")
    assert graph.nodes["node:activity"]["node_type"] == "molecular_quantity"


@pytest.mark.parametrize(
    ("field", "code"),
    [("nodes", "duplicate_node_id"), ("edges", "duplicate_edge_id")],
)
def test_duplicate_graph_ids_are_rejected(field: str, code: str) -> None:
    document = valid_document()
    values = getattr(document, field)
    duplicate = document.model_copy(update={field: values + (values[0],)})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(duplicate, validation_context())

    assert code in issue_codes(error.value)


def test_dangling_edge_is_rejected() -> None:
    document = valid_document()
    edge = document.edges[0].model_copy(update={"target": "node:does-not-exist"})
    invalid = document.model_copy(update={"edges": (edge,) + document.edges[1:]})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(invalid, validation_context())

    assert "dangling_edge" in issue_codes(error.value)
    assert "node:does-not-exist" in str(error.value)


def test_exactly_one_matching_genomic_edit_root_is_required() -> None:
    document = valid_document()
    root = document.nodes[0]
    second_root = root.model_copy(update={"id": "node:other-edit"})
    multiple = document.model_copy(update={"nodes": document.nodes + (second_root,)})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(multiple, validation_context())
    assert "genomic_edit_root_count" in issue_codes(error.value)

    mismatch_root = root.model_copy(update={"edit_reference": "edit:other"})
    mismatch = document.model_copy(update={"nodes": (mismatch_root,) + document.nodes[1:]})
    with pytest.raises(KEGValidationError) as error:
        validate_keg(mismatch, validation_context())
    assert "root_edit_mismatch" in issue_codes(error.value)


def test_result_must_exist_and_be_reachable() -> None:
    document = valid_document()
    disconnected = document.model_copy(update={"edges": document.edges[:-1]})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(disconnected, validation_context())
    assert "unreachable_result" in issue_codes(error.value)

    intermediate_result = document.model_copy(update={"result_node_ids": ("node:clearance",)})
    assert validate_keg(intermediate_result, validation_context()) is None

    missing = document.model_copy(update={"result_node_ids": ("node:missing",)})
    with pytest.raises(KEGValidationError) as error:
        validate_keg(missing, validation_context())
    assert "unknown_result_node" in issue_codes(error.value)


def test_cycle_fixture_is_rejected_as_non_dag() -> None:
    document = KEGDocument.model_validate_json(
        (FIXTURES / "invalid" / "keg_cycle_v0.json").read_text(encoding="utf-8")
    )

    with pytest.raises(KEGValidationError) as error:
        validate_keg(document)

    assert {"cycle", "root_has_incoming_edge"} <= issue_codes(error.value)


@pytest.mark.parametrize(
    ("update", "context", "expected_code"),
    [
        (
            {"evidence_ids": ("evidence:missing",)},
            validation_context(),
            "unresolved_evidence_reference",
        ),
        (
            {"applicability_reference": "applicability:missing"},
            validation_context(),
            "unresolved_applicability_reference",
        ),
        (
            {"transformation_reference": "mapping:missing"},
            validation_context(),
            "unresolved_transformation_reference",
        ),
    ],
)
def test_edge_references_must_resolve(
    update: dict[str, object], context: KEGValidationContext, expected_code: str
) -> None:
    document = valid_document()
    edge = document.edges[0].model_copy(update=update)
    invalid = document.model_copy(update={"edges": (edge,) + document.edges[1:]})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(invalid, context)

    assert expected_code in issue_codes(error.value)


def test_model_parameter_must_resolve_to_validation_context() -> None:
    document = valid_document()
    context = KEGValidationContext(mapping_ids=validation_context().mapping_ids)

    with pytest.raises(KEGValidationError) as error:
        validate_keg(document, context)

    assert "unresolved_model_parameter" in issue_codes(error.value)


def test_evidence_applicability_reference_must_resolve() -> None:
    document = valid_document()
    evidence = document.evidence[0].model_copy(
        update={"applicability_reference": "applicability:missing"}
    )
    invalid = document.model_copy(update={"evidence": (evidence,)})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(invalid, validation_context())

    assert "unresolved_applicability_reference" in issue_codes(error.value)
    assert "evidence:evidence:mock.applicability_reference" in str(error.value)


def test_edge_units_must_match_endpoint_quantity_dimensions() -> None:
    document = valid_document()
    edge = document.edges[1].model_copy(
        update={"units": EdgeUnits(source_unit="dimensionless", target_unit="mg/h")}
    )
    invalid = document.model_copy(update={"edges": (document.edges[0], edge, document.edges[2])})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(invalid, validation_context())

    assert "incompatible_unit" in issue_codes(error.value)
    assert "node:clearance" in str(error.value)


def test_unknown_pint_unit_is_actionable() -> None:
    document = valid_document()
    edge = document.edges[0].model_copy(
        update={"units": EdgeUnits(source_unit="not_a_real_unit", target_unit="dimensionless")}
    )
    invalid = document.model_copy(update={"edges": (edge,) + document.edges[1:]})

    with pytest.raises(KEGValidationError) as error:
        validate_keg(invalid, validation_context())

    assert "invalid_unit" in issue_codes(error.value)
    assert "not_a_real_unit" in str(error.value)


def test_invalid_fixture_reports_all_reference_and_unit_failures() -> None:
    document = KEGDocument.model_validate_json(
        (FIXTURES / "invalid" / "keg_dangling_and_unresolved_v0.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(KEGValidationError) as error:
        validate_keg(document)

    assert {
        "dangling_edge",
        "unresolved_evidence_reference",
        "unresolved_applicability_reference",
        "unresolved_transformation_reference",
        "invalid_unit",
        "incompatible_unit",
        "unreachable_result",
    } <= issue_codes(error.value)


def test_unknown_validation_status_is_rejected_by_schema() -> None:
    payload = valid_document().edges[0].model_dump(mode="json")
    payload["validation_status"] = "plausible_by_ai"

    with pytest.raises(ValidationError, match="validation_status"):
        KEGEdge.model_validate(payload)


def test_node_type_specific_references_are_enforced() -> None:
    with pytest.raises(ValidationError, match="require edit_reference"):
        KEGNode(id="node:edit", node_type=NodeType.GENOMIC_EDIT, label="Edit")

    with pytest.raises(ValidationError, match="model_parameter nodes require"):
        KEGNode(id="node:model", node_type=NodeType.MODEL_PARAMETER, label="Parameter")
