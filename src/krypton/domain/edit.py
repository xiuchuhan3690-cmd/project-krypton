"""C0 representation of one known, small, counterfactual genomic edit."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class EditType(StrEnum):
    SNV = "snv"
    INSERTION = "insertion"
    DELETION = "deletion"
    DELINS = "delins"


class Zygosity(StrEnum):
    HETEROZYGOUS = "heterozygous"
    HOMOZYGOUS = "homozygous"
    HEMIZYGOUS = "hemizygous"


class EditMode(StrEnum):
    GERMLINE = "germline"
    SOMATIC = "somatic"


_SEQUENCE_ID = re.compile(r"^(?:chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT)|NC_\d+\.\d+)$")
_ALLELE = re.compile(r"^[ACGT]*$")


class EditObject(BaseModel):
    """One GRCh38 edit in canonical 0-based interbase coordinates.

    ``start`` and ``end`` describe the half-open reference interval
    ``[start, end)``. Insertions have ``start == end`` and an empty reference
    allele; deletions have an empty edited allele. External coordinate systems
    such as VCF's 1-based anchored representation are adapter concerns.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    assembly: Literal["GRCh38"] = "GRCh38"
    sequence_id: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    reference_allele: str = Field(max_length=50)
    edited_allele: str = Field(max_length=50)
    edit_type: EditType
    zygosity: Zygosity
    mode: EditMode
    edited_tissues: tuple[str, ...]
    cell_fraction: float = Field(gt=0, le=1)
    delivery_modeled: bool = False
    off_target_modeled: bool = False

    @field_validator("id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("edit id must not be blank")
        return value

    @field_validator("sequence_id")
    @classmethod
    def valid_sequence_id(cls, value: str) -> str:
        if not _SEQUENCE_ID.fullmatch(value):
            raise ValueError(
                "sequence_id must be a canonical GRCh38 chromosome (for example chr22) "
                "or a versioned RefSeq accession"
            )
        return value

    @field_validator("reference_allele", "edited_allele")
    @classmethod
    def valid_dna_allele(cls, value: str) -> str:
        if not _ALLELE.fullmatch(value):
            raise ValueError(
                "alleles must contain uppercase DNA bases A, C, G, or T only; "
                "an empty allele is allowed only for an interbase insertion or deletion"
            )
        return value

    @field_validator("edited_tissues")
    @classmethod
    def valid_tissues(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not tissue.strip() for tissue in values):
            raise ValueError("edited_tissues must contain at least one non-blank tissue label")
        if len(values) != len(set(values)):
            raise ValueError("edited_tissues must not contain duplicates")
        return values

    @model_validator(mode="after")
    def validate_edit_consistency(self) -> EditObject:
        reference = self.reference_allele
        edited = self.edited_allele
        if self.end < self.start:
            raise ValueError("end must be greater than or equal to start")
        if reference == edited:
            raise ValueError("reference_allele and edited_allele must differ")

        reference_span = self.end - self.start
        if self.edit_type is EditType.SNV:
            valid_shape = reference_span == 1 and len(reference) == len(edited) == 1
        elif self.edit_type is EditType.INSERTION:
            valid_shape = reference_span == 0 and reference == "" and len(edited) > 0
        elif self.edit_type is EditType.DELETION:
            valid_shape = reference_span == len(reference) > 0 and edited == ""
        else:
            valid_shape = (
                reference_span == len(reference) > 0
                and len(edited) > 0
                and not (len(reference) == len(edited) == 1)
            )
        if not valid_shape:
            raise ValueError(
                f"coordinates and alleles are inconsistent with edit_type '{self.edit_type.value}' "
                "under the canonical 0-based interbase representation"
            )

        if self.mode is EditMode.GERMLINE:
            if self.cell_fraction != 1.0:
                raise ValueError("germline edits require cell_fraction=1.0")
            if self.edited_tissues != ("all",):
                raise ValueError("germline edits require edited_tissues=('all',)")
        elif "all" in self.edited_tissues:
            raise ValueError("somatic edits must name specific edited tissues, not 'all'")
        return self
