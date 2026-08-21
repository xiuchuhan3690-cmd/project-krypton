# Project Krypton governance

Project Krypton is currently a single-owner research-software project. The project owner has final authority for merge, release, scientific scope, licensing, and publication-boundary decisions. No committee or unconfirmed maintainer role is implied.

## Change classes and gates

Every proposed change is assigned the highest applicable class.

| Class | Change | Minimum gate |
|---|---|---|
| A | Documentation, CI, packaging, or repository mechanics | Complete public tests, dependency check, relevant packaging/boundary checks, owner review |
| B | Software behavior without scientific-semantic change | Class A gates plus positive/negative tests, compatibility and provenance review |
| C | Scientific semantics, evidence identity, model parameter, mapping, threshold, validation policy, or scientific claim | Class B gates plus explicit scientific review, regenerated frozen artifacts/digests, and a version-impact decision |
| D | External data, evidence-pack, redistribution, privacy, security, or licensing boundary | Class C gates plus documented rights/data review; fail closed until lawful publication scope is established |

A change that crosses classes uses the stricter gate. C and D changes may not be presented as maintenance-only changes.

## Review and merge

Pull requests must be scoped, explain their class, pass CI, and disclose provenance, rights, compatibility, and scientific-claim effects. Self-merge by the single owner is permitted only after the applicable gate is evidenced. Contributors cannot weaken fail-closed data, unit, applicability, provenance, or counterfactual-invariance checks merely to make a test pass.

Recommended branch protection for `main` is: require pull requests; require all CI jobs; require conversation resolution; block force pushes and deletion; apply rules to administrators; and require a current branch before merge. These controls are optional non-blocking hardening for v1.0.1; force pushes and deletion of release history remain prohibited by policy even when an equivalent GitHub ruleset is absent. `CODEOWNERS` is deferred until maintainer ownership rules are separately reviewed.

## Scientific and publication state

Version 1.0.1 preserves C0/C1/C2/C3A COMPLETE, C3B RESTRICTED_COMPLETE, route gate USABLE_WITH_STATED_SCOPE, validation maturity EXTERNAL_DESCRIPTIVE_SUPPORT, Rows 30 and 31 BLOCKED, no model contradiction, and C4 NOT_INCLUDED. A scientific-semantic change can require a version increase even when the Python API remains compatible.

The public repository may contain Project software, synthetic fixtures, generated schemas, citation/provenance metadata, public tests, and reviewed release artifacts. It must not contain external scientific datasets, private evidence packs, private canonical Git history, credentials, local working files, patient or genotype data, or unreviewed source-derived datasets.

## Dependencies, releases, and security

Dependency updates are human-reviewed pull requests; passing CI is necessary but not sufficient for merge. Automatic merge is not enabled. Project releases follow Semantic Versioning principles, while scientific-semantic compatibility is assessed independently of API compatibility. Only the project owner may authorize a release, tag, publication, or artifact signing. No signing identity or key is created by this policy.

Security and sensitive-data reports follow `SECURITY.md` through GitHub Private Vulnerability Reporting. Public issues must not be used for confidential reports, and no unverified contact route may be substituted.

## Participation policy decisions

A separate Code of Conduct is deferred until community participation begins. This avoids copying third-party standard text before the owner chooses a version, attribution, enforcement contact, and process. Until then, contributions must remain respectful, technical, lawful, and within `CONTRIBUTING.md`; the owner may close unsafe or out-of-scope submissions.

AI-assisted contributions must disclose the tool-assisted scope, identify human review, and affirm that prompts/inputs did not introduce unlicensed, private, confidential, or patient material. The contributor remains responsible for correctness, provenance, and licensing.
