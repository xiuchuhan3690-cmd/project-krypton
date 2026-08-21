"""In-memory C0 MPT mapping registry with explicit callable allowlisting."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from krypton.domain import ApplicabilityContext
from krypton.mpt.models import MPTMappingDefinition, MappingType

PureMappingCallable = Callable[[float, ApplicabilityContext], float]


class TranslationMapping(Protocol):
    """Generic versioned translation definition interface."""

    id: str
    version: str

    def digest(self) -> str: ...


class MappingNotFoundError(KeyError):
    pass


class DuplicateMappingError(ValueError):
    pass


class MPTRegistry:
    """Stores mapping data and project-code callables without dynamic evaluation."""

    def __init__(
        self,
        *,
        allowlisted_callables: dict[str, PureMappingCallable] | None = None,
    ) -> None:
        self._mappings: dict[str, MPTMappingDefinition] = {}
        self._callables = dict(allowlisted_callables or {})

    def register(self, mapping: MPTMappingDefinition) -> None:
        if mapping.id in self._mappings:
            raise DuplicateMappingError(f"mapping '{mapping.id}' is already registered")
        if (
            mapping.mapping_type is MappingType.CALLABLE
            and mapping.callable_name not in self._callables
        ):
            raise ValueError(
                f"callable '{mapping.callable_name}' is not in the project-code allowlist"
            )
        self._mappings[mapping.id] = mapping

    def get(self, mapping_id: str) -> MPTMappingDefinition:
        try:
            return self._mappings[mapping_id]
        except KeyError as error:
            raise MappingNotFoundError(f"mapping '{mapping_id}' is not registered") from error

    def get_callable(self, name: str) -> PureMappingCallable:
        try:
            return self._callables[name]
        except KeyError as error:
            raise MappingNotFoundError(f"callable '{name}' is not allowlisted") from error

    def list_mappings(self) -> tuple[MPTMappingDefinition, ...]:
        return tuple(self._mappings[key] for key in sorted(self._mappings))
