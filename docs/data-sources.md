# External scientific source workflow

Project Krypton public v1 does not redistribute paper-derived values, database
records, source tables, source fixtures, or frozen datasets—even where an
upstream license might permit redistribution.

For each source, `evidence_metadata/krypton_v1_external_source_reference_manifest.yaml`
records its citation, identifier, locator, scientific role, and local
regeneration requirement without reproducing the source data.

## Local pack procedure

1. Obtain each source through its publisher/database and comply with its terms.
2. Perform the documented extraction in a private workspace.
3. Represent the result using the canonical private schema and semantic units.
4. Create `evidence-pack-manifest.json` with schema version
   `krypton-local-evidence-pack-v1` and entries containing only `id`, `path`,
   lowercase `sha256`, and `scientific_role`.
5. Store the pack outside this checkout and set `KRYPTON_LOCAL_EVIDENCE_PACK`.
6. Run local-evidence verification. A missing file, stale digest, traversal,
   duplicate identity, or unsupported manifest version fails closed.

`PRIVATE_CANONICAL_HASH`, `LOCAL_REGENERATION_HASH`, and
`PUBLIC_METADATA_HASH` are distinct. Public metadata must never claim to be the
hash of non-distributed scientific content.

See [Scientific reproduction](scientific-reproduction.md) for the complete
conceptual workflow and fail-closed boundary. The public source-reference
manifest provides locators and roles, not a redistributable scientific dataset.
