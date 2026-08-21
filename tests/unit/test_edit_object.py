import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from krypton.domain import EditMode, EditObject, EditType, Zygosity


def edit_payload(**changes: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": "edit:mock-snv",
        "assembly": "GRCh38",
        "sequence_id": "chr22",
        "start": 100_000,
        "end": 100_001,
        "reference_allele": "A",
        "edited_allele": "G",
        "edit_type": "snv",
        "zygosity": "heterozygous",
        "mode": "germline",
        "edited_tissues": ["all"],
        "cell_fraction": 1.0,
        "delivery_modeled": False,
        "off_target_modeled": False,
    }
    payload.update(changes)
    return payload


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {
            "start": 100_001,
            "end": 100_001,
            "reference_allele": "",
            "edited_allele": "T",
            "edit_type": "insertion",
        },
        {
            "start": 100_001,
            "end": 100_002,
            "reference_allele": "T",
            "edited_allele": "",
            "edit_type": "deletion",
        },
        {
            "start": 100_000,
            "end": 100_002,
            "reference_allele": "AT",
            "edited_allele": "GC",
            "edit_type": "delins",
        },
    ],
)
def test_supported_edits_validate_and_round_trip(changes: dict[str, object]) -> None:
    edit = EditObject.model_validate(edit_payload(**changes))

    assert EditObject.model_validate_json(edit.model_dump_json()) == edit
    assert edit.assembly == "GRCh38"


def test_somatic_edit_tracks_tissues_and_cell_fraction() -> None:
    edit = EditObject.model_validate(
        edit_payload(mode="somatic", edited_tissues=["liver"], cell_fraction=0.35)
    )

    assert edit.mode is EditMode.SOMATIC
    assert edit.cell_fraction == 0.35


@pytest.mark.parametrize("allele", ["a", "N", "A/T", "-"])
def test_wrong_allele_format_is_rejected(allele: str) -> None:
    with pytest.raises(ValidationError, match="uppercase DNA bases"):
        EditObject.model_validate(edit_payload(edited_allele=allele))


def test_identical_alleles_are_rejected() -> None:
    with pytest.raises(ValidationError, match="must differ"):
        EditObject.model_validate(edit_payload(edited_allele="A"))


@pytest.mark.parametrize(
    "changes",
    [
        {"start": 100_000, "end": 100_001, "reference_allele": "", "edited_allele": "T", "edit_type": "insertion"},
        {
            "start": 100_000,
            "end": 100_002,
            "reference_allele": "A",
            "edited_allele": "",
            "edit_type": "deletion",
        },
        {"reference_allele": "AT", "edited_allele": "G", "edit_type": "delins"},
        {"reference_allele": "A", "edited_allele": "G", "edit_type": "delins"},
    ],
)
def test_edit_type_and_allele_shape_must_agree(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError, match="inconsistent with edit_type"):
        EditObject.model_validate(edit_payload(**changes))


def test_zero_is_a_valid_interbase_boundary() -> None:
    edit = EditObject.model_validate(edit_payload(start=0, end=1))

    assert edit.start == 0
    assert edit.end == 1


def test_reference_span_must_match_reference_allele_length() -> None:
    with pytest.raises(ValidationError, match="0-based interbase"):
        EditObject.model_validate(
            edit_payload(start=100_000, end=100_003, reference_allele="AT", edited_allele="GC", edit_type="delins")
        )


def test_reversed_interbase_interval_is_rejected() -> None:
    with pytest.raises(ValidationError, match="greater than or equal"):
        EditObject.model_validate(edit_payload(start=2, end=1))


def test_legacy_one_based_position_field_is_rejected() -> None:
    payload = edit_payload()
    payload.pop("start")
    payload.pop("end")
    payload["position"] = 100_001

    with pytest.raises(ValidationError) as error:
        EditObject.model_validate(payload)

    assert "start" in str(error.value)
    assert "end" in str(error.value)
    assert "position" in str(error.value)


def test_coordinate_fixtures_enforce_canonical_representation() -> None:
    fixture_root = Path(__file__).parents[2] / "src" / "krypton" / "resources" / "fixtures"
    for path in (fixture_root / "valid").glob("edit_*_0_based.json"):
        EditObject.model_validate(json.loads(path.read_text(encoding="utf-8")))

    legacy = json.loads(
        (fixture_root / "invalid" / "edit_legacy_1_based.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ValidationError):
        EditObject.model_validate(legacy)


def test_wrong_germline_cell_fraction_is_rejected() -> None:
    with pytest.raises(ValidationError, match="cell_fraction=1.0"):
        EditObject.model_validate(edit_payload(cell_fraction=0.8))


def test_germline_tissue_must_be_all() -> None:
    with pytest.raises(ValidationError, match="edited_tissues"):
        EditObject.model_validate(edit_payload(edited_tissues=["liver"]))


def test_somatic_tissue_cannot_be_all() -> None:
    with pytest.raises(ValidationError, match="specific edited tissues"):
        EditObject.model_validate(edit_payload(mode="somatic", cell_fraction=0.5))


@pytest.mark.parametrize(
    "changes",
    [
        {"assembly": "GRCh37"},
        {"sequence_id": "22"},
        {"start": -1},
        {"edited_tissues": []},
        {"cell_fraction": 1.1},
        {"zygosity": "unknown"},
    ],
)
def test_invalid_required_edit_fields_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        EditObject.model_validate(edit_payload(**changes))


def test_delivery_and_off_target_flags_are_represented_but_not_executed_here() -> None:
    edit = EditObject.model_validate(
        edit_payload(delivery_modeled=True, off_target_modeled=True)
    )

    assert edit.delivery_modeled is True
    assert edit.off_target_modeled is True
    assert edit.edit_type is EditType.SNV
    assert edit.zygosity is Zygosity.HETEROZYGOUS
