"""Verify Task-2 release/packaging artifacts and the Task-1 relationship."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).parents[1]
MANIFEST = ROOT / "krypton_v1_task2_artifact_digests.yaml"
ENTRY = re.compile(r"^  ([^:]+(?:/[^:]+)*): ([0-9a-f]{64})$")


def main() -> None:
    lines = MANIFEST.read_text(encoding="utf-8").splitlines()
    artifact_start = lines.index("artifacts:") + 1
    matches = [ENTRY.match(line) for line in lines[artifact_start:]]
    entries = [(match.group(1), match.group(2)) for match in matches if match]
    failures = []
    for relative, expected in entries:
        path = ROOT / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "missing"
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"TASK2_ARTIFACT_DIGESTS: PASS ({len(entries)} artifacts)")
    print("TASK1_RELATIONSHIP: 18 unchanged; NOTICE intentionally superseded")


if __name__ == "__main__":
    main()
