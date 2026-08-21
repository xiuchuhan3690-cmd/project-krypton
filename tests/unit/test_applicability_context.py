import pytest
from pydantic import ValidationError

from krypton.domain import AgeRange, ApplicabilityContext, ApplicabilityResult


def test_in_domain_uses_membership_and_range_containment() -> None:
    applicability = ApplicabilityContext(
        tissue=("liver", "kidney"),
        age_range=AgeRange(minimum_years=18, maximum_years=65),
        sex=("female", "male"),
        disease_status=("healthy",),
    )
    candidate = ApplicabilityContext(
        tissue=("liver",),
        age_range=AgeRange(minimum_years=30, maximum_years=40),
        sex=("female",),
        disease_status=("healthy",),
    )

    assert applicability.assess(candidate) is ApplicabilityResult.IN_DOMAIN


def test_overlapping_range_is_partial() -> None:
    applicability = ApplicabilityContext(age_range=AgeRange(minimum_years=18, maximum_years=65))
    candidate = ApplicabilityContext(age_range=AgeRange(minimum_years=60, maximum_years=70))

    assert applicability.assess(candidate) is ApplicabilityResult.PARTIAL


def test_disjoint_membership_is_out_of_domain() -> None:
    applicability = ApplicabilityContext(experimental_system=("human",))
    candidate = ApplicabilityContext(experimental_system=("mouse",))

    assert applicability.assess(candidate) is ApplicabilityResult.OUT_OF_DOMAIN


def test_mixed_match_and_mismatch_is_partial() -> None:
    applicability = ApplicabilityContext(tissue=("liver",), sex=("female",))
    candidate = ApplicabilityContext(tissue=("liver",), sex=("male",))

    assert applicability.assess(candidate) is ApplicabilityResult.PARTIAL


def test_missing_candidate_fact_is_unknown() -> None:
    applicability = ApplicabilityContext(tissue=("liver",), medications=("drug-a",))
    candidate = ApplicabilityContext(tissue=("liver",))

    assert applicability.assess(candidate) is ApplicabilityResult.UNKNOWN


def test_unconstrained_context_is_unknown() -> None:
    assert ApplicabilityContext().assess(ApplicabilityContext(tissue=("liver",))) is ApplicabilityResult.UNKNOWN


@pytest.mark.parametrize(
    "payload",
    [
        {"age_range": {"minimum_years": 70, "maximum_years": 20}},
        {"tissue": ["liver", "liver"]},
        {"environmental_tags": [""]},
    ],
)
def test_invalid_applicability_context_is_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ApplicabilityContext.model_validate(payload)
