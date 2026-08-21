"""Local, canonical C0 provenance manifests without a server component."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from krypton import __version__


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ArtifactReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("id", "version")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("artifact identifiers and versions must not be blank")
        return value


class VersionedReference(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)


class ProvenanceManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "provenance-manifest-v0"
    run_id: str = Field(min_length=1)
    timestamp: datetime
    krypton_package_version: str = Field(min_length=1)
    git_commit: str = Field(pattern=r"^(?:[0-9a-f]{40,64}|unborn|unknown)$")
    dirty_worktree: bool
    edit_object: ArtifactReference
    keg: ArtifactReference
    mpt: ArtifactReference
    model_artifact: ArtifactReference
    pair_run_spec: ArtifactReference
    environment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    dataset_versions: tuple[VersionedReference, ...] = ()
    container_image_digest: str | None = Field(
        default=None, pattern=r"^sha256:[0-9a-f]{64}$"
    )
    python_version: str = Field(min_length=1)
    dependency_lock_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    random_seed: int

    @field_validator("schema_version")
    @classmethod
    def supported_version(cls, value: str) -> str:
        if value != "provenance-manifest-v0":
            raise ValueError("C0 supports only schema_version 'provenance-manifest-v0'")
        return value

    @field_validator("run_id", "krypton_package_version", "python_version")
    @classmethod
    def text_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("provenance text fields must not be blank")
        return value

    @field_validator("timestamp")
    @classmethod
    def timestamp_has_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("provenance timestamp must include a timezone")
        return value

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    def digest(self) -> str:
        return _sha256_bytes(self.canonical_json().encode("utf-8"))


def digest_model(model: BaseModel) -> str:
    canonical = json.dumps(
        model.model_dump(mode="json"),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return _sha256_bytes(canonical.encode("utf-8"))


def _git_state(repository: Path) -> tuple[str, bool]:
    try:
        commit_process = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
        )
        commit = commit_process.stdout.strip() if commit_process.returncode == 0 else "unborn"
        status_process = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return commit, bool(status_process.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return "unknown", True


def collect_provenance(
    *,
    run_id: str,
    repository: Path,
    dependency_lock: Path,
    edit_object: ArtifactReference,
    keg: ArtifactReference,
    mpt: ArtifactReference,
    model_artifact: ArtifactReference,
    pair_run_spec: ArtifactReference,
    environment_digest: str,
    random_seed: int,
    dataset_versions: tuple[VersionedReference, ...] = (),
    container_image_digest: str | None = None,
    timestamp: datetime | None = None,
) -> ProvenanceManifest:
    if not dependency_lock.is_file():
        raise FileNotFoundError(f"dependency lock file does not exist: {dependency_lock}")
    git_commit, dirty = _git_state(repository)
    return ProvenanceManifest(
        run_id=run_id,
        timestamp=timestamp or datetime.now(UTC),
        krypton_package_version=__version__,
        git_commit=git_commit,
        dirty_worktree=dirty,
        edit_object=edit_object,
        keg=keg,
        mpt=mpt,
        model_artifact=model_artifact,
        pair_run_spec=pair_run_spec,
        environment_digest=environment_digest,
        dataset_versions=dataset_versions,
        container_image_digest=container_image_digest,
        python_version=platform.python_version(),
        dependency_lock_digest=_sha256_bytes(dependency_lock.read_bytes()),
        random_seed=random_seed,
    )
