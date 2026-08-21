# Project Krypton 1.0.0

Project Krypton is an evidence-gated, provenance-aware, and applicability-aware mechanistic pharmacogenomic research-software prototype. It provides typed contracts for connecting a defined genetic edit to an evidence-qualified mechanistic interpretation, a controlled model input, and a paired counterfactual consequence.

The scientific development history uses a limited CYP2C19 reference route. The public distribution demonstrates the generic architecture without distributing the external scientific data used by the private scientific record. Version 1.0.0 means the first public release of this rights-safe research-software prototype; it does not mean that the platform is clinically validated or generalized across biological routes.

> **Research-use and safety boundary:** Project Krypton 1.0 is research software. It is not clinical decision-support, diagnostic, treatment-selection, patient-specific prediction, or medical-advice software.

## What Krypton is

Krypton separates evidence, biological interpretation, numerical translation, model execution, counterfactual invariance, applicability, and provenance instead of hiding them inside one calculation.

```text
defined genetic state / edit
            |
            v
evidence-qualified KEG path
            |
            v
typed mechanistic translation (MPT)
            |
            v
validated Model Contract + adapter
            |
            v
immutable paired counterfactual run
            |
            v
consequence + applicability + provenance
```

The public core exposes `EditObject`, `EvidenceRecord`, `ApplicabilityContext`, typed quantity/categorical contracts, the Krypton Effect Graph (KEG), Mechanistic Parameter Translator (MPT), Model Contracts, the Pair Runner, guards, and canonical provenance. See [Architecture](docs/architecture.md).

## What Krypton is not

- It is not an arbitrary DNA or genotype-to-phenotype predictor.
- It is not clinical software and must not be used for patient care or treatment recommendations.
- Generalization to other genes, drugs, diseases, tissues, or biological routes has not been demonstrated.
- The C3B route is restricted to its stated scientific scope.
- External descriptive support is not independent quantitative external validation.
- C4 and independent-route generalization are not part of v1.0.

## Scientific status

The machine-readable source of truth is [`krypton_v1_release_metadata.yaml`](krypton_v1_release_metadata.yaml).

| Milestone | Status |
|---|---|
| C0 | COMPLETE |
| C1 | COMPLETE |
| C2 | COMPLETE |
| C3A | COMPLETE |
| C3B | RESTRICTED_COMPLETE |

| Gate or debt | State |
|---|---|
| Route gate | `USABLE_WITH_STATED_SCOPE` |
| Validation maturity | `EXTERNAL_DESCRIPTIVE_SUPPORT` |
| Validation Row 30 | **BLOCKED** |
| Validation Row 31 | **BLOCKED** |
| Model contradiction | NO |
| C4 | `NOT_INCLUDED` |

Rows 30 and 31 are visible, accepted validation debt. They were not converted to PASS or N/A. `EXTERNAL_DESCRIPTIVE_SUPPORT` means that external observations support limited directional or descriptive consistency; it does **not** establish independent quantitative external validation. Details are in [Scientific scope and limitations](docs/scientific-scope.md).

## Public and private boundary

The public distribution includes:

- Project-authored generic architecture and guards;
- public schemas and reference/provenance metadata;
- synthetic C0 fixtures, mock model, and representative demo;
- public tests and packaging/reproducibility infrastructure.

It does not include:

- paper-derived numerical datasets or source-table extractions;
- database-derived frozen scientific artifacts;
- calibration/validation data or private canonical scientific outputs;
- publisher PDFs, figures, tables, or supplementary files.

Full C1-C3B scientific execution therefore requires a lawfully constructed local evidence pack configured with `KRYPTON_LOCAL_EVIDENCE_PACK`. Pack access is fail-closed: there is no automatic download, default value, empty scientific record, or synthetic scientific substitute. See [Scientific reproduction](docs/scientific-reproduction.md), [Data sources](docs/data-sources.md), and the [public/private boundary](docs/public-private-boundary.md).

## Requirements and verified platforms

- Python 3.12: **VERIFIED**
- Windows x86-64 CPU: **VERIFIED**
- GitHub-hosted Ubuntu 24.04 / Python 3.12: **VERIFIED** for the current public CI suite
- GitHub-hosted Linux amd64 Docker: **VERIFIED** for the current Docker CI configuration
- macOS: **UNVERIFIED**
- ARM platforms: **UNVERIFIED**

These Linux results are deliberately narrow: they do not claim verification of every Linux distribution, Docker configuration, or architecture.

## Installation

The canonical public repository URL is <https://github.com/xiuchuhan3690-cmd/project-krypton>.

### Source checkout

From an obtained public source tree, using Python 3.12:

```text
git clone https://github.com/xiuchuhan3690-cmd/project-krypton.git
cd project-krypton
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pip check
.venv\Scripts\python -m pytest -q
```

On a POSIX shell, the equivalent interpreter path is `.venv/bin/python`; that path is exercised by the current GitHub-hosted Ubuntu CI configuration.

### Built wheel

From the directory containing the wheel downloaded from the v1.0.0 GitHub Release:

```text
python -m venv .venv
.venv\Scripts\python -m pip install dist/project_krypton-1.0.0-py3-none-any.whl
```

The wheel contains the generic public core, synthetic demo resources, public schemas, and release metadata. It does not contain the source test suite or external scientific data. Project Krypton is not published on PyPI; use the GitHub Release asset or build from the public source tree.

## Quick start

After either installation route:

```text
python -m krypton
python -m krypton.demo
```

The installed console equivalents are `krypton-info` and `krypton-demo`.

`python -m krypton` reports the software version separately from scientific scope. `python -m krypton.demo` runs the representative synthetic architecture demonstration.

## Representative public demo

Expected synthetic output:

| Endpoint | Value |
|---|---:|
| Baseline AUC | 10 mg·h/L |
| Edited AUC | 25 mg·h/L |
| Delta | +15 mg·h/L |

This is an **architecture demonstration using synthetic inputs**, not a CYP2C19 scientific result and not scientific validation. It exists so a user can inspect paired counterfactual execution, the authorized parameter difference, the Model Contract boundary, KEG/MPT participation, and provenance without obtaining external data. The only permitted branch difference is the synthetic edit-derived clearance change; context, environment, model, adapter, and seed remain invariant.

More detail is available in [Representative demo](docs/representative-demo.md).

## Tests

The two suites have different scopes and must not be conflated:

```text
Public distribution test suite:       228
  Public core:                         176
  Migration guards:                      9
  Packaging tests:                      13
  Documentation tests:                  12
  Resource parity tests:                  7
  CI/governance tests:                   11

Private canonical scientific reference suite: 1184
```

The public tree does not contain the private data needed to run the 1,184-test scientific reference suite. Test metadata is recorded in [`krypton_v1_documentation_test_manifest.yaml`](krypton_v1_documentation_test_manifest.yaml).

## Statement of need

Mechanistic research pipelines can mix biological assumptions, evidence qualification, transformations, model inputs, and execution in ways that make audit and counterfactual comparison difficult. Krypton demonstrates a typed separation of these concerns through explicit evidence and applicability records, graph-resolved mechanisms, versioned mappings and contracts, immutable paired runs, and canonical provenance. Public v1.0 demonstrates that generic architecture; its scientific claims remain bounded to the frozen status above. Comparative novelty claims are deferred to later publication review.

## Citation

Citation metadata is provided in [`CITATION.cff`](CITATION.cff). No DOI exists yet.

> Chuhan Xiu. *Project Krypton*, version 1.0.0. GitHub release; no archival DOI assigned.

The public author identity is frozen as XIU CHUHAN (family name Xiu, given name Chuhan). The canonical repository is <https://github.com/xiuchuhan3690-cmd/project-krypton>. ORCID, affiliation, public contact, and DOI remain absent until separately decided or created.

## Contributing, security, and release information

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [v1.0.0 release notes](docs/release-notes-v1.0.0.md)
- [Public artifact index](docs/artifact-index.md)

## License

Project Krypton-authored code, tests, schemas, scripts, public documentation, and Project-generated public metadata are licensed under Apache-2.0. External scientific data are not distributed. Source-reference metadata is provided for citation/provenance and is not relicensed as Project-authored scientific material. Dependencies retain their upstream licenses. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Future work

Independent-route generalization was considered as future work and is not part of v1.0. C4 is `NOT_INCLUDED`; no non-public route investigation is claimed as a v1.0 result.
