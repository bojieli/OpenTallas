"""Strict Qwen3-8B config, tensor, and checkpoint adapter.

The adapter is deliberately formula-driven and does not import Transformers.
It independently expands every tensor required by the pinned dense Qwen3
architecture and compares that contract with the byte-hashed checkpoint lock.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from compiler.frontend.checkpoint import (
    load_checkpoint_source,
    validate_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json

from .constants import (
    CONFIG_SHA256,
    DEFAULT_CONFIG,
    DEFAULT_SOURCE,
    INDEX_SHA256,
    LAYER_COUNT,
    LOCAL_CONFIG_SHA256,
    MODEL_ID,
    MODEL_NAME,
    OFFICIAL_CHECKPOINT_LOCK_ID,
    OFFICIAL_TENSOR_CONTENT_SHA256,
    PARAMETER_COUNT,
    PAYLOAD_BYTES,
    REPOSITORY,
    REVISION,
    TARGET_CONTEXT_TOKENS,
    TENSOR_COUNT,
    TENSORS_PER_LAYER,
)


TENSOR_CONTRACT_SCHEMA = "opentallas.qwen3.tensor_contract.v1"
CHECKPOINT_VALIDATION_SCHEMA = "opentallas.qwen3.checkpoint_validation.v1"
TENSOR_STRUCTURE_SHA256 = (
    "29985350e8adaacbc3f785f29dd56035f6ee522ff3b90f5985aad76cd89f0e98"
)


class Qwen3AdapterError(RuntimeError):
    """Raised when the target differs from the pinned official model."""


_EXPECTED_CONFIG: dict[str, Any] = {
    "architectures": ["Qwen3ForCausalLM"],
    "attention_bias": False,
    "attention_dropout": 0.0,
    "bos_token_id": 151643,
    "eos_token_id": 151645,
    "head_dim": 128,
    "hidden_act": "silu",
    "hidden_size": 4096,
    "initializer_range": 0.02,
    "intermediate_size": 12288,
    "max_position_embeddings": 40960,
    "max_window_layers": 36,
    "model_type": "qwen3",
    "num_attention_heads": 32,
    "num_hidden_layers": 36,
    "num_key_value_heads": 8,
    "rms_norm_eps": 1e-06,
    "rope_scaling": None,
    "rope_theta": 1000000,
    "sliding_window": None,
    "tie_word_embeddings": False,
    "torch_dtype": "bfloat16",
    "transformers_version": "4.51.0",
    "use_cache": True,
    "use_sliding_window": False,
    "vocab_size": 151936,
}


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _exact_config(config: Mapping[str, Any]) -> None:
    if not isinstance(config, Mapping):
        raise Qwen3AdapterError("Qwen3 config must be an object")
    missing = sorted(set(_EXPECTED_CONFIG) - set(config))
    unknown = sorted(set(config) - set(_EXPECTED_CONFIG))
    differing = sorted(
        key
        for key in set(config) & set(_EXPECTED_CONFIG)
        if config[key] != _EXPECTED_CONFIG[key]
        or type(config[key]) is not type(_EXPECTED_CONFIG[key])
    )
    if missing or unknown or differing:
        raise Qwen3AdapterError(
            "Qwen3 config differs from the pinned release: "
            f"missing={missing}, unknown={unknown}, differing={differing}"
        )
    if TARGET_CONTEXT_TOKENS > int(config["max_position_embeddings"]):
        raise Qwen3AdapterError(
            "8,000-token target exceeds the checkpoint position bound"
        )
    if int(config["num_attention_heads"]) % int(config["num_key_value_heads"]):
        raise Qwen3AdapterError("query heads are not divisible by KV heads")
    if int(config["num_attention_heads"]) * int(config["head_dim"]) != int(
        config["hidden_size"]
    ):
        raise Qwen3AdapterError("attention heads do not span the hidden dimension")


def load_official_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    """Load and byte-pin the checked-in semantic mirror of the official config."""

    try:
        payload = Path(path).read_bytes()
        config = load_strict_json(Path(path))
    except (OSError, ValueError) as exc:
        raise Qwen3AdapterError(f"cannot load Qwen3 config {path}: {exc}") from exc
    observed = _sha256(payload)
    if observed != LOCAL_CONFIG_SHA256:
        raise Qwen3AdapterError(
            f"Qwen3 local config SHA-256 differs: {observed} != {LOCAL_CONFIG_SHA256}"
        )
    _exact_config(config)
    return config


@dataclass(frozen=True)
class TensorSpec:
    """One released tensor and its complete decode execution role."""

    name: str
    shape: tuple[int, ...]
    role: str
    consumer: str
    layer: int | None = None
    dtype: str = "BF16"

    @property
    def parameter_count(self) -> int:
        return math.prod(self.shape)

    @property
    def size_bytes(self) -> int:
        return self.parameter_count * 2

    def record(self) -> dict[str, Any]:
        return {
            "consumer": self.consumer,
            "dtype": self.dtype,
            "layer": self.layer,
            "name": self.name,
            "parameter_count": self.parameter_count,
            "role": self.role,
            "shape": list(self.shape),
            "size_bytes": self.size_bytes,
        }


def _layer_specs(layer: int, config: Mapping[str, Any]) -> tuple[TensorSpec, ...]:
    hidden = int(config["hidden_size"])
    intermediate = int(config["intermediate_size"])
    q_width = int(config["num_attention_heads"]) * int(config["head_dim"])
    kv_width = int(config["num_key_value_heads"]) * int(config["head_dim"])
    head_dim = int(config["head_dim"])
    base = f"model.layers.{layer}"
    return (
        TensorSpec(
            f"{base}.input_layernorm.weight",
            (hidden,),
            "decoder_weight",
            "RMS_NORM_INPUT",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.q_proj.weight",
            (q_width, hidden),
            "decoder_weight",
            "Q_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.k_proj.weight",
            (kv_width, hidden),
            "decoder_weight",
            "K_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.v_proj.weight",
            (kv_width, hidden),
            "decoder_weight",
            "V_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.q_norm.weight",
            (head_dim,),
            "decoder_weight",
            "Q_HEAD_RMS_NORM",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.k_norm.weight",
            (head_dim,),
            "decoder_weight",
            "K_HEAD_RMS_NORM",
            layer,
        ),
        TensorSpec(
            f"{base}.self_attn.o_proj.weight",
            (hidden, q_width),
            "decoder_weight",
            "ATTENTION_OUTPUT_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.post_attention_layernorm.weight",
            (hidden,),
            "decoder_weight",
            "RMS_NORM_POST_ATTENTION",
            layer,
        ),
        TensorSpec(
            f"{base}.mlp.gate_proj.weight",
            (intermediate, hidden),
            "decoder_weight",
            "MLP_GATE_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.mlp.up_proj.weight",
            (intermediate, hidden),
            "decoder_weight",
            "MLP_UP_PROJECTION",
            layer,
        ),
        TensorSpec(
            f"{base}.mlp.down_proj.weight",
            (hidden, intermediate),
            "decoder_weight",
            "MLP_DOWN_PROJECTION",
            layer,
        ),
    )


def build_tensor_specs(config: Mapping[str, Any]) -> tuple[TensorSpec, ...]:
    """Expand all 399 official tensor shapes without reading checkpoint headers."""

    _exact_config(config)
    hidden = int(config["hidden_size"])
    vocab = int(config["vocab_size"])
    specs: list[TensorSpec] = [
        TensorSpec(
            "model.embed_tokens.weight",
            (vocab, hidden),
            "input_embedding",
            "TOKEN_EMBEDDING_LOOKUP",
        )
    ]
    for layer in range(int(config["num_hidden_layers"])):
        specs.extend(_layer_specs(layer, config))
    specs.extend(
        (
            TensorSpec(
                "model.norm.weight",
                (hidden,),
                "final_norm",
                "RMS_NORM_FINAL",
            ),
            TensorSpec(
                "lm_head.weight",
                (vocab, hidden),
                "output_head",
                "LOGITS_PROJECTION",
            ),
        )
    )
    result = tuple(specs)
    names = [spec.name for spec in result]
    if len(result) != TENSOR_COUNT or len(set(names)) != TENSOR_COUNT:
        raise Qwen3AdapterError("formula did not produce 399 unique Qwen3 tensors")
    layer_counts = Counter(spec.layer for spec in result if spec.layer is not None)
    if layer_counts != Counter(
        {layer: TENSORS_PER_LAYER for layer in range(LAYER_COUNT)}
    ):
        raise Qwen3AdapterError("formula did not produce 11 tensors for every layer")
    if sum(spec.parameter_count for spec in result) != PARAMETER_COUNT:
        raise Qwen3AdapterError(
            "formula parameter count differs from the pinned release"
        )
    if sum(spec.size_bytes for spec in result) != PAYLOAD_BYTES:
        raise Qwen3AdapterError("formula payload bytes differ from the pinned release")
    return result


def tensor_structure_sha256(specs: Iterable[TensorSpec]) -> str:
    records = [spec.record() for spec in specs]
    records.sort(key=lambda item: item["name"])
    return _sha256(canonical_json_bytes(records))


def _source_identity(source_path: Path) -> dict[str, Any]:
    try:
        source = load_checkpoint_source(source_path)
    except Exception as exc:
        raise Qwen3AdapterError(f"invalid Qwen3 checkpoint source: {exc}") from exc
    if (
        source["repository"] != REPOSITORY
        or source["revision"] != REVISION
        or source["remote_code_policy"] != "disabled"
        or source["checkpoint_index"] != "model.safetensors.index.json"
    ):
        raise Qwen3AdapterError(
            "checkpoint source is not the pinned local-only Qwen3 release"
        )
    expected = {item["path"]: item for item in source["expected_files"]}
    for path, digest in (
        ("config.json", CONFIG_SHA256),
        ("model.safetensors.index.json", INDEX_SHA256),
    ):
        record = expected.get(path)
        if record is None or record["sha256"] != digest:
            raise Qwen3AdapterError(f"checkpoint source does not pin {path} exactly")
    return source


def build_official_tensor_contract(
    config: Mapping[str, Any] | None = None,
    *,
    source_path: Path = DEFAULT_SOURCE,
) -> dict[str, Any]:
    """Emit a deterministic, complete source-to-tensor execution contract."""

    if config is None:
        config = load_official_config()
    _source_identity(source_path)
    specs = build_tensor_specs(config)
    structure = tensor_structure_sha256(specs)
    if structure != TENSOR_STRUCTURE_SHA256:
        raise Qwen3AdapterError(
            f"tensor structure identity differs: {structure} != {TENSOR_STRUCTURE_SHA256}"
        )
    records = [spec.record() for spec in specs]
    body = {
        "coverage": {
            "all_checkpoint_payloads_have_execution_roles": True,
            "expected_parameter_count": PARAMETER_COUNT,
            "expected_payload_bytes": PAYLOAD_BYTES,
            "expected_tensor_count": TENSOR_COUNT,
            "layer_count": LAYER_COUNT,
            "tensor_structure_sha256": structure,
        },
        "model": {
            "config_sha256": CONFIG_SHA256,
            "id": MODEL_ID,
            "name": MODEL_NAME,
            "repository": REPOSITORY,
            "revision": REVISION,
            "target_context_tokens": TARGET_CONTEXT_TOKENS,
        },
        "schema": TENSOR_CONTRACT_SCHEMA,
        "tensors": records,
    }
    return {**body, "contract_id": _sha256(canonical_json_bytes(body))}


def _locked_records(lock: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    records: dict[str, Mapping[str, Any]] = {}
    for shard in lock["shards"]:
        for tensor in shard["tensors"]:
            if tensor["name"] in records:
                raise Qwen3AdapterError(f"duplicate locked tensor {tensor['name']!r}")
            records[tensor["name"]] = tensor
    return records


def validate_official_checkpoint_lock(
    lock: dict[str, Any],
    config: Mapping[str, Any] | None = None,
    *,
    source_path: Path = DEFAULT_SOURCE,
) -> dict[str, Any]:
    """Require every locked tensor to match the official formula and identity."""

    try:
        validate_checkpoint_lock(lock)
    except Exception as exc:
        raise Qwen3AdapterError(f"invalid checkpoint lock: {exc}") from exc
    source = _source_identity(source_path)
    if lock["source"] != source:
        raise Qwen3AdapterError(
            "checkpoint lock source differs from the official source"
        )
    if config is None:
        config = load_official_config()
    specs = build_tensor_specs(config)
    expected = {spec.name: spec for spec in specs}
    observed = _locked_records(lock)
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    mismatched: list[str] = []
    for name in sorted(set(expected) & set(observed)):
        spec = expected[name]
        record = observed[name]
        if (
            record["dtype"] != spec.dtype
            or tuple(record["shape"]) != spec.shape
            or record["size_bytes"] != spec.size_bytes
        ):
            mismatched.append(name)
    if missing or extra or mismatched:
        raise Qwen3AdapterError(
            "checkpoint tensors differ from the official contract: "
            f"missing={missing[:8]}, extra={extra[:8]}, mismatched={mismatched[:8]}"
        )
    checkpoint = lock["checkpoint"]
    if (
        lock["lock_id"] != OFFICIAL_CHECKPOINT_LOCK_ID
        or checkpoint["tensor_content_sha256"] != OFFICIAL_TENSOR_CONTENT_SHA256
        or checkpoint["tensor_count"] != TENSOR_COUNT
        or checkpoint["payload_bytes"] != PAYLOAD_BYTES
        or checkpoint["shard_count"] != 5
    ):
        raise Qwen3AdapterError("checkpoint summary differs from the pinned release")
    body = {
        "checkpoint_lock_id": lock["lock_id"],
        "model_id": MODEL_ID,
        "parameter_count": PARAMETER_COUNT,
        "payload_bytes": PAYLOAD_BYTES,
        "schema": CHECKPOINT_VALIDATION_SCHEMA,
        "tensor_count": TENSOR_COUNT,
        "tensor_structure_sha256": tensor_structure_sha256(specs),
    }
    return {**body, "validation_id": _sha256(canonical_json_bytes(body))}


__all__ = [
    "CHECKPOINT_VALIDATION_SCHEMA",
    "Qwen3AdapterError",
    "TENSOR_CONTRACT_SCHEMA",
    "TENSOR_STRUCTURE_SHA256",
    "TensorSpec",
    "build_official_tensor_contract",
    "build_tensor_specs",
    "load_official_config",
    "tensor_structure_sha256",
    "validate_official_checkpoint_lock",
]
