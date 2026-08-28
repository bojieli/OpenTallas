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
from .deepseek_v4_graph import (
    DeepSeekV4GraphError,
    build_official_graph_contract,
    load_official_inference_config,
)
from .deepseek_v4_encoding import (
    DeepSeekV4CompletionError,
    DeepSeekV4EncodingError,
    encode_messages,
    parse_message_from_completion_text,
)
from .deepseek_v4_tokenizer import (
    DeepSeekV4TokenizerError,
    VerifiedDeepSeekV4Tokenizer,
    load_verified_deepseek_v4_tokenizer,
)

__all__ = [
    "CHECKPOINT_LOCK_SCHEMA",
    "CHECKPOINT_SOURCE_SCHEMA",
    "CheckpointError",
    "DeepSeekV4AdapterError",
    "DeepSeekV4CompletionError",
    "DeepSeekV4EncodingError",
    "DeepSeekV4GraphError",
    "DeepSeekV4TokenizerError",
    "VerifiedDeepSeekV4Tokenizer",
    "build_expected_tensor_contract",
    "build_checkpoint_lock",
    "build_official_tensor_specs",
    "build_official_graph_contract",
    "encode_messages",
    "load_checkpoint_lock",
    "load_checkpoint_source",
    "load_official_config",
    "load_official_inference_config",
    "load_verified_deepseek_v4_tokenizer",
    "parse_message_from_completion_text",
    "read_tensor_payload",
    "validate_checkpoint_source",
    "validate_checkpoint_lock",
    "validate_observed_tensor_records",
    "validate_official_checkpoint_lock",
    "verify_checkpoint_lock",
]
