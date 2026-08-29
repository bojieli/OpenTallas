"""Source-mapped DeepSeek V4 Flash semantic graph coverage.

This module turns the pinned official topology into an ordered graph contract.
It deliberately stops short of calling that graph executable: every operator is
owned, source-anchored, assigned a lowering and cost class, and connected to its
checkpoint tensor roles.  Qualified reference slices are named individually;
the remaining reference, service-engine, and RTL implementations stay explicitly
pending.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
from typing import Any

from compiler.frontend.deepseek_v4 import (
    DEFAULT_SOURCE,
    MODEL_ID,
    REPOSITORY,
    REVISION,
    TensorSpec,
    build_official_tensor_specs,
    load_official_config,
)
from compiler.frontend.checkpoint import load_checkpoint_source
from compiler.ir.model import canonical_json_bytes, load_strict_json


INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
KERNEL_SOURCE_SHA256 = (
    "59b325083d7103975cba025bd0d60ea343bb82d8fff53088afb7c04bd380c0c2"
)
CONVERT_SOURCE_SHA256 = (
    "6efe65ebc66b18c9f2656816608f941cacfe20da79c2dee19040ecbee8b42bfe"
)
GENERATE_SOURCE_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
MODEL_CARD_SHA256 = "252acafdc9204d0dba3fde1b0a93d71cd1664a4ceadfe222b60117ed0ccc56ff"
ENCODING_SOURCE_SHA256 = (
    "abc0d26120250dda0ae077dc64aa28836026e61e970854aaeb792445e6a0dde6"
)
TOKENIZER_SHA256 = "8f9f37ca37fdc4f5fd36d5cf4d3b0e8392edb4e894fd10cc0d70b4957c8633cf"
DEFAULT_INFERENCE_CONFIG = (
    Path(__file__).resolve().parents[1]
    / "models/deepseek-v4-flash-0731/inference_config.json"
)

_QUALIFIED_REFERENCE_OWNERS = {
    "BIASED_TOPK_ROUTE": "runtime.reference.selection.biased_topk_route_indices",
    "BF16_LINEAR": "runtime.reference.matrix.bf16_linear_bf16",
    "BINARY32_TO_BF16": ("runtime.reference.conversion.binary32_tensor_to_bf16_rne"),
    "CONFIDENCE_SCORE": "runtime.reference.confidence.confidence_score_bf16",
    "COMPRESS_KV_WRITE": ("runtime.reference.compressed_kv.compressed_kv_write_bf16"),
    "COMPRESS_POOL": "runtime.reference.compression_pool.compress_pool_f32",
    "COMPRESS_PROJECT": "runtime.reference.compression.compress_project_bf16",
    "COMPRESS_STATE_UPDATE": (
        "runtime.reference.compression_state.compress_state_update_f32"
    ),
    "COMPRESSED_KV_VALID_VIEW": (
        "runtime.reference.compressed_kv.compressed_kv_valid_view_bf16"
    ),
    "COMPRESSED_DENSE_INDEX": "runtime.reference.indexing.compressed_dense_indices",
    "DSPARK_NOISE_EMBED": "runtime.reference.structural.dspark_noise_embed_bf16",
    "DSPARK_WINDOW_INDEX": "runtime.reference.indexing.dspark_window_indices",
    "EXPERT_DISPATCH": ("runtime.reference.dispatch.dispatch_routed_experts_bf16"),
    "EXPERT_REDUCE": ("runtime.reference.dispatch.reduce_expert_outputs_bf16"),
    "FP4_QDQ": "runtime.reference.quantization.fp4_qdq_bf16",
    "FP8_QDQ": "runtime.reference.quantization.fp8_qdq_bf16",
    "FP8_LINEAR": "runtime.reference.matrix.dense_fp8_linear_bf16",
    "GROUPED_OUTPUT_PROJECT": (
        "runtime.reference.grouped_output.grouped_output_project_bf16"
    ),
    "HADAMARD_ROTATE": "runtime.reference.hadamard.hadamard_rotate_128_bf16",
    "HASH_ROUTE": "runtime.reference.lookup.hash_route_indices",
    "HC_EXPAND": "runtime.reference.structural.hc_expand_bf16",
    "HC_HEAD": "runtime.reference.hc_head.hc_head_bf16",
    "HC_PRE": "runtime.reference.hyper_connection.hc_pre_bf16",
    "HC_POST": "runtime.reference.vector.hc_post_bf16",
    "HEAD_RMS_NORM": "runtime.reference.normalization.head_rms_norm_bf16",
    "INDEX_SCORE": "runtime.reference.index_score.index_score_bf16",
    "INDEX_TOPK": "runtime.reference.selection.index_topk_indices",
    "RMS_NORM": "runtime.reference.normalization.rms_norm_bf16",
    "ROPE_APPLY": "runtime.reference.rope.rope_apply_bf16",
    "ROPE_INVERSE": "runtime.reference.rope.rope_inverse_bf16",
    "ROUTER_SCORE": "runtime.reference.routing.router_score_bf16",
    "ROUTER_WEIGHT_NORMALIZE": (
        "runtime.reference.routing.normalize_routed_weight_codes"
    ),
    "SAMPLE": "runtime.reference.sampling.deepseek_v4_sample_binary32",
    "SPARSE_ATTENTION": ("runtime.reference.sparse_attention.sparse_attention_bf16"),
    "SQRT_SOFTPLUS": (
        "runtime.reference.sqrt_softplus.sqrt_softplus_router_binary32"
    ),
    "MXFP4_SWIGLU": "runtime.reference.swiglu.mxfp4_swiglu_bf16",
    "FP8_SWIGLU": "runtime.reference.swiglu.fp8_swiglu_bf16",
    "TARGET_HIDDEN_CAPTURE": ("runtime.reference.vector.target_hidden_capture_bf16"),
    "TOKEN_EMBED": "runtime.reference.lookup.bf16_token_embedding",
    "WINDOW_INDEX": "runtime.reference.indexing.window_indices",
}


class DeepSeekV4GraphError(RuntimeError):
    """Raised when graph coverage is incomplete or source-inconsistent."""


@dataclass(frozen=True)
class OperatorRequirement:
    kind: str
    source_anchor: str
    semantic_summary: str
    lowering_class: str
    cost_class: str
    state_class: str

    def to_dict(self) -> dict[str, Any]:
        reference_owner = _QUALIFIED_REFERENCE_OWNERS.get(
            self.kind, f"compiler.reference.deepseek_v4.{self.kind.lower()}"
        )
        return {
            "cost_class": self.cost_class,
            "kind": self.kind,
            "lowering_class": self.lowering_class,
            "reference_owner": reference_owner,
            "reference_status": (
                "implemented_unit_qualified"
                if self.kind in _QUALIFIED_REFERENCE_OWNERS
                else "pending_implementation"
            ),
            "rtl_status": "pending_implementation",
            "semantic_spec_status": "mapped_to_pinned_official_source",
            "semantic_summary": self.semantic_summary,
            "service_engine_status": "pending_implementation",
            "source_anchor": self.source_anchor,
            "state_class": self.state_class,
        }


def _op(
    kind: str,
    anchor: str,
    summary: str,
    lowering: str,
    cost: str,
    state: str = "stateless",
) -> OperatorRequirement:
    return OperatorRequirement(kind, anchor, summary, lowering, cost, state)


_OPERATORS = (
    _op(
        "TOKEN_EMBED",
        "inference/model.py:ParallelEmbedding.forward",
        "Lookup token rows and combine vocabulary-parallel partial embeddings.",
        "ROM_LOOKUP",
        "memory.embedding_lookup",
    ),
    _op(
        "HC_EXPAND",
        "inference/model.py:Transformer.forward",
        "Replicate the embedding into hc_mult architectural hidden streams.",
        "STATE_WRITE",
        "vector.copy_expand",
    ),
    _op(
        "HC_PRE",
        "inference/model.py:Block.hc_pre;inference/kernel.py:hc_split_sinkhorn",
        "FP32-normalize, project, split pre/post/comb fields, run fixed-iteration Sinkhorn, and reduce HC streams.",
        "MHC_PROJECT",
        "mhc.fp32_sinkhorn",
    ),
    _op(
        "RMS_NORM",
        "inference/model.py:RMSNorm.forward",
        "FP32 RMS reduction and reciprocal square root followed by learned weight and architectural conversion.",
        "RMSNORM",
        "vector.rmsnorm",
    ),
    _op(
        "HEAD_RMS_NORM",
        "inference/model.py:Attention.forward",
        "Unweighted per-head BF16 square, mean conversion, epsilon add, reciprocal square root, and pointwise normalization after query expansion.",
        "RMSNORM",
        "vector.head_rmsnorm",
    ),
    _op(
        "FP8_LINEAR",
        "inference/model.py:linear;inference/kernel.py:fp8_gemm",
        "Dynamic per-128 activation quantization and block-scaled FP8 E4M3FN matrix contraction with FP32 corrected accumulation.",
        "MATMUL_DENSE",
        "matrix.fp8_block_scaled",
    ),
    _op(
        "BF16_LINEAR",
        "inference/model.py:linear",
        "Bias-free BF16 matrix contraction with exact products, increasing-K binary32 RNE accumulation, and one BF16 output conversion.",
        "MATMUL_DENSE",
        "matrix.bf16",
    ),
    _op(
        "ROPE_APPLY",
        "inference/model.py:apply_rotary_emb;inference/model.py:precompute_freqs_cis",
        "Apply the pinned YaRN/base complex rotary transform to declared rope dimensions.",
        "ROPE",
        "vector.rope",
    ),
    _op(
        "ROPE_INVERSE",
        "inference/model.py:apply_rotary_emb",
        "Apply conjugate rotary transform to the sparse-attention output.",
        "ROPE",
        "vector.rope_inverse",
    ),
    _op(
        "FP8_QDQ",
        "inference/kernel.py:act_quant_kernel",
        "Apply the pinned block-64 binary32 1e-4 floor, bit-ceiling E8M0 scale, E4M3FN RNE/clamp, and in-place BF16 reconstruction to the 448-value non-RoPE KV slice.",
        "CONVERT",
        "numeric.fp8_qdq",
    ),
    _op(
        "FP4_QDQ",
        "inference/kernel.py:fp4_quant_kernel",
        "Apply the block-32 6*2^-126 amax floor, binary32 bit-ceiling power-of-two scale, E2M1 RNE/clamp, and in-place BF16 reconstruction.",
        "CONVERT",
        "numeric.fp4_qdq",
    ),
    _op(
        "HADAMARD_ROTATE",
        "inference/model.py:rotate_activation",
        "Apply seven ascending-stride binary32 Sylvester butterfly stages, multiply once by binary32 0x3db504f3, and convert once to BF16 before indexer FP4 quantization.",
        "CONVERT",
        "vector.hadamard",
    ),
    _op(
        "WINDOW_INDEX",
        "inference/model.py:get_window_topk_idxs",
        "Construct causal circular-window indices for prefill or decode.",
        "GATHER",
        "index.window",
    ),
    _op(
        "KV_WINDOW_WRITE",
        "inference/model.py:Attention.forward",
        "Write current KV into the circular window cache at the pinned slot; target transaction semantics remain open.",
        "KV_COMMIT",
        "state.kv_window_write",
        "mutable_kv",
    ),
    _op(
        "COMPRESS_PROJECT",
        "inference/model.py:Compressor.forward",
        "Project hidden state into KV candidates and learned compression scores.",
        "MATMUL_DENSE",
        "matrix.compressor_projection",
    ),
    _op(
        "COMPRESS_POOL",
        "inference/model.py:Compressor.forward;inference/model.py:Compressor.overlap_transform",
        "Apply deterministic per-dimension stable softmax and weighted reduction to a complete ratio-derived candidate group.",
        "COMPRESS",
        "attention.compression_pool",
    ),
    _op(
        "BINARY32_TO_BF16",
        "inference/model.py:Compressor.forward:kv.to(dtype)",
        "Convert each finite pooled binary32 KV value once to BF16 with round-to-nearest, ties-to-even before RMS normalization.",
        "CONVERT",
        "numeric.binary32_to_bf16",
    ),
    _op(
        "COMPRESS_STATE_UPDATE",
        "inference/model.py:Compressor.forward",
        "Add FP32 positional scores, update raw incomplete KV/score windows transactionally, and emit complete ratio-derived pooling groups.",
        "KV_PREPARE",
        "state.compressor_prepare",
        "mutable_compressor",
    ),
    _op(
        "COMPRESS_KV_WRITE",
        "inference/model.py:Compressor.forward",
        "Advance the session-bound compressor cursor on every processed span and commit a complete normalized/rotated compressed KV entry only at its ratio-derived boundary.",
        "KV_COMMIT",
        "state.compressed_kv_write",
        "mutable_kv",
    ),
    _op(
        "COMPRESSED_KV_VALID_VIEW",
        "inference/model.py:Compressor.forward;inference/model.py:Indexer.forward;inference/model.py:Attention.forward",
        "Validate the active session/cursor and expose only the immutable contiguous committed prefix of a compressed-KV state.",
        "STATE_VIEW",
        "state.compressed_kv_valid_view",
        "mutable_kv",
    ),
    _op(
        "ATTENTION_KV_VIEW",
        "inference/model.py:Attention.forward;inference/model.py:DSparkBlock.forward",
        "Materialize the exact prefill or decode KV row space seen by sparse attention from current KV, committed circular-window state, and an optional valid compressed prefix.",
        "STATE_VIEW",
        "state.attention_kv_view",
        "mutable_kv",
    ),
    _op(
        "INDEX_SCORE",
        "inference/model.py:Indexer.forward",
        "Form rotated Q/K index scores, ReLU them, apply learned head weights, and reduce heads.",
        "INDEX_SCAN",
        "attention.index_score",
    ),
    _op(
        "INDEX_TOPK",
        "inference/model.py:Indexer.forward",
        "Apply the BF16 causal mask and deterministic score-descending/index-ascending top-k to compressed positions.",
        "TOPK",
        "index.topk512",
    ),
    _op(
        "COMPRESSED_DENSE_INDEX",
        "inference/model.py:get_compress_topk_idxs",
        "Enumerate all causally complete ratio-128 compressed entries with the window offset.",
        "GATHER",
        "index.compressed_dense",
    ),
    _op(
        "SPARSE_ATTENTION",
        "inference/kernel.py:sparse_attn_kernel",
        "Gather selected KV, compute scaled QK, online stable softmax with attention sink, and AV reduction.",
        "ATTEND",
        "attention.sparse_online_softmax",
    ),
    _op(
        "GROUPED_OUTPUT_PROJECT",
        "inference/model.py:Attention.forward",
        "Apply per-group low-rank output-a projection with the pinned group reshape.",
        "MATMUL_DENSE",
        "matrix.grouped_output",
    ),
    _op(
        "HC_POST",
        "inference/model.py:Block.hc_post",
        "Combine branch output with all residual HC streams using post and Sinkhorn combination coefficients.",
        "MHC_COMBINE",
        "mhc.combine",
    ),
    _op(
        "ROUTER_SCORE",
        "inference/model.py:Gate.forward",
        "Exactly widen BF16 hidden state and router weights, then project with increasing-K binary32 RNE accumulation.",
        "ROUTER_SCORE",
        "routing.score",
    ),
    _op(
        "SQRT_SOFTPLUS",
        "inference/model.py:Gate.forward",
        "Apply softplus followed by square root to obtain original routing scores.",
        "EXPERT_WEIGHT",
        "vector.sqrt_softplus",
    ),
    _op(
        "HASH_ROUTE",
        "inference/model.py:Gate.forward",
        "Look up six checkpoint-pinned expert IDs from the input token ID.",
        "HASH_ROUTE",
        "routing.hash_lookup",
    ),
    _op(
        "BIASED_TOPK_ROUTE",
        "inference/model.py:Gate.forward",
        "Add FP32 selection-only bias with one RNE rounding and select six experts by deterministic score-descending/index-ascending order.",
        "TOPK",
        "routing.topk6",
    ),
    _op(
        "ROUTER_WEIGHT_NORMALIZE",
        "inference/model.py:Gate.forward",
        "Gather unbiased FP32 scores, normalize with the canonical selected-slot tree, and apply the FP32 route scale.",
        "EXPERT_WEIGHT",
        "routing.weight_normalize",
    ),
    _op(
        "EXPERT_DISPATCH",
        "inference/model.py:MoE.forward",
        "Build deterministic token/top-slot groups for selected routed experts.",
        "LOOP",
        "routing.dispatch",
    ),
    _op(
        "MXFP4_SWIGLU",
        "inference/model.py:Expert.forward;inference/kernel.py:fp4_gemm;inference/convert.py:FP4_TABLE",
        "Execute routed w1/w3, pinned clamp, SiLU product, route weighting, and w2 with MXFP4 weights.",
        "MATMUL_ROUTED",
        "matrix.mxfp4_swiglu",
    ),
    _op(
        "FP8_SWIGLU",
        "inference/model.py:Expert.forward;inference/kernel.py:fp8_gemm",
        "Execute shared w1/w3, pinned clamp, SiLU product, and w2 with block-scaled FP8 weights.",
        "MATMUL_DENSE",
        "matrix.fp8_swiglu",
    ),
    _op(
        "EXPERT_REDUCE",
        "inference/model.py:MoE.forward",
        "Preserve every routed slot, reduce duplicate slots then ascending logical experts, add the shared expert last, and convert once to BF16.",
        "REDUCE",
        "routing.expert_reduce",
    ),
    _op(
        "HC_HEAD",
        "inference/model.py:Block.hc_head",
        "Compute sigmoid HC head weights and reduce HC streams into one hidden vector.",
        "MHC_COMBINE",
        "mhc.head",
    ),
    _op(
        "LM_HEAD",
        "inference/model.py:ParallelHead.forward",
        "Project FP32 hidden state to the untied BF16 vocabulary head and gather vocabulary partitions.",
        "MATMUL_DENSE",
        "matrix.vocabulary_head",
    ),
    _op(
        "SAMPLE",
        "inference/model.py:sample",
        "Apply temperature and the declared Gumbel-max or zero-temperature argmax policy.",
        "CONTROL",
        "control.sampling",
    ),
    _op(
        "TARGET_HIDDEN_CAPTURE",
        "inference/model.py:Transformer.forward",
        "Mean HC streams at declared target layers and retain them for DSpark projection.",
        "STATE_WRITE",
        "vector.target_hidden_capture",
    ),
    _op(
        "DSPARK_MAIN_PROJECT",
        "inference/model.py:DSparkBlock.forward_embed",
        "Concatenate captured main hiddens, apply FP8 projection, and RMS-normalize DSpark conditioning.",
        "MATMUL_DENSE",
        "matrix.dspark_main_project",
    ),
    _op(
        "DSPARK_NOISE_EMBED",
        "inference/model.py:DSparkBlock.forward_embed",
        "Construct the five-token noise block, preserve token zero, embed, and HC-expand it.",
        "ROM_LOOKUP",
        "memory.dspark_noise_embedding",
    ),
    _op(
        "DSPARK_PREFILL_KV",
        "inference/model.py:DSparkAttention.forward",
        "During prefill, derive and commit each DSpark stage's main-model window KV without executing its block.",
        "KV_COMMIT",
        "state.dspark_prefill_kv",
        "mutable_kv",
    ),
    _op(
        "DSPARK_WINDOW_INDEX",
        "inference/model.py:get_dspark_topk_idxs",
        "Combine the causal main window with the five current draft positions.",
        "GATHER",
        "index.dspark_window",
    ),
    _op(
        "MARKOV_AUTOREGRESSIVE_LOOP",
        "inference/model.py:DSparkBlock.forward_head",
        "Run five ordered Markov embedding/head additions and token samples, carrying each sampled token forward.",
        "LOOP",
        "control.dspark_markov_loop",
    ),
    _op(
        "CONFIDENCE_SCORE",
        "inference/model.py:DSparkConfidenceHead.forward",
        "Concatenate DSpark hidden and Markov embeddings and project an FP32 confidence score per draft token.",
        "MATMUL_DENSE",
        "matrix.dspark_confidence",
    ),
)

OPERATOR_CATALOG = {item.kind: item for item in _OPERATORS}


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    kind: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    phases: tuple[str, ...]
    guard: str | None
    optional_inputs: tuple[str, ...]
    optional_output_guards: tuple[tuple[str, str], ...]
    predicate_outputs: tuple[str, ...]
    attributes: dict[str, Any]
    state_reads: tuple[str, ...]
    state_writes: tuple[str, ...]
    tensor_roles: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "attributes": self.attributes,
            "id": self.node_id,
            "inputs": list(self.inputs),
            "kind": self.kind,
            "guard": self.guard,
            "optional_inputs": list(self.optional_inputs),
            "optional_output_guards": dict(self.optional_output_guards),
            "outputs": list(self.outputs),
            "phases": list(self.phases),
            "predicate_outputs": list(self.predicate_outputs),
            "state_reads": list(self.state_reads),
            "state_writes": list(self.state_writes),
            "tensor_roles": list(self.tensor_roles),
        }


class _GraphBuilder:
    def __init__(self) -> None:
        self.nodes: list[GraphNode] = []
        self.node_ids: set[str] = set()
        self.values: set[str] = {
            "request.input_ids",
            "request.session_ids",
            "request.start_pos",
        }
        self.value_phases: dict[str, frozenset[str]] = {
            "request.input_ids": frozenset({"prefill", "decode"}),
            "request.session_ids": frozenset({"prefill", "decode"}),
            "request.start_pos": frozenset({"prefill", "decode"}),
        }
        self.value_guards: dict[str, str | None] = {
            value: None for value in self.values
        }
        self.predicate_values: set[str] = set()

    def add(
        self,
        node_id: str,
        kind: str,
        inputs: tuple[str, ...],
        output_names: tuple[str, ...] = ("output",),
        *,
        phases: tuple[str, ...] = ("prefill", "decode"),
        guard: str | None = None,
        optional_inputs: tuple[str, ...] = (),
        optional_output_guards: dict[str, str] | None = None,
        predicate_outputs: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
        state_reads: tuple[str, ...] = (),
        state_writes: tuple[str, ...] = (),
        tensor_roles: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        if node_id in self.node_ids:
            raise DeepSeekV4GraphError(f"duplicate graph node {node_id!r}")
        if kind not in OPERATOR_CATALOG:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has unknown kind {kind!r}"
            )
        missing_inputs = sorted(set(inputs) - self.values)
        if missing_inputs:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has unavailable inputs {missing_inputs}"
            )
        if guard is not None and guard not in self.values:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has unavailable guard {guard!r}"
            )
        if guard is not None and guard not in self.predicate_values:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} guard {guard!r} is not a declared predicate"
            )
        if guard is not None and self.value_guards[guard] is not None:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} guard {guard!r} is itself guarded; "
                "nested guards are unsupported"
            )
        if len(set(optional_inputs)) != len(optional_inputs) or not set(
            optional_inputs
        ).issubset(inputs):
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has invalid optional inputs"
            )
        if not phases or any(phase not in {"prefill", "decode"} for phase in phases):
            raise DeepSeekV4GraphError(f"graph node {node_id!r} has invalid phases")
        phase_set = frozenset(phases)
        invalid_phase_inputs = sorted(
            value
            for value in inputs
            if not phase_set.issubset(self.value_phases[value])
        )
        if invalid_phase_inputs:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} consumes phase-unavailable values "
                f"{invalid_phase_inputs}"
            )
        if guard is not None and not phase_set.issubset(self.value_phases[guard]):
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} consumes a phase-unavailable guard"
            )
        guarded_inputs = {
            value: self.value_guards[value]
            for value in inputs
            if self.value_guards[value] is not None
        }
        for value, value_guard in guarded_inputs.items():
            if guard == value_guard:
                continue
            if value not in optional_inputs or value_guard not in inputs:
                raise DeepSeekV4GraphError(
                    f"graph node {node_id!r} consumes guarded value {value!r} "
                    "without the same execution guard or an explicit optional "
                    "input plus its guard"
                )
        for value in optional_inputs:
            if self.value_guards[value] is None:
                raise DeepSeekV4GraphError(
                    f"graph node {node_id!r} marks unguarded value {value!r} optional"
                )
        if (
            type(output_names) is not tuple
            or not output_names
            or any(type(name) is not str or not name for name in output_names)
            or len(set(output_names)) != len(output_names)
        ):
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has invalid or duplicate output names"
            )
        if (
            type(predicate_outputs) is not tuple
            or any(type(name) is not str for name in predicate_outputs)
            or len(set(predicate_outputs)) != len(predicate_outputs)
            or not set(predicate_outputs).issubset(output_names)
        ):
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has invalid predicate outputs"
            )
        if guard is not None and predicate_outputs:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} cannot produce predicates under a guard"
            )
        outputs = tuple(f"{node_id}.{name}" for name in output_names)
        if set(outputs) & self.values:
            raise DeepSeekV4GraphError(f"graph node {node_id!r} redefines a value")
        output_by_name = dict(zip(output_names, outputs, strict=True))
        resolved_predicate_outputs = tuple(
            output_by_name[name] for name in predicate_outputs
        )
        predicate_output_set = set(resolved_predicate_outputs)
        if optional_output_guards is not None and (
            type(optional_output_guards) is not dict
            or any(
                type(name) is not str or type(output_guard) is not str
                for name, output_guard in optional_output_guards.items()
            )
        ):
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} has invalid optional-output guards"
            )
        resolved_output_guards: dict[str, str] = {}
        for output_name, raw_guard in (optional_output_guards or {}).items():
            if output_name not in output_by_name:
                raise DeepSeekV4GraphError(
                    f"graph node {node_id!r} guards unknown output {output_name!r}"
                )
            resolved_guard = output_by_name.get(raw_guard, raw_guard)
            if resolved_guard not in self.values and resolved_guard not in outputs:
                raise DeepSeekV4GraphError(
                    f"graph node {node_id!r} has unavailable output guard {raw_guard!r}"
                )
            resolved_output_guards[output_by_name[output_name]] = resolved_guard
        if guard is not None and resolved_output_guards:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} cannot combine a node guard with "
                "per-output guards"
            )
        guarded_outputs = set(resolved_output_guards)
        for output, output_guard in resolved_output_guards.items():
            if output == output_guard:
                raise DeepSeekV4GraphError(
                    f"graph node {node_id!r} output {output!r} cannot guard itself"
                )
            if output_guard in outputs:
                if output_guard in guarded_outputs:
                    relationship = (
                        "circularly guarded"
                        if resolved_output_guards[output_guard] == output
                        else "itself guarded"
                    )
                    raise DeepSeekV4GraphError(
                        f"graph node {node_id!r} output guard {output_guard!r} "
                        f"is {relationship}"
                    )
                if output_guard not in predicate_output_set:
                    raise DeepSeekV4GraphError(
                        f"graph node {node_id!r} sibling output guard "
                        f"{output_guard!r} is not a declared predicate"
                    )
            else:
                if output_guard not in self.predicate_values:
                    raise DeepSeekV4GraphError(
                        f"graph node {node_id!r} output guard {output_guard!r} "
                        "is not a declared predicate"
                    )
                if self.value_guards[output_guard] is not None:
                    raise DeepSeekV4GraphError(
                        f"graph node {node_id!r} output guard {output_guard!r} "
                        "is itself guarded"
                    )
                if not phase_set.issubset(self.value_phases[output_guard]):
                    raise DeepSeekV4GraphError(
                        f"graph node {node_id!r} consumes a phase-unavailable "
                        "output guard"
                    )
        if guarded_outputs & predicate_output_set:
            raise DeepSeekV4GraphError(
                f"graph node {node_id!r} cannot guard a predicate output"
            )
        node_output_guards = {output: guard for output in outputs if guard is not None}
        node_output_guards.update(resolved_output_guards)
        node = GraphNode(
            node_id=node_id,
            kind=kind,
            inputs=inputs,
            outputs=outputs,
            phases=phases,
            guard=guard,
            optional_inputs=optional_inputs,
            optional_output_guards=tuple(sorted(resolved_output_guards.items())),
            predicate_outputs=resolved_predicate_outputs,
            attributes=attributes or {},
            state_reads=state_reads,
            state_writes=state_writes,
            tensor_roles=tensor_roles,
        )
        self.nodes.append(node)
        self.node_ids.add(node_id)
        self.values.update(outputs)
        self.value_phases.update({output: phase_set for output in outputs})
        self.value_guards.update(
            {output: node_output_guards.get(output) for output in outputs}
        )
        self.predicate_values.update(resolved_predicate_outputs)
        return outputs


def _fp8_roles(base: str) -> tuple[str, str]:
    return (f"{base}.weight", f"{base}.scale")


def _rms_norm_attributes(width: int) -> dict[str, Any]:
    if width not in {128, 512, 1024, 4096}:
        raise DeepSeekV4GraphError(f"unsupported RMS_NORM width {width}")
    return {
        "checkpoint_weight_dtype": "bf16",
        "epsilon": 1e-6,
        "epsilon_binary32": "0x358637bd",
        "input_dtype": "bf16",
        "intermediate_overflow": "poison",
        "operation_rounding": "binary32_rne_each_operation",
        "output_dtype": "bf16",
        "output_zero": "canonical_positive",
        "reduction_tree": "num_6_1_balanced_binary32_rne",
        "rsqrt_rounding": "correct_binary32_rne",
        "subnormal_policy": "preserve",
        "weight_compute_dtype": "binary32_exact_bf16_widen",
        "width": width,
    }


def _head_rms_norm_attributes() -> dict[str, Any]:
    return {
        "epsilon": 1e-6,
        "epsilon_add_rounding": "bf16_rne",
        "epsilon_bf16": "0x3586",
        "head_dim": 512,
        "input_dtype": "bf16",
        "intermediate_overflow": "poison",
        "mean_conversion": "binary32_rne_divide_then_bf16_rne",
        "output_dtype": "bf16",
        "output_zero": "canonical_positive",
        "pointwise_multiply_rounding": "bf16_rne",
        "reduction_tree": "num_6_1_balanced_binary32_rne",
        "rsqrt_rounding": "correct_bf16_rne",
        "square_rounding": "bf16_rne",
        "subnormal_policy": "preserve",
    }


def _bf16_linear_attributes() -> dict[str, Any]:
    return {
        "accumulation_order": "increasing_reduction_index",
        "accumulation_rounding": "binary32_rne_each_fused_product_add",
        "accumulator_dtype": "binary32",
        "bias": "none",
        "checkpoint_weight_dtype": "bf16",
        "in_features": 4096,
        "input_dtype": "bf16",
        "intermediate_overflow": "poison",
        "out_features": 64,
        "output_dtype": "bf16",
        "output_rounding": "bf16_rne_once",
        "output_zero": "canonical_positive",
        "product": "exact_bf16_product",
        "subnormal_policy": "preserve",
    }


def _router_score_attributes() -> dict[str, Any]:
    return {
        "accumulation_order": "increasing_reduction_index",
        "accumulation_rounding": "binary32_rne_each_fused_product_add",
        "accumulator_dtype": "binary32",
        "bias": "none",
        "checkpoint_weight_dtype": "bf16",
        "experts": 256,
        "in_features": 4096,
        "input_compute_dtype": "binary32_exact_bf16_widen",
        "input_dtype": "bf16",
        "intermediate_overflow": "poison",
        "output_dtype": "binary32",
        "product": "exact_bf16_product",
        "subnormal_policy": "preserve",
        "weight_compute_dtype": "binary32_exact_bf16_widen",
    }


def _expert_reduce_attributes() -> dict[str, Any]:
    return {
        "distinct_expert_order": "ascending_logical_expert_id",
        "duplicate_slot_order": "ascending_selected_slot",
        "duplicate_slot_policy": "preserve_all",
        "intermediate_overflow": "poison",
        "output_dtype": "bf16",
        "output_rounding": "bf16_rne_once",
        "output_saturation": "sticky_count",
        "output_zero": "canonical_positive",
        "reduction_tree": "num_6_1_balanced_binary32_rne",
        "routed_alignment": "expert_dispatch_groups_one_to_one",
        "routed_input_dtype": "bf16",
        "shared_add_order": "after_routed_reduction",
        "shared_add_rounding": "binary32_rne_once",
        "shared_input_dtype": "bf16",
        "subnormal_policy": "preserve",
    }


def _confidence_score_attributes() -> dict[str, Any]:
    return {
        "accumulation_order": "increasing_reduction_index",
        "accumulation_rounding": "binary32_rne_each_fused_product_add",
        "accumulator_dtype": "binary32",
        "bias": "none",
        "block_size": 5,
        "checkpoint_weight_dtype": "bf16",
        "concatenation_order": "hidden_then_markov",
        "hidden_input_dtype": "bf16",
        "hidden_width": 4096,
        "input_compute_dtype": "binary32_exact_bf16_widen",
        "input_width": 4352,
        "intermediate_overflow": "poison",
        "markov_input_dtype": "bf16",
        "markov_width": 256,
        "output_count": 1,
        "output_dtype": "binary32",
        "output_zero": "canonical_positive",
        "product": "exact_bf16_product",
        "subnormal_policy": "preserve",
        "weight_compute_dtype": "binary32_exact_bf16_widen",
    }


def _compress_project_attributes(
    *,
    ratio: int,
    output_features: int,
    projection_scope: str,
) -> dict[str, Any]:
    expected_output_features = {
        ("indexer", 4): 256,
        ("main", 4): 1024,
        ("main", 128): 512,
    }
    expected = expected_output_features.get((projection_scope, ratio))
    if expected is None or output_features != expected:
        raise DeepSeekV4GraphError(
            "unsupported COMPRESS_PROJECT profile "
            f"scope={projection_scope!r}, ratio={ratio}, "
            f"output_features={output_features}"
        )
    return {
        "accumulation_order": "increasing_reduction_index",
        "accumulation_rounding": "binary32_rne_each_fused_product_add",
        "accumulator_dtype": "binary32",
        "activation_quantization": "none",
        "bias": "none",
        "checkpoint_weight_dtype": "bf16",
        "in_features": 4096,
        "input_compute_dtype": "binary32_exact_bf16_widen",
        "input_dtype": "bf16",
        "intermediate_overflow": "poison",
        "output_conversion": "none",
        "output_dtypes": {"kv": "binary32", "scores": "binary32"},
        "output_features": output_features,
        "output_zero": "canonical_positive",
        "overlap": ratio == 4,
        "product": "exact_bf16_product",
        "projection_arithmetic": "independent",
        "projection_order": "kv_then_gate",
        "projection_scope": projection_scope,
        "ratio": ratio,
        "subnormal_policy": "preserve",
        "weight_compute_dtype": "binary32_exact_bf16_widen",
        "weight_layout": "output_by_input",
    }


def _compress_state_attributes(
    *,
    ratio: int,
    head_dim: int,
    projection_scope: str,
) -> dict[str, Any]:
    expected = {
        ("indexer", 4): 128,
        ("main", 4): 512,
        ("main", 128): 512,
    }.get((projection_scope, ratio))
    if expected is None or head_dim != expected:
        raise DeepSeekV4GraphError(
            "unsupported COMPRESS_STATE_UPDATE profile "
            f"scope={projection_scope!r}, ratio={ratio}, head_dim={head_dim}"
        )
    overlap = ratio == 4
    return {
        "ape_checkpoint_dtype": "binary32",
        "ape_shape": [ratio, (2 if overlap else 1) * head_dim],
        "candidate_input_dtype": "binary32",
        "counter_scope": "logical_raw_state_reads_and_writes",
        "decode_sequence_length": 1,
        "head_dim": head_dim,
        "intermediate_overflow": "poison",
        "new_session_prefill": "reset_all_active_raw_slots_then_apply",
        "output": "optional_pool_kv_pool_scores_and_should_compress_predicate",
        "overlap": overlap,
        "positional_score_add_rounding": "binary32_rne",
        "projection_scope": projection_scope,
        "ratio": ratio,
        "session_identity": "per_active_batch_lowercase_sha256",
        "session_prefill_transition": "fresh_identity_reset_then_apply",
        "state_dtype": "binary32",
        "state_metadata": "session_id_next_position_monotonic_version",
        "state_slots": (2 if overlap else 1) * ratio,
        "state_transaction": "causal_validate_prepare_immutable_commit_target_adaptation",
    }


def _compress_pool_attributes(*, ratio: int, head_dim: int) -> dict[str, Any]:
    if (ratio, head_dim) not in {(4, 128), (4, 512), (128, 512)}:
        raise DeepSeekV4GraphError(
            f"unsupported COMPRESS_POOL profile ratio={ratio}, head_dim={head_dim}"
        )
    overlap = ratio == 4
    return {
        "candidate_count": 2 * ratio if overlap else ratio,
        "candidate_input_dtype": "binary32",
        "first_overlap_padding": (
            "positive_zero_kv_and_negative_infinity_score"
            if overlap
            else "not_applicable"
        ),
        "head_dim": head_dim,
        "intermediate_overflow": "poison",
        "maximum": "per_dimension_finite_binary32_numeric_value",
        "output_dtype": "binary32",
        "output_zero": "canonical_positive",
        "overlap": overlap,
        "probability_division_rounding": "binary32_rne",
        "predicate": "execute_only_when_compress_state_should_compress",
        "ratio": ratio,
        "reduction_tree": "num_6_1_balanced_binary32_rne",
        "score_exponential": "correctly_rounded_binary32",
        "score_subtraction_rounding": "binary32_rne",
        "subnormal_policy": "preserve",
        "weighted_value_multiply_rounding": "binary32_rne",
    }


def _binary32_to_bf16_attributes(*, head_dim: int) -> dict[str, Any]:
    if head_dim not in {128, 512}:
        raise DeepSeekV4GraphError(f"unsupported BINARY32_TO_BF16 width={head_dim}")
    return {
        "counter_scope": "logical_binary32_reads_and_bf16_writes",
        "finite_input_required": True,
        "finite_saturation": "sticky_count",
        "input_dtype": "binary32",
        "input_rank": 3,
        "intermediate_overflow": "poison",
        "output_dtype": "bf16",
        "output_zero": "canonical_positive",
        "predicate": "execute_only_when_compress_state_should_compress",
        "rounding": "round_to_nearest_ties_to_even_once",
        "subnormal_policy": "preserve_gradual_underflow",
        "transaction": "validate_prepare_atomic_immutable_commit",
        "width": head_dim,
    }


def _compress_kv_write_attributes(
    *,
    layer: int,
    ratio: int,
    scope: str,
    projection_scope: str,
    head_dim: int,
) -> dict[str, Any]:
    if (projection_scope, ratio, head_dim) not in {
        ("indexer", 4, 128),
        ("main", 4, 512),
        ("main", 128, 512),
    }:
        raise DeepSeekV4GraphError(
            "unsupported COMPRESS_KV_WRITE profile "
            f"scope={projection_scope!r}, ratio={ratio}, head_dim={head_dim}"
        )
    return {
        "cache_slot": "completed_absolute_position_floor_div_ratio",
        "committed_input_dtype": "bf16_after_normalize_position_transform_and_qdq",
        "decode_sequence_length": 1,
        "head_dim": head_dim,
        "kv_head_count": 1,
        "layer": layer,
        "new_session_prefill": "invalidate_then_commit_complete_prefix",
        "optional_payload": "present_exactly_when_should_compress",
        "retired_lane_identity": "preserved_tombstone_prevents_session_resurrection",
        "projection_scope": projection_scope,
        "ratio": ratio,
        "session_identity": "per_active_batch_lowercase_sha256",
        "session_reuse": "fresh_prefill_identity_not_retained_by_any_lane",
        "scope": scope,
        "state_metadata": "session_id_next_position_valid_prefix_monotonic_version",
        "state_transaction": "causal_valid_prefix_validate_prepare_immutable_commit_target_adaptation",
    }


def _compressed_kv_valid_view_attributes(
    *,
    ratio: int,
    projection_scope: str,
    head_dim: int,
) -> dict[str, Any]:
    if (projection_scope, ratio, head_dim) not in {
        ("indexer", 4, 128),
        ("main", 4, 512),
        ("main", 128, 512),
    }:
        raise DeepSeekV4GraphError(
            "unsupported COMPRESSED_KV_VALID_VIEW profile "
            f"scope={projection_scope!r}, ratio={ratio}, head_dim={head_dim}"
        )
    return {
        "capacity_rows_exposed": False,
        "head_dim": head_dim,
        "kv_head_count": 1,
        "output": "active_batch_contiguous_valid_prefix_only",
        "payload_dtype": "bf16",
        "projection_scope": projection_scope,
        "ratio": ratio,
        "session_identity": "per_active_batch_lowercase_sha256",
        "stale_invalid_payload": "never_exposed",
        "validation": "session_cursor_prefix_and_payload_before_immutable_view",
    }


def _attention_kv_view_attributes(
    *,
    ratio: int,
    dspark: bool,
) -> dict[str, Any]:
    if ratio not in {0, 4, 128}:
        raise DeepSeekV4GraphError(
            f"unsupported ATTENTION_KV_VIEW compression ratio {ratio}"
        )
    return {
        "compressed_offset": "current_sequence_length" if ratio else "not_applicable",
        "compression_ratio": ratio,
        "decode_layout": "committed_window_capacity_then_valid_compressed_prefix",
        "dspark": dspark,
        "output_dtype": "bf16",
        "prefill_layout": "current_full_kv_then_valid_compressed_prefix",
        "session_identity": "per_active_batch_lowercase_sha256",
        "status": "pending_reference_and_session_bound_window_state",
        "window_size": 128,
    }


def _index_score_attributes() -> dict[str, Any]:
    return {
        "candidate_axis": "may_be_empty",
        "finite_saturation": "sticky_count_at_each_bf16_boundary",
        "head_dim": 128,
        "head_reduction_order": "ascending_logical_head",
        "head_reduction_tree": "num_6_1_balanced_binary32_rne",
        "head_weight_input_dtype": "bf16",
        "head_weight_scale_binary32": "0x3c3504f3",
        "head_weight_scale_rounding": ("direct_binary32_factor_to_bf16_rne_once"),
        "heads": 64,
        "intermediate_overflow": "poison",
        "kv_input_dtype": "bf16",
        "mask_and_topk": "separate_index_topk_operator",
        "output_dtype": "bf16",
        "output_rounding": "bf16_rne_once",
        "output_zero": "canonical_positive",
        "qk_accumulation_order": "increasing_head_dimension",
        "qk_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
        "qk_accumulator_dtype": "binary32",
        "qk_output_rounding": "bf16_rne_once",
        "query_input_dtype": "bf16",
        "ratio": 4,
        "relu": "bf16_nonpositive_to_positive_zero",
        "score_weight_product_rounding": "direct_bf16_product_to_bf16_rne_once",
        "subnormal_policy": "preserve",
        "tensor_parallel_reduction": (
            "contiguous_logical_head_partitions_compose_global_tree"
        ),
    }


def _sparse_attention_attributes(ratio: int) -> dict[str, Any]:
    if ratio not in {0, 4, 128}:
        raise DeepSeekV4GraphError(
            f"unsupported sparse-attention compression ratio {ratio}"
        )
    return {
        "attention_sink_dtype": "binary32",
        "av_accumulation_order": "ascending_source_slot_within_each_block",
        "av_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
        "block_order": "ascending_64_slot_source_blocks",
        "block_size": 64,
        "counter_scope": ("logical_source_work_separates_valid_kv_reads_from_padding"),
        "duplicate_index_policy": "preserve_every_source_slot",
        "final_division_rounding": "binary32_rne",
        "finite_saturation": "sticky_count_at_final_bf16_boundary",
        "first_block_valid_policy": "at_least_one_valid_index_required",
        "head_dim": 512,
        "heads": 64,
        "index_dtype": "int32",
        "intermediate_overflow": "poison",
        "kv_input_dtype": "bf16",
        "kv_read_bytes_per_valid_slot": 1024,
        "online_denominator_update": ("separate_binary32_multiply_then_add"),
        "online_max": "maximum_by_finite_binary32_numeric_value",
        "online_rescale_exp": "correctly_rounded_binary32",
        "output_dtype": "bf16",
        "output_rounding": "bf16_rne_once",
        "output_zero": "canonical_positive",
        "padding_index": -1,
        "probability_dtype": "bf16",
        "probability_rounding": "binary32_to_bf16_rne_once_before_av",
        "qk_accumulation_order": "increasing_head_dimension",
        "qk_accumulation_rounding": ("binary32_rne_each_fused_product_add"),
        "qk_accumulator_dtype": "binary32",
        "query_input_dtype": "bf16",
        "ratio": ratio,
        "score_reduction_tree": "num_6_1_balanced_64_lane_binary32_rne",
        "score_scale_binary32": "0x3d3504f3",
        "score_scale_rounding": "binary32_rne_multiply",
        "sink_denominator_order": "after_all_selected_blocks",
        "sink_exp": "general_cr32_finite_overflow_poison",
        "subnormal_policy": "preserve",
        "tail_padding": "implicit_negative_one_to_64_slot_block",
    }


def _add_block_graph(
    graph: _GraphBuilder,
    hidden: str,
    *,
    scope: str,
    layer: int,
    ratio: int,
    hash_route: bool,
    dspark: bool = False,
    conditioning: str | None = None,
) -> str:
    root = f"{scope}.layer{layer:02d}"
    normal_phases = ("decode",) if dspark else ("prefill", "decode")
    if dspark:
        if conditioning is None:
            raise DeepSeekV4GraphError("DSpark block lacks main-model conditioning")
        graph.add(
            f"{root}.prefill_kv",
            "DSPARK_PREFILL_KV",
            (conditioning, "request.start_pos"),
            phases=("prefill",),
            attributes={"layer": layer, "window_size": 128},
            state_reads=(f"state.dspark.layer{layer}.window_kv",),
            state_writes=(f"state.dspark.layer{layer}.window_kv",),
            tensor_roles=(
                *_fp8_roles("attention.kv_projection"),
                "attention.kv_norm.weight",
            ),
        )
    attn_input, attn_post, attn_comb, attn_residual = graph.add(
        f"{root}.hc_attn_pre",
        "HC_PRE",
        (hidden,),
        ("branch", "post", "comb", "residual"),
        phases=normal_phases,
        attributes={"branch": "attention", "hc_mult": 4, "layer": layer},
        tensor_roles=(
            "hyper_connection.attn.base",
            "hyper_connection.attn.projection",
            "hyper_connection.attn.scale",
        ),
    )
    (attn_norm,) = graph.add(
        f"{root}.attn_norm",
        "RMS_NORM",
        (attn_input,),
        phases=normal_phases,
        attributes=_rms_norm_attributes(4096),
        tensor_roles=("block.attention_norm.weight",),
    )
    (q_rank,) = graph.add(
        f"{root}.query_a",
        "FP8_LINEAR",
        (attn_norm,),
        phases=normal_phases,
        attributes={"in_features": 4096, "out_features": 1024},
        tensor_roles=_fp8_roles("attention.query_a"),
    )
    (q_rank_norm,) = graph.add(
        f"{root}.query_norm",
        "RMS_NORM",
        (q_rank,),
        phases=normal_phases,
        attributes=_rms_norm_attributes(1024),
        tensor_roles=("attention.q_norm.weight",),
    )
    (query,) = graph.add(
        f"{root}.query_b",
        "FP8_LINEAR",
        (q_rank_norm,),
        phases=normal_phases,
        attributes={"heads": 64, "head_dim": 512},
        tensor_roles=_fp8_roles("attention.query_b"),
    )
    (query,) = graph.add(
        f"{root}.query_head_norm",
        "HEAD_RMS_NORM",
        (query,),
        phases=normal_phases,
        attributes=_head_rms_norm_attributes(),
    )
    (query,) = graph.add(
        f"{root}.query_rope",
        "ROPE_APPLY",
        (query, "request.start_pos"),
        phases=normal_phases,
        attributes={"inverse": False, "rope_dim": 64},
    )
    (kv,) = graph.add(
        f"{root}.kv_project",
        "FP8_LINEAR",
        (attn_norm,),
        phases=normal_phases,
        attributes={"in_features": 4096, "out_features": 512},
        tensor_roles=_fp8_roles("attention.kv_projection"),
    )
    (kv,) = graph.add(
        f"{root}.kv_norm",
        "RMS_NORM",
        (kv,),
        phases=normal_phases,
        attributes=_rms_norm_attributes(512),
        tensor_roles=("attention.kv_norm.weight",),
    )
    (kv,) = graph.add(
        f"{root}.kv_rope",
        "ROPE_APPLY",
        (kv, "request.start_pos"),
        phases=normal_phases,
        attributes={"inverse": False, "rope_dim": 64},
    )
    (kv,) = graph.add(
        f"{root}.kv_fp8_qdq",
        "FP8_QDQ",
        (kv,),
        phases=normal_phases,
        attributes={
            "block_size": 64,
            "dimensions": "non_rope",
            "inplace": True,
            "quantized_width": 448,
            "rope_width": 64,
            "scale_format": "ue8m0",
            "scale_storage": "e8m0",
        },
    )
    if dspark:
        (main_kv,) = graph.add(
            f"{root}.main_kv_project",
            "FP8_LINEAR",
            (conditioning,),
            phases=normal_phases,
            attributes={
                "in_features": 4096,
                "out_features": 512,
                "source": "dspark_conditioning",
            },
            tensor_roles=_fp8_roles("attention.kv_projection"),
        )
        (main_kv,) = graph.add(
            f"{root}.main_kv_norm",
            "RMS_NORM",
            (main_kv,),
            phases=normal_phases,
            attributes=_rms_norm_attributes(512),
            tensor_roles=("attention.kv_norm.weight",),
        )
        (main_kv,) = graph.add(
            f"{root}.main_kv_rope",
            "ROPE_APPLY",
            (main_kv, "request.start_pos"),
            phases=normal_phases,
            attributes={"inverse": False, "rope_dim": 64},
        )
        (main_kv,) = graph.add(
            f"{root}.main_kv_fp8_qdq",
            "FP8_QDQ",
            (main_kv,),
            phases=normal_phases,
            attributes={
                "block_size": 64,
                "dimensions": "non_rope",
                "inplace": True,
                "quantized_width": 448,
                "rope_width": 64,
                "scale_format": "ue8m0",
                "scale_storage": "e8m0",
            },
        )
    window_kind = "DSPARK_WINDOW_INDEX" if dspark else "WINDOW_INDEX"
    (window_indices,) = graph.add(
        f"{root}.window_indices",
        window_kind,
        ("request.start_pos",),
        phases=normal_phases,
        attributes={"draft_block_size": 5 if dspark else 0, "window_size": 128},
    )
    (window_kv_state,) = graph.add(
        f"{root}.window_kv_write",
        "KV_WINDOW_WRITE",
        (main_kv if dspark else kv, "request.start_pos"),
        ("committed_window",),
        phases=normal_phases,
        attributes={"layer": layer, "scope": scope, "window_size": 128},
        state_reads=(f"state.{scope}.layer{layer}.window_kv",),
        state_writes=(f"state.{scope}.layer{layer}.window_kv",),
    )
    attention_indices = window_indices
    compressed_kv_view: str | None = None
    if ratio:
        projected_compressed_kv, compression_scores = graph.add(
            f"{root}.compress_project",
            "COMPRESS_PROJECT",
            (attn_norm,),
            ("kv", "scores"),
            phases=normal_phases,
            attributes=_compress_project_attributes(
                ratio=ratio,
                output_features=1024 if ratio == 4 else 512,
                projection_scope="main",
            ),
            tensor_roles=(
                "attention.compressor.wkv.weight",
                "attention.compressor.wgate.weight",
            ),
        )
        pool_kv, pool_scores, should_compress = graph.add(
            f"{root}.compress_state",
            "COMPRESS_STATE_UPDATE",
            (
                projected_compressed_kv,
                compression_scores,
                "request.start_pos",
                "request.session_ids",
            ),
            ("pool_kv", "pool_scores", "should_compress"),
            phases=normal_phases,
            optional_output_guards={
                "pool_kv": "should_compress",
                "pool_scores": "should_compress",
            },
            predicate_outputs=("should_compress",),
            attributes=_compress_state_attributes(
                ratio=ratio,
                head_dim=512,
                projection_scope="main",
            ),
            state_reads=(f"state.{scope}.layer{layer}.compressor",),
            state_writes=(f"state.{scope}.layer{layer}.compressor",),
            tensor_roles=("attention.compressor.position_weight",),
        )
        (compressed_kv,) = graph.add(
            f"{root}.compress_pool",
            "COMPRESS_POOL",
            (pool_kv, pool_scores, should_compress),
            phases=normal_phases,
            guard=should_compress,
            attributes=_compress_pool_attributes(ratio=ratio, head_dim=512),
        )
        (compressed_kv,) = graph.add(
            f"{root}.compress_bf16",
            "BINARY32_TO_BF16",
            (compressed_kv, should_compress),
            phases=normal_phases,
            guard=should_compress,
            attributes=_binary32_to_bf16_attributes(head_dim=512),
        )
        (compressed_kv,) = graph.add(
            f"{root}.compress_norm",
            "RMS_NORM",
            (compressed_kv,),
            phases=normal_phases,
            guard=should_compress,
            attributes=_rms_norm_attributes(512),
            tensor_roles=("attention.compressor.norm.weight",),
        )
        (compressed_kv,) = graph.add(
            f"{root}.compress_rope",
            "ROPE_APPLY",
            (compressed_kv, "request.start_pos"),
            phases=normal_phases,
            guard=should_compress,
            attributes={"compressed": True, "inverse": False, "ratio": ratio},
        )
        (compressed_kv,) = graph.add(
            f"{root}.compress_fp8_qdq",
            "FP8_QDQ",
            (compressed_kv,),
            phases=normal_phases,
            guard=should_compress,
            attributes={
                "block_size": 64,
                "dimensions": "non_rope",
                "inplace": True,
                "quantized_width": 448,
                "rope_width": 64,
                "scale_format": "ue8m0",
                "scale_storage": "e8m0",
            },
        )
        (compressed_kv_state,) = graph.add(
            f"{root}.compress_kv_write",
            "COMPRESS_KV_WRITE",
            (
                compressed_kv,
                should_compress,
                "request.start_pos",
                "request.session_ids",
            ),
            ("committed_state",),
            phases=normal_phases,
            optional_inputs=(compressed_kv,),
            attributes=_compress_kv_write_attributes(
                layer=layer,
                ratio=ratio,
                scope=scope,
                projection_scope="main",
                head_dim=512,
            ),
            state_reads=(f"state.{scope}.layer{layer}.compressed_kv",),
            state_writes=(f"state.{scope}.layer{layer}.compressed_kv",),
        )
        (compressed_kv_view,) = graph.add(
            f"{root}.compress_kv_valid_view",
            "COMPRESSED_KV_VALID_VIEW",
            (compressed_kv_state, "request.session_ids"),
            phases=normal_phases,
            attributes=_compressed_kv_valid_view_attributes(
                ratio=ratio,
                projection_scope="main",
                head_dim=512,
            ),
        )
        if ratio == 4:
            (index_query,) = graph.add(
                f"{root}.index_query",
                "FP8_LINEAR",
                (q_rank_norm,),
                phases=normal_phases,
                attributes={"head_dim": 128, "heads": 64},
                tensor_roles=_fp8_roles("attention.indexer.query"),
            )
            (index_query,) = graph.add(
                f"{root}.index_query_rope",
                "ROPE_APPLY",
                (index_query, "request.start_pos"),
                phases=normal_phases,
                attributes={"inverse": False, "rope_dim": 64},
            )
            (index_query,) = graph.add(
                f"{root}.index_query_rotate",
                "HADAMARD_ROTATE",
                (index_query,),
                phases=normal_phases,
                attributes={
                    "arithmetic": "binary32_rne",
                    "butterfly_order": "ascending_stride_1_to_64",
                    "input_dtype": "bf16",
                    "normalization_scale_binary32": "0x3db504f3",
                    "output_dtype": "bf16",
                    "stages": 7,
                    "subnormal_policy": "preserve",
                    "width": 128,
                },
            )
            (index_query,) = graph.add(
                f"{root}.index_query_fp4",
                "FP4_QDQ",
                (index_query,),
                phases=normal_phases,
                attributes={"block_size": 32},
            )
            index_kv, index_scores = graph.add(
                f"{root}.index_compress_project",
                "COMPRESS_PROJECT",
                (attn_norm,),
                ("kv", "scores"),
                phases=normal_phases,
                attributes=_compress_project_attributes(
                    ratio=4,
                    output_features=256,
                    projection_scope="indexer",
                ),
                tensor_roles=(
                    "attention.indexer.compressor.wkv.weight",
                    "attention.indexer.compressor.wgate.weight",
                ),
            )
            index_pool_kv, index_pool_scores, index_should_compress = graph.add(
                f"{root}.index_compress_state",
                "COMPRESS_STATE_UPDATE",
                (
                    index_kv,
                    index_scores,
                    "request.start_pos",
                    "request.session_ids",
                ),
                ("pool_kv", "pool_scores", "should_compress"),
                phases=normal_phases,
                optional_output_guards={
                    "pool_kv": "should_compress",
                    "pool_scores": "should_compress",
                },
                predicate_outputs=("should_compress",),
                attributes=_compress_state_attributes(
                    ratio=4,
                    head_dim=128,
                    projection_scope="indexer",
                ),
                state_reads=(f"state.{scope}.layer{layer}.index_compressor",),
                state_writes=(f"state.{scope}.layer{layer}.index_compressor",),
                tensor_roles=("attention.indexer.compressor.position_weight",),
            )
            (index_kv,) = graph.add(
                f"{root}.index_compress_pool",
                "COMPRESS_POOL",
                (index_pool_kv, index_pool_scores, index_should_compress),
                phases=normal_phases,
                guard=index_should_compress,
                attributes=_compress_pool_attributes(ratio=4, head_dim=128),
            )
            (index_kv,) = graph.add(
                f"{root}.index_compress_bf16",
                "BINARY32_TO_BF16",
                (index_kv, index_should_compress),
                phases=normal_phases,
                guard=index_should_compress,
                attributes=_binary32_to_bf16_attributes(head_dim=128),
            )
            (index_kv,) = graph.add(
                f"{root}.index_compress_norm",
                "RMS_NORM",
                (index_kv,),
                phases=normal_phases,
                guard=index_should_compress,
                attributes=_rms_norm_attributes(128),
                tensor_roles=("attention.indexer.compressor.norm.weight",),
            )
            (index_kv,) = graph.add(
                f"{root}.index_kv_rotate",
                "HADAMARD_ROTATE",
                (index_kv,),
                phases=normal_phases,
                guard=index_should_compress,
                attributes={
                    "arithmetic": "binary32_rne",
                    "butterfly_order": "ascending_stride_1_to_64",
                    "input_dtype": "bf16",
                    "normalization_scale_binary32": "0x3db504f3",
                    "output_dtype": "bf16",
                    "stages": 7,
                    "subnormal_policy": "preserve",
                    "width": 128,
                },
            )
            (index_kv,) = graph.add(
                f"{root}.index_kv_fp4",
                "FP4_QDQ",
                (index_kv,),
                phases=normal_phases,
                guard=index_should_compress,
                attributes={"block_size": 32},
            )
            (index_kv_state,) = graph.add(
                f"{root}.index_compress_kv_write",
                "COMPRESS_KV_WRITE",
                (
                    index_kv,
                    index_should_compress,
                    "request.start_pos",
                    "request.session_ids",
                ),
                ("committed_state",),
                phases=normal_phases,
                optional_inputs=(index_kv,),
                attributes=_compress_kv_write_attributes(
                    layer=layer,
                    ratio=4,
                    scope=scope,
                    projection_scope="indexer",
                    head_dim=128,
                ),
                state_reads=(f"state.{scope}.layer{layer}.index_compressed_kv",),
                state_writes=(f"state.{scope}.layer{layer}.index_compressed_kv",),
            )
            (index_kv_view,) = graph.add(
                f"{root}.index_compress_kv_valid_view",
                "COMPRESSED_KV_VALID_VIEW",
                (index_kv_state, "request.session_ids"),
                phases=normal_phases,
                attributes=_compressed_kv_valid_view_attributes(
                    ratio=4,
                    projection_scope="indexer",
                    head_dim=128,
                ),
            )
            (head_weights,) = graph.add(
                f"{root}.index_head_weights",
                "BF16_LINEAR",
                (attn_norm,),
                phases=normal_phases,
                attributes=_bf16_linear_attributes(),
                tensor_roles=("attention.indexer.head_weights.weight",),
            )
            (index_score,) = graph.add(
                f"{root}.index_score",
                "INDEX_SCORE",
                (index_query, index_kv_view, head_weights),
                phases=normal_phases,
                attributes=_index_score_attributes(),
            )
            (attention_indices,) = graph.add(
                f"{root}.index_topk",
                "INDEX_TOPK",
                (index_score, window_indices, "request.start_pos"),
                phases=normal_phases,
                attributes={"top_k": 512},
            )
        else:
            (attention_indices,) = graph.add(
                f"{root}.compressed_dense_indices",
                "COMPRESSED_DENSE_INDEX",
                (window_indices, "request.start_pos"),
                phases=normal_phases,
                attributes={"ratio": ratio},
            )
    attention_kv_inputs = (
        main_kv if dspark else kv,
        window_kv_state,
        *((compressed_kv_view,) if compressed_kv_view is not None else ()),
        "request.start_pos",
        "request.session_ids",
    )
    (attention_kv,) = graph.add(
        f"{root}.attention_kv_view",
        "ATTENTION_KV_VIEW",
        attention_kv_inputs,
        phases=normal_phases,
        attributes=_attention_kv_view_attributes(ratio=ratio, dspark=dspark),
    )
    (attention_output,) = graph.add(
        f"{root}.sparse_attention",
        "SPARSE_ATTENTION",
        (query, attention_kv, attention_indices),
        phases=normal_phases,
        attributes=_sparse_attention_attributes(ratio),
        tensor_roles=("attention.sink",),
    )
    (attention_output,) = graph.add(
        f"{root}.output_inverse_rope",
        "ROPE_INVERSE",
        (attention_output, "request.start_pos"),
        phases=normal_phases,
        attributes={"rope_dim": 64},
    )
    (attention_output,) = graph.add(
        f"{root}.output_a",
        "GROUPED_OUTPUT_PROJECT",
        (attention_output,),
        phases=normal_phases,
        attributes={"groups": 8, "rank": 1024},
        tensor_roles=_fp8_roles("attention.output_a"),
    )
    (attention_output,) = graph.add(
        f"{root}.output_b",
        "FP8_LINEAR",
        (attention_output,),
        phases=normal_phases,
        attributes={"in_features": 8192, "out_features": 4096},
        tensor_roles=_fp8_roles("attention.output_b"),
    )
    (hidden,) = graph.add(
        f"{root}.hc_attn_post",
        "HC_POST",
        (attention_output, attn_residual, attn_post, attn_comb),
        phases=normal_phases,
        attributes={"branch": "attention", "hc_mult": 4},
    )

    ffn_input, ffn_post, ffn_comb, ffn_residual = graph.add(
        f"{root}.hc_ffn_pre",
        "HC_PRE",
        (hidden,),
        ("branch", "post", "comb", "residual"),
        phases=normal_phases,
        attributes={"branch": "ffn", "hc_mult": 4, "layer": layer},
        tensor_roles=(
            "hyper_connection.ffn.base",
            "hyper_connection.ffn.projection",
            "hyper_connection.ffn.scale",
        ),
    )
    (ffn_input,) = graph.add(
        f"{root}.ffn_norm",
        "RMS_NORM",
        (ffn_input,),
        phases=normal_phases,
        attributes=_rms_norm_attributes(4096),
        tensor_roles=("block.ffn_norm.weight",),
    )
    (router_scores,) = graph.add(
        f"{root}.router_score",
        "ROUTER_SCORE",
        (ffn_input,),
        phases=normal_phases,
        attributes=_router_score_attributes(),
        tensor_roles=("moe.router.weight",),
    )
    (original_scores,) = graph.add(
        f"{root}.router_activation",
        "SQRT_SOFTPLUS",
        (router_scores,),
        phases=normal_phases,
        attributes={"score_function": "sqrtsoftplus"},
    )
    route_kind = "HASH_ROUTE" if hash_route else "BIASED_TOPK_ROUTE"
    route_roles = (
        ("moe.hash_route.table",) if hash_route else ("moe.router.selection_bias",)
    )
    (expert_indices,) = graph.add(
        f"{root}.route_select",
        route_kind,
        (original_scores, "request.input_ids"),
        phases=normal_phases,
        attributes={"experts": 256, "top_k": 6},
        tensor_roles=route_roles,
    )
    (expert_weights,) = graph.add(
        f"{root}.route_weights",
        "ROUTER_WEIGHT_NORMALIZE",
        (original_scores, expert_indices),
        phases=normal_phases,
        attributes={"route_scale": 1.5, "top_k": 6},
    )
    (dispatch,) = graph.add(
        f"{root}.expert_dispatch",
        "EXPERT_DISPATCH",
        (ffn_input, expert_indices, expert_weights),
        phases=normal_phases,
        attributes={"expert_count": 256, "top_k": 6},
    )
    (routed_output,) = graph.add(
        f"{root}.routed_experts",
        "MXFP4_SWIGLU",
        (dispatch,),
        phases=normal_phases,
        attributes={
            "expert_count": 256,
            "intermediate_size": 2048,
            "swiglu_limit": 10.0,
            "top_k": 6,
        },
        tensor_roles=(
            "moe.routed_expert.gate.weight",
            "moe.routed_expert.gate.scale",
            "moe.routed_expert.down.weight",
            "moe.routed_expert.down.scale",
            "moe.routed_expert.up.weight",
            "moe.routed_expert.up.scale",
        ),
    )
    (shared_output,) = graph.add(
        f"{root}.shared_expert",
        "FP8_SWIGLU",
        (ffn_input,),
        phases=normal_phases,
        attributes={"intermediate_size": 2048, "swiglu_limit": 10.0},
        tensor_roles=(
            "moe.shared_expert.gate.weight",
            "moe.shared_expert.gate.scale",
            "moe.shared_expert.down.weight",
            "moe.shared_expert.down.scale",
            "moe.shared_expert.up.weight",
            "moe.shared_expert.up.scale",
        ),
    )
    (ffn_output,) = graph.add(
        f"{root}.expert_reduce",
        "EXPERT_REDUCE",
        (dispatch, routed_output, shared_output),
        phases=normal_phases,
        attributes=_expert_reduce_attributes(),
    )
    (hidden,) = graph.add(
        f"{root}.hc_ffn_post",
        "HC_POST",
        (ffn_output, ffn_residual, ffn_post, ffn_comb),
        phases=normal_phases,
        attributes={"branch": "ffn", "hc_mult": 4},
    )
    return hidden


def load_official_inference_config(
    path: Path = DEFAULT_INFERENCE_CONFIG,
    source_path: Path = DEFAULT_SOURCE,
) -> dict[str, Any]:
    source = load_checkpoint_source(source_path)
    if source["repository"] != REPOSITORY or source["revision"] != REVISION:
        raise DeepSeekV4GraphError("inference config source is not pinned V4 Flash")
    expected = {item["path"]: item for item in source["expected_files"]}
    for remote_path, digest in (
        ("inference/config.json", INFERENCE_CONFIG_SHA256),
        ("inference/model.py", MODEL_SOURCE_SHA256),
        ("inference/kernel.py", KERNEL_SOURCE_SHA256),
        ("inference/convert.py", CONVERT_SOURCE_SHA256),
        ("inference/generate.py", GENERATE_SOURCE_SHA256),
        ("README.md", MODEL_CARD_SHA256),
        ("encoding/encoding_dsv4.py", ENCODING_SOURCE_SHA256),
        ("tokenizer.json", TOKENIZER_SHA256),
    ):
        if expected.get(remote_path, {}).get("sha256") != digest:
            raise DeepSeekV4GraphError(f"source hash differs for {remote_path}")
    try:
        payload = path.read_bytes()
        config = load_strict_json(path)
    except (OSError, ValueError) as exc:
        raise DeepSeekV4GraphError(
            f"cannot load inference config {path}: {exc}"
        ) from exc
    if hashlib.sha256(payload).hexdigest() != INFERENCE_CONFIG_SHA256:
        raise DeepSeekV4GraphError("committed inference config is not byte-exact")
    root = load_official_config(source_path=source_path)
    expected_values = {
        "compress_ratios": root["compress_ratios"],
        "dim": root["hidden_size"],
        "dspark_block_size": root["dspark_block_size"],
        "dspark_markov_rank": root["dspark_markov_rank"],
        "dspark_noise_token_id": root["dspark_noise_token_id"],
        "dspark_target_layer_ids": root["dspark_target_layer_ids"],
        "expert_dtype": root["expert_dtype"],
        "head_dim": root["head_dim"],
        "hc_mult": root["hc_mult"],
        "hc_sinkhorn_iters": root["hc_sinkhorn_iters"],
        "index_head_dim": root["index_head_dim"],
        "index_n_heads": root["index_n_heads"],
        "index_topk": root["index_topk"],
        "moe_inter_dim": root["moe_intermediate_size"],
        "n_activated_experts": root["num_experts_per_tok"],
        "n_hash_layers": root["num_hash_layers"],
        "n_heads": root["num_attention_heads"],
        "n_layers": root["num_hidden_layers"],
        "n_mtp_layers": 3,
        "n_routed_experts": root["n_routed_experts"],
        "n_shared_experts": root["n_shared_experts"],
        "o_groups": root["o_groups"],
        "o_lora_rank": root["o_lora_rank"],
        "q_lora_rank": root["q_lora_rank"],
        "route_scale": root["routed_scaling_factor"],
        "score_func": root["scoring_func"],
        "swiglu_limit": root["swiglu_limit"],
        "vocab_size": root["vocab_size"],
        "window_size": root["sliding_window"],
    }
    for key, value in expected_values.items():
        if config.get(key) != value:
            raise DeepSeekV4GraphError(
                f"inference config {key!r} differs: {config.get(key)!r} versus {value!r}"
            )
    return config


def _assert_tensor_role_coverage(
    nodes: list[GraphNode], specs: tuple[TensorSpec, ...]
) -> dict[str, Any]:
    expected_roles = {spec.semantic_role for spec in specs}
    consumed_roles = {role for node in nodes for role in node.tensor_roles}
    missing = sorted(expected_roles - consumed_roles)
    extra = sorted(consumed_roles - expected_roles)
    if missing or extra:
        raise DeepSeekV4GraphError(
            f"graph tensor-role coverage differs: missing={missing}, extra={extra}"
        )
    all_by_role: defaultdict[str, list[str]] = defaultdict(list)
    main_by_layer_role: defaultdict[tuple[int, str], list[str]] = defaultdict(list)
    dspark_by_layer_role: defaultdict[tuple[int, str], list[str]] = defaultdict(list)
    for node in nodes:
        for role in node.tensor_roles:
            all_by_role[role].append(node.node_id)
            main_match = re.match(r"^main\.layer(\d{2})\.", node.node_id)
            if main_match:
                main_by_layer_role[(int(main_match.group(1)), role)].append(
                    node.node_id
                )
            dspark_match = re.match(r"^dspark\.layer(\d{2})\.", node.node_id)
            if dspark_match:
                dspark_by_layer_role[(int(dspark_match.group(1)), role)].append(
                    node.node_id
                )
    assignments: list[dict[str, Any]] = []
    for spec in specs:
        if spec.scope == "global":
            candidates = all_by_role[spec.semantic_role]
        elif spec.scope == "main":
            candidates = main_by_layer_role[(spec.layer, spec.semantic_role)]
        elif spec.scope == "dspark" and spec.semantic_role.startswith("dspark."):
            candidates = all_by_role[spec.semantic_role]
        elif spec.scope == "dspark":
            candidates = dspark_by_layer_role[(spec.layer, spec.semantic_role)]
        else:  # pragma: no cover - TensorSpec currently validates these scopes
            raise DeepSeekV4GraphError(f"unknown tensor scope {spec.scope!r}")
        if not candidates:
            raise DeepSeekV4GraphError(
                f"tensor {spec.name!r} has no layer- and scope-correct graph consumer"
            )
        assignments.append({"consumers": sorted(candidates), "tensor": spec.name})
    return {
        "assigned_tensor_count": len(assignments),
        "assignment_sha256": hashlib.sha256(
            canonical_json_bytes(assignments)
        ).hexdigest(),
        "maximum_consumers_per_tensor": max(
            len(item["consumers"]) for item in assignments
        ),
        "multi_consumer_tensor_count": sum(
            len(item["consumers"]) > 1 for item in assignments
        ),
        "unassigned_tensor_count": 0,
    }


def build_official_graph_contract() -> dict[str, Any]:
    """Generate the complete source-mapped graph and open implementation ledger."""

    config = load_official_config()
    inference_config = load_official_inference_config()
    specs = build_official_tensor_specs(config)
    if inference_config["n_mtp_layers"] != 3:
        raise DeepSeekV4GraphError(
            "official inference graph does not have three DSpark stages"
        )
    graph = _GraphBuilder()
    (hidden,) = graph.add(
        "main.token_embed",
        "TOKEN_EMBED",
        ("request.input_ids",),
        attributes={"hidden_size": 4096, "vocab_size": 129280},
        tensor_roles=("model.token_embedding.weight",),
    )
    (hidden,) = graph.add(
        "main.hc_expand",
        "HC_EXPAND",
        (hidden,),
        attributes={"hc_mult": 4},
    )
    target_hiddens: list[str] = []
    for layer, ratio in enumerate(config["compress_ratios"][:43]):
        hidden = _add_block_graph(
            graph,
            hidden,
            scope="main",
            layer=layer,
            ratio=ratio,
            hash_route=layer < 3,
        )
        if layer in config["dspark_target_layer_ids"]:
            (captured,) = graph.add(
                f"main.layer{layer:02d}.target_hidden",
                "TARGET_HIDDEN_CAPTURE",
                (hidden,),
                attributes={
                    "hc_mult": config["hc_mult"],
                    "hc_reduce": "mean",
                    "layer": layer,
                },
            )
            target_hiddens.append(captured)
    (main_hidden,) = graph.add(
        "main.hc_head",
        "HC_HEAD",
        (hidden,),
        attributes={"epsilon": 1e-6, "hc_mult": 4},
        tensor_roles=(
            "model.hyper_connection_head.base",
            "model.hyper_connection_head.projection",
            "model.hyper_connection_head.scale",
        ),
    )
    (main_hidden,) = graph.add(
        "main.final_norm",
        "RMS_NORM",
        (main_hidden,),
        attributes=_rms_norm_attributes(4096),
        tensor_roles=("model.final_norm.weight",),
    )
    (main_logits,) = graph.add(
        "main.lm_head",
        "LM_HEAD",
        (main_hidden,),
        attributes={"untied": True, "vocab_size": 129280},
        tensor_roles=("model.lm_head.weight",),
    )
    (main_token,) = graph.add(
        "main.sample",
        "SAMPLE",
        (main_logits,),
        attributes={
            "greedy_policy": "finite_binary32_first_index_argmax_exact",
            "official_stochastic_replay": (
                "blocked_unpinned_torch_cuda_rng_exponential_softmax_backend"
            ),
            "policy": "runtime_temperature_gumbel_or_argmax",
            "target_stochastic_adaptation": (
                "explicit_positive_binary32_exponential_draws_cr32_exp_balanced_softmax"
            ),
        },
    )

    (dspark_condition,) = graph.add(
        "dspark.main_project",
        "DSPARK_MAIN_PROJECT",
        tuple(target_hiddens),
        attributes={"source_layers": [40, 41, 42]},
        tensor_roles=(
            *_fp8_roles("dspark.main_hidden_projection"),
            "dspark.main_hidden_norm.weight",
        ),
    )
    (draft_hidden,) = graph.add(
        "dspark.noise_embed",
        "DSPARK_NOISE_EMBED",
        (main_token, "request.input_ids"),
        attributes={"block_size": 5, "hc_mult": 4, "noise_token_id": 128799},
        tensor_roles=("model.token_embedding.weight",),
    )
    for stage in range(3):
        draft_hidden = _add_block_graph(
            graph,
            draft_hidden,
            scope="dspark",
            layer=stage,
            ratio=0,
            hash_route=False,
            dspark=True,
            conditioning=dspark_condition,
        )
    (draft_hidden,) = graph.add(
        "dspark.hc_head",
        "HC_HEAD",
        (draft_hidden,),
        phases=("decode",),
        attributes={"epsilon": 1e-6, "hc_mult": 4},
        tensor_roles=(
            "dspark.hyper_connection_head.base",
            "dspark.hyper_connection_head.projection",
            "dspark.hyper_connection_head.scale",
        ),
    )
    (draft_hidden,) = graph.add(
        "dspark.final_norm",
        "RMS_NORM",
        (draft_hidden,),
        phases=("decode",),
        attributes=_rms_norm_attributes(4096),
        tensor_roles=("dspark.final_norm.weight",),
    )
    (draft_logits,) = graph.add(
        "dspark.lm_head",
        "LM_HEAD",
        (draft_hidden,),
        phases=("decode",),
        attributes={"block_size": 5, "shared_main_head": True},
        tensor_roles=("model.lm_head.weight",),
    )
    draft_tokens, markov_embeddings = graph.add(
        "dspark.markov_loop",
        "MARKOV_AUTOREGRESSIVE_LOOP",
        (draft_logits, main_token),
        ("tokens", "embeddings"),
        phases=("decode",),
        attributes={"block_size": 5, "markov_rank": 256},
        tensor_roles=(
            "dspark.markov_embedding.weight",
            "dspark.markov_head.weight",
        ),
    )
    (confidence,) = graph.add(
        "dspark.confidence",
        "CONFIDENCE_SCORE",
        (draft_hidden, markov_embeddings),
        phases=("decode",),
        attributes=_confidence_score_attributes(),
        tensor_roles=("dspark.confidence_head.weight",),
    )
    tensor_assignment = _assert_tensor_role_coverage(graph.nodes, specs)
    kind_counts = Counter(node.kind for node in graph.nodes)
    used_kinds = set(kind_counts)
    unknown_kinds = used_kinds - OPERATOR_CATALOG.keys()
    unused_kinds = OPERATOR_CATALOG.keys() - used_kinds
    if unknown_kinds or unused_kinds:
        raise DeepSeekV4GraphError(
            f"operator catalog coverage differs: unknown={sorted(unknown_kinds)}, "
            f"unused={sorted(unused_kinds)}"
        )
    if any(requirement.cost_class.startswith("zero") for requirement in _OPERATORS):
        raise DeepSeekV4GraphError("operator catalog contains a zero-cost class")
    operator_catalog = [
        OPERATOR_CATALOG[kind].to_dict() for kind in sorted(OPERATOR_CATALOG)
    ]
    body: dict[str, Any] = {
        "adaptations": [
            {
                "decision": "resolve three DSpark stages from official inference config and checkpoint namespaces",
                "inference_config_n_mtp_layers": 3,
                "root_config_num_nextn_predict_layers": 1,
            },
            {
                "decision": "freeze compressor pooling arithmetic rather than inherit backend-dependent reduction and exponential behavior",
                "source_behavior": "PyTorch softmax and reduction results may vary with backend implementation details",
                "target_contract": "NUM-6.13 finite binary32 stable softmax, correctly rounded exponential, balanced reductions, preserved subnormals, and positive-zero canonicalization",
            },
            {
                "decision": "make new-session raw compressor-state reset an explicit causal transaction",
                "source_behavior": "Compressor.forward overwrites only raw-state rows addressed by the current call and trusts its caller to maintain session and position continuity",
                "target_contract": "the target state update validates a canonical session identity and exact next position, resets every active raw slot before fresh prefill, increments a monotonic lane version, and returns an immutable prepared version that downstream poison may discard",
            },
            {
                "decision": "track a session-bound committed-prefix view for compressed KV",
                "source_behavior": "the released PyTorch cache object exposes payload storage without validity, session, cursor, retirement, or generation metadata",
                "target_contract": "causal writes bind a contiguous valid prefix to the exact active sessions, cursor, and monotonic versions; retired lanes retain tombstones; the qualified view never exposes stale capacity rows",
            },
        ],
        "coverage": {
            "catalog_kind_count": len(OPERATOR_CATALOG),
            "consumed_tensor_role_count": len(
                {role for node in graph.nodes for role in node.tensor_roles}
            ),
            "execution_status": "blocked_pending_reference_and_service_engine",
            "missing_cost_class_count": 0,
            "missing_lowering_count": 0,
            "missing_reference_owner_count": 0,
            "node_count": len(graph.nodes),
            "pending_reference_kind_count": sum(
                record["reference_status"] == "pending_implementation"
                for record in operator_catalog
            ),
            "pending_rtl_kind_count": len(OPERATOR_CATALOG),
            "pending_service_engine_kind_count": len(OPERATOR_CATALOG),
            "unknown_kind_count": 0,
            "unmapped_tensor_role_count": 0,
        },
        "graph_inputs": [
            "request.input_ids",
            "request.session_ids",
            "request.start_pos",
        ],
        "graph_outputs": [main_token, main_logits, draft_tokens, confidence],
        "model_id": MODEL_ID,
        "nodes": [node.to_dict() for node in graph.nodes],
        "open_semantic_issues": [
            {
                "id": "DSV4-SEM-001",
                "issue": "The pinned local generate.py never invokes forward_spec; model.py produces five DSpark draft samples and confidence but does not define target verification or speculative acceptance, while the model-card vLLM recipe requests seven speculative tokens.",
                "required_resolution": "Pin and independently specify the vLLM or SGLang DSpark verification/acceptance contract before claiming speculative end-to-end execution.",
                "severity": "blocking",
                "source_anchor": "inference/generate.py:generate;inference/model.py:Transformer.forward_spec;README.md:How to Run with vLLM",
            },
            {
                "id": "DSV4-SEM-003",
                "issue": "The target-only controller now verifies greedy argmax, rejects top_p other than 1.0, and chains stochastic RNG-state hashes. Exact stochastic candidate replay remains blocked because Gumbel-max consumes an unpinned PyTorch/CUDA generator stack; the release recipe recommends top_p although local generate.py has no top-p filter.",
                "required_resolution": "Pin and qualify the exact Torch/CUDA exponential-race RNG behavior, or freeze a greedy-only acceptance boundary; top-p behavior requires a separately pinned implementation.",
                "severity": "blocking",
                "source_anchor": "inference/model.py:sample;inference/generate.py:main;README.md:How to Run Locally;compiler/frontend/deepseek_v4_generation.py",
            },
            {
                "id": "DSV4-SEM-004",
                "issue": "This graph begins at token IDs. The pinned message protocol, exact local tokenizer, completion parser, and target-only generation controller are independently implemented, but they have not been connected to checkpoint-derived logits in one end-to-end execution.",
                "required_resolution": "Bind verified prompt encoding and tokenization to the operator-complete executor, then decode and parse its generated token IDs with full prompt-to-completion differential evidence.",
                "severity": "blocking",
                "source_anchor": "encoding/encoding_dsv4.py;tokenizer.json;tokenizer_config.json;inference/generate.py:main;compiler/frontend/deepseek_v4_encoding.py;compiler/frontend/deepseek_v4_tokenizer.py;compiler/frontend/deepseek_v4_generation.py",
            },
            {
                "id": "DSV4-SEM-005",
                "issue": "Independent references now define E2M1, E8M0, E4M3FN, BF16, activation microscaling, ordered binary32 accumulation, official 32-value routed and 128-value dense block dots, complete routed-MXFP4 and shared-FP8 SwiGLU, complete dense FP8 and BF16 linear, binary32 router-score, sqrt-softplus router activation, compressor, and DSpark confidence projections, causal raw compressor-state updates, deterministic compressor pooling, explicit pooled-binary32 to BF16 conversion, session-bound compressed-KV prefix commit and valid-prefix view, learned sparse-index scoring, block-64 sparse attention with learned sink and explicit mutable-KV traffic, complete grouped attention-output projection, base/YaRN RoPE application and inverse, weighted RMS normalization, unweighted BF16 head RMS normalization, complete HC pre-mixing and final HC-head reduction, KV FP8 and indexer FP4 QDQ, indexer Hadamard semantics, and fail-closed greedy/target-adapted sampling, comprising forty complete matrix/vector/normalization/structural/index/lookup/selection/routing/attention/conversion/state/control operator kinds. Six matrix, KV-view/window-state, and speculative-control operator kinds remain pending even though every kind has a source, lowering, and cost-class ledger entry.",
                "required_resolution": "Implement and qualify complete target-precision semantics for each graph operator before marking that operator executable; scalar and block-dot primitives alone do not close matrix or layer lowering.",
                "severity": "blocking",
                "source_anchor": "inference/kernel.py:act_quant_kernel;inference/kernel.py:fp4_quant_kernel;inference/kernel.py:fp8_gemm_kernel;inference/kernel.py:fp4_gemm_kernel;inference/kernel.py:sparse_attn_kernel;inference/kernel.py:hc_split_sinkhorn_kernel;inference/model.py:RMSNorm.forward;inference/model.py:Attention.forward;inference/model.py:Compressor.forward;inference/model.py:Indexer.forward;inference/model.py:Transformer.forward;inference/model.py:Block.hc_pre;inference/model.py:Block.hc_head;inference/model.py:Block.hc_post;inference/model.py:Gate.forward;inference/model.py:MoE.forward;inference/model.py:Expert.forward;inference/model.py:apply_rotary_emb;inference/model.py:sample;runtime/reference/formats.py;runtime/reference/transcendental.py;runtime/reference/compression.py;runtime/reference/compression_state.py;runtime/reference/compression_pool.py;runtime/reference/conversion.py;runtime/reference/compressed_kv.py;runtime/reference/grouped_output.py;runtime/reference/hyper_connection.py;runtime/reference/hc_head.py;runtime/reference/index_score.py;runtime/reference/rope.py;runtime/reference/sparse_attention.py;runtime/reference/sqrt_softplus.py;runtime/reference/normalization.py;runtime/reference/quantization.py;runtime/reference/vector.py;runtime/reference/dispatch.py;runtime/reference/swiglu.py;runtime/reference/sampling.py",
            },
            {
                "id": "DSV4-SEM-006",
                "issue": "Independent references now define immutable causal raw compressor-state updates plus session-bound compressed-KV writes and valid-prefix views, including fresh-session reset, exact decode cursor, lane retirement, tombstones, monotonic versions, and stale-capacity exclusion. The generation controller still has no operator-complete executor that invokes those transactions together with window-KV mutation and binds the resulting committed-state hash to each processed span.",
                "required_resolution": "Implement service-engine and session-controller integration for the qualified compressor transactions, specify and implement the remaining window-KV transaction, and bind reset, abort, commit, bounds, isolation, and state hashes to generation invocations.",
                "severity": "blocking",
                "source_anchor": "inference/model.py:Attention.forward;inference/model.py:Compressor.forward;compiler/frontend/deepseek_v4_generation.py;runtime/reference/compression_state.py;runtime/reference/compressed_kv.py",
            },
            {
                "id": "DSV4-SEM-007",
                "issue": "A deterministic plan covers all 72,317 official tensors, and an atomic hash-locked applicator plus independent replay checker is qualified on identity, slicing, native MXFP4, and wo_a BF16 fixture paths. The 166.9-GB official payload has not yet been streamed through that machinery or bound to canonical output hashes.",
                "required_resolution": "Apply the plan to every hash-locked official payload byte, emit per-rank canonical tensor hashes, and pass independent full-payload transform checks before image generation.",
                "severity": "blocking",
                "source_anchor": "inference/convert.py:main;compiler/canonical/deepseek_v4.py;compiler/canonical/plan.py;compiler/checking/deepseek_v4_transforms.py",
            },
        ],
        "operator_catalog": operator_catalog,
        "operator_counts": [
            {"kind": kind, "node_count": kind_counts[kind]}
            for kind in sorted(kind_counts)
        ],
        "schema": "opentallas.deepseek_v4_graph_contract.v1",
        "source": {
            "convert_sha256": CONVERT_SOURCE_SHA256,
            "encoding_sha256": ENCODING_SOURCE_SHA256,
            "generate_sha256": GENERATE_SOURCE_SHA256,
            "inference_config_sha256": INFERENCE_CONFIG_SHA256,
            "kernel_sha256": KERNEL_SOURCE_SHA256,
            "model_card_sha256": MODEL_CARD_SHA256,
            "model_sha256": MODEL_SOURCE_SHA256,
            "repository": REPOSITORY,
            "revision": REVISION,
            "tokenizer_sha256": TOKENIZER_SHA256,
        },
        "system_scope": {
            "covered": [
                "one target-model prefill/decode forward graph from token IDs",
                "attached three-stage DSpark draft and confidence graph",
                "all checkpoint tensor roles and per-layer consumers",
                "mutable window-KV, raw-compressor, and compressed-KV state access sites",
                "host message wire encoding and completion parsing outside the token-ID graph",
                "hash-verified local tokenizer encode and decode behavior",
                "target-only prefill/decode, EOS, and executor-commit control with synthetic transcripts",
                "scalar target formats, activation microscaling, ordered accumulation, and official block-dot primitives",
                "unit-qualified routed-MXFP4 and shared-FP8 SwiGLU, dense FP8 linear, index-head BF16 linear, binary32 router-score, sqrt-softplus router activation, compressor, and DSpark-confidence projections, causal raw compressor-state update, deterministic compressor pool, pooled-binary32 to BF16 conversion, session-bound compressed-KV write and valid-prefix view, learned sparse-index scoring, block-64 sparse attention with learned sink and explicit mutable-KV traffic, complete grouped attention-output projection, base/YaRN RoPE application and inverse, weighted RMS normalization, unweighted BF16 head RMS normalization, complete HC pre-mixing, final HC-head reduction, KV FP8 QDQ, indexer FP4 QDQ, indexer Hadamard rotation, target-hidden capture, HC expansion, HC post-mixing, token embedding, hash-route, window, compressed-dense, DSpark index/noise-embedding, biased-router top-k, learned-index top-k, routed-weight normalization, expert-dispatch, expert-reduction, and fail-closed greedy/target-adapted sampling references",
                "complete official-tensor canonical transform plan and independently checked transform primitives",
                "atomic hash-locked canonical application and replay on an adversarial development fixture",
            ],
            "request_boundary": "token_ids_session_ids_and_start_position",
            "unresolved": [
                "end-to-end binding of the verified host boundary to checkpoint-derived logits",
                "exact stochastic replay for the unpinned Torch/CUDA RNG stack",
                "DSpark target verification and speculative acceptance",
                "full official-payload transform application and canonical output hashes",
                "six remaining operator-complete target-precision references",
                "service-engine integration of qualified raw-compressor and compressed-KV transactions, remaining window-KV transaction semantics, session control, and microcode",
                "physical placement, HBM/KV allocation, and static schedule",
            ],
        },
        "tensor_contract_schema": "opentallas.deepseek_v4_tensor_contract.v1",
        "tensor_assignment": tensor_assignment,
    }
    return {
        **body,
        "graph_contract_id": hashlib.sha256(canonical_json_bytes(body)).hexdigest(),
    }


def graph_summary() -> dict[str, Any]:
    contract = build_official_graph_contract()
    return {
        "coverage": contract["coverage"],
        "graph_contract_id": contract["graph_contract_id"],
        "model_id": contract["model_id"],
        "operator_counts": contract["operator_counts"],
        "schema": "opentallas.deepseek_v4_graph_summary.v1",
    }
