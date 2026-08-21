"""Machine-readable installed-package identity."""

from __future__ import annotations

import json

from krypton import __version__


def main() -> None:
    print(
        json.dumps(
            {
                "software_name": "Project Krypton",
                "software_version": __version__,
                "scientific_scope": "restricted research prototype",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
