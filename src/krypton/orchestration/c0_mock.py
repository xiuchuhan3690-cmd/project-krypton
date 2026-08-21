"""Full C0 mock workflow integration; deliberately not biological evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
from pydantic import BaseModel, ConfigDict

from krypton.adapters import MockPKAdapter
from krypton.domain import (
    ArtifactReference,
    ConfidenceLevel,
    EditObject,
    EvidencePathEntry,
    EvidenceRecord,
    ModelVersionReference,
    PhenotypeConsequence,
    PredictedDirection,
    ProvenanceManifest,
    QuantityValue,
    collect_provenance,
    digest_model,
)
from krypton.keg import KEGDocument, KEGValidationContext, validate_keg
from krypton.models import ModelContract
from krypton.mpt import (
    MPTMappingDefinition,
    MPTRegistry,
    MPTRequest,
    MPTResult,
    translate,
)
from krypton.orchestration.pair_runner import (
    EditDerivedParameterChange,
    NamedQuantity,
    PairRunResult,
    PairRunSpec,
    PairRunner,
    SharedSetting,
)
from krypton.registry import ModelRegistry

MOCK_ADAPTER_ENTRY_POINT = "krypton.adapters.mock:MockPKAdapter"
DEFAULT_MOCK_TIMESTAMP = datetime(2026, 8, 16, tzinfo=UTC)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


class C0MockWorkflowResult(BaseModel):
    """Serializable aggregate proving every C0 component participated."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    edit: EditObject
    evidence: EvidenceRecord
    applicability_id: str
    keg: KEGDocument
    keg_path_node_ids: tuple[str, ...]
    keg_path_edge_ids: tuple[str, ...]
    mpt_mapping: MPTMappingDefinition
    mpt_result: MPTResult
    model_contract: ModelContract
    pair_run_spec: PairRunSpec
    pair_result: PairRunResult
    provenance: ProvenanceManifest
    consequence: PhenotypeConsequence

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    def digest(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


class C0MockWorkflow:
    """Prepared mock workflow exposing its adapter for pre-execution assertions."""

    def __init__(self, project_root: Path, *, timestamp: datetime = DEFAULT_MOCK_TIMESTAMP) -> None:
        self.project_root = project_root.resolve()
        self.timestamp = timestamp
        self.keg = KEGDocument.model_validate_json(
            (self.project_root / "fixtures" / "valid" / "keg_mock_v0.json").read_text(
                encoding="utf-8"
            )
        )
        self.edit = self.keg.edit
        self.evidence = self.keg.evidence[0]
        self.applicability_id = "applicability:mock"
        self.applicability = self.keg.applicability_contexts[self.applicability_id]
        self.mapping = MPTMappingDefinition.model_validate_json(
            (
                self.project_root
                / "fixtures"
                / "valid"
                / "mpt_scale_mapping_v0.json"
            ).read_text(encoding="utf-8")
        )
        request_fixture = MPTRequest.model_validate_json(
            (self.project_root / "fixtures" / "valid" / "mpt_request_v0.json").read_text(
                encoding="utf-8"
            )
        )
        self.mpt_request = request_fixture.model_copy(
            update={
                "context": self.applicability,
                "evidence": (self.evidence,),
            }
        )
        self.mpt_registry = MPTRegistry()
        self.mpt_registry.register(self.mapping)

        self.model_registry = ModelRegistry(
            adapter_factories={MOCK_ADAPTER_ENTRY_POINT: MockPKAdapter}
        )
        self.model_registry.load_directory(self.project_root / "registry" / "models")
        self.contract = self.model_registry.get_contract("contract:mock-pk", "1.0.0")
        adapter = self.model_registry.get_adapter("contract:mock-pk", "1.0.0")
        if not isinstance(adapter, MockPKAdapter):
            raise TypeError("C0 mock workflow requires the allowlisted MockPKAdapter")
        self.adapter = adapter

        validate_keg(
            self.keg,
            KEGValidationContext(
                mapping_ids=frozenset(
                    {
                        "mapping:edit-activity",
                        "mapping:activity-clearance",
                        "mapping:clearance-auc",
                    }
                ),
                model_parameters=frozenset(
                    {
                        (
                            self.contract.id,
                            self.contract.metadata.model_version,
                            self.mapping.target.parameter_id,
                        )
                    }
                ),
            ),
        )
        graph = self.keg.to_multidigraph()
        root_id = next(
            node.id for node in self.keg.nodes if node.node_type.value == "genomic_edit"
        )
        result_id = self.keg.result_node_ids[0]
        self.keg_path_node_ids = tuple(nx.shortest_path(graph, root_id, result_id))
        self.keg_path_edge_ids = tuple(
            sorted(graph.get_edge_data(source, target))[0]
            for source, target in zip(self.keg_path_node_ids, self.keg_path_node_ids[1:])
        )

    def _pair_spec(
        self,
        mpt_result: MPTResult,
        unauthorized_edited_dose: QuantityValue | None,
    ) -> PairRunSpec:
        overrides = (
            (NamedQuantity(parameter_id="dose", quantity=unauthorized_edited_dose),)
            if unauthorized_edited_dose is not None
            else ()
        )
        adapter_id = f"{self.adapter.__class__.__module__}:{self.adapter.__class__.__qualname__}"
        return PairRunSpec(
            id="pair:mock-clearance",
            edit_id=self.edit.id,
            model_contract_id=self.contract.id,
            model_contract_version=self.contract.metadata.model_version,
            adapter_id=adapter_id,
            adapter_artifact_digest=self.adapter.artifact_digest,
            seed=42,
            context=self.applicability,
            environment=(SharedSetting(key="simulation_mode", value="deterministic"),),
            initial_conditions=(SharedSetting(key="state", value="mock-steady-state"),),
            shared_inputs=(
                NamedQuantity(
                    parameter_id="dose",
                    quantity=QuantityValue(
                        distribution="fixed",
                        unit="mg",
                        semantic_kind="dose_amount",
                        value=100,
                    ),
                ),
            ),
            authorized_changes=(
                EditDerivedParameterChange(
                    parameter_id=mpt_result.target.parameter_id,
                    baseline=mpt_result.baseline,
                    edited=mpt_result.edited,
                    mapping_id=mpt_result.mapping_id,
                    mapping_version=mpt_result.mapping_version,
                    mapping_digest=mpt_result.mapping_digest,
                ),
            ),
            edited_input_overrides=overrides,
        )

    def run(
        self,
        *,
        unauthorized_edited_dose: QuantityValue | None = None,
    ) -> C0MockWorkflowResult:
        mpt_result = translate(self.mpt_request, self.mpt_registry)
        pair_spec = self._pair_spec(mpt_result, unauthorized_edited_dose)
        pair_result = PairRunner(self.contract, self.adapter).run(pair_spec)
        provenance = collect_provenance(
            run_id="run:mock-c0-e2e",
            repository=self.project_root,
            dependency_lock=self.project_root / "requirements.lock",
            edit_object=ArtifactReference(
                id=self.edit.id,
                version="edit-object-v0",
                digest=digest_model(self.edit),
            ),
            keg=ArtifactReference(
                id=self.keg.id,
                version=self.keg.schema_version,
                digest=self.keg.digest(),
            ),
            mpt=ArtifactReference(
                id=mpt_result.mapping_id,
                version=mpt_result.mapping_version,
                digest=mpt_result.mapping_digest,
            ),
            model_artifact=ArtifactReference(
                id=self.contract.id,
                version=self.contract.metadata.model_version,
                digest=self.contract.metadata.artifact_digest,
            ),
            pair_run_spec=ArtifactReference(
                id=pair_spec.id,
                version="pair-run-spec-v0",
                digest=pair_spec.digest(),
            ),
            environment_digest=pair_spec.environment_digest(),
            random_seed=pair_result.baseline_branch.seed,
            timestamp=self.timestamp,
        )
        delta = pair_result.deltas[0]
        consequence = PhenotypeConsequence(
            id="consequence:mock-auc",
            endpoint="mock_auc",
            baseline=delta.baseline,
            edited=delta.edited,
            delta=delta.delta,
            delta_propagated=True,
            predicted_direction=PredictedDirection.INCREASE,
            time_horizon="mock total exposure",
            confidence=ConfidenceLevel.MODERATE,
            applicability_assessment=mpt_result.applicability_result,
            major_uncertainties=(
                "Artificial architecture equation with no biological interpretation",
            ),
            evidence_path=(
                EvidencePathEntry(
                    evidence_id=self.evidence.id,
                    evidence_class=self.evidence.evidence_class,
                    keg_edge_ids=self.keg_path_edge_ids,
                    mapping_id=mpt_result.mapping_id,
                ),
            ),
            model_versions=(
                ModelVersionReference(
                    model_name=self.contract.metadata.model_name,
                    model_version=self.contract.metadata.model_version,
                    contract_id=self.contract.id,
                    artifact_digest=self.contract.metadata.artifact_digest,
                ),
            ),
            provenance_reference=f"sha256:{provenance.digest()}",
        )
        return C0MockWorkflowResult(
            edit=self.edit,
            evidence=self.evidence,
            applicability_id=self.applicability_id,
            keg=self.keg,
            keg_path_node_ids=self.keg_path_node_ids,
            keg_path_edge_ids=self.keg_path_edge_ids,
            mpt_mapping=self.mapping,
            mpt_result=mpt_result,
            model_contract=self.contract,
            pair_run_spec=pair_spec,
            pair_result=pair_result,
            provenance=provenance,
            consequence=consequence,
        )


def build_c0_mock_workflow(
    project_root: Path, *, timestamp: datetime = DEFAULT_MOCK_TIMESTAMP
) -> C0MockWorkflow:
    return C0MockWorkflow(project_root, timestamp=timestamp)
