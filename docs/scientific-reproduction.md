# Scientific reproduction with a local evidence pack

The public distribution alone cannot reproduce the complete C1-C3B scientific reference route because Project Krypton does not redistribute external scientific data, even when a particular source might permit redistribution.

The intended conceptual process is:

```text
public source-reference metadata
              |
              v
lawful user acquisition from the cited source
              |
              v
private extraction under the documented semantics
              |
              v
local evidence-pack manifest + SHA-256
              |
              v
fail-closed validation
              |
              v
private full-route execution and provenance
```

## Responsibilities

The user is responsible for lawful source access, compliance with source terms, accurate extraction, source/version/locator recording, and secure local storage. Krypton does not automatically download publisher or database content and does not provide source tables, figures, PDFs, supplements, or extracted numerical datasets.

## Pack location and manifest

Store the pack outside the public checkout and set:

```text
KRYPTON_LOCAL_EVIDENCE_PACK=<absolute path to the private local pack>
```

The root must contain `evidence-pack-manifest.json` with schema version `krypton-local-evidence-pack-v1`. Every artifact entry contains exactly:

- `id` — unique artifact identity;
- `path` — relative path confined to the pack root;
- `sha256` — lowercase SHA-256 of the local file;
- `scientific_role` — nonblank role description.

The public loader rejects a missing configuration, missing or invalid manifest, unsupported version, empty pack, duplicate identity, malformed digest, absolute/traversal path, outside-root resolution, missing file, unknown artifact, or stale digest.

## Digest namespaces

- `PRIVATE_CANONICAL_HASH` identifies an artifact in the private research record.
- `PUBLIC_METADATA_HASH` identifies redistributable reference or release metadata.
- `LOCAL_REGENERATION_HASH` identifies a user's lawfully regenerated local artifact.

These digests are not interchangeable. A public metadata hash must never be represented as the digest of non-distributed scientific content.

## No fallback

If the pack is absent or invalid, scientific execution is unavailable. Krypton does not switch to a default, approximate, rounded, synthetic, or empty scientific input. The synthetic C0 demo is a separate architecture demonstration and is never a substitute for the scientific route.

For source identifiers, versions, roles, and acquisition locators, see [Data sources](data-sources.md) and `../evidence_metadata/krypton_v1_external_source_reference_manifest.yaml`.
