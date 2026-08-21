"""Verify public metadata/schema digests without requiring a YAML dependency."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "krypton_v1_public_artifact_digests.yaml"
ENTRY = re.compile(r"^  ([^:]+(?:/[^:]+)*): ([0-9a-f]{64})$")


def main() -> None:
    entries = [ENTRY.match(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines()]
    parsed = [(match.group(1), match.group(2)) for match in entries if match]
    if not parsed:
        raise SystemExit("no digest entries found")
    failures = []
    for relative, expected in parsed:
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"PUBLIC_ARTIFACT_DIGESTS: PASS ({len(parsed)} artifacts)")


if __name__ == "__main__":
    main()
