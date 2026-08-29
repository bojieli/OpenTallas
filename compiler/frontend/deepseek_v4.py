"""Official DeepSeek V4 Flash graph and checkpoint tensor adapter.

The adapter is intentionally exact rather than model-family generic.  It accepts
only the content-pinned DeepSeek-V4-Flash-0731 release, resolves every expected
checkpoint tensor from the official config and inference implementation, and
fails on any missing, extra, mistyped, or misshaped tensor.  It does not execute
the release's Python code.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
import re
from typing import Any, Iterable

from compiler.frontend.checkpoint import (
    DTYPE_BITS,
    load_checkpoint_source,
    validate_checkpoint_lock,
)
from compiler.ir.model import canonical_json_bytes, load_strict_json


MODEL_ID = "deepseek-v4-flash-0731"
REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
CONFIG_SHA256 = "6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023"
INDEX_SHA256 = "98efab455cf08dfbbbaaba6f570e1bf10bf927d2b4c3c453a59c2f6f0e3be92b"
TENSOR_STRUCTURE_SHA256 = (
    "18285fe60ca3655be488bbabb88b59489b8ee03cff7fc4f4729424051ca83e0e"
)
OFFICIAL_CHECKPOINT_LOCK_ID = (
    "30b3d07304b92cb26440e5ea9e28dcb06c835dbf35652529fa9a856da07ad760"
)
OFFICIAL_TENSOR_CONTENT_SHA256 = (
    "7ca2e951786c4cd46b64b437d975da3565a1692bdceeb804c09d5fe9e1503b3f"
)
TENSOR_COUNT = 72_317
PAYLOAD_BYTES = 166_878_536_440

TARGET_DIR = (
    Path(__file__).resolve().parents[1]
    / "models"
    / "deepseek-v4-flash-0731"
)
DEFAULT_CONFIG = TARGET_DIR / "config.json"
DEFAULT_SOURCE = TARGET_DIR / "checkpoint_source.json"

_MAIN_COMPRESS_RATIOS = (
    0,
    0,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
    128,
    4,
)
_DSPARK_COMPRESS_RATIOS = (0, 0, 0)


class DeepSeekV4AdapterError(RuntimeError):
    """Raised when the official graph or tensor contract differs."""


def _expect(config: dict[str, Any], key: str, expected: Any) -> None:
    if key not in config or config[key] != expected:
        raise DeepSeekV4AdapterError(
            f"official config {key!r} differs: {config.get(key)!r} versus {expected!r}"
        )


def validate_official_config(config: dict[str, Any]) -> None:
    """Require the exact architecture-affecting V4 Flash configuration."""

    if not isinstance(config, dict):
        raise DeepSeekV4AdapterError("official model config must be an object")
    expected_scalars = {
        "architectures": ["DeepseekV4ForCausalLM"],
        "bos_token_id": 0,
        "compress_rope_theta": 160000,
        "dspark_block_size": 5,
        "dspark_markov_rank": 256,
        "dspark_noise_token_id": 128799,
        "dspark_target_layer_ids": [40, 41, 42],
        "eos_token_id": 1,
        "expert_dtype": "fp4",
        "hc_eps": 1e-6,
        "hc_mult": 4,
        "hc_sinkhorn_iters": 20,
        "head_dim": 512,
        "hidden_act": "silu",
        "hidden_size": 4096,
        "index_head_dim": 128,
        "index_n_heads": 64,
        "index_topk": 512,
        "max_position_embeddings": 1_048_576,
        "model_type": "deepseek_v4",
        "moe_intermediate_size": 2048,
        "n_routed_experts": 256,
        "n_shared_experts": 1,
        "norm_topk_prob": True,
        "num_attention_heads": 64,
        "num_experts_per_tok": 6,
        "num_hash_layers": 3,
        "num_hidden_layers": 43,
        "num_key_value_heads": 1,
        # The release root config says one prediction layer, while the official
        # inference config and checkpoint contain three DSpark stages.  This
        # value remains pinned here; stage resolution is explicit below.
        "num_nextn_predict_layers": 1,
        "o_groups": 8,
        "o_lora_rank": 1024,
        "q_lora_rank": 1024,
        "qk_rope_head_dim": 64,
        "rms_norm_eps": 1e-6,
        "rope_theta": 10000,
        "routed_scaling_factor": 1.5,
        "scoring_func": "sqrtsoftplus",
        "sliding_window": 128,
        "swiglu_limit": 10.0,
        "tie_word_embeddings": False,
        "topk_method": "noaux_tc",
        "torch_dtype": "bfloat16",
        "use_cache": True,
        "vocab_size": 129280,
    }
    for key, expected in expected_scalars.items():
        _expect(config, key, expected)
    _expect(
        config,
        "quantization_config",
        {
            "activation_scheme": "dynamic",
            "fmt": "e4m3",
            "quant_method": "fp8",
            "scale_fmt": "ue8m0",
            "weight_block_size": [128, 128],
        },
    )
    _expect(
        config,
        "rope_scaling",
        {
            "beta_fast": 32,
            "beta_slow": 1,
            "factor": 16,
            "original_max_position_embeddings": 65536,
            "type": "yarn",
        },
    )
    _expect(
        config,
        "compress_ratios",
        [*_MAIN_COMPRESS_RATIOS, *_DSPARK_COMPRESS_RATIOS],
    )


def load_official_config(
    path: Path = DEFAULT_CONFIG, source_path: Path = DEFAULT_SOURCE
) -> dict[str, Any]:
    """Load the byte-exact committed copy of the official release config."""

    source = load_checkpoint_source(source_path)
    if source["repository"] != REPOSITORY or source["revision"] != REVISION:
        raise DeepSeekV4AdapterError("checkpoint source is not the pinned V4 Flash release")
    expected = {item["path"]: item for item in source["expected_files"]}["config.json"]
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise DeepSeekV4AdapterError(f"cannot read official config {path}: {exc}") from exc
    digest = hashlib.sha256(payload).hexdigest()
    if digest != expected["sha256"] or len(payload) != expected["size_bytes"]:
        raise DeepSeekV4AdapterError(
            "official config bytes differ from the checkpoint source contract"
        )
    try:
        config = load_strict_json(path)
    except ValueError as exc:
        raise DeepSeekV4AdapterError(f"invalid official config: {exc}") from exc
    validate_official_config(config)
    return config


@dataclass(frozen=True)
class TensorSpec:
    """One exact tensor expected in the official checkpoint."""

    name: str
    storage_dtype: str
    shape: tuple[int, ...]
    logical_dtype: str
    semantic_role: str
    scope: str
    layer: int | None = None
    expert: int | None = None
    scale_for: str | None = None

    @property
    def size_bytes(self) -> int:
        return math.prod(self.shape) * DTYPE_BITS[self.storage_dtype] // 8

    def structure_record(self) -> dict[str, Any]:
        return {
            "dtype": self.storage_dtype,
            "name": self.name,
            "shape": list(self.shape),
            "size_bytes": self.size_bytes,
        }

    def contract_record(self) -> dict[str, Any]:
        return {
            **self.structure_record(),
            "expert": self.expert,
            "layer": self.layer,
            "logical_dtype": self.logical_dtype,
            "scale_for": self.scale_for,
            "scope": self.scope,
            "semantic_role": self.semantic_role,
        }


class _TensorBuilder:
    def __init__(self) -> None:
        self.specs: dict[str, TensorSpec] = {}

    def add(
        self,
        name: str,
        dtype: str,
        shape: tuple[int, ...],
        role: str,
        *,
        scope: str,
        layer: int | None = None,
        expert: int | None = None,
        logical_dtype: str | None = None,
        scale_for: str | None = None,
    ) -> None:
        if name in self.specs:
            raise DeepSeekV4AdapterError(f"adapter generated duplicate tensor {name!r}")
        if dtype not in DTYPE_BITS:
            raise DeepSeekV4AdapterError(f"adapter generated unsupported dtype {dtype!r}")
        self.specs[name] = TensorSpec(
            name=name,
            storage_dtype=dtype,
            shape=shape,
            logical_dtype=logical_dtype or dtype,
            semantic_role=role,
            scope=scope,
            layer=layer,
            expert=expert,
            scale_for=scale_for,
        )

    def fp8_linear(
        self,
        prefix: str,
        out_features: int,
        in_features: int,
        role: str,
        *,
        scope: str,
        layer: int | None = None,
    ) -> None:
        weight = f"{prefix}.weight"
        self.add(
            weight,
            "F8_E4M3",
            (out_features, in_features),
            f"{role}.weight",
            scope=scope,
            layer=layer,
            logical_dtype="FP8_E4M3FN",
        )
        self.add(
            f"{prefix}.scale",
            "F8_E8M0",
            (
                math.ceil(out_features / 128),
                math.ceil(in_features / 128),
            ),
            f"{role}.scale",
            scope=scope,
            layer=layer,
            logical_dtype="UE8M0_SCALE",
            scale_for=weight,
        )

    def fp4_linear(
        self,
        prefix: str,
        out_features: int,
        in_features: int,
        role: str,
        *,
        scope: str,
        layer: int,
        expert: int,
    ) -> None:
        if in_features % 32:
            raise DeepSeekV4AdapterError("FP4 logical K dimension is not block aligned")
        weight = f"{prefix}.weight"
        self.add(
            weight,
            "I8",
            (out_features, in_features // 2),
            f"{role}.weight",
            scope=scope,
            layer=layer,
            expert=expert,
            logical_dtype="MXFP4_E2M1_X2",
        )
        self.add(
            f"{prefix}.scale",
            "F8_E8M0",
            (out_features, in_features // 32),
            f"{role}.scale",
            scope=scope,
            layer=layer,
            expert=expert,
            logical_dtype="UE8M0_SCALE",
            scale_for=weight,
        )


def _add_hyper_connection(
    builder: _TensorBuilder,
    prefix: str,
    branch: str,
    *,
    dim: int,
    hc_mult: int,
    scope: str,
    layer: int,
) -> None:
    mix_hc = (2 + hc_mult) * hc_mult
    hc_dim = hc_mult * dim
    root = f"{prefix}.hc_{branch}"
    role = f"hyper_connection.{branch}"
    builder.add(
        f"{root}_base",
        "F32",
        (mix_hc,),
        f"{role}.base",
        scope=scope,
        layer=layer,
        logical_dtype="FP32",
    )
    builder.add(
        f"{root}_fn",
        "F32",
        (mix_hc, hc_dim),
        f"{role}.projection",
        scope=scope,
        layer=layer,
        logical_dtype="FP32",
    )
    builder.add(
        f"{root}_scale",
        "F32",
        (3,),
        f"{role}.scale",
        scope=scope,
        layer=layer,
        logical_dtype="FP32",
    )


def _add_block(
    builder: _TensorBuilder,
    prefix: str,
    layer: int,
    compress_ratio: int,
    *,
    config: dict[str, Any],
    scope: str,
    hash_route: bool,
) -> None:
    if compress_ratio not in {0, 4, 128}:
        raise DeepSeekV4AdapterError(f"unsupported compression ratio {compress_ratio}")
    dim = config["hidden_size"]
    heads = config["num_attention_heads"]
    head_dim = config["head_dim"]
    q_rank = config["q_lora_rank"]
    groups = config["o_groups"]
    o_rank = config["o_lora_rank"]
    inter = config["moe_intermediate_size"]
    experts = config["n_routed_experts"]
    hc_mult = config["hc_mult"]

    attn = f"{prefix}.attn"
    builder.add(
        f"{attn}.attn_sink",
        "F32",
        (heads,),
        "attention.sink",
        scope=scope,
        layer=layer,
        logical_dtype="FP32",
    )
    builder.add(
        f"{attn}.kv_norm.weight",
        "BF16",
        (head_dim,),
        "attention.kv_norm.weight",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{attn}.q_norm.weight",
        "BF16",
        (q_rank,),
        "attention.q_norm.weight",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wkv",
        head_dim,
        dim,
        "attention.kv_projection",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wo_a",
        groups * o_rank,
        heads * head_dim // groups,
        "attention.output_a",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wo_b",
        dim,
        groups * o_rank,
        "attention.output_b",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wq_a",
        q_rank,
        dim,
        "attention.query_a",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{attn}.wq_b",
        heads * head_dim,
        q_rank,
        "attention.query_b",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{prefix}.attn_norm.weight",
        "BF16",
        (dim,),
        "block.attention_norm.weight",
        scope=scope,
        layer=layer,
    )

    if compress_ratio:
        compressor = f"{attn}.compressor"
        coefficient = 2 if compress_ratio == 4 else 1
        compressed_dim = coefficient * head_dim
        builder.add(
            f"{compressor}.ape",
            "F32",
            (compress_ratio, compressed_dim),
            "attention.compressor.position_weight",
            scope=scope,
            layer=layer,
            logical_dtype="FP32",
        )
        builder.add(
            f"{compressor}.norm.weight",
            "BF16",
            (head_dim,),
            "attention.compressor.norm.weight",
            scope=scope,
            layer=layer,
        )
        for projection in ("wgate", "wkv"):
            builder.add(
                f"{compressor}.{projection}.weight",
                "BF16",
                (compressed_dim, dim),
                f"attention.compressor.{projection}.weight",
                scope=scope,
                layer=layer,
            )
        if compress_ratio == 4:
            index_dim = config["index_head_dim"]
            index_heads = config["index_n_heads"]
            indexer = f"{attn}.indexer"
            index_compressor = f"{indexer}.compressor"
            builder.add(
                f"{index_compressor}.ape",
                "F32",
                (compress_ratio, 2 * index_dim),
                "attention.indexer.compressor.position_weight",
                scope=scope,
                layer=layer,
                logical_dtype="FP32",
            )
            builder.add(
                f"{index_compressor}.norm.weight",
                "BF16",
                (index_dim,),
                "attention.indexer.compressor.norm.weight",
                scope=scope,
                layer=layer,
            )
            for projection in ("wgate", "wkv"):
                builder.add(
                    f"{index_compressor}.{projection}.weight",
                    "BF16",
                    (2 * index_dim, dim),
                    f"attention.indexer.compressor.{projection}.weight",
                    scope=scope,
                    layer=layer,
                )
            builder.add(
                f"{indexer}.weights_proj.weight",
                "BF16",
                (index_heads, dim),
                "attention.indexer.head_weights.weight",
                scope=scope,
                layer=layer,
            )
            builder.fp8_linear(
                f"{indexer}.wq_b",
                index_heads * index_dim,
                q_rank,
                "attention.indexer.query",
                scope=scope,
                layer=layer,
            )
    ffn = f"{prefix}.ffn"
    builder.add(
        f"{ffn}.gate.weight",
        "BF16",
        (experts, dim),
        "moe.router.weight",
        scope=scope,
        layer=layer,
    )
    if hash_route:
        builder.add(
            f"{ffn}.gate.tid2eid",
            "I64",
            (config["vocab_size"], config["num_experts_per_tok"]),
            "moe.hash_route.table",
            scope=scope,
            layer=layer,
            logical_dtype="INT64",
        )
    else:
        builder.add(
            f"{ffn}.gate.bias",
            "F32",
            (experts,),
            "moe.router.selection_bias",
            scope=scope,
            layer=layer,
            logical_dtype="FP32",
        )
    for expert in range(experts):
        root = f"{ffn}.experts.{expert}"
        builder.fp4_linear(
            f"{root}.w1",
            inter,
            dim,
            "moe.routed_expert.gate",
            scope=scope,
            layer=layer,
            expert=expert,
        )
        builder.fp4_linear(
            f"{root}.w2",
            dim,
            inter,
            "moe.routed_expert.down",
            scope=scope,
            layer=layer,
            expert=expert,
        )
        builder.fp4_linear(
            f"{root}.w3",
            inter,
            dim,
            "moe.routed_expert.up",
            scope=scope,
            layer=layer,
            expert=expert,
        )
    shared = f"{ffn}.shared_experts"
    builder.fp8_linear(
        f"{shared}.w1",
        inter,
        dim,
        "moe.shared_expert.gate",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{shared}.w2",
        dim,
        inter,
        "moe.shared_expert.down",
        scope=scope,
        layer=layer,
    )
    builder.fp8_linear(
        f"{shared}.w3",
        inter,
        dim,
        "moe.shared_expert.up",
        scope=scope,
        layer=layer,
    )
    builder.add(
        f"{prefix}.ffn_norm.weight",
        "BF16",
        (dim,),
        "block.ffn_norm.weight",
        scope=scope,
        layer=layer,
    )
    _add_hyper_connection(
        builder,
        prefix,
        "attn",
        dim=dim,
        hc_mult=hc_mult,
        scope=scope,
        layer=layer,
    )
    _add_hyper_connection(
        builder,
        prefix,
        "ffn",
        dim=dim,
        hc_mult=hc_mult,
        scope=scope,
        layer=layer,
    )


def build_official_tensor_specs(config: dict[str, Any]) -> tuple[TensorSpec, ...]:
    """Generate the complete 72,317-tensor contract from official semantics."""

    validate_official_config(config)
    builder = _TensorBuilder()
    dim = config["hidden_size"]
    vocab = config["vocab_size"]
    hc_mult = config["hc_mult"]

    builder.add(
        "embed.weight",
        "BF16",
        (vocab, dim),
        "model.token_embedding.weight",
        scope="global",
    )
    builder.add(
        "head.weight",
        "BF16",
        (vocab, dim),
        "model.lm_head.weight",
        scope="global",
    )
    builder.add(
        "norm.weight",
        "BF16",
        (dim,),
        "model.final_norm.weight",
        scope="global",
    )
    builder.add(
        "hc_head_base",
        "F32",
        (hc_mult,),
        "model.hyper_connection_head.base",
        scope="global",
        logical_dtype="FP32",
    )
    builder.add(
        "hc_head_fn",
        "F32",
        (hc_mult, hc_mult * dim),
        "model.hyper_connection_head.projection",
        scope="global",
        logical_dtype="FP32",
    )
    builder.add(
        "hc_head_scale",
        "F32",
        (1,),
        "model.hyper_connection_head.scale",
        scope="global",
        logical_dtype="FP32",
    )

    for layer, ratio in enumerate(_MAIN_COMPRESS_RATIOS):
        _add_block(
            builder,
            f"layers.{layer}",
            layer,
            ratio,
            config=config,
            scope="main",
            hash_route=layer < config["num_hash_layers"],
        )
    for stage, ratio in enumerate(_DSPARK_COMPRESS_RATIOS):
        _add_block(
            builder,
            f"mtp.{stage}",
            stage,
            ratio,
            config=config,
            scope="dspark",
            hash_route=False,
        )

    target_layers = config["dspark_target_layer_ids"]
    builder.fp8_linear(
        "mtp.0.main_proj",
        dim,
        dim * len(target_layers),
        "dspark.main_hidden_projection",
        scope="dspark",
        layer=0,
    )
    builder.add(
        "mtp.0.main_norm.weight",
        "BF16",
        (dim,),
        "dspark.main_hidden_norm.weight",
        scope="dspark",
        layer=0,
    )
    final_stage = len(_DSPARK_COMPRESS_RATIOS) - 1
    final_prefix = f"mtp.{final_stage}"
    builder.add(
        f"{final_prefix}.confidence_head.proj.weight",
        "BF16",
        (1, dim + config["dspark_markov_rank"]),
        "dspark.confidence_head.weight",
        scope="dspark",
        layer=final_stage,
    )
    for suffix, role in (
        ("hc_head_base", "base"),
        ("hc_head_fn", "projection"),
        ("hc_head_scale", "scale"),
    ):
        shape = {
            "base": (hc_mult,),
            "projection": (hc_mult, hc_mult * dim),
            "scale": (1,),
        }[role]
        builder.add(
            f"{final_prefix}.{suffix}",
            "F32",
            shape,
            f"dspark.hyper_connection_head.{role}",
            scope="dspark",
            layer=final_stage,
            logical_dtype="FP32",
        )
    markov_rank = config["dspark_markov_rank"]
    builder.add(
        f"{final_prefix}.markov_head.markov_w1.weight",
        "BF16",
        (vocab, markov_rank),
        "dspark.markov_embedding.weight",
        scope="dspark",
        layer=final_stage,
    )
    builder.add(
        f"{final_prefix}.markov_head.markov_w2.weight",
        "BF16",
        (vocab, markov_rank),
        "dspark.markov_head.weight",
        scope="dspark",
        layer=final_stage,
    )
    builder.add(
        f"{final_prefix}.norm.weight",
        "BF16",
        (dim,),
        "dspark.final_norm.weight",
        scope="dspark",
        layer=final_stage,
    )

    specs = tuple(builder.specs[name] for name in sorted(builder.specs))
    if len(specs) != TENSOR_COUNT:
        raise DeepSeekV4AdapterError(
            f"adapter generated {len(specs)} tensors instead of {TENSOR_COUNT}"
        )
    return specs


def tensor_structure_sha256(specs: Iterable[TensorSpec]) -> str:
    records = sorted(
        (spec.structure_record() for spec in specs), key=lambda item: item["name"]
    )
    return hashlib.sha256(canonical_json_bytes(records)).hexdigest()


def _normalized_pattern(name: str) -> str:
    value = re.sub(r"(?<=layers\.)\d+", "{layer}", name)
    value = re.sub(r"(?<=experts\.)\d+", "{expert}", value)
    return re.sub(r"(?<=mtp\.)\d+", "{mtp}", value)


def build_expected_tensor_contract(config: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, payload-free tensor-role contract summary."""

    specs = build_official_tensor_specs(config)
    structure_sha256 = tensor_structure_sha256(specs)
    if structure_sha256 != TENSOR_STRUCTURE_SHA256:
        raise DeepSeekV4AdapterError(
            "generated tensor structure differs from the independently locked "
            "official shard-header inventory"
        )
    dtype_counts: Counter[str] = Counter()
    dtype_bytes: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    role_bytes: Counter[str] = Counter()
    pattern_counts: Counter[str] = Counter()
    scope_counts: Counter[str] = Counter()
    scope_bytes: Counter[str] = Counter()
    for spec in specs:
        dtype_counts[spec.storage_dtype] += 1
        dtype_bytes[spec.storage_dtype] += spec.size_bytes
        role_counts[spec.semantic_role] += 1
        role_bytes[spec.semantic_role] += spec.size_bytes
        pattern_counts[_normalized_pattern(spec.name)] += 1
        scope_counts[spec.scope] += 1
        scope_bytes[spec.scope] += spec.size_bytes
    body: dict[str, Any] = {
        "adaptations": [
            {
                "decision": "derive three DSpark stages from checkpoint namespaces, "
                "the three compression-ratio tail entries, and official inference config",
                "root_config_value": {"num_nextn_predict_layers": 1},
                "resolved_value": {"dspark_stage_count": 3},
                "status": "explicit_release_source_reconciliation",
            }
        ],
        "config_sha256": CONFIG_SHA256,
        "coverage": {
            "expected_tensor_count": len(specs),
            "expected_payload_bytes": sum(spec.size_bytes for spec in specs),
            "extra_tensor_count": None,
            "missing_tensor_count": None,
            "observed_tensor_count": None,
            "unknown_role_count": 0,
            "validation_status": "expected_contract_only",
        },
        "dtype_summary": [
            {
                "dtype": dtype,
                "payload_bytes": dtype_bytes[dtype],
                "tensor_count": dtype_counts[dtype],
            }
            for dtype in sorted(dtype_counts)
        ],
        "index_sha256": INDEX_SHA256,
        "model_id": MODEL_ID,
        "operator_graph_status": "not_yet_executable",
        "pattern_count": len(pattern_counts),
        "repository": REPOSITORY,
        "revision": REVISION,
        "role_summary": [
            {
                "payload_bytes": role_bytes[role],
                "role": role,
                "tensor_count": role_counts[role],
            }
            for role in sorted(role_counts)
        ],
        "schema": "opentallas.deepseek_v4_tensor_contract.v1",
        "scope_summary": [
            {
                "payload_bytes": scope_bytes[scope],
                "scope": scope,
                "tensor_count": scope_counts[scope],
            }
            for scope in sorted(scope_counts)
        ],
        "tensor_structure_sha256": structure_sha256,
    }
    return {
        **body,
        "contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def validate_observed_tensor_records(
    records: Iterable[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    """Compare checkpoint-lock tensor records with the complete official contract."""

    expected_specs = build_official_tensor_specs(config)
    expected = {spec.name: spec.structure_record() for spec in expected_specs}
    observed: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(records):
        if not isinstance(raw, dict):
            raise DeepSeekV4AdapterError(f"observed tensor {index} must be an object")
        name = raw.get("name")
        if not isinstance(name, str) or not name:
            raise DeepSeekV4AdapterError(f"observed tensor {index} has no valid name")
        if name in observed:
            raise DeepSeekV4AdapterError(f"observed duplicate tensor {name!r}")
        observed[name] = {
            "dtype": raw.get("dtype"),
            "name": name,
            "shape": raw.get("shape"),
            "size_bytes": raw.get("size_bytes"),
        }
    missing = sorted(expected.keys() - observed.keys())
    extra = sorted(observed.keys() - expected.keys())
    mismatched = sorted(
        name
        for name in expected.keys() & observed.keys()
        if expected[name] != observed[name]
    )
    if missing or extra or mismatched:
        raise DeepSeekV4AdapterError(
            "official checkpoint tensor contract differs: "
            f"missing={missing[:8]}, extra={extra[:8]}, mismatched={mismatched[:8]}"
        )
    structure = hashlib.sha256(
        canonical_json_bytes([observed[name] for name in sorted(observed)])
    ).hexdigest()
    if structure != TENSOR_STRUCTURE_SHA256:
        raise DeepSeekV4AdapterError("observed tensor structure digest differs")
    return {
        "payload_bytes": sum(item["size_bytes"] for item in observed.values()),
        "status": "pass",
        "tensor_count": len(observed),
        "tensor_structure_sha256": structure,
    }


def validate_official_checkpoint_lock(
    lock: dict[str, Any], config: dict[str, Any]
) -> dict[str, Any]:
    """Bind a structurally valid full checkpoint lock to the V4 tensor contract."""

    validate_checkpoint_lock(lock)
    source = lock["source"]
    if source["repository"] != REPOSITORY or source["revision"] != REVISION:
        raise DeepSeekV4AdapterError("checkpoint lock is not the pinned V4 Flash release")
    expected_files = {item["path"]: item for item in source["expected_files"]}
    if expected_files.get("config.json", {}).get("sha256") != CONFIG_SHA256:
        raise DeepSeekV4AdapterError("checkpoint lock has a different official config")
    if (
        expected_files.get("model.safetensors.index.json", {}).get("sha256")
        != INDEX_SHA256
    ):
        raise DeepSeekV4AdapterError("checkpoint lock has a different official index")
    summary = lock["checkpoint"]
    if (
        lock["lock_id"] != OFFICIAL_CHECKPOINT_LOCK_ID
        or summary["tensor_content_sha256"] != OFFICIAL_TENSOR_CONTENT_SHA256
    ):
        raise DeepSeekV4AdapterError(
            "checkpoint lock content is not the pinned official V4 Flash release"
        )
    if summary["tensor_count"] != TENSOR_COUNT or summary["payload_bytes"] != PAYLOAD_BYTES:
        raise DeepSeekV4AdapterError("checkpoint lock summary differs from V4 Flash")
    records = [
        tensor for shard in lock["shards"] for tensor in shard["tensors"]
    ]
    validation = validate_observed_tensor_records(records, config)
    return {
        "checkpoint_lock_id": lock["lock_id"],
        "config_sha256": CONFIG_SHA256,
        "index_sha256": INDEX_SHA256,
        "model_id": MODEL_ID,
        "schema": "opentallas.deepseek_v4_checkpoint_validation.v1",
        **validation,
    }


def role_totals(specs: Iterable[TensorSpec]) -> dict[str, dict[str, int]]:
    """Return compact semantic-role totals for downstream placement planning."""

    counts: defaultdict[str, int] = defaultdict(int)
    sizes: defaultdict[str, int] = defaultdict(int)
    for spec in specs:
        counts[spec.semantic_role] += 1
        sizes[spec.semantic_role] += spec.size_bytes
    return {
        role: {"payload_bytes": sizes[role], "tensor_count": counts[role]}
        for role in sorted(counts)
    }
