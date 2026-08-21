"""Installed-package entry point for the deterministic synthetic C0 demo."""

from __future__ import annotations

import json

from krypton import __version__
from krypton.orchestration import build_c0_mock_workflow
from krypton.resources import public_resource_root


def demo_summary() -> dict[str, object]:
    with public_resource_root() as root:
        result = build_c0_mock_workflow(root).run()
    return {
        "workflow": "project-krypton-c0-mock",
        "software_version": __version__,
        "scientific_scope": "restricted research prototype",
        "warning": "Artificial architecture test only; not biological evidence.",
        "edit_id": result.edit.id,
        "evidence_id": result.evidence.id,
        "keg_path": list(result.keg_path_node_ids),
        "mapping_id": result.mpt_result.mapping_id,
        "clearance": {
            "baseline_L_per_h": result.mpt_result.baseline.value,
            "edited_L_per_h": result.mpt_result.edited.value,
        },
        "auc": {
            "baseline_mg_h_per_L": result.consequence.baseline.value,
            "edited_mg_h_per_L": result.consequence.edited.value,
            "delta_mg_h_per_L": result.consequence.delta.value,
        },
        "authorized_differences": [
            item.parameter_id for item in result.pair_result.difference_report.authorized
        ],
        "unexpected_differences": [
            item.parameter_id for item in result.pair_result.difference_report.unexpected
        ],
        "provenance_reference": result.consequence.provenance_reference,
        "workflow_digest": result.digest(),
    }


def main() -> None:
    print(json.dumps(demo_summary(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
