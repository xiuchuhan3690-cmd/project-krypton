"""Fail closed when private scientific data or local/secret material leaks."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).parents[1].resolve()
TEXT_SUFFIXES = {".csv", ".ini", ".json", ".lock", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
PROHIBITED_PATHS = (
    "artifacts/",
    "evidence/",
    "fixtures/c1/",
    "fixtures/c2/",
    "fixtures/c3a/",
    "fixtures/c3b/",
    "src/krypton/resources/fixtures/c1/",
    "src/krypton/resources/fixtures/c2/",
    "src/krypton/resources/fixtures/c3a/",
    "src/krypton/resources/fixtures/c3b/",
    "registry/calibrations/",
    "registry/mpt/",
    "src/krypton/resources/registry/calibrations/",
    "src/krypton/resources/registry/mpt/",
    "src/krypton/c2/",
    "src/krypton/c3a/",
    "src/krypton/c3b/",
    "vocabularies/",
    "src/krypton/resources/vocabularies/",
)
PROHIBITED_TEXT = {
    "local-windows-user-path": re.compile(r"(?i)(?:[a-z]:\\users\\|PC_User|\\\.codex\\|/\.codex/|OneDrive)"),
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "credential-assignment": re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{8,}"),
    "c2-extracted-source-cell": re.compile(r'(?i)(?:arithmetic_mean|source_value)\s*["\']?\s*[:=]\s*["\']?(?:50\.2|32\.3|4\.3|18\.4|11\.9|0\.95)\b'),
    "c3a-extracted-parameter": re.compile(r'(?i)(?:clf_value|clh_value|ka_value|vc_value)\s*["\']?\s*[:=]'),
    "c3b-fitted-source-value": re.compile(r'(?i)(?:k_rxn|k_rec|beta_b|y0)\s*["\']?\s*[:=]\s*["\']?(?:0\.751|0\.031|0\.\d+|\d+\.\d+)'),
}
ALLOWED_EXTERNAL_DATA = {
    "external_data/.gitignore",
    "external_data/DO_NOT_COMMIT_EXTERNAL_SCIENTIFIC_DATA.md",
}


def main() -> None:
    findings: list[dict[str, str]] = []
    for obsolete in ("fixtures", "schemas", "registry"):
        if (ROOT / obsolete).exists():
            findings.append({"kind": "obsolete-runtime-resource-root", "path": obsolete})
    # Repository metadata is expected after the Task-6 public initialization.
    # Payload checks intentionally inspect only versioned/publication candidates;
    # the one-time Task-6 freeze separately proves that private history was not
    # copied into the newly initialized repository.
    files = [
        path
        for path in ROOT.rglob("*")
        if path.is_file()
        and ".git" not in path.parts
        and ".pytest_cache" not in path.parts
        and "__pycache__" not in path.parts
    ]
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if any(relative.startswith(prefix) for prefix in PROHIBITED_PATHS):
            findings.append({"kind": "prohibited-path", "path": relative})
        if relative.startswith("external_data/") and relative not in ALLOWED_EXTERNAL_DATA:
            findings.append({"kind": "external-data-file", "path": relative})
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        # The verifier necessarily contains its own detection signatures.
        if relative in {
            "scripts/verify_public_boundary.py",
            "scripts/verify_distribution.py",
            "scripts/verify_task7a_private_candidate.py",
        }:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in PROHIBITED_TEXT.items():
            if pattern.search(text):
                findings.append({"kind": name, "path": relative})
    report = {"files_scanned": len(files), "findings": findings, "status": "PASS" if not findings else "FAIL"}
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if not findings else 1)


if __name__ == "__main__":
    main()
