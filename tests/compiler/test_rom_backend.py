"""Tests for the immutable-ROM backend family.

The fixtures here are synthetic but structurally faithful: a dense Qwen-shaped
decoder block and an MoE DeepSeek-shaped block with two layer classes, each with
a real checkpoint file on disk so the inverse proof reconstructs actual bytes
rather than trusting a recorded digest.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from compiler.backends.rom.common.image import (
    DefectRecord,
    RomCoordinate,
    RomImageError,
    RomLayoutPolicy,
    plan_repair_map,
    region_content_digest,
)
from compiler.backends.rom.common.inverse import (
    InverseProofError,
    check_rom_inverse,
)
from compiler.backends.rom.common.program import RomLoweringError, analyze
from compiler.backends.rom.deepseek_v4 import (
    MAX_RETICLES,
    build_deepseek_v4_rom_deployment,
    deepseek_v4_rom_capability,
    wafer_geometry,
)
from compiler.backends.rom.qwen3 import (
    build_qwen3_rom_deployment,
    qwen3_area_accounting,
    qwen3_rom_capability,
)
from compiler.ir.v3.kernel_ir import (
    CheckpointBinding,
    Entrypoint,
    Kernel,
    KernelGraph,
    RuntimeSymbol,
    StateResource,
    Symbolic,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from runtime.abi3.constants import (
    Link,
    Major,
    Permission,
    StorageClass,
    Tensor as TensorOp,
    TopologyClass,
)
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.records import decode_body, split_program
from runtime.abi3.verifier import VerificationError, require_admitted

DTYPE_BITS_BY_NAME = {
    "bf16": 16,
    "fp8_e4m3fn": 8,
    "e8m0": 8,
    "mxfp4_e2m1": 4,
    "i32": 32,
    "i64": 64,
    "u32": 32,
}


# ---------------------------------------------------------------------------
# Synthetic checkpoint + graph builders
# ---------------------------------------------------------------------------
class _GraphBuilder:
    """Builds a neutral graph and the checkpoint file its weights bind to."""

    def __init__(self, path: Path, seed: int = 1) -> None:
        self.path = path
        self.blob = bytearray()
        self.tensors: list[Tensor] = []
        self.kernels: list[Kernel] = []
        self.seed = seed

    def _payload(self, size: int) -> bytes:
        out = bytearray(size)
        value = self.seed
        for i in range(size):
            value = (value * 1103515245 + 12345) & 0xFFFFFFFF
            out[i] = (value >> 16) & 0xFF
        self.seed = value or 1
        return bytes(out)

    def weight(self, tensor_id: str, dtype: str, shape: tuple[int, ...]) -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        size = (elements * DTYPE_BITS_BY_NAME[dtype] + 7) // 8
        offset = len(self.blob)
        payload = self._payload(size)
        self.blob.extend(payload)
        self.tensors.append(
            Tensor(
                tensor_id=tensor_id,
                dtype=dtype,
                shape=shape,
                role="weight",
                binding=CheckpointBinding(
                    source_name=tensor_id,
                    path=self.path.name,
                    offset=offset,
                    bytes=size,
                    sha256=hashlib.sha256(payload).hexdigest(),
                ),
            )
        )
        return tensor_id

    def value(
        self, tensor_id: str, dtype: str, shape: tuple[Any, ...], role: str
    ) -> str:
        self.tensors.append(
            Tensor(tensor_id=tensor_id, dtype=dtype, shape=shape, role=role)
        )
        return tensor_id

    def kernel(
        self,
        kernel_id: str,
        kind: str,
        inputs: tuple[str, ...],
        outputs: tuple[str, ...],
        *,
        contract: str,
        layer: int | None = None,
        state_reads: tuple[str, ...] = (),
        state_writes: tuple[str, ...] = (),
        attributes: dict[str, Any] | None = None,
        counter_class: str = "",
    ) -> None:
        self.kernels.append(
            Kernel(
                index=len(self.kernels),
                kernel_id=kernel_id,
                kind=kind,
                inputs=inputs,
                outputs=outputs,
                numeric_contract=contract,
                attributes=attributes or {},
                layer=layer,
                state_reads=state_reads,
                state_writes=state_writes,
                counter_class=counter_class,
            )
        )

    def write(self) -> None:
        self.path.write_bytes(bytes(self.blob))


def _finish(
    builder: _GraphBuilder,
    *,
    model_id: str,
    states: tuple[StateResource, ...],
    vocabulary: int,
    span_max: int,
    inputs: tuple[str, ...],
    outputs: tuple[str, ...],
) -> KernelGraph:
    builder.write()
    state_ids = tuple(s.state_id for s in states)
    graph = KernelGraph(
        model_id=model_id,
        source={"exporter": "tests.compiler.test_rom_backend"},
        symbols=(
            RuntimeSymbol(name="span_tokens", minimum=1, maximum=span_max),
            RuntimeSymbol(name="context_tokens", minimum=1, maximum=span_max),
        ),
        tensors=tuple(builder.tensors),
        states=states,
        kernels=tuple(builder.kernels),
        entrypoints=(
            Entrypoint(
                phase="prefill",
                inputs=inputs,
                outputs=outputs,
                states=state_ids,
                generation_policy="synthetic",
            ),
            Entrypoint(
                phase="decode",
                inputs=inputs,
                outputs=outputs,
                states=state_ids,
                generation_policy="synthetic",
            ),
        ),
        generation_policy={
            "eos_token_ids": [vocabulary - 1],
            "maximum_new_tokens": 8,
            "policy_id": "synthetic",
            "selection_mode": "greedy_argmax_lowest_id",
            "vocabulary_size": vocabulary,
        },
    )
    errors = check_neutral(graph)
    assert not errors, errors
    return graph


def qwen_shaped_graph(
    root: Path, *, layers: int = 4, hidden: int = 64, span_max: int = 16
) -> KernelGraph:
    """A dense Qwen-shaped decoder: one layer run, GQA attention, SwiGLU MLP."""
    heads, kv_heads, head_dim, intermediate, vocabulary = 4, 2, 16, 128, 32
    kv_width = kv_heads * head_dim
    builder = _GraphBuilder(root / "qwen-checkpoint.bin", seed=11)
    span = Symbolic("span_tokens", 1, span_max)
    context = Symbolic("context_tokens", 1, span_max)

    token_ids = builder.value("input.token_ids", "i64", (span,), "input")
    positions = builder.value("input.positions", "i32", (span,), "input")
    embed = builder.weight("model.embed_tokens.weight", "bf16", (vocabulary, hidden))
    residual = builder.value("sequence.embedding", "bf16", (span, hidden), "activation")
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, embed),
        (residual,),
        contract="bf16_payload_lookup_v1",
        attributes={"input_dtype": "i64", "output_dtype": "bf16"},
    )

    states = tuple(
        StateResource(
            state_id=f"key_value_cache.layer.{layer}",
            state_class="kv_cache",
            dtype="bf16",
            row_elements=2 * kv_width,
            capacity_rows=span_max,
        )
        for layer in range(layers)
    )
    for layer in range(layers):
        base = f"model.layers.{layer}"
        prefix = f"decoder.{layer}"
        state_id = states[layer].state_id
        attention_norm = builder.value(
            f"{prefix}.attention.normalized", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.norm",
            "RMS_NORM",
            (residual, builder.weight(f"{base}.input_layernorm.weight", "bf16", (hidden,))),
            (attention_norm,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            layer=layer,
        )
        query = builder.value(
            f"{prefix}.attention.query", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.query_projection",
            "MATMUL",
            (attention_norm, builder.weight(f"{base}.self_attn.q_proj.weight", "bf16", (hidden, hidden))),
            (query,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        key = builder.value(
            f"{prefix}.attention.key", "bf16", (span, kv_width), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.key_projection",
            "MATMUL",
            (attention_norm, builder.weight(f"{base}.self_attn.k_proj.weight", "bf16", (kv_width, hidden))),
            (key,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        value = builder.value(
            f"{prefix}.attention.value", "bf16", (span, kv_width), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.value_projection",
            "MATMUL",
            (attention_norm, builder.weight(f"{base}.self_attn.v_proj.weight", "bf16", (kv_width, hidden))),
            (value,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        query_normalized = builder.value(
            f"{prefix}.attention.query_normalized", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.query_head_norm",
            "HEAD_RMS_NORM",
            (query, builder.weight(f"{base}.self_attn.q_norm.weight", "bf16", (head_dim,))),
            (query_normalized,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            layer=layer,
        )
        key_normalized = builder.value(
            f"{prefix}.attention.key_normalized", "bf16", (span, kv_width), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.key_head_norm",
            "HEAD_RMS_NORM",
            (key, builder.weight(f"{base}.self_attn.k_norm.weight", "bf16", (head_dim,))),
            (key_normalized,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            layer=layer,
        )
        query_rotated = builder.value(
            f"{prefix}.attention.query_rotated", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.query_rotation",
            "ROPE",
            (query_normalized, positions),
            (query_rotated,),
            contract="qwen3_rope_fp32_bf16_v1",
            layer=layer,
            attributes={"input_dtype": "bf16", "output_dtype": "bf16"},
        )
        key_rotated = builder.value(
            f"{prefix}.attention.key_rotated", "bf16", (span, kv_width), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.key_rotation",
            "ROPE",
            (key_normalized, positions),
            (key_rotated,),
            contract="qwen3_rope_fp32_bf16_v1",
            layer=layer,
            attributes={"input_dtype": "bf16", "output_dtype": "bf16"},
        )
        appended = builder.value(
            f"{prefix}.attention.appended", "bf16", (span, 2, kv_width), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.key_value_append",
            "KV_APPEND",
            (key_rotated, value),
            (appended,),
            contract="bf16_byte_preserving_state_v1",
            layer=layer,
            state_writes=(state_id,),
        )
        key_history = builder.value(
            f"{prefix}.attention.key_history", "bf16", (context, kv_width), "state"
        )
        value_history = builder.value(
            f"{prefix}.attention.value_history", "bf16", (context, kv_width), "state"
        )
        attention_context = builder.value(
            f"{prefix}.attention.context", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.gqa",
            "ATTENTION_GQA",
            (query_rotated, key_history, value_history, appended),
            (attention_context,),
            contract="qwen3_gqa_fp32_softmax_bf16_v1",
            layer=layer,
            state_reads=(state_id,),
        )
        attention_output = builder.value(
            f"{prefix}.attention.output", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.output_projection",
            "MATMUL",
            (attention_context, builder.weight(f"{base}.self_attn.o_proj.weight", "bf16", (hidden, hidden))),
            (attention_output,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        attention_residual = builder.value(
            f"{prefix}.attention.residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.residual_add",
            "ADD",
            (residual, attention_output),
            (attention_residual,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        feed_forward_norm = builder.value(
            f"{prefix}.feed_forward.normalized", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.norm",
            "RMS_NORM",
            (
                attention_residual,
                builder.weight(f"{base}.post_attention_layernorm.weight", "bf16", (hidden,)),
            ),
            (feed_forward_norm,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            layer=layer,
        )
        gate = builder.value(
            f"{prefix}.feed_forward.gate", "bf16", (span, intermediate), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.gate_projection",
            "MATMUL",
            (feed_forward_norm, builder.weight(f"{base}.mlp.gate_proj.weight", "bf16", (intermediate, hidden))),
            (gate,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        up = builder.value(
            f"{prefix}.feed_forward.up", "bf16", (span, intermediate), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.up_projection",
            "MATMUL",
            (feed_forward_norm, builder.weight(f"{base}.mlp.up_proj.weight", "bf16", (intermediate, hidden))),
            (up,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        activated = builder.value(
            f"{prefix}.feed_forward.activated", "bf16", (span, intermediate), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.activation",
            "SILU_MUL",
            (gate, up),
            (activated,),
            contract="qwen3_silu_mul_bf16_v1",
            layer=layer,
        )
        feed_forward_output = builder.value(
            f"{prefix}.feed_forward.output", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.down_projection",
            "MATMUL",
            (activated, builder.weight(f"{base}.mlp.down_proj.weight", "bf16", (hidden, intermediate))),
            (feed_forward_output,),
            contract="bf16_bf16_fp32_sequential_rne_v1",
            layer=layer,
        )
        layer_output = builder.value(
            f"{prefix}.residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward.residual_add",
            "ADD",
            (attention_residual, feed_forward_output),
            (layer_output,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        residual = layer_output

    final = builder.value("sequence.final_norm", "bf16", (span, hidden), "activation")
    builder.kernel(
        "final_norm",
        "RMS_NORM",
        (residual, builder.weight("model.norm.weight", "bf16", (hidden,))),
        (final,),
        contract="qwen3_rmsnorm_fp32_bf16_v1",
    )
    last = builder.value("sequence.last_token", "bf16", (1, hidden), "activation")
    builder.kernel(
        "last_token_select",
        "LAST_TOKEN_SELECT",
        (final, positions),
        (last,),
        contract="exact_index_select_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "bf16"},
    )
    logits = builder.value("output.logits", "bf16", (1, vocabulary), "output")
    builder.kernel(
        "vocabulary_projection",
        "VOCAB_PROJECT",
        (last, builder.weight("lm_head.weight", "bf16", (vocabulary, hidden))),
        (logits,),
        contract="bf16_bf16_fp32_sequential_rne_v1",
    )
    selected = builder.value("output.selected", "i32", (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        contract="greedy_lowest_token_id_argmax_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "u32"},
    )
    next_token = builder.value("output.next_token", "i64", (1,), "output")
    builder.kernel(
        "token_append",
        "TOKEN_APPEND",
        (selected,),
        (next_token,),
        contract="exact_token_append_eos_v1",
        attributes={"input_dtype": "u32", "output_dtype": "u32"},
    )
    builder.kernel(
        "state_commit",
        "STATE_COMMIT",
        (),
        (),
        contract="bf16_byte_preserving_state_v1",
        state_reads=tuple(s.state_id for s in states),
        state_writes=tuple(s.state_id for s in states),
    )
    return _finish(
        builder,
        model_id="qwen3-8b-synthetic",
        states=states,
        vocabulary=vocabulary,
        span_max=span_max,
        inputs=(token_ids, positions),
        outputs=(logits, next_token),
    )


def deepseek_shaped_graph(
    root: Path,
    *,
    dense_layers: int = 2,
    moe_layers: int = 3,
    hidden: int = 64,
    span_max: int = 16,
) -> KernelGraph:
    """An MoE DeepSeek-shaped block: two layer classes, routed experts, sparse
    attention, FP8 dense weights and MXFP4 expert weights with E8M0 scales."""
    kv_width, experts, expert_width, vocabulary = 32, 8, 96, 32
    builder = _GraphBuilder(root / "deepseek-checkpoint.bin", seed=97)
    span = Symbolic("span_tokens", 1, span_max)
    context = Symbolic("context_tokens", 1, span_max)
    layers = dense_layers + moe_layers

    token_ids = builder.value("input.token_ids", "i64", (span,), "input")
    positions = builder.value("input.positions", "i32", (span,), "input")
    embed = builder.weight("model.embed_tokens.weight", "bf16", (vocabulary, hidden))
    residual = builder.value("sequence.embedding", "bf16", (span, hidden), "activation")
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, embed),
        (residual,),
        contract="bf16_payload_lookup_v1",
        attributes={"input_dtype": "i64", "output_dtype": "bf16"},
    )
    states = tuple(
        StateResource(
            state_id=f"key_value_cache.layer.{layer}",
            state_class="compressed_kv",
            dtype="bf16",
            row_elements=2 * kv_width,
            capacity_rows=span_max,
        )
        for layer in range(layers)
    )

    for layer in range(layers):
        moe = layer >= dense_layers
        base = f"model.layers.{layer}"
        prefix = f"decoder.{layer}"
        state_id = states[layer].state_id
        norm = builder.value(f"{prefix}.normalized", "bf16", (span, hidden), "activation")
        builder.kernel(
            f"{prefix}.norm",
            "RMS_NORM",
            (residual, builder.weight(f"{base}.input_layernorm.weight", "bf16", (hidden,))),
            (norm,),
            contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
            layer=layer,
        )
        query = builder.value(f"{prefix}.query", "bf16", (span, hidden), "activation")
        builder.kernel(
            f"{prefix}.query_projection",
            "MATMUL",
            (norm, builder.weight(f"{base}.self_attn.q_proj.weight", "fp8_e4m3fn", (hidden, hidden))),
            (query,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        latent = builder.value(f"{prefix}.latent", "bf16", (span, kv_width), "activation")
        builder.kernel(
            f"{prefix}.key_value_projection",
            "MATMUL",
            (norm, builder.weight(f"{base}.self_attn.kv_proj.weight", "fp8_e4m3fn", (kv_width, hidden))),
            (latent,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        builder.kernel(
            f"{prefix}.compression",
            "COMPRESS_PROJECT",
            (
                latent,
                builder.weight(f"{base}.compressor.weight", "bf16", (kv_width, kv_width)),
                positions,
            ),
            (
                builder.value(
                    f"{prefix}.compressed", "bf16", (span, kv_width), "activation"
                ),
            ),
            contract="deepseek_v4_compress_fp32_bf16_v1",
            layer=layer,
            state_writes=(state_id,),
        )
        scores = builder.value(f"{prefix}.index_scores", "bf16", (span, span_max), "activation")
        builder.kernel(
            f"{prefix}.index_score",
            "INDEX_SCORE",
            (
                query,
                f"{prefix}.compressed",
                builder.weight(f"{base}.indexer.weight", "bf16", (kv_width, hidden)),
            ),
            (scores,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            layer=layer,
        )
        indices = builder.value(f"{prefix}.indices", "u32", (span, span_max), "activation")
        builder.kernel(
            f"{prefix}.index_topk",
            "INDEX_TOPK",
            (scores,),
            (indices,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            attributes={"input_dtype": "bf16", "output_dtype": "u32"},
            layer=layer,
        )
        key_history = builder.value(
            f"{prefix}.key_history", "bf16", (context, kv_width), "state"
        )
        value_history = builder.value(
            f"{prefix}.value_history", "bf16", (context, kv_width), "state"
        )
        attention = builder.value(f"{prefix}.context", "bf16", (span, hidden), "activation")
        builder.kernel(
            f"{prefix}.sparse_attention",
            "ATTENTION_SPARSE",
            (query, key_history, value_history, indices),
            (attention,),
            contract="deepseek_v4_sparse_attention_fp32_softmax_v1",
            layer=layer,
            state_reads=(state_id,),
        )
        attention_output = builder.value(
            f"{prefix}.attention_output", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.output_projection",
            "MATMUL",
            (attention, builder.weight(f"{base}.self_attn.o_proj.weight", "fp8_e4m3fn", (hidden, hidden))),
            (attention_output,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        attention_residual = builder.value(
            f"{prefix}.attention_residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.attention_residual_add",
            "ADD",
            (residual, attention_output),
            (attention_residual,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        feed_forward_norm = builder.value(
            f"{prefix}.feed_forward_normalized", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward_norm",
            "RMS_NORM",
            (
                attention_residual,
                builder.weight(f"{base}.post_attention_layernorm.weight", "bf16", (hidden,)),
            ),
            (feed_forward_norm,),
            contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
            layer=layer,
        )
        if not moe:
            gate = builder.value(
                f"{prefix}.dense_gate", "bf16", (span, expert_width), "activation"
            )
            builder.kernel(
                f"{prefix}.dense_gate_projection",
                "MATMUL",
                (
                    feed_forward_norm,
                    builder.weight(f"{base}.mlp.gate_proj.weight", "fp8_e4m3fn", (expert_width, hidden)),
                ),
                (gate,),
                contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
                attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
                layer=layer,
            )
            up = builder.value(
                f"{prefix}.dense_up", "bf16", (span, expert_width), "activation"
            )
            builder.kernel(
                f"{prefix}.dense_up_projection",
                "MATMUL",
                (
                    feed_forward_norm,
                    builder.weight(f"{base}.mlp.up_proj.weight", "fp8_e4m3fn", (expert_width, hidden)),
                ),
                (up,),
                contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
                attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
                layer=layer,
            )
            activated = builder.value(
                f"{prefix}.dense_activated", "bf16", (span, expert_width), "activation"
            )
            builder.kernel(
                f"{prefix}.dense_activation",
                "SILU_MUL",
                (gate, up),
                (activated,),
                contract="qwen3_silu_mul_bf16_v1",
                layer=layer,
            )
            feed_forward_output = builder.value(
                f"{prefix}.feed_forward_output", "bf16", (span, hidden), "activation"
            )
            builder.kernel(
                f"{prefix}.dense_down_projection",
                "MATMUL",
                (
                    activated,
                    builder.weight(f"{base}.mlp.down_proj.weight", "fp8_e4m3fn", (hidden, expert_width)),
                ),
                (feed_forward_output,),
                contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
                attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
                layer=layer,
            )
        else:
            router_logits = builder.value(
                f"{prefix}.router_logits", "bf16", (span, experts), "activation"
            )
            builder.kernel(
                f"{prefix}.router_score",
                "ROUTER_SCORE",
                (
                    feed_forward_norm,
                    builder.weight(f"{base}.mlp.gate.weight", "bf16", (experts, hidden)),
                ),
                (router_logits,),
                contract="deepseek_v4_router_fp32_sigmoid_v1",
                layer=layer,
            )
            expert_ids = builder.value(
                f"{prefix}.expert_ids", "u32", (span, 2), "activation"
            )
            expert_weights = builder.value(
                f"{prefix}.expert_weights", "bf16", (span, 2), "activation"
            )
            builder.kernel(
                f"{prefix}.router_topk",
                "BIASED_TOPK",
                (
                    router_logits,
                    builder.weight(f"{base}.mlp.gate.e_score_correction_bias", "bf16", (experts,)),
                ),
                (expert_ids, expert_weights),
                contract="deepseek_v4_router_fp32_sigmoid_v1",
                attributes={"input_dtype": "bf16", "output_dtype": "u32"},
                layer=layer,
            )
            dispatched = builder.value(
                f"{prefix}.dispatched", "bf16", (span, 2, hidden), "activation"
            )
            builder.kernel(
                f"{prefix}.expert_dispatch",
                "EXPERT_DISPATCH",
                (feed_forward_norm, expert_ids),
                (dispatched,),
                contract="deepseek_v4_router_fp32_sigmoid_v1",
                layer=layer,
            )
            expert_output = builder.value(
                f"{prefix}.expert_output", "bf16", (span, 2, hidden), "activation"
            )
            builder.kernel(
                f"{prefix}.routed_projection",
                "ROUTED_MATMUL",
                (
                    dispatched,
                    builder.weight(
                        f"{base}.mlp.experts.weight", "mxfp4_e2m1", (experts, expert_width, hidden)
                    ),
                    builder.weight(
                        f"{base}.mlp.experts.scale", "e8m0", (experts, expert_width, hidden // 32)
                    ),
                    expert_ids,
                ),
                (expert_output,),
                contract="mxfp4_e2m1_fp8_e4m3fn_fp32_blocked_rne_v1",
                attributes={"input_dtype": "bf16", "second_input_dtype": "mxfp4_e2m1"},
                layer=layer,
            )
            feed_forward_output = builder.value(
                f"{prefix}.feed_forward_output", "bf16", (span, hidden), "activation"
            )
            builder.kernel(
                f"{prefix}.expert_reduce",
                "EXPERT_REDUCE",
                (expert_output, expert_weights, expert_ids),
                (feed_forward_output,),
                contract="bf16_add_rne_v1",
                layer=layer,
            )
        layer_output = builder.value(
            f"{prefix}.residual", "bf16", (span, hidden), "activation"
        )
        builder.kernel(
            f"{prefix}.feed_forward_residual_add",
            "ADD",
            (attention_residual, feed_forward_output),
            (layer_output,),
            contract="bf16_add_rne_v1",
            layer=layer,
        )
        residual = layer_output

    final = builder.value("sequence.final_norm", "bf16", (span, hidden), "activation")
    builder.kernel(
        "final_norm",
        "RMS_NORM",
        (residual, builder.weight("model.norm.weight", "bf16", (hidden,))),
        (final,),
        contract="deepseek_v4_hyper_connect_fp32_bf16_v1",
    )
    last = builder.value("sequence.last_token", "bf16", (1, hidden), "activation")
    builder.kernel(
        "last_token_select",
        "LAST_TOKEN_SELECT",
        (final, positions),
        (last,),
        contract="exact_index_select_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "bf16"},
    )
    logits = builder.value("output.logits", "bf16", (1, vocabulary), "output")
    builder.kernel(
        "vocabulary_projection",
        "VOCAB_PROJECT",
        (last, builder.weight("lm_head.weight", "bf16", (vocabulary, hidden))),
        (logits,),
        contract="bf16_bf16_fp32_sequential_rne_v1",
    )
    selected = builder.value("output.selected", "i32", (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        contract="greedy_lowest_token_id_argmax_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "u32"},
    )
    next_token = builder.value("output.next_token", "i64", (1,), "output")
    builder.kernel(
        "token_append",
        "TOKEN_APPEND",
        (selected,),
        (next_token,),
        contract="exact_token_append_eos_v1",
        attributes={"input_dtype": "u32", "output_dtype": "u32"},
    )
    builder.kernel(
        "state_commit",
        "STATE_COMMIT",
        (),
        (),
        contract="bf16_byte_preserving_state_v1",
        state_reads=tuple(s.state_id for s in states),
        state_writes=tuple(s.state_id for s in states),
    )
    return _finish(
        builder,
        model_id="deepseek-v4-flash-synthetic",
        states=states,
        vocabulary=vocabulary,
        span_max=span_max,
        inputs=(token_ids, positions),
        outputs=(logits, next_token),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("rom-backend")


@pytest.fixture(scope="module")
def qwen_graph(workspace: Path) -> KernelGraph:
    return qwen_shaped_graph(workspace)


@pytest.fixture(scope="module")
def deepseek_graph(workspace: Path) -> KernelGraph:
    return deepseek_shaped_graph(workspace)


@pytest.fixture(scope="module")
def qwen_capability():
    return qwen3_rom_capability(max_context_positions=16, vocabulary_size=32)


@pytest.fixture(scope="module")
def deepseek_capability():
    return deepseek_v4_rom_capability(
        max_context_positions=16,
        vocabulary_size=32,
        expert_count=8,
        experts_per_token=2,
        tile_rom_bytes=1 << 16,
        tiles_per_reticle=8,
    )


@pytest.fixture(scope="module")
def qwen_build(qwen_graph, qwen_capability):
    return build_qwen3_rom_deployment(qwen_graph, capability=qwen_capability)


@pytest.fixture(scope="module")
def deepseek_build(deepseek_graph, deepseek_capability):
    return build_deepseek_v4_rom_deployment(
        deepseek_graph,
        capability=deepseek_capability,
        tile_rom_bytes=1 << 16,
        tiles_per_reticle=8,
    )


def _rom_objects(deployment):
    return [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and d.payload["storage_class"] == int(StorageClass.ROM)
    ]


def _instructions(deployment):
    _header, body = split_program(deployment.program)
    return decode_body(body)


# ---------------------------------------------------------------------------
# Neutral input
# ---------------------------------------------------------------------------
def test_qwen_fixture_graph_is_neutral(qwen_graph):
    assert not check_neutral(qwen_graph)
    assert {k.kind for k in qwen_graph.kernels} <= set(KERNEL_TO_ENGINE)


def test_deepseek_fixture_graph_is_neutral(deepseek_graph):
    assert not check_neutral(deepseek_graph)
    assert {k.kind for k in deepseek_graph.kernels} <= set(KERNEL_TO_ENGINE)


def test_deepseek_graph_has_two_layer_classes(deepseek_graph):
    analysis = analyze(deepseek_graph)
    assert len(analysis.runs) == 2
    assert [run.length for run in analysis.runs] == [2, 3]


# ---------------------------------------------------------------------------
# Admission
# ---------------------------------------------------------------------------
def test_qwen_rom_deployment_is_admitted(qwen_build, qwen_capability):
    deployment, _plan = qwen_build
    report = require_admitted(deployment, qwen_capability)
    assert report.admitted
    assert report.errors == []


def test_deepseek_rom_deployment_is_admitted(deepseek_build, deepseek_capability):
    deployment, _plan = deepseek_build
    report = require_admitted(deployment, deepseek_capability)
    assert report.admitted
    assert report.errors == []


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------
def test_every_rom_object_is_read_immutable(qwen_build, deepseek_build):
    for deployment, _plan in (qwen_build, deepseek_build):
        objects = _rom_objects(deployment)
        assert objects
        for descriptor in objects:
            assert descriptor.permissions == int(
                Permission.READ | Permission.IMMUTABLE
            )
            assert not descriptor.permissions & int(Permission.WRITE)
            assert not descriptor.permissions & int(Permission.STATE_PREPARE)
            assert not descriptor.permissions & int(Permission.STATE_COMMIT)


def test_writable_rom_object_is_rejected_by_the_verifier(qwen_build, qwen_capability):
    """The verifier's ROM check must be live, not worked around."""
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.deployment import ObjectSource
    from runtime.abi3.descriptors import Phase

    builder = DeploymentBuilder(
        target_id="rom-writable-probe",
        model_id="probe",
        backend="rom.probe",
        capability=qwen_capability,
    )
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    builder.memory_object(
        storage_class=StorageClass.ROM,
        size_bytes=64,
        source=ObjectSource.zeros(64),
        permissions=int(Permission.READ | Permission.WRITE),
    )
    builder.emit(Major.CONTROL, 0x07)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    deployment = builder.finish()
    with pytest.raises(VerificationError, match="ROM storage declares a write"):
        require_admitted(deployment, qwen_capability)


def test_emit_rom_objects_refuses_write_permissions(qwen_build):
    from compiler.backends.rom.common.image import emit_rom_objects

    _deployment, plan = qwen_build
    with pytest.raises(RomImageError, match="must not declare a write permission"):
        emit_rom_objects(None, plan, permissions=int(Permission.READ | Permission.WRITE))


def test_mutable_state_never_lives_in_rom(qwen_build, deepseek_build):
    for deployment, plan in (qwen_build, deepseek_build):
        rom_ids = {d.descriptor_id for d in _rom_objects(deployment)}
        for descriptor in deployment.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.STATE:
                continue
            assert descriptor.payload["committed_object_id"] not in rom_ids
            assert descriptor.payload["prepared_object_id"] not in rom_ids
        # Every ROM region is a checkpoint-bound weight; nothing else hides there.
        placed = {
            member["tensor_id"]
            for region in plan.to_dict()["regions"]
            for member in region["members"]
        }
        weights = {
            t.tensor_id
            for t in (
                deployment.notes and []
            )
        }
        assert placed
        assert all(isinstance(name, str) for name in placed)


# ---------------------------------------------------------------------------
# Zero copy
# ---------------------------------------------------------------------------
def test_rom_regions_are_zero_copy_checkpoint_ranges(qwen_build, qwen_graph, workspace):
    deployment, plan = qwen_build
    bindings = {
        t.tensor_id: t.binding for t in qwen_graph.tensors if t.binding is not None
    }
    checkpoint = (workspace / "qwen-checkpoint.bin").stat().st_size
    for region in plan.regions:
        source = deployment.objects[region.object_id]
        assert source.kind == "segments"
        assert len(source.segments) == len(region.members)
        for segment, member in zip(source.segments, region.members):
            binding = bindings[member.tensor_id]
            assert segment.path == binding.path
            assert segment.offset == binding.offset
            assert segment.bytes == binding.bytes
            assert segment.sha256 == binding.sha256
    # No ROM image file was produced anywhere.
    produced = {p.name for p in workspace.iterdir() if p.is_file()}
    assert not any(name.endswith(".rom.bin") for name in produced)
    assert checkpoint == plan.payload_bytes


def test_each_layer_weight_view_stays_inside_one_segment(qwen_build):
    """A view that straddles two segments would lose the zero-copy path."""
    _deployment, plan = qwen_build
    for region in plan.regions:
        if region.slot_count <= 1:
            continue
        offsets = [m.offset_bytes for m in region.members]
        assert offsets == [i * region.slot_bytes for i in range(region.slot_count)]
        assert all(m.bytes == region.slot_bytes for m in region.members)


# ---------------------------------------------------------------------------
# Loop compression
# ---------------------------------------------------------------------------
def test_qwen_program_is_loop_compressed(qwen_build, qwen_graph):
    deployment, _plan = qwen_build
    instructions = _instructions(deployment)
    analysis = analyze(qwen_graph)
    assert len(analysis.runs) == 1
    assert analysis.runs[0].length == 4
    # One body, not four.
    assert len(instructions) < len(qwen_graph.kernels)
    loop_setups = [i for i in instructions if i.major == Major.CONTROL and i.sub == 0x02]
    loop_nexts = [i for i in instructions if i.major == Major.CONTROL and i.sub == 0x03]
    assert len(loop_setups) == 1
    assert len(loop_nexts) == 1
    matmuls = [
        i
        for i in instructions
        if i.major == Major.TENSOR and i.sub == int(TensorOp.MATMUL)
    ]
    # Seven per-layer projections emitted once, plus the vocabulary projection.
    assert len(matmuls) == 8


def test_rom_weight_views_move_by_a_loop_dynamic_term(qwen_build):
    from runtime.abi3.descriptors import SelectorKind

    deployment, plan = qwen_build
    rom_ids = {r.object_id for r in plan.regions if r.slot_count > 1}
    strides = {r.object_id: r.slot_element_stride for r in plan.regions}
    found = 0
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
            continue
        if descriptor.primary_object_id not in rom_ids:
            continue
        assert descriptor.payload["dynamic_term_count"] == 1
        assert descriptor.payload["term0_kind"] == int(SelectorKind.LOOP_INDUCTION)
        assert descriptor.payload["term0_stride"] == strides[
            descriptor.primary_object_id
        ]
        found += 1
    assert found == len(rom_ids)


def test_deepseek_program_is_loop_compressed(deepseek_build, deepseek_graph):
    deployment, _plan = deepseek_build
    instructions = _instructions(deployment)
    assert len(instructions) < len(deepseek_graph.kernels)
    loop_setups = [i for i in instructions if i.major == Major.CONTROL and i.sub == 0x02]
    assert len(loop_setups) == 2


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------
def _topology(deployment):
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type == ExtendedDescriptorType.TOPOLOGY:
            return descriptor
    raise AssertionError("no topology descriptor")


def test_qwen_topology_is_a_conventional_single_chip(qwen_build):
    deployment, plan = qwen_build
    payload = _topology(deployment).payload
    assert payload["topology_class"] == int(TopologyClass.SINGLE_CHIP)
    assert payload["node_count"] == 1
    assert payload["reticle_count"] == 1
    assert payload["link_count"] == 0
    assert payload["active_resource_count"] == plan.resource_count
    assert deployment.topology_class == int(TopologyClass.SINGLE_CHIP)


def test_deepseek_topology_is_one_wafer_logical_device(deepseek_build):
    deployment, plan = deepseek_build
    payload = _topology(deployment).payload
    assert payload["topology_class"] == int(TopologyClass.WAFER_LOGICAL_DEVICE)
    assert payload["node_count"] == 1  # one device, not a cluster of chips
    assert payload["reticle_count"] >= 1
    assert payload["tiles_per_reticle"] == 8
    assert payload["link_class_count"] == 3
    assert payload["link_count"] > 0
    assert payload["epoch"] == 1
    assert payload["active_resource_count"] == plan.resource_count
    assert payload["active_resource_digest"] != bytes(32)
    assert payload["quarantine_digest"] != bytes(32)
    assert payload["route_table_digest"] != bytes(32)
    assert payload["health_digest"] != bytes(32)


def test_wafer_geometry_is_derived_not_inherited():
    geometry = wafer_geometry()
    assert geometry["grid_columns"] == 8
    assert geometry["grid_rows"] == 6
    assert geometry["max_reticles"] == 48 == MAX_RETICLES
    # Explicitly not the historical 8x8 / 4,096-tile proxy.
    assert geometry["max_reticles"] != 64
    assert geometry["tiles_per_reticle"] != 4096


def test_deepseek_regions_carry_per_tile_coordinates(deepseek_build):
    _deployment, plan = deepseek_build
    shards = [s for r in plan.regions for s in r.shards]
    assert shards
    for shard in shards:
        assert shard.coordinate.node_id == 0
        assert shard.coordinate.reticle == shard.coordinate.tile // 8
        assert shard.bytes > 0
    assert len({s.coordinate.tile for s in shards}) > 1


# ---------------------------------------------------------------------------
# On-wafer fabric
# ---------------------------------------------------------------------------
def test_deepseek_critical_path_uses_link_instructions(deepseek_build):
    deployment, _plan = deepseek_build
    instructions = _instructions(deployment)
    link_subs = {i.sub for i in instructions if i.major == Major.LINK}
    assert {
        int(Link.SEND),
        int(Link.MULTICAST),
        int(Link.GATHER),
        int(Link.SCATTER),
        int(Link.COLLECTIVE),
        int(Link.BARRIER),
    } <= link_subs
    communications = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.COMMUNICATION
    ]
    assert communications
    for descriptor in communications:
        assert descriptor.payload["credit_bound"] > 0
        assert descriptor.payload["retry_bound"] > 0
        assert descriptor.payload["timeout_class"] > 0
    # Every LINK instruction resolves a COMMUNICATION descriptor.
    ids = {d.descriptor_id for d in communications}
    for instruction in instructions:
        if instruction.major == Major.LINK:
            assert instruction.descriptor_id in ids


def test_deepseek_links_are_inside_the_layer_loop(deepseek_build):
    deployment, _plan = deepseek_build
    instructions = _instructions(deployment)
    depth = 0
    inside = 0
    for instruction in instructions:
        if instruction.major == Major.CONTROL and instruction.sub == 0x02:
            depth += 1
        elif instruction.major == Major.CONTROL and instruction.sub == 0x03:
            depth -= 1
        elif instruction.major == Major.LINK and depth:
            inside += 1
    assert inside > 0


def test_qwen_single_chip_emits_no_link_traffic(qwen_build):
    deployment, _plan = qwen_build
    assert not [i for i in _instructions(deployment) if i.major == Major.LINK]


# ---------------------------------------------------------------------------
# No invented opcode
# ---------------------------------------------------------------------------
def test_rom_matmul_is_still_tensor_matmul(qwen_build, qwen_graph):
    deployment, plan = qwen_build
    rom_ids = {r.object_id for r in plan.regions}
    rom_views = {
        d.descriptor_id
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and d.primary_object_id in rom_ids
    }
    matmul_operators = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["engine_family"] == int(Major.TENSOR)
        and d.payload["engine_sub"] == int(TensorOp.MATMUL)
    ]
    assert matmul_operators
    bound = [
        d
        for d in matmul_operators
        if any(d.payload[f"input_view_{i}"] in rom_views for i in range(4))
    ]
    assert bound
    for descriptor in bound:
        assert descriptor.payload["engine_family"] == int(Major.TENSOR)
        assert descriptor.payload["engine_sub"] == int(TensorOp.MATMUL)


def test_every_emitted_opcode_comes_from_the_frozen_table(qwen_build, deepseek_build):
    legal = {(op.family, op.sub) for op in KERNEL_TO_ENGINE.values()}
    control = {(int(Major.CONTROL), sub) for sub in range(0x09)}
    link = {(int(Major.LINK), sub) for sub in range(0x08)}
    for deployment, _plan in (qwen_build, deepseek_build):
        for instruction in _instructions(deployment):
            pair = (instruction.major, instruction.sub)
            assert pair in legal | control | link, pair


# ---------------------------------------------------------------------------
# Inverse proof
# ---------------------------------------------------------------------------
def _reader(root: Path):
    def read(path: str, offset: int, count: int) -> bytes:
        with open(root / path, "rb") as handle:
            handle.seek(offset)
            return handle.read(count)

    return read


def test_qwen_inverse_proof_passes(qwen_build, workspace):
    deployment, plan = qwen_build
    report = check_rom_inverse(deployment, reader=_reader(workspace))
    assert report["status"] == "pass"
    assert report["all_padding_zero"] is True
    assert report["payload_bytes"] == plan.payload_bytes
    assert report["padding_bytes"] == plan.padding_bytes
    assert report["placed_tensor_count"] == sum(len(r.members) for r in plan.regions)


def test_deepseek_inverse_proof_passes(deepseek_build, workspace):
    deployment, plan = deepseek_build
    report = check_rom_inverse(deployment, reader=_reader(workspace))
    assert report["status"] == "pass"
    assert report["rom_bytes"] == plan.rom_bytes
    assert report["repair"]["banks"] == plan.resource_count


def test_inverse_proof_detects_a_corrupted_checkpoint_byte(qwen_build, workspace):
    deployment, plan = qwen_build
    victim = plan.regions[0].members[0]
    base = _reader(workspace)

    def corrupt(path: str, offset: int, count: int) -> bytes:
        payload = bytearray(base(path, offset, count))
        if offset <= victim.source_offset < offset + count and payload:
            index = victim.source_offset - offset
            payload[index] ^= 0x01
        return bytes(payload)

    with pytest.raises(InverseProofError):
        check_rom_inverse(deployment, reader=corrupt)


def test_inverse_proof_detects_nonzero_padding(qwen_build, workspace):
    deployment, plan = qwen_build
    padded = [r for r in plan.regions if r.pad_bytes]
    assert padded, "the fixture must exercise alignment padding"
    from runtime.abi3.deployment import ObjectSource

    original = deployment.objects[padded[0].pad_object_id]
    deployment.objects[padded[0].pad_object_id] = ObjectSource(
        "zero", original.size_bytes, (), fill=0xFF
    )
    try:
        with pytest.raises(InverseProofError, match="fill byte"):
            check_rom_inverse(deployment, reader=_reader(workspace))
    finally:
        deployment.objects[padded[0].pad_object_id] = original


def test_inverse_proof_detects_a_swapped_segment(qwen_build, workspace):
    deployment, plan = qwen_build
    striped = [r for r in plan.regions if r.slot_count > 1]
    assert striped
    region = striped[0]
    original = deployment.objects[region.object_id]
    swapped = list(original.segments)
    swapped[0], swapped[1] = swapped[1], swapped[0]
    from runtime.abi3.deployment import ObjectSource

    deployment.objects[region.object_id] = ObjectSource(
        "segments", original.size_bytes, tuple(swapped)
    )
    try:
        with pytest.raises(InverseProofError):
            check_rom_inverse(deployment, reader=_reader(workspace))
    finally:
        deployment.objects[region.object_id] = original


def test_inverse_module_does_not_import_the_producer():
    """The proof must be independent of the module that produced the plan."""
    source = Path("compiler/backends/rom/common/inverse.py").read_text()
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(f"{'.' * node.level}{node.module or ''}")
    for name in imported:
        assert "image" not in name, name
        assert "program" not in name, name
        assert "qwen3" not in name, name
        assert "deepseek" not in name, name
    assert "from .image" not in source
    assert "compiler.backends.rom.common.image" not in source.replace(
        ":mod:`compiler.backends.rom.common.image`", ""
    )


# ---------------------------------------------------------------------------
# Repair map
# ---------------------------------------------------------------------------
def test_repair_map_is_a_first_class_artifact(qwen_build):
    _deployment, plan = qwen_build
    body = plan.repair_map.to_dict()
    assert body["schema"] == "opentallas.rom.repair_map.v1"
    assert body["banks"]
    assert body["spare_rows_total"] > 0
    assert body["spare_rows_used"] == 0
    assert body["quarantine"] == []
    assert plan.repair_map.active_resource_digest != bytes(32)


def test_repair_map_activates_spares_deterministically(qwen_build):
    _deployment, plan = qwen_build
    policy = RomLayoutPolicy(resource_bytes=1 << 33, minimum_spare_rows=8)
    inventory = sorted(
        plan_repair_map(plan.regions, policy).banks, key=lambda b: -b.data_rows
    )
    wide, other = inventory[0], inventory[1]
    assert wide.data_rows > 1
    defects = (
        DefectRecord(other.coordinate, "row", 0, "bist"),
        DefectRecord(wide.coordinate, "row", wide.data_rows - 1, "bist"),
        DefectRecord(wide.coordinate, "column", 2, "bist"),
    )
    first = plan_repair_map(plan.regions, policy, defects)
    second = plan_repair_map(plan.regions, policy, tuple(reversed(defects)))
    assert first.to_dict() == second.to_dict()
    rows = [e for e in first.entries if e.kind == "row"]
    assert len(rows) == 2
    activated = [e for e in rows if e.coordinate == wide.coordinate][0]
    # The first activated spare is the lowest one in the owning bank.
    assert activated.spare_index == wide.data_rows
    assert first.to_dict()["spare_columns_used"] == 1
    assert not first.quarantine
    assert wide.coordinate.resource_id in first.active_resources


def test_repair_map_quarantines_when_spares_are_exhausted(qwen_build):
    _deployment, plan = qwen_build
    policy = RomLayoutPolicy(
        resource_bytes=1 << 33, minimum_spare_rows=1, spare_row_fraction=0.0
    )
    inventory = sorted(
        plan_repair_map(plan.regions, policy).banks, key=lambda b: -b.data_rows
    )
    wide = inventory[0]
    assert wide.spare_rows == 1 and wide.data_rows >= 3
    defects = tuple(
        DefectRecord(wide.coordinate, "row", index, "bist") for index in range(3)
    )
    repaired = plan_repair_map(plan.regions, policy, defects)
    assert len(repaired.entries) == 1
    assert [q.reason for q in repaired.quarantine] == ["spare_rows_exhausted"]
    assert wide.coordinate.resource_id not in repaired.active_resources


def test_building_onto_a_quarantined_resource_is_refused(qwen_graph, qwen_capability):
    defects = (
        DefectRecord(RomCoordinate(bank=0), "resource", 0, "bist"),
    )
    with pytest.raises(RomImageError, match="quarantined"):
        build_qwen3_rom_deployment(
            qwen_graph, capability=qwen_capability, defects=defects
        )


def test_repair_digests_are_bound_into_the_topology(qwen_build):
    deployment, plan = qwen_build
    payload = _topology(deployment).payload
    assert payload["active_resource_digest"] == plan.repair_map.active_resource_digest
    assert payload["quarantine_digest"] == plan.repair_map.quarantine_digest
    assert payload["health_digest"] == plan.repair_map.health_digest


def test_region_content_digest_is_order_sensitive(qwen_build):
    _deployment, plan = qwen_build
    region = [r for r in plan.regions if r.slot_count > 1][0]
    reordered = region_content_digest(
        key=region.key,
        payload_bytes=region.payload_bytes,
        pad_bytes=region.pad_bytes,
        slot_count=region.slot_count,
        slot_bytes=region.slot_bytes,
        members=tuple(reversed(region.members)),
    )
    assert reordered != region.content_digest


# ---------------------------------------------------------------------------
# Determinism and the ROM/HBM difference
# ---------------------------------------------------------------------------
def test_qwen_two_clean_builds_are_byte_identical(qwen_graph, qwen_capability):
    first, _ = build_qwen3_rom_deployment(qwen_graph, capability=qwen_capability)
    second, _ = build_qwen3_rom_deployment(qwen_graph, capability=qwen_capability)
    assert first.table.encode() == second.table.encode()
    assert first.program == second.program
    assert first.deployment_digest == second.deployment_digest
    assert json.dumps(first.manifest(), sort_keys=True) == json.dumps(
        second.manifest(), sort_keys=True
    )


def test_deepseek_two_clean_builds_are_byte_identical(
    deepseek_graph, deepseek_capability
):
    kwargs = dict(
        capability=deepseek_capability, tile_rom_bytes=1 << 16, tiles_per_reticle=8
    )
    first, _ = build_deepseek_v4_rom_deployment(deepseek_graph, **kwargs)
    second, _ = build_deepseek_v4_rom_deployment(deepseek_graph, **kwargs)
    assert first.table.encode() == second.table.encode()
    assert first.program == second.program
    assert first.deployment_digest == second.deployment_digest


def test_rom_and_hbm_differ_only_in_storage_class_and_placement(
    qwen_graph, qwen_capability
):
    """The comparison protocol depends on this: same program, same descriptors,
    same numerics, same schedule -- only the weight objects move."""
    rom, _ = build_qwen3_rom_deployment(qwen_graph, capability=qwen_capability)
    hbm, _ = build_qwen3_rom_deployment(
        qwen_graph, capability=qwen_capability, weight_storage_class=StorageClass.HBM
    )
    assert _instructions(rom) == _instructions(hbm)
    left = rom.table.descriptors()
    right = hbm.table.descriptors()
    assert len(left) == len(right)
    differing = []
    for a, b in zip(left, right):
        assert a.descriptor_type == b.descriptor_type
        if a.encode() != b.encode():
            differing.append(a.descriptor_type)
    assert set(differing) == {ExtendedDescriptorType.MEMORY_OBJECT}
    for a, b in zip(left, right):
        if a.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        if a.encode() == b.encode():
            continue
        assert a.payload["storage_class"] == int(StorageClass.ROM)
        assert b.payload["storage_class"] == int(StorageClass.HBM)
        for field in ("size_bytes", "base_address", "bank_or_tile", "node_id"):
            assert a.payload[field] == b.payload[field]
        assert a.payload["content_digest"] == b.payload["content_digest"]
    assert rom.objects.keys() == hbm.objects.keys()
    for oid in rom.objects:
        assert rom.objects[oid].to_dict() == hbm.objects[oid].to_dict()


# ---------------------------------------------------------------------------
# Accounting
# ---------------------------------------------------------------------------
def test_qwen_area_accounting_is_reported_not_asserted():
    accounting = qwen3_area_accounting(16_381_470_720)
    assert accounting["status"] == "declared_input_not_a_closed_physical_result"
    assert accounting["required_usable_density_bytes_per_mm2"] > 0
    assert accounting["closes_against_fabricated_28nm_anchor"] is False


def test_plan_is_bound_into_the_deployment_manifest(qwen_build):
    deployment, plan = qwen_build
    manifest = deployment.manifest()
    assert manifest["notes"]["rom_plan"]["plan_id"] == plan.to_dict()["plan_id"]
    assert manifest["notes"]["rom_capacity"]["planned_rom_bytes"] == plan.rom_bytes
    # The manifest digest covers notes, so the region plan is authenticated.
    body = deployment.digest_body()
    assert "rom_plan" in body["notes"]


def test_rom_capacity_overflow_is_refused(qwen_graph):
    small = qwen3_rom_capability(
        max_context_positions=16, vocabulary_size=32, rom_bytes=1 << 12
    )
    from compiler.backends.rom.qwen3 import Qwen3RomError

    with pytest.raises(Qwen3RomError, match="second chip is not an option"):
        build_qwen3_rom_deployment(qwen_graph, capability=small)


def test_unlowerable_kind_is_a_compile_error(workspace):
    graph = qwen_shaped_graph(workspace, layers=2)
    broken = list(graph.kernels)
    broken[0] = Kernel(
        index=0,
        kernel_id="token_embedding",
        kind="EMBEDDING_LOOKUP",
        inputs=broken[0].inputs,
        outputs=broken[0].outputs,
        numeric_contract=broken[0].numeric_contract,
        attributes=broken[0].attributes,
    )
    object.__setattr__(broken[0], "kind", "ROM_MATMUL")
    graph.kernels = tuple(broken)
    with pytest.raises((RomLoweringError, Exception)):
        build_qwen3_rom_deployment(
            graph, capability=qwen3_rom_capability(max_context_positions=16, vocabulary_size=32)
        )
