"""Audit built wheel/sdist contents, metadata, and rights-safe boundary."""

from __future__ import annotations

import hashlib
import json
import re
import tarfile
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).parents[1]
DIST = ROOT / "dist"
CONTRACT = ROOT / "krypton_v1_package_contents_manifest.yaml"
TEXT_SUFFIXES = {"", ".csv", ".ini", ".json", ".lock", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
FORBIDDEN_PARTS = {".git", ".venv", ".venv-build", ".venv-wheel", "artifacts", "evidence", "vocabularies", "__pycache__"}
LEAK_PATTERNS = {
    "local-path": re.compile(r"(?i)(?:[a-z]:\\users\\|PC_User|OneDrive|[/\\]\.codex[/\\])"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential": re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{8,}"),
    "c2-source-cell": re.compile(r'(?i)(?:arithmetic_mean|source_value)\s*["\']?\s*[:=]\s*["\']?(?:50\.2|32\.3|4\.3|18\.4|11\.9|0\.95)\b'),
    "c3a-parameter": re.compile(r'(?i)(?:clf_value|clh_value|ka_value|vc_value)\s*["\']?\s*[:=]'),
    "c3b-fitted-source-value": re.compile(r'(?i)(?:k_rxn|k_rec|beta_b|y0)\s*["\']?\s*[:=]\s*["\']?(?:0\.751|0\.031|0\.\d+|\d+\.\d+)'),
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_contract(path: Path = CONTRACT) -> dict[str, object]:
    """Load the current JSON-compatible YAML distribution contract."""

    return json.loads(path.read_text(encoding="utf-8"))


def normalize_sdist_name(name: str) -> str:
    """Remove the versioned archive root before contract comparison."""

    path = PurePosixPath(name)
    return PurePosixPath(*path.parts[1:]).as_posix()


def member_set_digest(names: set[str] | list[str]) -> str:
    """Digest an exact normalized archive-member set without hashing archive bytes."""

    canonical = "\n".join(sorted(names)) + "\n"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def member_set_matches(
    names: set[str] | list[str], *, expected_count: int, expected_digest: str
) -> bool:
    """Require both measured count and exact member-set identity."""

    return len(names) == expected_count and member_set_digest(names) == expected_digest


def inspect_names(names: list[str], read_bytes) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for name in names:
        path = PurePosixPath(name)
        if any(part in FORBIDDEN_PARTS for part in path.parts):
            findings.append({"kind": "forbidden-path", "path": name})
        if path.suffix.lower() not in TEXT_SUFFIXES or name.endswith("/"):
            continue
        if path.name in {
            "verify_distribution.py",
            "verify_public_boundary.py",
            "verify_task7a_private_candidate.py",
        }:
            continue
        text = read_bytes(name).decode("utf-8", errors="replace")
        for kind, pattern in LEAK_PATTERNS.items():
            if pattern.search(text):
                findings.append({"kind": kind, "path": name})
    return findings


def main() -> None:
    contract = load_contract()
    wheels = sorted(DIST.glob("project_krypton-1.0.0-*.whl"))
    sdists = sorted(DIST.glob("project_krypton-1.0.0.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise SystemExit("expected exactly one Project Krypton 1.0.0 wheel and sdist")
    wheel, sdist = wheels[0], sdists[0]
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        findings = inspect_names(wheel_names, archive.read)
        required = {
            "krypton/resources/krypton_v1_release_metadata.yaml",
            "krypton/resources/requirements.lock",
            "krypton/resources/registry/models/mock_pk_v1.json",
            "krypton/resources/fixtures/valid/keg_mock_v0.json",
            "krypton/resources/schemas/quantity-value.schema.json",
            "project_krypton-1.0.0.dist-info/licenses/LICENSE",
            "project_krypton-1.0.0.dist-info/licenses/NOTICE",
            "project_krypton-1.0.0.dist-info/licenses/THIRD_PARTY_NOTICES.md",
        }
        missing = sorted(required - set(wheel_names))
        metadata_name = "project_krypton-1.0.0.dist-info/METADATA"
        metadata = BytesParser().parsebytes(archive.read(metadata_name))
        requirements = metadata.get_all("Requires-Dist", [])
        if metadata["Name"] != "project-krypton" or metadata["Version"] != "1.0.0":
            findings.append({"kind": "metadata-identity", "path": metadata_name})
        if metadata["License-Expression"] != "Apache-2.0":
            findings.append({"kind": "metadata-license", "path": metadata_name})
        if any(name in " ".join(requirements).lower() for name in ("numpy", "scipy")):
            findings.append({"kind": "private-dependency", "path": metadata_name})
        wheel_contract = contract["wheel"]  # type: ignore[assignment]
        if not member_set_matches(
            wheel_names,
            expected_count=wheel_contract["expected_file_count"],  # type: ignore[index]
            expected_digest=wheel_contract["expected_member_set_sha256"],  # type: ignore[index]
        ):
            findings.append({"kind": "wheel-member-set-contract-mismatch", "path": wheel.name})
    with tarfile.open(sdist) as archive:
        sdist_members = [member for member in archive.getmembers() if member.isfile()]
        sdist_names = [member.name for member in sdist_members]
        member_map = {member.name: member for member in sdist_members}
        findings.extend(
            inspect_names(
                sdist_names,
                lambda name: archive.extractfile(member_map[name]).read(),  # type: ignore[union-attr]
            )
        )
        normalized_sdist_names = {normalize_sdist_name(name) for name in sdist_names}
        sdist_contract = contract["sdist"]  # type: ignore[assignment]
        if not member_set_matches(
            normalized_sdist_names,
            expected_count=sdist_contract["expected_file_count"],  # type: ignore[index]
            expected_digest=sdist_contract["expected_member_set_sha256"],  # type: ignore[index]
        ):
            findings.append(
                {"kind": "unexpected-unclassified-sdist-member-set", "path": sdist.name}
            )
    report = {
        "status": "PASS" if not findings and not missing else "FAIL",
        "wheel": {
            "filename": wheel.name,
            "sha256": digest(wheel),
            "file_count": len(wheel_names),
            "files": wheel_names,
            "requires_dist": requirements,
        },
        "sdist": {
            "filename": sdist.name,
            "sha256": digest(sdist),
            "file_count": len(sdist_names),
            "files": sdist_names,
        },
        "missing_required_wheel_files": missing,
        "findings": findings,
    }
    output = DIST / "distribution-audit.json"
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key not in {"wheel", "sdist"}}, indent=2, sort_keys=True))
    print(f"WHEEL: {wheel.name} {report['wheel']['sha256']} ({len(wheel_names)} files)")
    print(f"SDIST: {sdist.name} {report['sdist']['sha256']} ({len(sdist_names)} files)")
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
