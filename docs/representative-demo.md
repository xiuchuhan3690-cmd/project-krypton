# Representative synthetic demo

The public demo exists to verify the generic architecture without external scientific data.

Run after installation:

```text
python -m krypton
python -m krypton.demo
```

Expected architecture-only result:

```text
baseline AUC: 10 mg*h/L
edited AUC:   25 mg*h/L
delta:        +15 mg*h/L
```

The inputs, evidence record, graph, mapping, and model are synthetic. This is not a CYP2C19 result, biological calibration, clinical prediction, or validation dataset.

The demo exercises:

1. a typed synthetic `EditObject` and `EvidenceRecord`;
2. a valid KEG path;
3. a deterministic MPT mapping;
4. a validated mock Model Contract and adapter;
5. baseline/edited Pair Runner invariance;
6. one authorized edit-derived parameter difference;
7. baseline/edited/delta consequence output;
8. canonical provenance and digest reporting.

An attempted edited-branch dose change is rejected before adapter execution by the same pair-invariance guard. No evidence pack is required because the demo makes no external scientific claim.
