"""Export deterministic Draft 2020-12 schemas for the public-core contracts."""

from __future__ import annotations

import json
from pathlib import Path

from krypton.domain import (
    ApplicabilityContext,
    EditObject,
    EvidenceRecord,
    PhenotypeConsequence,
    ProvenanceManifest,
    QuantityValue,
)
from krypton.keg import KEGDocument
from krypton.models import ModelContract
from krypton.mpt import MPTMappingDefinition, MPTResultUnion
from krypton.orchestration import PairRunSpec


ROOT = Path(__file__).parents[1]
SCHEMAS = {
    "applicability-context.schema.json": ApplicabilityContext,
    "edit-object.schema.json": EditObject,
    "evidence-record.schema.json": EvidenceRecord,
    "keg-document.schema.json": KEGDocument,
    "model-contract.schema.json": ModelContract,
    "mpt-mapping.schema.json": MPTMappingDefinition,
    "mpt-result.schema.json": MPTResultUnion,
    "pair-run-spec.schema.json": PairRunSpec,
    "phenotype-consequence.schema.json": PhenotypeConsequence,
    "provenance-manifest.schema.json": ProvenanceManifest,
    "quantity-value.schema.json": QuantityValue,
}


def main() -> None:
    output = ROOT / "src" / "krypton" / "resources" / "schemas"
    output.mkdir(exist_ok=True)
    for filename, model in sorted(SCHEMAS.items()):
        schema = model.model_json_schema()
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        schema = {key: schema[key] for key in sorted(schema)}
        (output / filename).write_text(
            json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
