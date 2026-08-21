# Project Krypton 1.0.1 release notes

Project Krypton v1.0.1 is the first formal GitHub Release of the rights-safe research-software prototype. An earlier `v1.0.0` tag was created during a controlled but halted publication attempt. A Windows Git checkout line-ending defect was found before completion, so no v1.0.0 GitHub Release or release assets were published. The tag remains unchanged as historical provenance.

Version 1.0.1 corrects cross-platform Git checkout and line-ending reproducibility. It makes no scientific-semantic, model, biological, calibration, or validation change.

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
- Clinical, diagnostic, treatment-selection, patient-specific prediction, or medical-advice functionality.

## Verification status

- Public suite: 228 tests, including strict distribution-membership, portable-digest, source/installed resource-parity, and CI/governance regression coverage.
- Private canonical scientific reference: 1,184 tests; not distributed or runnable from the public tree.
- Windows x86-64 CPU / Python 3.12: verified.
- GitHub-hosted Ubuntu 24.04 / Python 3.12: verified for the current public CI suite.
- GitHub-hosted Linux amd64 Docker: verified for the current Docker CI configuration.
- macOS and ARM: unverified.

## Scientific and data boundary

C3B remains `RESTRICTED_COMPLETE`, route gate `USABLE_WITH_STATED_SCOPE`, validation maturity `EXTERNAL_DESCRIPTIVE_SUPPORT`, with Rows 30 and 31 BLOCKED. C4 is `NOT_INCLUDED`. External descriptive support is not independent quantitative external validation, and the synthetic demo is not a CYP2C19 scientific result.

No external scientific data are distributed. Full C1-C3B reproduction requires lawful local acquisition and a validated pack configured through `KRYPTON_LOCAL_EVIDENCE_PACK`; failure is explicit and closed.

Project Krypton is not published on PyPI. No DOI or Zenodo deposition exists. `SHA256SUMS.txt` in the v1.0.1 GitHub Release records the exact SHA-256 values of its uploaded wheel and sdist.
