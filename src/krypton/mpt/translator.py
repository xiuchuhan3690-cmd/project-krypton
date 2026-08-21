"""Deterministic execution of supported C0 MPT mappings."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log
from typing import Protocol

import pint

from krypton.domain import ApplicabilityResult, DistributionType, QuantityValue
from krypton.mpt.models import (
    MPTMappingDefinition,
    MPTRequest,
    MPTResult,
    MPTResultValue,
    MappingType,
)
from krypton.mpt.registry import MPTRegistry

_UNITS = pint.UnitRegistry()


class MPTTranslationError(ValueError):
    pass


class MechanisticParameterTranslator(Protocol):
    """Generic interface consumed by later orchestration code."""

    def translate(self, request: MPTRequest) -> MPTResultValue: ...


@dataclass(frozen=True)
class RegistryMPT:
    """Translator backed only by an explicit C0 mapping registry."""

    registry: MPTRegistry

    def translate(self, request: MPTRequest) -> MPTResultValue:
        return translate(request, self.registry)


def _linear_transform(
    quantity: QuantityValue,
    *,
    factor: float,
    offset: float,
    target_unit: str,
    target_kind: str,
) -> QuantityValue:
    common = {
        "distribution": quantity.distribution,
        "unit": target_unit,
        "semantic_kind": target_kind,
        "uncertainty": quantity.uncertainty,
        "correlation_group": quantity.correlation_group,
    }
    if quantity.distribution is DistributionType.FIXED:
        return QuantityValue(**common, value=factor * quantity.value + offset)
    if quantity.distribution is DistributionType.INTERVAL:
        transformed = (factor * quantity.lower + offset, factor * quantity.upper + offset)
        return QuantityValue(**common, lower=min(transformed), upper=max(transformed))
    if quantity.distribution is DistributionType.NORMAL:
        return QuantityValue(
            **common,
            mean=factor * quantity.mean + offset,
            standard_deviation=abs(factor) * quantity.standard_deviation,
        )
    if quantity.distribution is DistributionType.LOGNORMAL:
        if factor <= 0 or offset != 0:
            raise MPTTranslationError(
                "lognormal quantities support only a positive multiplicative transformation"
            )
        return QuantityValue(
            **common,
            mean=quantity.mean + log(factor),
            standard_deviation=quantity.standard_deviation,
        )
    if factor != 1 or offset != 0:
        raise MPTTranslationError("beta quantities support identity translation only")
    return QuantityValue(
        **common,
        alpha=quantity.alpha,
        beta=quantity.beta,
    )


def _convert_to_source(quantity: QuantityValue, mapping: MPTMappingDefinition) -> QuantityValue:
    if quantity.semantic_kind != mapping.source_quantity_kind:
        raise MPTTranslationError(
            f"source semantic kind must be '{mapping.source_quantity_kind}', "
            f"received '{quantity.semantic_kind}'"
        )
    try:
        factor = _UNITS.Quantity(1, quantity.unit).to(mapping.source_unit).magnitude
    except (pint.DimensionalityError, pint.UndefinedUnitError) as error:
        raise MPTTranslationError(
            f"source unit '{quantity.unit}' is incompatible with mapping unit "
            f"'{mapping.source_unit}': {error}"
        ) from error
    return _linear_transform(
        quantity,
        factor=float(factor),
        offset=0,
        target_unit=mapping.source_unit,
        target_kind=mapping.source_quantity_kind,
    )


def _translate_one(
    quantity: QuantityValue,
    mapping: MPTMappingDefinition,
    registry: MPTRegistry,
    request: MPTRequest,
) -> QuantityValue:
    source = _convert_to_source(quantity, mapping)
    target = mapping.target
    if mapping.mapping_type is MappingType.IDENTITY:
        factor = _UNITS.Quantity(1, mapping.source_unit).to(target.canonical_unit).magnitude
        result = _linear_transform(
            source,
            factor=float(factor),
            offset=0,
            target_unit=target.canonical_unit,
            target_kind=target.quantity_kind,
        )
    elif mapping.mapping_type is MappingType.SCALE:
        result = _linear_transform(
            source,
            factor=mapping.scale_factor,
            offset=0,
            target_unit=target.canonical_unit,
            target_kind=target.quantity_kind,
        )
    elif mapping.mapping_type is MappingType.LOOKUP:
        if source.distribution is not DistributionType.FIXED:
            raise MPTTranslationError("lookup mappings require fixed source quantities")
        table = {entry.source_value: entry.target_value for entry in mapping.lookup_entries}
        if source.value not in table:
            raise MPTTranslationError(
                f"lookup mapping '{mapping.id}' has no entry for source value {source.value}"
            )
        result = QuantityValue(
            distribution="fixed",
            unit=target.canonical_unit,
            semantic_kind=target.quantity_kind,
            value=table[source.value],
            uncertainty=source.uncertainty,
            correlation_group=source.correlation_group,
        )
    else:
        if source.distribution is not DistributionType.FIXED:
            raise MPTTranslationError("callable mappings require fixed source quantities")
        function = registry.get_callable(mapping.callable_name)
        value = function(source.value, request.context)
        if not isinstance(value, (int, float)) or not isfinite(value):
            raise MPTTranslationError(
                f"allowlisted callable '{mapping.callable_name}' must return a finite number"
            )
        result = QuantityValue(
            distribution="fixed",
            unit=target.canonical_unit,
            semantic_kind=target.quantity_kind,
            value=float(value),
            uncertainty=source.uncertainty,
            correlation_group=source.correlation_group,
        )
    _validate_target_range(result, mapping)
    return result


def _validate_target_range(quantity: QuantityValue, mapping: MPTMappingDefinition) -> None:
    constraint = mapping.target.valid_range
    if constraint is None:
        return
    values: tuple[float, ...]
    if quantity.distribution is DistributionType.FIXED:
        values = (quantity.value,)
    elif quantity.distribution is DistributionType.INTERVAL:
        values = (quantity.lower, quantity.upper)
    elif quantity.distribution in {DistributionType.NORMAL, DistributionType.LOGNORMAL}:
        values = (quantity.mean,)
    else:
        values = (0.0, 1.0)
    for value in values:
        if constraint.minimum is not None and value < constraint.minimum:
            raise MPTTranslationError(
                f"mapping '{mapping.id}' produced {value} {quantity.unit}, below target "
                f"minimum {constraint.minimum}; values are never silently clamped"
            )
        if constraint.maximum is not None and value > constraint.maximum:
            raise MPTTranslationError(
                f"mapping '{mapping.id}' produced {value} {quantity.unit}, above target "
                f"maximum {constraint.maximum}; values are never silently clamped"
            )


def translate(request: MPTRequest, registry: MPTRegistry) -> MPTResult:
    """Translate a baseline/edited pair through one explicitly selected mapping."""

    mapping = registry.get(request.mapping_id)
    available_evidence = {record.id for record in request.evidence}
    missing_evidence = set(mapping.evidence_ids) - available_evidence
    if missing_evidence:
        raise MPTTranslationError(
            f"mapping '{mapping.id}' has unresolved evidence IDs: {sorted(missing_evidence)}"
        )

    applicability = mapping.applicability.assess(request.context)
    warnings: list[str] = []
    if applicability is ApplicabilityResult.OUT_OF_DOMAIN:
        warnings.append("mapping applicability is out_of_domain")
    elif applicability is ApplicabilityResult.PARTIAL:
        warnings.append("mapping applicability is partial")
    elif applicability is ApplicabilityResult.UNKNOWN:
        warnings.append("mapping applicability is unknown")

    baseline = _translate_one(request.baseline, mapping, registry, request)
    edited = _translate_one(request.edited, mapping, registry, request)
    return MPTResult(
        mapping_id=mapping.id,
        mapping_version=mapping.version,
        mapping_digest=mapping.digest(),
        evidence_ids=mapping.evidence_ids,
        applicability_result=applicability,
        target=mapping.target,
        baseline=baseline,
        edited=edited,
        warnings=tuple(warnings),
    )
