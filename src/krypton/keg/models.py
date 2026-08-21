"""Canonical JSON-backed Krypton Effect Graph data models."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import TypeAlias

import networkx as nx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from krypton.domain import (
    ApplicabilityContext,
    CategoricalValue,
    EditObject,
    EvidenceRecord,
    QuantityValue,
)

AttributeValue: TypeAlias = str | int | float | bool | None
NodeValue: TypeAlias = QuantityValue | CategoricalValue


class NodeType(StrEnum):
    GENOMIC_EDIT = "genomic_edit"
    MOLECULAR_QUANTITY = "molecular_quantity"
    CELLULAR_STATE = "cellular_state"
    TISSUE_PARAMETER = "tissue_parameter"
    MODEL_PARAMETER = "model_parameter"
    PHYSIOLOGICAL_STATE = "physiological_state"
    PHENOTYPE_ENDPOINT = "phenotype_endpoint"


class ValidationStatus(StrEnum):
    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    REJECTED = "rejected"


class EdgeUnits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_unit: str = Field(min_length=1)
    target_unit: str = Field(min_length=1)

    @field_validator("source_unit", "target_unit")
    @classmethod
    def units_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("edge units must be explicit; use 'dimensionless' when appropriate")
        return value


class KEGNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    node_type: NodeType
    label: str = Field(min_length=1)
    quantity_kind: str | None = None
    quantity: NodeValue | None = None
    baseline: NodeValue | None = None
    edited: NodeValue | None = None
    edit_reference: str | None = None
    model_contract_reference: str | None = None
    model_contract_version: str | None = None
    model_parameter_id: str | None = None
    attributes: dict[str, AttributeValue] = Field(default_factory=dict)

    @field_validator(
        "id",
        "label",
        "quantity_kind",
        "edit_reference",
        "model_contract_reference",
        "model_contract_version",
        "model_parameter_id",
    )
    @classmethod
    def strings_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("KEG identifiers and labels must not be blank")
        return value

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> KEGNode:
        if self.node_type is NodeType.GENOMIC_EDIT:
            if self.edit_reference is None:
                raise ValueError("genomic_edit nodes require edit_reference")
        elif self.edit_reference is not None:
            raise ValueError("edit_reference is only valid on genomic_edit nodes")

        model_fields = (
            self.model_contract_reference,
            self.model_contract_version,
            self.model_parameter_id,
        )
        if self.node_type is NodeType.MODEL_PARAMETER:
            if any(value is None for value in model_fields):
                raise ValueError(
                    "model_parameter nodes require model_contract_reference, "
                    "model_contract_version, and model_parameter_id"
                )
        elif any(value is not None for value in model_fields):
            raise ValueError("model contract fields are only valid on model_parameter nodes")

        values = (self.quantity, self.baseline, self.edited)
        if any(value is not None for value in values) and self.quantity_kind is None:
            raise ValueError("nodes carrying a value require an extensible quantity_kind")
        if self.quantity is not None and (
            self.baseline is not None or self.edited is not None
        ):
            raise ValueError("legacy quantity and paired baseline/edited values are exclusive")
        if (self.baseline is None) != (self.edited is None):
            raise ValueError("paired KEG values require both baseline and edited")
        if self.baseline is not None and type(self.baseline) is not type(self.edited):
            raise ValueError("baseline and edited KEG values must use the same value type")
        return self


class KEGEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    relation_type: str = Field(min_length=1)
    transformation_reference: str | None = None
    units: EdgeUnits
    tissue: str | None = None
    time_scale: str | None = None
    evidence_ids: tuple[str, ...] = ()
    applicability_reference: str | None = None
    uncertainty_note: str | None = None
    mapping_version: str | None = None
    model_version: str | None = None
    validation_status: ValidationStatus = ValidationStatus.UNVALIDATED

    @field_validator(
        "id",
        "source",
        "target",
        "relation_type",
        "transformation_reference",
        "tissue",
        "time_scale",
        "applicability_reference",
        "uncertainty_note",
        "mapping_version",
        "model_version",
    )
    @classmethod
    def strings_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("KEG edge strings must not be blank")
        return value

    @field_validator("evidence_ids")
    @classmethod
    def evidence_ids_must_be_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("edge evidence_ids must not contain blank identifiers")
        if len(values) != len(set(values)):
            raise ValueError("edge evidence_ids must be unique")
        return values

    @model_validator(mode="after")
    def transformation_has_version(self) -> KEGEdge:
        if self.transformation_reference is not None and self.mapping_version is None:
            raise ValueError("a transformation_reference requires mapping_version")
        return self


class KEGDocument(BaseModel):
    """Canonical KEG v0 document; NetworkX is only a derived runtime view."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "keg-v0"
    id: str = Field(min_length=1)
    edit: EditObject
    nodes: tuple[KEGNode, ...]
    edges: tuple[KEGEdge, ...]
    evidence: tuple[EvidenceRecord, ...] = ()
    applicability_contexts: dict[str, ApplicabilityContext] = Field(default_factory=dict)
    result_node_ids: tuple[str, ...]

    @field_validator("schema_version")
    @classmethod
    def supported_schema_version(cls, value: str) -> str:
        if value != "keg-v0":
            raise ValueError("C0 supports only schema_version 'keg-v0'")
        return value

    @field_validator("id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("KEG document id must not be blank")
        return value

    @field_validator("result_node_ids")
    @classmethod
    def result_nodes_required_and_unique(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values:
            raise ValueError("KEG requires at least one downstream result_node_id")
        if any(not value.strip() for value in values):
            raise ValueError("result_node_ids must not contain blank identifiers")
        if len(values) != len(set(values)):
            raise ValueError("result_node_ids must be unique")
        return values

    @field_validator("applicability_contexts")
    @classmethod
    def applicability_ids_must_not_be_blank(
        cls, values: dict[str, ApplicabilityContext]
    ) -> dict[str, ApplicabilityContext]:
        if any(not key.strip() for key in values):
            raise ValueError("applicability context identifiers must not be blank")
        return values

    def canonical_json(self) -> str:
        """Return deterministic, whitespace-free canonical JSON for this document."""

        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_multidigraph(self) -> nx.MultiDiGraph:
        """Build a disposable runtime view without making NetworkX canonical."""

        graph = nx.MultiDiGraph(keg_id=self.id, schema_version=self.schema_version)
        for node in self.nodes:
            graph.add_node(node.id, **node.model_dump(mode="json"))
        for edge in self.edges:
            graph.add_edge(
                edge.source,
                edge.target,
                key=edge.id,
                **edge.model_dump(mode="json"),
            )
        return graph
