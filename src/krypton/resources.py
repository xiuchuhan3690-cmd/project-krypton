"""Repository-independent access to bundled public-core resources."""

from __future__ import annotations

from contextlib import AbstractContextManager
from importlib import resources
from pathlib import Path


def public_resource(name: str):
    """Return a traversable public resource without assuming a repository root."""

    if not name or name.startswith(("/", "\\")) or ".." in Path(name).parts:
        raise ValueError("public resource name must be a safe relative path")
    return resources.files("krypton").joinpath("resources", *Path(name).parts)


def public_resource_root() -> AbstractContextManager[Path]:
    """Materialize the bundled resource root for Path-based public workflows."""

    return resources.as_file(resources.files("krypton").joinpath("resources"))


def read_public_text(name: str) -> str:
    """Read UTF-8 text from the public resource allowlist."""

    resource = public_resource(name)
    if not resource.is_file():
        raise FileNotFoundError(f"unknown public package resource: {name}")
    return resource.read_text(encoding="utf-8")
