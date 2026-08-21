"""C0 applicability contexts with deliberately simple matching rules."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ApplicabilityResult(StrEnum):
    IN_DOMAIN = "in_domain"
    PARTIAL = "partial"
    OUT_OF_DOMAIN = "out_of_domain"
    UNKNOWN = "unknown"


class AgeRange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    minimum_years: float = Field(ge=0)
    maximum_years: float = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> AgeRange:
        if self.minimum_years > self.maximum_years:
            raise ValueError("minimum_years must not exceed maximum_years")
        return self


class ApplicabilityContext(BaseModel):
    """A set of allowed labels/ranges, or a candidate context for assessment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tissue: tuple[str, ...] = ()
    age_range: AgeRange | None = None
    sex: tuple[str, ...] = ()
    disease_status: tuple[str, ...] = ()
    medications: tuple[str, ...] = ()
    population_ancestry: tuple[str, ...] = ()
    environmental_tags: tuple[str, ...] = ()
    developmental_stage: tuple[str, ...] = ()
    experimental_system: tuple[str, ...] = ()

    @field_validator(
        "tissue",
        "sex",
        "disease_status",
        "medications",
        "population_ancestry",
        "environmental_tags",
        "developmental_stage",
        "experimental_system",
    )
    @classmethod
    def labels_must_be_normalized(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("applicability labels must not be blank")
        if len(values) != len(set(values)):
            raise ValueError("applicability labels must be unique within a field")
        return values

    def assess(self, candidate: ApplicabilityContext) -> ApplicabilityResult:
        """Assess ``candidate`` using equality, membership, and range containment."""

        constrained = False
        outcomes: list[ApplicabilityResult] = []
        fields = (
            "tissue",
            "sex",
            "disease_status",
            "medications",
            "population_ancestry",
            "environmental_tags",
            "developmental_stage",
            "experimental_system",
        )
        for field in fields:
            allowed = set(getattr(self, field))
            if not allowed:
                continue
            constrained = True
            actual = set(getattr(candidate, field))
            if not actual:
                outcomes.append(ApplicabilityResult.UNKNOWN)
            elif actual <= allowed:
                outcomes.append(ApplicabilityResult.IN_DOMAIN)
            elif actual & allowed:
                outcomes.append(ApplicabilityResult.PARTIAL)
            else:
                outcomes.append(ApplicabilityResult.OUT_OF_DOMAIN)

        if self.age_range is not None:
            constrained = True
            actual_age = candidate.age_range
            if actual_age is None:
                outcomes.append(ApplicabilityResult.UNKNOWN)
            elif (
                self.age_range.minimum_years <= actual_age.minimum_years
                and actual_age.maximum_years <= self.age_range.maximum_years
            ):
                outcomes.append(ApplicabilityResult.IN_DOMAIN)
            elif (
                actual_age.maximum_years < self.age_range.minimum_years
                or actual_age.minimum_years > self.age_range.maximum_years
            ):
                outcomes.append(ApplicabilityResult.OUT_OF_DOMAIN)
            else:
                outcomes.append(ApplicabilityResult.PARTIAL)

        if not constrained or not outcomes:
            return ApplicabilityResult.UNKNOWN
        if ApplicabilityResult.UNKNOWN in outcomes:
            return ApplicabilityResult.UNKNOWN
        if ApplicabilityResult.OUT_OF_DOMAIN in outcomes:
            if all(outcome is ApplicabilityResult.OUT_OF_DOMAIN for outcome in outcomes):
                return ApplicabilityResult.OUT_OF_DOMAIN
            return ApplicabilityResult.PARTIAL
        if ApplicabilityResult.PARTIAL in outcomes:
            return ApplicabilityResult.PARTIAL
        return ApplicabilityResult.IN_DOMAIN
