"""Pinned source and checkpoint ingestion for executable compiler builds."""

from .checkpoint import (
    CHECKPOINT_LOCK_SCHEMA,
    CHECKPOINT_SOURCE_SCHEMA,
    CheckpointError,
    build_checkpoint_lock,
    load_checkpoint_lock,
    load_checkpoint_source,
    read_tensor_payload,
    validate_checkpoint_source,
    validate_checkpoint_lock,
    verify_checkpoint_lock,
)
from .deepseek_v4 import (
    DeepSeekV4AdapterError,
    build_expected_tensor_contract,
    build_official_tensor_specs,
    load_official_config,
    validate_observed_tensor_records,
    validate_official_checkpoint_lock,
)

__all__ = [
    "CHECKPOINT_LOCK_SCHEMA",
    "CHECKPOINT_SOURCE_SCHEMA",
    "CheckpointError",
    "DeepSeekV4AdapterError",
    "build_expected_tensor_contract",
    "build_checkpoint_lock",
    "build_official_tensor_specs",
    "load_checkpoint_lock",
    "load_checkpoint_source",
    "load_official_config",
    "read_tensor_payload",
    "validate_checkpoint_source",
    "validate_checkpoint_lock",
    "validate_observed_tensor_records",
    "validate_official_checkpoint_lock",
    "verify_checkpoint_lock",
]
