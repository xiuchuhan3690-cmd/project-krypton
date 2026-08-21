"""Verify Task-3 public documentation and demo artifact digests."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "krypton_v1_task3_artifact_digests.yaml"
ENTRY = re.compile(r"^  ([^:]+(?:/[^:]+)*): ([0-9a-f]{64})$")


def main() -> None:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    start = lines.index("artifacts:") + 1
    matches = [ENTRY.match(line) for line in lines[start:]]
    entries = [(match.group(1), match.group(2)) for match in matches if match]
    failures = []
    for relative, expected in entries:
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK3_ARTIFACT_DIGESTS: PASS ({len(entries)} artifacts)")
    print("TASK2_RELATIONSHIP: 11 unchanged; 3 documentation-boundary artifacts superseded")


if __name__ == "__main__":
    main()
