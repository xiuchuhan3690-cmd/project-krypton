from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.domain import ApplicabilityContext, ApplicabilityResult, QuantityValue
from krypton.mpt import (
    DuplicateMappingError,
    LookupEntry,
    MappingNotFoundError,
    MappingType,
    MPTMappingDefinition,
    MPTRegistry,
    MPTRequest,
    MPTResult,
    MPTTranslationError,
    ParameterRange,
    RegistryMPT,
    TargetParameterReference,
    translate,
)


FIXTURES = Path(__file__).parents[2] / "src" / "krypton" / "resources" / "fixtures"
VALID_MAPPING = FIXTURES / "valid" / "mpt_scale_mapping_v0.json"
VALID_REQUEST = FIXTURES / "valid" / "mpt_request_v0.json"


def scale_mapping() -> MPTMappingDefinition:
    return MPTMappingDefinition.model_validate_json(VALID_MAPPING.read_text(encoding="utf-8"))


def valid_request() -> MPTRequest:
    return MPTRequest.model_validate_json(VALID_REQUEST.read_text(encoding="utf-8"))


def clearance_target(**changes: object) -> TargetParameterReference:
    payload: dict[str, object] = {
        "contract_id": "contract:mock-pk",
        "contract_version": "1.0.0",
        "parameter_id": "clearance",
        "biological_meaning": "Artificial clearance",
        "quantity_kind": "clearance",
        "canonical_unit": "L/h",
        "physical_dimension": "[length] ** 3 / [time]",
        "valid_range": {"minimum": 0.1, "maximum": 100.0},
    }
    payload.update(changes)
    return TargetParameterReference.model_validate(payload)


def registry_with(mapping: MPTMappingDefinition, **callables: object) -> MPTRegistry:
    registry = MPTRegistry(allowlisted_callables=callables)
    registry.register(mapping)
    return registry


def test_scale_fixture_translates_expected_baseline_and_edited_values() -> None:
    mapping = scale_mapping()
    request = valid_request()
    result = translate(request, registry_with(mapping))

    assert result.mapping_id == "mapping:activity-clearance"
    assert result.mapping_version == "1.0.0"
    assert result.mapping_digest == mapping.digest()
    assert len(result.mapping_digest) == 64
    assert result.evidence_ids == ("evidence:mock",)
    assert result.applicability_result is ApplicabilityResult.IN_DOMAIN
    assert result.target.parameter_id == "clearance"
    assert result.target.contract_id == "contract:mock-pk"
    assert result.baseline.value == pytest.approx(10.0)
    assert result.edited.value == pytest.approx(4.0)
    assert result.baseline.unit == result.edited.unit == "L/h"
    assert result.baseline.semantic_kind == "clearance"
    assert result.warnings == ()
    assert MPTResult.model_validate_json(result.model_dump_json()) == result


def test_registry_backed_generic_translator_interface() -> None:
    mapping = scale_mapping()
    translator = RegistryMPT(registry_with(mapping))

    result = translator.translate(valid_request())

    assert result.mapping_id == mapping.id
    assert result.edited.value == pytest.approx(4.0)


def test_identity_mapping_converts_compatible_units() -> None:
    mapping = MPTMappingDefinition(
        id="mapping:clearance-identity",
        version="1.0.0",
        mapping_type="identity",
        source_quantity_kind="clearance",
        source_unit="mL/min",
        target=clearance_target(),
        evidence_ids=("evidence:mock",),
        applicability=ApplicabilityContext(tissue=("liver",)),
    )
    request = valid_request().model_copy(
        update={
            "mapping_id": mapping.id,
            "baseline": QuantityValue(
                distribution="fixed", unit="mL/min", semantic_kind="clearance", value=100
            ),
            "edited": QuantityValue(
                distribution="fixed", unit="mL/min", semantic_kind="clearance", value=50
            ),
        }
    )

    result = translate(request, registry_with(mapping))

    assert result.baseline.value == pytest.approx(6.0)
    assert result.edited.value == pytest.approx(3.0)
    assert result.baseline.unit == "L/h"


def test_scale_mapping_preserves_interval_uncertainty_shape() -> None:
    mapping = scale_mapping()
    request = valid_request().model_copy(
        update={
            "baseline": QuantityValue(
                distribution="interval",
                unit="dimensionless",
                semantic_kind="relative_activity",
                lower=0.8,
                upper=1.0,
            ),
            "edited": QuantityValue(
                distribution="interval",
                unit="dimensionless",
                semantic_kind="relative_activity",
                lower=0.3,
                upper=0.5,
            ),
        }
    )

    result = translate(request, registry_with(mapping))

    assert (result.baseline.lower, result.baseline.upper) == pytest.approx((8.0, 10.0))
    assert (result.edited.lower, result.edited.upper) == pytest.approx((3.0, 5.0))


def test_lookup_mapping_translates_only_registered_values() -> None:
    mapping = scale_mapping().model_copy(
        update={
            "id": "mapping:activity-lookup",
            "mapping_type": MappingType.LOOKUP,
            "scale_factor": None,
            "lookup_entries": (
                LookupEntry(source_value=1.0, target_value=10.0),
                LookupEntry(source_value=0.4, target_value=4.0),
            ),
        }
    )
    result = translate(
        valid_request().model_copy(update={"mapping_id": mapping.id}),
        registry_with(mapping),
    )

    assert result.baseline.value == 10.0
    assert result.edited.value == 4.0


def test_allowlisted_pure_python_callable_mapping() -> None:
    def mock_scale(value: float, context: ApplicabilityContext) -> float:
        assert context.tissue == ("liver",)
        return value * 10

    mapping = scale_mapping().model_copy(
        update={
            "id": "mapping:activity-callable",
            "mapping_type": MappingType.CALLABLE,
            "scale_factor": None,
            "callable_name": "mock_scale",
        }
    )
    request = valid_request().model_copy(update={"mapping_id": mapping.id})

    result = translate(request, registry_with(mapping, mock_scale=mock_scale))

    assert result.baseline.value == 10.0
    assert result.edited.value == 4.0


def test_callable_must_be_explicitly_allowlisted() -> None:
    mapping = scale_mapping().model_copy(
        update={
            "id": "mapping:not-allowlisted",
            "mapping_type": MappingType.CALLABLE,
            "scale_factor": None,
            "callable_name": "unknown_function",
        }
    )

    with pytest.raises(ValueError, match="not in the project-code allowlist"):
        MPTRegistry().register(mapping)


def test_callable_must_return_a_finite_number() -> None:
    mapping = scale_mapping().model_copy(
        update={
            "id": "mapping:bad-callable",
            "mapping_type": MappingType.CALLABLE,
            "scale_factor": None,
            "callable_name": "bad",
        }
    )
    request = valid_request().model_copy(update={"mapping_id": mapping.id})

    with pytest.raises(MPTTranslationError, match="finite number"):
        translate(request, registry_with(mapping, bad=lambda value, context: float("nan")))


def test_arbitrary_expression_mapping_fixture_is_schema_invalid() -> None:
    payload = (FIXTURES / "invalid" / "mpt_expression_mapping_v0.json").read_text(
        encoding="utf-8"
    )

    with pytest.raises(ValidationError) as error:
        MPTMappingDefinition.model_validate_json(payload)

    assert "mapping_type" in str(error.value)
    assert "expression" in str(error.value)


def test_mapping_evidence_must_resolve_from_request_fixture() -> None:
    request = MPTRequest.model_validate_json(
        (FIXTURES / "invalid" / "mpt_unresolved_evidence_request_v0.json").read_text(
            encoding="utf-8"
        )
    )

    with pytest.raises(MPTTranslationError, match="unresolved evidence"):
        translate(request, registry_with(scale_mapping()))


def test_unknown_mapping_and_duplicate_registration_are_rejected() -> None:
    registry = registry_with(scale_mapping())

    with pytest.raises(MappingNotFoundError, match="not registered"):
        registry.get("mapping:missing")
    with pytest.raises(DuplicateMappingError, match="already registered"):
        registry.register(scale_mapping())


def test_source_semantic_kind_must_match_mapping() -> None:
    request = valid_request().model_copy(
        update={
            "edited": QuantityValue(
                distribution="fixed",
                unit="dimensionless",
                semantic_kind="log2_fold_change",
                value=0.4,
            )
        }
    )

    with pytest.raises(MPTTranslationError, match="source semantic kind"):
        translate(request, registry_with(scale_mapping()))


def test_source_unit_dimension_must_match_mapping() -> None:
    request = valid_request().model_copy(
        update={
            "edited": QuantityValue(
                distribution="fixed",
                unit="mg",
                semantic_kind="relative_activity",
                value=0.4,
            )
        }
    )

    with pytest.raises(MPTTranslationError, match="incompatible"):
        translate(request, registry_with(scale_mapping()))


def test_target_range_violation_is_rejected_without_clamping() -> None:
    request = valid_request().model_copy(
        update={
            "edited": QuantityValue(
                distribution="fixed",
                unit="dimensionless",
                semantic_kind="relative_activity",
                value=20,
            )
        }
    )

    with pytest.raises(MPTTranslationError, match="never silently clamped"):
        translate(request, registry_with(scale_mapping()))


def test_lookup_missing_value_and_non_fixed_input_are_rejected() -> None:
    mapping = scale_mapping().model_copy(
        update={
            "id": "mapping:lookup",
            "mapping_type": MappingType.LOOKUP,
            "scale_factor": None,
            "lookup_entries": (LookupEntry(source_value=1.0, target_value=10.0),),
        }
    )
    request = valid_request().model_copy(update={"mapping_id": mapping.id})
    with pytest.raises(MPTTranslationError, match="no entry"):
        translate(request, registry_with(mapping))

    interval_request = request.model_copy(
        update={
            "edited": QuantityValue(
                distribution="interval",
                unit="dimensionless",
                semantic_kind="relative_activity",
                lower=0.3,
                upper=0.5,
            )
        }
    )
    with pytest.raises(MPTTranslationError, match="fixed source"):
        translate(interval_request, registry_with(mapping))


@pytest.mark.parametrize(
    ("context", "expected", "warning"),
    [
        (
            ApplicabilityContext(tissue=("kidney",), experimental_system=("internal_mock",)),
            ApplicabilityResult.PARTIAL,
            "partial",
        ),
        (ApplicabilityContext(), ApplicabilityResult.UNKNOWN, "unknown"),
    ],
)
def test_non_in_domain_applicability_is_preserved_as_warning(
    context: ApplicabilityContext, expected: ApplicabilityResult, warning: str
) -> None:
    request = valid_request().model_copy(update={"context": context})

    result = translate(request, registry_with(scale_mapping()))

    assert result.applicability_result is expected
    assert warning in result.warnings[0]


def test_target_unit_and_declared_dimension_must_agree() -> None:
    with pytest.raises(ValidationError, match="physical_dimension"):
        clearance_target(physical_dimension="[mass]")


@pytest.mark.parametrize(
    "changes",
    [
        {"mapping_type": "scale", "scale_factor": None},
        {"mapping_type": "identity", "scale_factor": 2.0},
        {"mapping_type": "lookup", "scale_factor": None, "lookup_entries": ()},
        {
            "mapping_type": "lookup",
            "scale_factor": None,
            "lookup_entries": (
                LookupEntry(source_value=1, target_value=2),
                LookupEntry(source_value=1, target_value=3),
            ),
        },
    ],
)
def test_mapping_configuration_is_explicit_and_unambiguous(changes: dict[str, object]) -> None:
    payload = scale_mapping().model_dump()
    payload.update(changes)

    with pytest.raises(ValidationError):
        MPTMappingDefinition.model_validate(payload)


def test_registry_listing_is_deterministic() -> None:
    first = scale_mapping().model_copy(update={"id": "mapping:z"})
    second = scale_mapping().model_copy(update={"id": "mapping:a"})
    registry = MPTRegistry()
    registry.register(first)
    registry.register(second)

    assert [mapping.id for mapping in registry.list_mappings()] == ["mapping:a", "mapping:z"]
