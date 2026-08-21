from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.domain import (
    ApplicabilityResult,
    ConfidenceLevel,
    EvidenceClass,
    EvidencePathEntry,
    PhenotypeConsequence,
    PredictedDirection,
    QuantityValue,
)


ROOT = Path(__file__).parents[2]
RESOURCE_ROOT = ROOT / "src" / "krypton" / "resources"
VALID_FIXTURE = RESOURCE_ROOT / "fixtures" / "valid" / "phenotype_consequence_mock_v0.json"


def valid_payload() -> dict[str, object]:
    return PhenotypeConsequence.model_validate_json(
        VALID_FIXTURE.read_text(encoding="utf-8")
    ).model_dump()


def consequence(**changes: object) -> PhenotypeConsequence:
    payload = valid_payload()
    payload.update(changes)
    return PhenotypeConsequence.model_validate(payload)


def fixed(value: float, unit: str = "mg*h/L") -> QuantityValue:
    return QuantityValue(
        distribution="fixed", unit=unit, semantic_kind="auc", value=value
    )


def test_valid_consequence_fixture_round_trips() -> None:
    result = PhenotypeConsequence.model_validate_json(VALID_FIXTURE.read_text(encoding="utf-8"))

    assert result.endpoint == "mock_auc"
    assert result.baseline.value == 10
    assert result.edited.value == 25
    assert result.delta.value == 15
    assert result.predicted_direction is PredictedDirection.INCREASE
    assert result.confidence is ConfidenceLevel.MODERATE
    assert result.applicability_assessment is ApplicabilityResult.IN_DOMAIN
    assert result.confidence_ceiling_reasons == ()
    assert PhenotypeConsequence.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        (
            {"applicability_assessment": ApplicabilityResult.OUT_OF_DOMAIN},
            "out-of-domain",
        ),
        (
            {"out_of_domain_flags": ("age outside validated range",)},
            "out-of-domain",
        ),
        (
            {"applicability_assessment": ApplicabilityResult.UNKNOWN},
            "unresolved",
        ),
        (
            {
                "evidence_path": (
                    EvidencePathEntry(
                        evidence_id="evidence:speculative",
                        evidence_class=EvidenceClass.SPECULATIVE_MAPPING,
                    ),
                )
            },
            "speculative-only",
        ),
    ],
)
def test_low_confidence_ceilings(changes: dict[str, object], reason: str) -> None:
    result = consequence(confidence=ConfidenceLevel.HIGH, **changes)

    assert result.confidence is ConfidenceLevel.LOW
    assert any(reason in item for item in result.confidence_ceiling_reasons)


def test_ceiling_never_raises_already_lower_confidence() -> None:
    result = consequence(
        confidence=ConfidenceLevel.INDETERMINATE,
        applicability_assessment=ApplicabilityResult.OUT_OF_DOMAIN,
    )

    assert result.confidence is ConfidenceLevel.INDETERMINATE


def test_partial_applicability_does_not_invent_an_unspecified_ceiling() -> None:
    result = consequence(
        confidence=ConfidenceLevel.MODERATE,
        applicability_assessment=ApplicabilityResult.PARTIAL,
    )

    assert result.confidence is ConfidenceLevel.MODERATE
    assert result.confidence_ceiling_reasons == ()


def test_unpropagated_delta_is_indeterminate() -> None:
    result = consequence(
        delta=None,
        delta_propagated=False,
        predicted_direction=PredictedDirection.INCREASE,
        confidence=ConfidenceLevel.HIGH,
    )

    assert result.delta is None
    assert result.predicted_direction is PredictedDirection.INDETERMINATE
    assert result.confidence is ConfidenceLevel.INDETERMINATE
    assert "not propagated" in result.confidence_ceiling_reasons[0]


def test_bad_delta_fixture_is_rejected() -> None:
    fixture = RESOURCE_ROOT / "fixtures" / "invalid" / "phenotype_consequence_bad_delta_v0.json"

    with pytest.raises(ValidationError, match="does not equal edited-baseline"):
        PhenotypeConsequence.model_validate_json(fixture.read_text(encoding="utf-8"))


def test_direction_must_match_fixed_delta() -> None:
    with pytest.raises(ValidationError, match="predicted_direction"):
        consequence(predicted_direction=PredictedDirection.DECREASE)


def test_consequence_units_must_already_be_canonical_and_identical() -> None:
    with pytest.raises(ValidationError, match="baseline and edited"):
        consequence(edited=fixed(0.025, "g*h/L"), delta=fixed(0.015, "g*h/L"))

    with pytest.raises(ValidationError, match="delta unit"):
        consequence(delta=fixed(0.015, "g*h/L"))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("major_uncertainties", "major uncertainty"),
        ("evidence_path", "evidence path"),
        ("model_versions", "model version"),
    ],
)
def test_required_traceability_collections_cannot_be_empty(field: str, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        consequence(**{field: ()})


def test_delta_presence_matches_propagation_flag() -> None:
    with pytest.raises(ValidationError, match="requires delta"):
        consequence(delta=None, delta_propagated=True)
    with pytest.raises(ValidationError, match="represented as null"):
        consequence(delta_propagated=False)
