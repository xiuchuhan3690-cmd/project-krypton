"""Numerical quantities and their explicitly classified uncertainty."""

from __future__ import annotations

from enum import StrEnum
from math import isfinite

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DistributionType(StrEnum):
    FIXED = "fixed"
    INTERVAL = "interval"
    NORMAL = "normal"
    LOGNORMAL = "lognormal"
    BETA = "beta"


class UncertaintyType(StrEnum):
    MEASUREMENT = "measurement_uncertainty"
    BIOLOGICAL_VARIABILITY = "biological_variability"
    PARAMETER = "parameter_uncertainty"
    MODEL = "model_uncertainty"
    EVIDENCE = "evidence_uncertainty"


class UncertaintyAnnotation(BaseModel):
    """A qualitative uncertainty annotation; numerical uncertainty is in QuantityValue."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    category: UncertaintyType
    description: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = ()

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("uncertainty description must not be blank")
        return value


class QuantityValue(BaseModel):
    """A unit-bearing scalar or supported C0 probability distribution.

    ``mean`` and ``standard_deviation`` use linear-space parameters for normal
    quantities and log-space parameters for lognormal quantities.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    distribution: DistributionType
    unit: str = Field(min_length=1)
    semantic_kind: str | None = None
    value: float | None = None
    lower: float | None = None
    upper: float | None = None
    mean: float | None = None
    standard_deviation: float | None = Field(default=None, gt=0)
    alpha: float | None = Field(default=None, gt=0)
    beta: float | None = Field(default=None, gt=0)
    uncertainty: tuple[UncertaintyAnnotation, ...] = ()
    correlation_group: str | None = None

    @field_validator("unit")
    @classmethod
    def unit_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("unit must be explicit; use 'dimensionless' when appropriate")
        return value

    @field_validator("value", "lower", "upper", "mean")
    @classmethod
    def values_must_be_finite(cls, value: float | None) -> float | None:
        if value is not None and not isfinite(value):
            raise ValueError("numerical quantity values must be finite")
        return value

    @field_validator("semantic_kind", "correlation_group")
    @classmethod
    def optional_strings_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("optional labels must be omitted rather than blank")
        return value

    @model_validator(mode="after")
    def validate_distribution_parameters(self) -> QuantityValue:
        supplied = {
            name
            for name in ("value", "lower", "upper", "mean", "standard_deviation", "alpha", "beta")
            if getattr(self, name) is not None
        }
        expected = {
            DistributionType.FIXED: {"value"},
            DistributionType.INTERVAL: {"lower", "upper"},
            DistributionType.NORMAL: {"mean", "standard_deviation"},
            DistributionType.LOGNORMAL: {"mean", "standard_deviation"},
            DistributionType.BETA: {"alpha", "beta"},
        }[self.distribution]
        if supplied != expected:
            missing = sorted(expected - supplied)
            unexpected = sorted(supplied - expected)
            details = []
            if missing:
                details.append(f"missing {missing}")
            if unexpected:
                details.append(f"unexpected {unexpected}")
            raise ValueError(
                f"{self.distribution.value} distribution parameters are invalid: "
                + "; ".join(details)
            )
        if self.distribution is DistributionType.INTERVAL and self.lower >= self.upper:
            raise ValueError("interval lower must be strictly less than upper")
        if self.distribution is DistributionType.BETA and self.unit != "dimensionless":
            raise ValueError("beta distributions require the explicit unit 'dimensionless'")
        return self
