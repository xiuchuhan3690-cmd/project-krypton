import math

import pytest
from pydantic import ValidationError

from krypton.domain import (
    DistributionType,
    QuantityValue,
    UncertaintyAnnotation,
    UncertaintyType,
)


@pytest.mark.parametrize(
    "payload",
    [
        {"distribution": "fixed", "unit": "mg", "value": 100.0},
        {"distribution": "interval", "unit": "L/h", "lower": 4.0, "upper": 10.0},
        {
            "distribution": "normal",
            "unit": "mg/L",
            "mean": 2.0,
            "standard_deviation": 0.2,
        },
        {
            "distribution": "lognormal",
            "unit": "L/h",
            "mean": 1.0,
            "standard_deviation": 0.25,
        },
        {"distribution": "beta", "unit": "dimensionless", "alpha": 2.0, "beta": 5.0},
    ],
)
def test_supported_quantity_distributions_round_trip(payload: dict[str, object]) -> None:
    quantity = QuantityValue.model_validate(payload)

    assert QuantityValue.model_validate_json(quantity.model_dump_json()) == quantity


def test_uncertainty_annotations_and_correlation_group_are_preserved() -> None:
    quantity = QuantityValue(
        distribution=DistributionType.FIXED,
        unit="dimensionless",
        semantic_kind="relative_activity",
        value=0.4,
        uncertainty=(
            UncertaintyAnnotation(
                category=UncertaintyType.BIOLOGICAL_VARIABILITY,
                description="Mock inter-individual variability",
                evidence_ids=("evidence:mock",),
            ),
        ),
        correlation_group="activity-pair",
    )

    assert quantity.uncertainty[0].category is UncertaintyType.BIOLOGICAL_VARIABILITY
    assert quantity.correlation_group == "activity-pair"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"distribution": "fixed", "unit": "", "value": 1}, "unit"),
        ({"distribution": "fixed", "unit": "mg"}, "missing"),
        (
            {"distribution": "fixed", "unit": "mg", "value": 1, "mean": 1},
            "unexpected",
        ),
        (
            {"distribution": "interval", "unit": "mg", "lower": 2, "upper": 1},
            "strictly less",
        ),
        (
            {
                "distribution": "normal",
                "unit": "mg",
                "mean": 1,
                "standard_deviation": 0,
            },
            "greater than 0",
        ),
        (
            {"distribution": "beta", "unit": "percent", "alpha": 2, "beta": 3},
            "dimensionless",
        ),
    ],
)
def test_invalid_quantity_values_are_rejected(payload: dict[str, object], message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        QuantityValue.model_validate(payload)


def test_non_finite_quantity_is_rejected() -> None:
    with pytest.raises(ValidationError, match="finite"):
        QuantityValue(distribution="fixed", unit="mg", value=math.inf)
