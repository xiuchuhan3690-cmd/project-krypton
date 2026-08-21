"""Version-controlled JSON model registry with allowlisted project adapters."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from krypton.models import ModelAdapter, ModelContract

AdapterFactory = Callable[[ModelContract], ModelAdapter]


class TypedRegistryRecord(Protocol):
    """Structural extension point for versioned, typed model contracts."""

    registry_version: str
    mechanisms: tuple[str, ...]
    contract: Any
    adapter: Any

    @property
    def contract_id(self) -> str: ...

    @property
    def contract_version(self) -> str: ...


TypedRecordParser = Callable[[object], TypedRegistryRecord]
TypedAdapterFactory = Callable[[Any], Any]


class AdapterRegistration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    entry_point: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("entry_point")
    @classmethod
    def entry_point_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("adapter entry_point must not be blank")
        return value


class ModelRegistryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    registry_version: str = "model-registry-v0"
    mechanisms: tuple[str, ...]
    contract: ModelContract
    adapter: AdapterRegistration

    @field_validator("registry_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != "model-registry-v0":
            raise ValueError("C0 supports only registry_version 'model-registry-v0'")
        return value

    @field_validator("mechanisms")
    @classmethod
    def mechanisms_required(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if not values or any(not value.strip() for value in values):
            raise ValueError("registry records require non-blank mechanism labels")
        if len(values) != len(set(values)):
            raise ValueError("registry mechanism labels must be unique")
        return values

    @property
    def contract_id(self) -> str:
        return self.contract.id

    @property
    def contract_version(self) -> str:
        return self.contract.metadata.model_version

class ModelRegistryError(ValueError):
    pass


class ModelRegistry:
    def __init__(
        self,
        *,
        adapter_factories: dict[str, AdapterFactory | TypedAdapterFactory],
        record_parsers: dict[str, TypedRecordParser] | None = None,
    ) -> None:
        self._adapter_factories = dict(adapter_factories)
        self._record_parsers = dict(record_parsers or {})
        self._records: dict[tuple[str, str], ModelRegistryRecord | TypedRegistryRecord] = {}

    def load_directory(self, directory: Path) -> None:
        for path in sorted(directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                registry_version = payload.get("registry_version")
                if registry_version == "model-registry-v0":
                    record = ModelRegistryRecord.model_validate(payload)
                elif registry_version in self._record_parsers:
                    record = self._record_parsers[registry_version](payload)
                else:
                    raise ValueError(f"unsupported registry_version '{registry_version}'")
            except (OSError, ValueError, json.JSONDecodeError) as error:
                raise ModelRegistryError(f"failed to load model registry file '{path}': {error}") from error
            key = (record.contract_id, record.contract_version)
            if key in self._records:
                raise ModelRegistryError(f"duplicate model contract registration {key!r}")
            if record.adapter.entry_point not in self._adapter_factories:
                raise ModelRegistryError(
                    f"adapter entry point '{record.adapter.entry_point}' is not allowlisted project code"
                )
            self._records[key] = record

    def get_contract(self, contract_id: str, version: str) -> Any:
        key = (contract_id, version)
        try:
            return self._records[key].contract
        except KeyError as error:
            raise ModelRegistryError(f"model contract {key!r} is not registered") from error

    def get_adapter(self, contract_id: str, version: str) -> Any:
        key = (contract_id, version)
        try:
            record = self._records[key]
        except KeyError as error:
            raise ModelRegistryError(f"model contract {key!r} is not registered") from error
        factory = self._adapter_factories[record.adapter.entry_point]
        # Preserve the C0 factory signature while allowing typed records to
        # carry model/artifact pins needed by their adapter factory.
        adapter = factory(record.contract) if isinstance(record, ModelRegistryRecord) else factory(record)
        if adapter.artifact_digest != record.adapter.artifact_digest:
            raise ModelRegistryError("constructed adapter artifact digest does not match registry pin")
        return adapter

    def get_adapter_by_model(self, model_id: str, version: str) -> Any:
        matches = [
            record
            for record in self._records.values()
            if getattr(record, "model_id", None) == model_id
            and getattr(record, "model_version", None) == version
        ]
        if len(matches) != 1:
            raise ModelRegistryError(
                f"model {(model_id, version)!r} does not resolve to exactly one registration"
            )
        record = matches[0]
        factory = self._adapter_factories[record.adapter.entry_point]
        adapter = factory(record.contract) if isinstance(record, ModelRegistryRecord) else factory(record)
        if adapter.artifact_digest != record.adapter.artifact_digest:
            raise ModelRegistryError("constructed adapter artifact digest does not match registry pin")
        return adapter

    def list_by_mechanism(self, mechanism: str) -> tuple[Any, ...]:
        return tuple(
            record.contract
            for _, record in sorted(self._records.items())
            if mechanism in record.mechanisms
        )
