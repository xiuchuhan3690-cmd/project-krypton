# Public packaging boundary

Project Krypton 1.0.1 uses a hybrid distribution: the repository and Docker image carry the complete rights-safe public software/test surface, while the wheel carries the generic `krypton` package plus synthetic C0 resources and public schemas. External scientific data are never package data.

The distribution name is `project-krypton`; the import name remains `krypton`. Version `1.0.1` is the first formal GitHub Release of the rights-safe research-software prototype and records cross-platform checkout remediation, not general scientific or clinical validation.

Project-authored runtime fixtures, schemas, and the synthetic mock registry live physically under `src/krypton/resources`. Editable source and installed wheel executions both resolve that same layout through `krypton.resources` and `importlib.resources`; no repository-root or working-directory fallback is supported.

Runtime requirements use compatible ranges in wheel metadata. `requirements.lock` is the exact developer/Docker reproduction environment. NumPy and SciPy are private-scientific-only dependencies and are absent from the public lock and wheel requirements.

Installed entry points:

```text
python -m krypton
python -m krypton.demo
krypton-info
krypton-demo
```

The demo is synthetic. A C1-C3B route must explicitly open a local pack through `KRYPTON_LOCAL_EVIDENCE_PACK`; absence raises an evidence-pack-required error and never selects synthetic or default scientific values.
