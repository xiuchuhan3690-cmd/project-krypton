"""Deliberately artificial PK adapter used only for architecture verification."""

from __future__ import annotations

from decimal import Decimal

from krypton.domain import QuantityValue
from krypton.models import (
    ModelContract,
    ModelContractError,
    ModelInputBundle,
    ModelOutputBundle,
    canonicalize_inputs,
    validate_outputs,
)

MOCK_ADAPTER_ARTIFACT_DIGEST = (
    "09b1bbefaef9b9a44abea8422d3c504b17e26f2b7436fb82340a12a905a63b5e"
)
MOCK_ADAPTER_B_ARTIFACT_DIGEST = (
    "57b41b2c31a64897d55b308ae7b15ba3641d9fcc5cb634550a91950588d13443"
)


class MockPKAdapter:
    """Pinned AUC = dose / clearance implementation; not biological evidence."""

    artifact_digest = MOCK_ADAPTER_ARTIFACT_DIGEST

    def __init__(self, contract: ModelContract) -> None:
        self.contract = contract
        self.execution_count = 0

    def execute(self, inputs: ModelInputBundle) -> ModelOutputBundle:
        canonical = canonicalize_inputs(self.contract, inputs)
        dose = canonical.values["dose"].value
        clearance = canonical.values["clearance"].value
        self.execution_count += 1
        auc = dose / clearance
        outputs = ModelOutputBundle(
            contract_id=self.contract.id,
            contract_version=self.contract.metadata.model_version,
            values={
                "auc": QuantityValue(
                    distribution="fixed",
                    unit="mg*h/L",
                    semantic_kind="auc",
                    value=auc,
                )
            },
        )
        return validate_outputs(self.contract, outputs)


class MockPKAdapterB:
    """Replaceable Decimal-based implementation of the same mock contract."""

    artifact_digest = MOCK_ADAPTER_B_ARTIFACT_DIGEST

    def __init__(self, contract: ModelContract) -> None:
        self.contract = contract
        self.execution_count = 0

    def execute(self, inputs: ModelInputBundle) -> ModelOutputBundle:
        canonical = canonicalize_inputs(self.contract, inputs)
        dose = Decimal(str(canonical.values["dose"].value))
        clearance = Decimal(str(canonical.values["clearance"].value))
        self.execution_count += 1
        auc = float(dose / clearance)
        outputs = ModelOutputBundle(
            contract_id=self.contract.id,
            contract_version=self.contract.metadata.model_version,
            values={
                "auc": QuantityValue(
                    distribution="fixed",
                    unit="mg*h/L",
                    semantic_kind="auc",
                    value=auc,
                )
            },
        )
        return validate_outputs(self.contract, outputs)
