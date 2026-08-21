# Scientific scope and limitations

This document explains the scientific status labels recorded in `krypton_v1_release_metadata.yaml`. Packaging completeness and scientific validation maturity are different axes.

## Frozen status

| Milestone | Status |
|---|---|
| C0 | COMPLETE |
| C1 | COMPLETE |
| C2 | COMPLETE |
| C3A | COMPLETE |
| C3B | RESTRICTED_COMPLETE |

```text
route_gate: USABLE_WITH_STATED_SCOPE
validation_maturity: EXTERNAL_DESCRIPTIVE_SUPPORT
row_30: BLOCKED
row_31: BLOCKED
model_contradiction: false
C4: NOT_INCLUDED
```

## Meaning of C3B restricted completion

`RESTRICTED_COMPLETE` means the frozen, limited reference workflow met its internal completion requirements while retaining explicit scope and validation debt. It does not mean general biological-route completion, broad population validity, clinical readiness, or independent external validation.

`USABLE_WITH_STATED_SCOPE` means the route may be used as a bounded research proof of concept only when its assumptions, applicability conditions, evidence roles, and limitations are carried with the result.

`EXTERNAL_DESCRIPTIVE_SUPPORT` means selected external observations provide descriptive or directional consistency under the frozen evidence roles. It is not equivalent to independent quantitative external validation, prospective validation, individual prediction accuracy, or clinical utility.

Rows 30 and 31 remain **BLOCKED**. They are visible validation debt, not hidden footnotes, and were not reclassified as PASS or not applicable. They do not by themselves establish a model contradiction; the frozen model-contradiction status is `false`.

## Reference-route boundary

The private scientific development record uses a limited CYP2C19/pantoprazole reference route. The public tree provides source citations and generic software but not the external values, calibration artifacts, or scientific regression fixtures required to reproduce that route. CYP2C19 is therefore development history and a reference implementation context—not a treatment recommendation or supported patient-specific service.

## Unsupported interpretations

Project Krypton v1.0 must not be interpreted as:

- a generalized DNA consequence predictor;
- a whole-body or arbitrary genotype-to-phenotype platform;
- a diagnostic, treatment-selection, or clinical decision-support system;
- evidence of generalization to other genes, drugs, diseases, populations, or routes;
- evidence that a synthetic public demo is scientifically calibrated.

Independent-route generalization remains future work. C4 is not included in v1.0.
