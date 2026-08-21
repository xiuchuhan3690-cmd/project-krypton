# Project Krypton 1.0.0 draft release notes

Status: draft for a future public release. No GitHub release, tag, repository, DOI, or deposition has been created.

## Included

- Generic typed Project Krypton public-core architecture and guards.
- Canonical public schemas.
- Rights-safe source-reference and provenance metadata.
- Synthetic C0 representative demo with baseline AUC 10, edited AUC 25, and delta +15.
- Hybrid source, wheel, Dockerfile, and local-evidence-pack distribution boundary.
- Public tests, packaging verification, documentation, and license/third-party notices.

## Not included

- External scientific data, paper-derived values, source tables, database extracts, PDFs, figures, or supplements.
- Private C1-C3B evidence, calibration, validation, canonical outputs, and regression fixtures.
- C4 or independent-route generalization.
- Clinical, diagnostic, treatment-selection, or medical-advice functionality.

## Installation and quick check

With Python 3.12 and an obtained source tree:

```text
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pytest -q
python -m krypton
python -m krypton.demo
```

The wheel may instead be installed from the local candidate artifact. No PyPI or repository URL is claimed yet.

## Verification status

- Public suite: 221 tests, including source/installed resource-parity and CI/governance regression coverage.
- Private canonical scientific reference: 1,184 tests; not distributed or runnable from the public tree.
- Windows x86-64 CPU / Python 3.12: verified.
- Linux amd64 Docker, macOS, and ARM: unverified.
- Dockerfile boundary: statically verified; Docker runtime not verified.

## Scientific limitations

C3B remains `RESTRICTED_COMPLETE`, route gate `USABLE_WITH_STATED_SCOPE`, validation maturity `EXTERNAL_DESCRIPTIVE_SUPPORT`, with Rows 30 and 31 BLOCKED. External descriptive support is not independent quantitative external validation. The synthetic demo is not scientific validation.

## External scientific data

No external scientific data are distributed. Full C1-C3B reproduction requires lawful local acquisition and a validated pack configured through `KRYPTON_LOCAL_EVIDENCE_PACK`; failure is explicit and closed.

## Checksums

Task-2 candidate artifacts were audited, but publication checksums will be rebuilt and frozen during a later artifact-publication task. Do not treat draft checksums as final release identifiers.
