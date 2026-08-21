# Public architecture

Project Krypton makes the boundaries between an edit, evidence, biological interpretation, parameter translation, model execution, counterfactual comparison, applicability, and provenance explicit. The public implementation is generic; it does not bundle the private CYP2C19 scientific route.

```text
EditObject -----------------------------+
    |                                   |
    v                                   v
Krypton Effect Graph (KEG)       ApplicabilityContext
    |                                   |
    +---- EvidenceRecord references ----+
    |
    v
Mechanistic Parameter Translator (MPT)
    |
    v
Model Contract <----> allowlisted ModelAdapter
    |
    v
Counterfactual Pair Runner
    |
    +--> baseline output
    +--> edited output
    +--> authorized/unexpected difference report
    |
    v
PhenotypeConsequence + ProvenanceManifest
```

## Contracts and roles

### EditObject

Represents a defined edit using the canonical zero-based interbase coordinate convention. External coordinate formats must be converted at an adapter boundary; internal code does not guess between conventions.

### EvidenceRecord

Carries a versioned evidence identity, evidence class, source locator, curated claim, limitations, and applicability reference. Evidence identifiers are resolved rather than treated as informal comments. External source-derived scientific records are private/local and are not shipped in v1.0.

### ApplicabilityContext

Declares the population, biological system, environmental assumptions, and other domain constraints under which evidence or a mapping applies. Applicability is evaluated explicitly, including unresolved and out-of-domain outcomes.

### QuantityValue and categorical values

Typed values keep semantic kind, units, distribution semantics, and uncertainty explicit. Numerical and categorical effects are separate contracts; categorical states are not silently coerced into numerical model parameters.

### Krypton Effect Graph

The KEG is a canonical document plus a NetworkX `MultiDiGraph` runtime view. Validation checks unique identifiers, references, DAG structure, roots, reachability, units where applicable, evidence, mappings, and model-parameter references.

### Mechanistic Parameter Translator

MPT mappings translate an evidence-qualified upstream result into a typed downstream effect. Public mapping primitives are deterministic and versioned. Arbitrary expression evaluation and implicit model-SDK coupling are excluded.

### Model Contract and adapter

A Model Contract declares parameter/output names, types, semantics, units, dimensions, ranges, metadata, and artifact identity. Adapters validate at the boundary, perform explicit unit conversion, and reject missing, unknown, or out-of-range inputs rather than silently clamping them.

### Counterfactual Pair Runner

One immutable specification creates baseline and edited branches. Context, environment, initial conditions, model/adapter/version, and seed are shared. Before adapter execution, canonical hashes and a structural diff prove that only edit-derived authorized changes differ. Unexpected changes fail before execution.

### Provenance and consequence

`ProvenanceManifest` records package/runtime information and digest-addressed inputs. `PhenotypeConsequence` links baseline, edited, delta, direction, applicability, uncertainty, evidence path, model versions, out-of-domain flags, and provenance. Canonical JSON and SHA-256 provide deterministic identities; they do not make a scientific claim stronger.

### Guards

Guards reject malformed coordinates, unresolved references, graph cycles, unit/dimension errors, unsupported result types, categorical-to-numeric coercion, missing local evidence packs, stale digests, path traversal, and unauthorized pair differences.

## Distribution boundary

The installed wheel uses `importlib.resources` for synthetic C0 fixtures, the mock registry, public schemas, and release metadata. Scientific routes use the separate, fail-closed local-pack boundary described in [Scientific reproduction](scientific-reproduction.md). No repository-root lookup is required for the installed public demo.
