"""Model-independent external model contracts and adapter protocol."""

from krypton.models.contract import (
    ModelAdapter,
    ModelContract,
    ModelContractError,
    ModelInputBundle,
    ModelInputSpec,
    ModelMetadata,
    ModelOutputBundle,
    ModelOutputSpec,
    NumericRange,
    ParameterType,
    canonicalize_inputs,
    validate_outputs,
)

__all__ = [
    "ModelAdapter",
    "ModelContract",
    "ModelContractError",
    "ModelInputBundle",
    "ModelInputSpec",
    "ModelMetadata",
    "ModelOutputBundle",
    "ModelOutputSpec",
    "NumericRange",
    "ParameterType",
    "canonicalize_inputs",
    "validate_outputs",
]
