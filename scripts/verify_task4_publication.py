"""Write or verify the final Task-4 publication proof sidecars."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
PUBLICATION = ROOT / "krypton_v1_publication_manifest.yaml"
ARTIFACTS = ROOT / "krypton_v1_artifact_publication_manifest.yaml"
CLEAN_ROOM = ROOT / "krypton_v1_clean_room_manifest.yaml"
DIGESTS = ROOT / "krypton_v1_task4_publication_digests.yaml"
IGNORED_PARTS = {"dist", "build", ".git", ".pytest_cache", "__pycache__"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(path: Path) -> str:
    entries = {
        child.relative_to(path).as_posix(): sha256(child)
        for child in path.rglob("*")
        if child.is_file() and not any(part in IGNORED_PARTS for part in child.parts)
    }
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def artifact_digest(path: Path) -> str:
    if path.is_file():
        return sha256(path)
    if path.is_dir():
        return tree_sha256(path)
    return "missing"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_candidates() -> list[Path]:
    return sorted(
        (
            path
            for path in ROOT.rglob("*")
            if path.is_file()
            and path != DIGESTS
            and not any(part in IGNORED_PARTS or part.startswith(".venv") for part in path.parts)
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def write_digest_manifest() -> None:
    entries = {
        path.relative_to(ROOT).as_posix(): sha256(path)
        for path in source_candidates()
    }
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    payload = {
        "schema_version": "krypton-v1-task4-publication-digests-1",
        "algorithm": "sha256",
        "release_candidate": "TASK4_VERIFIED_RELEASE_CANDIDATE",
        "historical_provenance": {
            "task3_wheel": "5398ef06bf072c6d6903d09baa20d054aba7a9c779bc79f5952fbcc7bb4125c9",
            "task3_sdist": "21ee24680b710486badc3d671c262e6667a5ca6bcc15fd16b2cfe2e944579ac0",
            "task4r_wheel": "351fd4d7a3232234dbdb40ca6c0001c4edf13cacf2ccf634269a2f0fa6120469",
            "task4r_sdist": "dbdf9916f119a653ad32da3bc5c00c78205389f652ed577d041a1f8fd356b33e",
        },
        "inventory_sha256": hashlib.sha256(canonical).hexdigest(),
        "artifacts": entries,
    }
    DIGESTS.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE_TASK4_PUBLICATION_DIGESTS: {len(entries)} artifacts")


def main() -> None:
    if sys.argv[1:] == ["--write"]:
        write_digest_manifest()
        return

    publication = load(PUBLICATION)
    artifact_manifest = load(ARTIFACTS)
    clean_room = load(CLEAN_ROOM)
    digest_manifest = load(DIGESTS)
    failures: list[str] = []

    if publication.get("release_candidate") != "TASK4_VERIFIED_RELEASE_CANDIDATE":
        failures.append("release candidate identity mismatch")
    if publication.get("software_version") != "1.0.0":
        failures.append("software version mismatch")
    if publication.get("public_test_counts", {}).get("total") != 211:
        failures.append("public test count mismatch")
    if publication.get("canonical_reference_test_count") != 1184:
        failures.append("canonical reference count mismatch")
    if clean_room.get("result") != "PASS":
        failures.append("clean-room result is not PASS")

    entries = digest_manifest.get("artifacts", {})
    for relative, expected in sorted(entries.items()):
        actual = artifact_digest(ROOT / relative)
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(canonical).hexdigest() != digest_manifest.get("inventory_sha256"):
        failures.append("source inventory checksum mismatch")

    for record in artifact_manifest.get("artifacts", []):
        path = ROOT / record.get("path", "")
        actual = artifact_digest(path)
        if actual != record.get("sha256"):
            failures.append(f"classified artifact digest mismatch: {record.get('path')}")

    for kind in ("wheel", "sdist"):
        record = publication.get(kind, {})
        path = ROOT / "dist" / record.get("filename", "")
        actual = sha256(path) if path.is_file() else "missing"
        if actual != record.get("sha256"):
            failures.append(f"{kind} digest mismatch")

    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK4_PUBLICATION_DIGESTS: PASS ({len(entries)} source artifacts)")
    print(f"ARTIFACT_CLASSIFICATION: PASS ({len(artifact_manifest.get('artifacts', []))} artifacts)")
    print("CLEAN_ROOM_PROOF: PASS")


if __name__ == "__main__":
    main()
