from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from krypton.domain import (
    ConfidenceLevel,
    CurationMetadata,
    EvidenceClass,
    EvidenceRecord,
)


def valid_evidence() -> EvidenceRecord:
    timestamp = datetime(2026, 8, 16, 0, 0, tzinfo=UTC)
    return EvidenceRecord(
        id="evidence:mock-assumption",
        evidence_class=EvidenceClass.MECHANISTIC_MODEL_ASSUMPTION,
        source="internal-mock",
        identifier="mock-clearance-mapping",
        version="1.0.0",
        claim="Mock enzyme activity scales mock clearance.",
        applicability_reference="applicability:mock",
        confidence=ConfidenceLevel.LOW,
        limitations=("Architecture test only; not biological evidence.",),
        retrieval_timestamp=timestamp,
        curation=CurationMetadata(curator="project-krypton", curated_at=timestamp),
    )


def test_evidence_record_round_trip_and_enum_coverage() -> None:
    evidence = valid_evidence()

    assert EvidenceRecord.model_validate_json(evidence.model_dump_json()) == evidence
    assert {item.value for item in EvidenceClass} == {
        "observed_interventional_human",
        "observed_human_functional",
        "observed_model_system",
        "validated_computational_prediction",
        "association",
        "mechanistic_model_assumption",
        "speculative_mapping",
    }


def test_naive_retrieval_timestamp_is_rejected() -> None:
    payload = valid_evidence().model_dump()
    payload["retrieval_timestamp"] = datetime(2026, 8, 16)

    with pytest.raises(ValidationError, match="timezone"):
        EvidenceRecord.model_validate(payload)


def test_naive_curation_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="timezone"):
        CurationMetadata(curator="project-krypton", curated_at=datetime(2026, 8, 16))


def test_blank_claim_and_limitation_are_rejected() -> None:
    payload = valid_evidence().model_dump()
    payload["claim"] = "   "
    payload["limitations"] = ("",)

    with pytest.raises(ValidationError) as error:
        EvidenceRecord.model_validate(payload)

    assert "required evidence text" in str(error.value)
    assert "limitations" in str(error.value)


def test_unknown_evidence_class_is_rejected() -> None:
    payload = valid_evidence().model_dump()
    payload["evidence_class"] = "generated_by_llm"

    with pytest.raises(ValidationError, match="evidence_class"):
        EvidenceRecord.model_validate(payload)
