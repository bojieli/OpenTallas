"""Production compiler and verification path for pinned Qwen3-8B."""

from .adapter import (
    Qwen3AdapterError,
    build_official_tensor_contract,
    build_tensor_specs,
    load_official_config,
    validate_official_checkpoint_lock,
)
from .constants import MODEL_ID, REPOSITORY, REVISION, TARGET_CONTEXT_TOKENS

__all__ = [
    "MODEL_ID",
    "Qwen3AdapterError",
    "REPOSITORY",
    "REVISION",
    "TARGET_CONTEXT_TOKENS",
    "build_official_tensor_contract",
    "build_tensor_specs",
    "load_official_config",
    "validate_official_checkpoint_lock",
]
