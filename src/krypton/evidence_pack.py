"""Fail-closed access to a user-supplied local scientific evidence pack."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

EVIDENCE_PACK_ENV = "KRYPTON_LOCAL_EVIDENCE_PACK"
PACK_MANIFEST = "evidence-pack-manifest.json"


class EvidencePackError(ValueError):
    """Raised before external scientific content is consumed."""


class EvidencePackNotConfigured(EvidencePackError):
    pass


@dataclass(frozen=True)
class EvidencePackArtifact:
    id: str
    relative_path: str
    sha256: str
    scientific_role: str


class LocalEvidencePack:
    """Validated manifest and byte loader; it assigns no scientific meaning."""

    def __init__(self, root: Path, artifacts: Mapping[str, EvidencePackArtifact]) -> None:
        self.root = root
        self._artifacts = dict(artifacts)

    @classmethod
    def open(cls, root: Path) -> "LocalEvidencePack":
        resolved_root = root.expanduser().resolve(strict=True)
        if not resolved_root.is_dir():
            raise EvidencePackError("evidence pack root must be a directory")
        manifest_path = resolved_root / PACK_MANIFEST
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise EvidencePackError("evidence pack manifest is missing or invalid") from error
        if payload.get("schema_version") != "krypton-local-evidence-pack-v1":
            raise EvidencePackError("unsupported evidence pack manifest version")
        rows = payload.get("artifacts")
        if not isinstance(rows, list) or not rows:
            raise EvidencePackError("evidence pack must declare at least one artifact")
        artifacts: dict[str, EvidencePackArtifact] = {}
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"id", "path", "sha256", "scientific_role"}:
                raise EvidencePackError("invalid evidence pack artifact entry")
            artifact = EvidencePackArtifact(
                id=str(row["id"]), relative_path=str(row["path"]),
                sha256=str(row["sha256"]), scientific_role=str(row["scientific_role"]),
            )
            if not artifact.id.strip() or not artifact.scientific_role.strip():
                raise EvidencePackError("artifact identity and scientific role must not be blank")
            if artifact.id in artifacts:
                raise EvidencePackError("duplicate evidence pack artifact identity")
            if len(artifact.sha256) != 64 or any(ch not in "0123456789abcdef" for ch in artifact.sha256):
                raise EvidencePackError("artifact digest must be lowercase SHA-256")
            relative = Path(artifact.relative_path)
            if relative.is_absolute() or ".." in relative.parts:
                raise EvidencePackError("artifact path must remain inside the evidence pack")
            candidate = (resolved_root / relative).resolve(strict=True)
            if resolved_root not in candidate.parents or not candidate.is_file():
                raise EvidencePackError("artifact path must resolve to a file inside the evidence pack")
            artifacts[artifact.id] = artifact
        return cls(resolved_root, artifacts)

    def list_artifacts(self) -> tuple[EvidencePackArtifact, ...]:
        return tuple(self._artifacts[key] for key in sorted(self._artifacts))

    def read_bytes(self, artifact_id: str) -> bytes:
        try:
            artifact = self._artifacts[artifact_id]
        except KeyError as error:
            raise EvidencePackError(f"unknown evidence pack artifact: {artifact_id}") from error
        value = (self.root / artifact.relative_path).read_bytes()
        actual = hashlib.sha256(value).hexdigest()
        if actual != artifact.sha256:
            raise EvidencePackError(f"evidence pack artifact digest mismatch: {artifact_id}")
        return value


def open_configured_evidence_pack(environ: Mapping[str, str] | None = None) -> LocalEvidencePack:
    configured = (environ or os.environ).get(EVIDENCE_PACK_ENV)
    if not configured:
        raise EvidencePackNotConfigured(f"set {EVIDENCE_PACK_ENV} to a local evidence pack directory")
    return LocalEvidencePack.open(Path(configured))

