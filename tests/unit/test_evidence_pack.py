from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from krypton.evidence_pack import EvidencePackError, EvidencePackNotConfigured, LocalEvidencePack, open_configured_evidence_pack


def make_pack(root: Path, value: bytes = b"local user-supplied input") -> tuple[Path, str]:
    root.mkdir()
    data = root / "inputs" / "artifact.json"
    data.parent.mkdir()
    data.write_bytes(value)
    digest = hashlib.sha256(value).hexdigest()
    (root / "evidence-pack-manifest.json").write_text(json.dumps({
        "schema_version": "krypton-local-evidence-pack-v1",
        "artifacts": [{"id": "local:test", "path": "inputs/artifact.json", "sha256": digest, "scientific_role": "test-only local input"}],
    }), encoding="utf-8")
    return root, digest


def test_local_pack_round_trip_and_digest(tmp_path: Path) -> None:
    root, digest = make_pack(tmp_path / "pack")
    pack = LocalEvidencePack.open(root)
    assert pack.list_artifacts()[0].sha256 == digest
    assert pack.read_bytes("local:test") == b"local user-supplied input"


def test_environment_boundary_is_explicit(tmp_path: Path) -> None:
    root, _ = make_pack(tmp_path / "pack")
    assert open_configured_evidence_pack({"KRYPTON_LOCAL_EVIDENCE_PACK": str(root)}).root == root.resolve()


def test_missing_environment_fails_closed() -> None:
    with pytest.raises(EvidencePackNotConfigured):
        open_configured_evidence_pack({})


@pytest.mark.parametrize("version", ["legacy", "", None])
def test_unknown_manifest_version_rejected(tmp_path: Path, version: str | None) -> None:
    root, _ = make_pack(tmp_path / "pack")
    payload = json.loads((root / "evidence-pack-manifest.json").read_text())
    payload["schema_version"] = version
    (root / "evidence-pack-manifest.json").write_text(json.dumps(payload))
    with pytest.raises(EvidencePackError, match="version"):
        LocalEvidencePack.open(root)


def test_stale_digest_rejected_on_read(tmp_path: Path) -> None:
    root, _ = make_pack(tmp_path / "pack")
    pack = LocalEvidencePack.open(root)
    (root / "inputs" / "artifact.json").write_bytes(b"changed")
    with pytest.raises(EvidencePackError, match="digest mismatch"):
        pack.read_bytes("local:test")


def test_path_traversal_rejected(tmp_path: Path) -> None:
    root, _ = make_pack(tmp_path / "pack")
    payload = json.loads((root / "evidence-pack-manifest.json").read_text())
    payload["artifacts"][0]["path"] = "../outside.json"
    (root / "evidence-pack-manifest.json").write_text(json.dumps(payload))
    with pytest.raises(EvidencePackError, match="inside"):
        LocalEvidencePack.open(root)


def test_duplicate_identity_rejected(tmp_path: Path) -> None:
    root, _ = make_pack(tmp_path / "pack")
    payload = json.loads((root / "evidence-pack-manifest.json").read_text())
    payload["artifacts"].append(dict(payload["artifacts"][0]))
    (root / "evidence-pack-manifest.json").write_text(json.dumps(payload))
    with pytest.raises(EvidencePackError, match="duplicate"):
        LocalEvidencePack.open(root)

