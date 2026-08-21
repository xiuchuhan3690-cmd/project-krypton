"""Explicit, deterministic KEG v0 validation rules."""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx
import pint
from pydantic import BaseModel, ConfigDict

from krypton.domain import CategoricalValue, QuantityValue
from krypton.keg.models import KEGDocument, KEGNode, NodeType


@dataclass(frozen=True)
class KEGValidationContext:
    """References resolved by later registries without implementing them here."""

    mapping_ids: frozenset[str] = frozenset()
    model_parameters: frozenset[tuple[str, str, str]] = frozenset()


class KEGValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    location: str
    message: str


class KEGValidationError(ValueError):
    def __init__(self, issues: list[KEGValidationIssue]) -> None:
        self.issues = tuple(issues)
        summary = "; ".join(
            f"{issue.code} at {issue.location}: {issue.message}" for issue in issues
        )
        super().__init__(f"KEG validation failed with {len(issues)} issue(s): {summary}")


_UNITS = pint.UnitRegistry()


def _issue(issues: list[KEGValidationIssue], code: str, location: str, message: str) -> None:
    issues.append(KEGValidationIssue(code=code, location=location, message=message))


def _duplicate_ids(items: tuple[object, ...]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for item in items:
        item_id = getattr(item, "id")
        if item_id in seen:
            duplicates.add(item_id)
        seen.add(item_id)
    return duplicates


def _unit_dimension(unit: str) -> pint.util.UnitsContainer | None:
    try:
        return _UNITS.Quantity(1, unit).dimensionality
    except (pint.UndefinedUnitError, pint.DefinitionSyntaxError, TypeError):
        return None


def _validate_endpoint_unit(
    *,
    issues: list[KEGValidationIssue],
    edge_id: str,
    endpoint: str,
    declared_unit: str,
    node: KEGNode | None,
) -> None:
    declared_dimension = _unit_dimension(declared_unit)
    if declared_dimension is None:
        _issue(
            issues,
            "invalid_unit",
            f"edge:{edge_id}.units.{endpoint}_unit",
            f"unit '{declared_unit}' is not recognized by Pint",
        )
        return
    if (
        node is None
        or node.quantity is None
        or isinstance(node.quantity, CategoricalValue)
    ):
        return
    node_dimension = _unit_dimension(node.quantity.unit)
    if node_dimension is None:
        _issue(
            issues,
            "invalid_unit",
            f"node:{node.id}.quantity.unit",
            f"unit '{node.quantity.unit}' is not recognized by Pint",
        )
    elif node_dimension != declared_dimension:
        _issue(
            issues,
            "incompatible_unit",
            f"edge:{edge_id}.units.{endpoint}_unit",
            f"declared unit '{declared_unit}' is dimensionally incompatible with "
            f"node '{node.id}' unit '{node.quantity.unit}'",
        )


def validate_keg(
    document: KEGDocument,
    context: KEGValidationContext | None = None,
) -> None:
    """Validate every C0 structural and reference invariant or raise once."""

    context = context or KEGValidationContext()
    issues: list[KEGValidationIssue] = []

    for duplicate in sorted(_duplicate_ids(document.nodes)):
        _issue(issues, "duplicate_node_id", "nodes", f"node id '{duplicate}' is not unique")
    for duplicate in sorted(_duplicate_ids(document.edges)):
        _issue(issues, "duplicate_edge_id", "edges", f"edge id '{duplicate}' is not unique")
    for duplicate in sorted(_duplicate_ids(document.evidence)):
        _issue(
            issues,
            "duplicate_evidence_id",
            "evidence",
            f"evidence id '{duplicate}' is not unique",
        )

    nodes = {node.id: node for node in document.nodes}
    evidence_ids = {record.id for record in document.evidence}
    applicability_ids = set(document.applicability_contexts)

    for record in document.evidence:
        if record.applicability_reference not in applicability_ids:
            _issue(
                issues,
                "unresolved_applicability_reference",
                f"evidence:{record.id}.applicability_reference",
                f"applicability context '{record.applicability_reference}' does not exist",
            )

    graph = nx.MultiDiGraph()
    graph.add_nodes_from(nodes)
    for edge in document.edges:
        source_node = nodes.get(edge.source)
        target_node = nodes.get(edge.target)
        if source_node is None:
            _issue(
                issues,
                "dangling_edge",
                f"edge:{edge.id}.source",
                f"source node '{edge.source}' does not exist",
            )
        if target_node is None:
            _issue(
                issues,
                "dangling_edge",
                f"edge:{edge.id}.target",
                f"target node '{edge.target}' does not exist",
            )
        if source_node is not None and target_node is not None:
            graph.add_edge(edge.source, edge.target, key=edge.id)

        for evidence_id in edge.evidence_ids:
            if evidence_id not in evidence_ids:
                _issue(
                    issues,
                    "unresolved_evidence_reference",
                    f"edge:{edge.id}.evidence_ids",
                    f"evidence '{evidence_id}' is not embedded in this KEG document",
                )
        if (
            edge.applicability_reference is not None
            and edge.applicability_reference not in applicability_ids
        ):
            _issue(
                issues,
                "unresolved_applicability_reference",
                f"edge:{edge.id}.applicability_reference",
                f"applicability context '{edge.applicability_reference}' does not exist",
            )
        if (
            edge.transformation_reference is not None
            and edge.transformation_reference not in context.mapping_ids
        ):
            _issue(
                issues,
                "unresolved_transformation_reference",
                f"edge:{edge.id}.transformation_reference",
                f"mapping '{edge.transformation_reference}' is not registered in the validation context",
            )

        _validate_endpoint_unit(
            issues=issues,
            edge_id=edge.id,
            endpoint="source",
            declared_unit=edge.units.source_unit,
            node=source_node,
        )
        _validate_endpoint_unit(
            issues=issues,
            edge_id=edge.id,
            endpoint="target",
            declared_unit=edge.units.target_unit,
            node=target_node,
        )

    roots = [node for node in document.nodes if node.node_type is NodeType.GENOMIC_EDIT]
    if len(roots) != 1:
        _issue(
            issues,
            "genomic_edit_root_count",
            "nodes",
            f"expected exactly one genomic_edit root, found {len(roots)}",
        )
        root = None
    else:
        root = roots[0]
        if root.edit_reference != document.edit.id:
            _issue(
                issues,
                "root_edit_mismatch",
                f"node:{root.id}.edit_reference",
                f"root references '{root.edit_reference}', expected '{document.edit.id}'",
            )
        if graph.in_degree(root.id) != 0:
            _issue(
                issues,
                "root_has_incoming_edge",
                f"node:{root.id}",
                "the genomic_edit root must have zero incoming edges",
            )

    if not nx.is_directed_acyclic_graph(graph):
        _issue(issues, "cycle", "edges", "KEG v0 must be a directed acyclic graph")

    for result_id in document.result_node_ids:
        result = nodes.get(result_id)
        if result is None:
            _issue(
                issues,
                "unknown_result_node",
                "result_node_ids",
                f"result node '{result_id}' does not exist",
            )
        elif root is not None and not nx.has_path(graph, root.id, result_id):
            _issue(
                issues,
                "unreachable_result",
                f"node:{result_id}",
                f"result is not reachable from genomic_edit root '{root.id}'",
            )

    for node in document.nodes:
        if node.node_type is NodeType.MODEL_PARAMETER:
            reference = (
                node.model_contract_reference,
                node.model_contract_version,
                node.model_parameter_id,
            )
            if reference not in context.model_parameters:
                _issue(
                    issues,
                    "unresolved_model_parameter",
                    f"node:{node.id}",
                    f"model parameter {reference!r} is not registered in the validation context",
                )
        for slot_name in ("quantity", "baseline", "edited"):
            value = getattr(node, slot_name)
            if isinstance(value, QuantityValue) and _unit_dimension(value.unit) is None:
                _issue(
                    issues,
                    "invalid_unit",
                    f"node:{node.id}.{slot_name}.unit",
                    f"unit '{value.unit}' is not recognized by Pint",
                )

    if issues:
        raise KEGValidationError(issues)
