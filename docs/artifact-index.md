# Public artifact index

## Release and scientific status

- [`../krypton_v1_release_metadata.yaml`](../krypton_v1_release_metadata.yaml) — primary current-release authority for v1.0.1 identity, scientific state, current test counts, platform status, repository state, and local-pack policy. Its packaged resource copy is byte-equivalent.
- [`scientific-scope.md`](scientific-scope.md) — plain-language interpretation of the frozen scientific scope and validation debt.
- [`../CHANGELOG.md`](../CHANGELOG.md) — public distribution changes.
- [`release-notes-v1.0.1.md`](release-notes-v1.0.1.md) — v1.0.1 first-formal-release notes and concise v1.0.0 halted-publication history.

## Rights and source boundary

- [`../krypton_v1_public_migration_manifest.yaml`](../krypton_v1_public_migration_manifest.yaml) — private-to-public representation map.
- [`../evidence_metadata/krypton_v1_external_source_reference_manifest.yaml`](../evidence_metadata/krypton_v1_external_source_reference_manifest.yaml) — reference-only source identities and locators.
- [`data-sources.md`](data-sources.md) — lawful acquisition and local-pack overview.
- [`public-private-boundary.md`](public-private-boundary.md) — distribution boundary.
- [`../THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md) — dependency and external-source notice boundary.

## Packaging and dependencies

- [`../krypton_v1_package_contents_manifest.yaml`](../krypton_v1_package_contents_manifest.yaml) — authoritative current distribution contract, including exact expected wheel/sdist member sets and counts.
- [`../krypton_v1_dependency_boundary.yaml`](../krypton_v1_dependency_boundary.yaml) — runtime/test/build/private dependency classification.
- [`../krypton_v1_packaging_test_manifest.yaml`](../krypton_v1_packaging_test_manifest.yaml) — immutable historical Task-2 packaging evidence; not current release state.
- [`packaging.md`](packaging.md) — installable distribution boundary.

## Tests and documentation

- [`../krypton_v1_public_test_manifest.yaml`](../krypton_v1_public_test_manifest.yaml) — immutable historical Task-1 public/private test classification; not the current test-count authority.
- [`../krypton_v1_documentation_test_manifest.yaml`](../krypton_v1_documentation_test_manifest.yaml) — immutable historical Task-3 test counts and documentation checks; not the current test-count authority.

Task-numbered manifests and the Task-4/4R/5/6 publication, clean-room, and freeze manifests preserve checkpoint-specific provenance. Their historical counts, repository state, platform state, and archive hashes must not be interpreted as current v1.0 release facts.
- [`architecture.md`](architecture.md) — public implementation architecture.
- [`scientific-reproduction.md`](scientific-reproduction.md) — fail-closed local evidence-pack workflow.

## Demo

- `python -m krypton.demo` — installed representative demo.
- [`representative-demo.md`](representative-demo.md) — purpose, expected result, and non-scientific boundary.
- [`../examples/c0_mock/run.py`](../examples/c0_mock/run.py) — source-checkout equivalent.
