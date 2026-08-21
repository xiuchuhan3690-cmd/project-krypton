# Do not commit external scientific data

This directory is a local-only mount point. Paper-derived values, database
records, frozen scientific fixtures, source tables, source PDFs, and evidence
pack artifacts must never be committed to the public Project Krypton history.

Set `KRYPTON_LOCAL_EVIDENCE_PACK` to a directory outside the Git checkout. The
pack must contain `evidence-pack-manifest.json`; Krypton validates every local
artifact against its declared SHA-256 digest before use.

