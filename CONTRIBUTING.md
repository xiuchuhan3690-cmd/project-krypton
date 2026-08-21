# Contributing to Project Krypton

Project Krypton welcomes contributions to the rights-safe public core: typed contracts, generic graph/mapping/model infrastructure, guards, tests, documentation, packaging, and synthetic examples.

## Development setup

Use Python 3.12 from a public source checkout. Install the frozen public dependency set before the editable project:

```text
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r requirements.lock
.venv\Scripts\python -m pip install -e ".[test]"
.venv\Scripts\python -m pip check
.venv\Scripts\python -m pytest -q
```

On POSIX systems use `.venv/bin/python`. Run `python scripts/verify_public_boundary.py` and `python scripts/verify_task7a_private_candidate.py` before proposing a change. Packaging changes should also run `python scripts/verify_distribution.py` after rebuilding the candidate wheel and sdist.

## Public/private data rule

Do not commit external scientific data. This includes paper-derived numerical cells, copied tables, frozen database records, calibration/validation inputs, PDFs, figures, supplements, and private canonical artifacts—even when a source license might permit redistribution. Do not put such content in source, tests, fixtures, documentation, examples, build output, or Git history.

Lawfully acquired scientific inputs belong outside the checkout in a local pack referenced by `KRYPTON_LOCAL_EVIDENCE_PACK`. Never weaken fail-closed behavior or add silent defaults, synthetic scientific substitutes, or automatic external downloads.

## Scientific-state protection

Contributions must not silently change models, parameters, units, calibrations, thresholds, evidence identity, provenance, validation policy, or completion status. In particular, C3B remains `RESTRICTED_COMPLETE`, `USABLE_WITH_STATED_SCOPE`, and `EXTERNAL_DESCRIPTIVE_SUPPORT`; Rows 30 and 31 remain BLOCKED, and C4 is not part of v1.0.

## Review expectations

- Classify the change under `GOVERNANCE.md`; scientific-semantic and data/rights changes require stronger gates than routine maintenance.
- Keep changes scoped and typed, with positive and negative tests.
- Preserve canonical serialization and explicit unit/applicability validation.
- Explain provenance, rights, scientific-claim, and backward-compatibility effects.
- Update machine-readable metadata when public counts or boundaries change.
- Treat external-data leakage, unauthorized pair differences, silent coercion, and misleading scientific claims as blocking defects.
- Identify third-party material and its license; do not assume that citation alone grants redistribution rights.

No CLA or DCO is required at this stage. By contributing, you must have authority to submit your original contribution under the repository license. AI-assisted work must identify the assisted scope, the human review performed, and any relevant input provenance. Do not provide private, confidential, copyrighted source material, patient data, or external scientific datasets to an AI system for this project.

## Issues and reports

The canonical repository is <https://github.com/xiuchuhan3690-cmd/project-krypton> and remains private during pre-publication validation. After publication, use its issue templates for reproducible software bugs, documentation problems, and feature discussions. A verified confidential security-reporting mechanism is a hard visibility gate and must be activated before public reader access; never use a public issue for security, secret, or external-data exposure. No contact address is inferred in advance.
