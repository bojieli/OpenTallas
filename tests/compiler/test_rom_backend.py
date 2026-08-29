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
from typing import Any

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
    NO_ID,
    ParticipantScope,
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

    def _payload(self, size: int, dtype: str = "u8") -> bytes:
        self.seed = (self.seed * 1103515245 + 12345) & 0xFFFFFFFF
        raw = hashlib.shake_128(str(self.seed).encode("ascii")).digest(size)
        if dtype != "bf16" or size % 2:
            return raw
        # A random bit pattern is a valid BF16 code but not a plausible weight:
        # its exponent ranges over the whole format, and the numeric contracts
        # fail closed on the overflow that follows.  Constraining the exponent
        # to [2^-3, 2) keeps the fixture exercising real arithmetic.
        codes = bytearray(raw)
        for index in range(0, size, 2):
            value = codes[index] | (codes[index + 1] << 8)
            exponent = 124 + ((value >> 5) & 0x03)
            value = (value & 0x807F) | (exponent << 7)
            codes[index] = value & 0xFF
            codes[index + 1] = value >> 8
        return bytes(codes)

    def weight(
        self,
        tensor_id: str,
        dtype: str,
        shape: tuple[int, ...],
        *,
        scale_block_elements: int = 0,
        scale_dtype: str = "e8m0",
    ) -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        size = (elements * DTYPE_BITS_BY_NAME[dtype] + 7) // 8
        offset = len(self.blob)
        payload = self._payload(size, dtype)
        self.blob.extend(payload)
        scale_id: str | None = None
        if scale_block_elements:
            scale_id = f"{tensor_id.rsplit('.', 1)[0]}.scale"
            scale_shape = (*shape[:-1], shape[-1] // scale_block_elements)
            self.weight(scale_id, scale_dtype, scale_shape)
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
                scale_tensor_id=scale_id,
                scale_block_elements=scale_block_elements,
            )
        )
        return tensor_id

    def constant(
        self,
        tensor_id: str,
        dtype: str,
        shape: tuple[int, ...],
        generator: str,
        parameters: dict[str, Any],
    ) -> str:
        """A derived constant: no checkpoint range, an attested generator."""
        self.tensors.append(
            Tensor(
                tensor_id=tensor_id,
                dtype=dtype,
                shape=shape,
                role="constant",
                generator=generator,
                generator_parameters=parameters,
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
    heads, kv_heads, vocabulary = 4, 2, 32
    head_dim = hidden // heads
    kv_width = kv_heads * head_dim
    intermediate = 2 * hidden
    # One checkpoint file per configuration, so a differently shaped fixture
    # never clobbers another test's authenticated bytes.
    builder = _GraphBuilder(
        root / f"qwen-checkpoint-l{layers}-h{hidden}-s{span_max}.bin", seed=11
    )
    span = Symbolic("span_tokens", 1, span_max)
    context = Symbolic("context_tokens", 1, span_max)

    token_ids = builder.value("input.token_ids", "u32", (span,), "input")
    positions = builder.value("input.positions", "u32", (span,), "input")
    rope_table = builder.constant(
        "rope.coefficient_table",
        "fp32",
        (span_max, 2 * head_dim),
        "rope_coefficients_v1",
        {"head_dim": head_dim, "maximum_position": span_max, "theta": 1000000.0},
    )
    rope_rows = builder.value(
        "rope.coefficient_rows", "fp32", (span, 2 * head_dim), "activation"
    )
    builder.kernel(
        "rope.coefficient_gather",
        "GATHER",
        (positions, rope_table),
        (rope_rows,),
        contract="exact_index_select_v1",
        attributes={"input_dtype": "u32", "output_dtype": "fp32"},
    )
    embed = builder.weight("model.embed_tokens.weight", "bf16", (vocabulary, hidden))
    residual = builder.value("sequence.embedding", "bf16", (span, hidden), "activation")
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, embed),
        (residual,),
        contract="bf16_payload_lookup_v1",
        attributes={"input_dtype": "u32", "output_dtype": "bf16"},
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
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        query = builder.value(
            f"{prefix}.attention.query", "bf16", (span, heads, head_dim), "activation"
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
            f"{prefix}.attention.key", "bf16", (span, kv_heads, head_dim), "activation"
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
            f"{prefix}.attention.value", "bf16", (span, kv_heads, head_dim), "activation"
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
            f"{prefix}.attention.query_normalized",
            "bf16",
            (span, heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.query_head_norm",
            "HEAD_RMS_NORM",
            (query, builder.weight(f"{base}.self_attn.q_norm.weight", "bf16", (head_dim,))),
            (query_normalized,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        key_normalized = builder.value(
            f"{prefix}.attention.key_normalized",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.key_head_norm",
            "HEAD_RMS_NORM",
            (key, builder.weight(f"{base}.self_attn.k_norm.weight", "bf16", (head_dim,))),
            (key_normalized,),
            contract="qwen3_rmsnorm_fp32_bf16_v1",
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        query_rotated = builder.value(
            f"{prefix}.attention.query_rotated",
            "bf16",
            (span, heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.query_rotation",
            "ROPE",
            (query_normalized, rope_rows),
            (query_rotated,),
            contract="qwen3_rope_fp32_bf16_v1",
            layer=layer,
            attributes={
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "second_input_dtype": "fp32",
            },
        )
        key_rotated = builder.value(
            f"{prefix}.attention.key_rotated",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.key_rotation",
            "ROPE",
            (key_normalized, rope_rows),
            (key_rotated,),
            contract="qwen3_rope_fp32_bf16_v1",
            layer=layer,
            attributes={
                "input_dtype": "bf16",
                "output_dtype": "bf16",
                "second_input_dtype": "fp32",
            },
        )
        appended_key = builder.value(
            f"{prefix}.attention.appended_key",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.key_append",
            "KV_APPEND",
            (key_rotated, positions),
            (appended_key,),
            contract="bf16_byte_preserving_state_v1",
            layer=layer,
            state_writes=(state_id,),
        )
        appended_value = builder.value(
            f"{prefix}.attention.appended_value",
            "bf16",
            (span, kv_heads, head_dim),
            "activation",
        )
        builder.kernel(
            f"{prefix}.attention.value_append",
            "KV_APPEND",
            (value, positions),
            (appended_value,),
            contract="bf16_byte_preserving_state_v1",
            layer=layer,
            state_writes=(state_id,),
        )
        key_history = builder.value(
            f"{prefix}.attention.key_history",
            "bf16",
            (context, kv_heads, head_dim),
            "state",
        )
        value_history = builder.value(
            f"{prefix}.attention.value_history",
            "bf16",
            (context, kv_heads, head_dim),
            "state",
        )
        attention_context = builder.value(
            f"{prefix}.attention.context", "bf16", (span, heads, head_dim), "activation"
        )
        builder.kernel(
            f"{prefix}.attention.gqa",
            "ATTENTION_GQA",
            (query_rotated, key_history, value_history, positions),
            (attention_context,),
            contract="qwen3_gqa_fp32_softmax_bf16_v1",
            attributes={
                "causal": True,
                "query_heads_per_key_value_head": heads // kv_heads,
                "scale_bf16_code": 16000,
            },
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
            attributes={"epsilon": 1e-06},
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
        attributes={"epsilon": 1e-06},
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
    selected = builder.value("output.selected", "u32", (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        contract="greedy_lowest_token_id_argmax_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "u32"},
    )
    next_token = builder.value("output.next_token", "u32", (1,), "output")
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
    sequence: tuple[str, ...] | None = None,
) -> KernelGraph:
    """An MoE DeepSeek-shaped block: two layer classes, routed experts, sparse
    attention, FP8 dense weights and MXFP4 expert weights with E8M0 scales."""
    kv_width, experts, expert_width, vocabulary = 32, 8, 96, 32
    if sequence is None:
        sequence = ("dense",) * dense_layers + ("moe",) * moe_layers
    tag = "".join(kind[0] for kind in sequence)
    builder = _GraphBuilder(
        root / f"deepseek-checkpoint-{tag}-h{hidden}.bin", seed=97
    )
    span = Symbolic("span_tokens", 1, span_max)
    context = Symbolic("context_tokens", 1, span_max)
    layers = len(sequence)

    token_ids = builder.value("input.token_ids", "u32", (span,), "input")
    positions = builder.value("input.positions", "u32", (span,), "input")
    embed = builder.weight("model.embed_tokens.weight", "bf16", (vocabulary, hidden))
    residual = builder.value("sequence.embedding", "bf16", (span, hidden), "activation")
    builder.kernel(
        "token_embedding",
        "EMBEDDING_LOOKUP",
        (token_ids, embed),
        (residual,),
        contract="bf16_payload_lookup_v1",
        attributes={"input_dtype": "u32", "output_dtype": "bf16"},
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
        moe = sequence[layer] == "moe"
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
            attributes={"epsilon": 1e-06},
            layer=layer,
        )
        query = builder.value(f"{prefix}.query", "bf16", (span, hidden), "activation")
        builder.kernel(
            f"{prefix}.query_projection",
            "MATMUL",
            (norm, builder.weight(
                    f"{base}.self_attn.q_proj.weight",
                    "fp8_e4m3fn",
                    (hidden, hidden),
                    scale_block_elements=32,
                )),
            (query,),
            contract="fp8_e4m3fn_fp8_e4m3fn_fp32_sequential_rne_v1",
            attributes={"input_dtype": "bf16", "second_input_dtype": "fp8_e4m3fn"},
            layer=layer,
        )
        latent = builder.value(f"{prefix}.latent", "bf16", (span, kv_width), "activation")
        builder.kernel(
            f"{prefix}.key_value_projection",
            "MATMUL",
            (norm, builder.weight(
                    f"{base}.self_attn.kv_proj.weight",
                    "fp8_e4m3fn",
                    (kv_width, hidden),
                    scale_block_elements=32,
                )),
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
            (attention, builder.weight(
                    f"{base}.self_attn.o_proj.weight",
                    "fp8_e4m3fn",
                    (hidden, hidden),
                    scale_block_elements=32,
                )),
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
            attributes={"epsilon": 1e-06},
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
            dispatched_ids = builder.value(
                f"{prefix}.dispatched_ids", "u32", (span, 2), "activation"
            )
            builder.kernel(
                f"{prefix}.expert_dispatch",
                "EXPERT_DISPATCH",
                (feed_forward_norm, expert_ids),
                (dispatched, dispatched_ids),
                contract="deepseek_v4_router_fp32_sigmoid_v1",
                attributes={"expert_count": experts},
                layer=layer,
            )
            expert_output = builder.value(
                f"{prefix}.expert_output", "bf16", (span, 2, expert_width), "activation"
            )
            # The routed bank is named by attribute, exactly as the DeepSeek
            # front end does: one tensor per expert, ascending logical ID.
            bank = [
                builder.weight(
                    f"{base}.mlp.experts.{expert}.w1.weight",
                    "mxfp4_e2m1",
                    (expert_width, hidden),
                    scale_block_elements=32,
                )
                for expert in range(experts)
            ]
            builder.kernel(
                f"{prefix}.routed_projection",
                "ROUTED_MATMUL",
                (dispatched, dispatched_ids),
                (expert_output,),
                contract="mxfp4_e2m1_fp8_e4m3fn_fp32_blocked_rne_v1",
                attributes={
                    "expert_count": experts,
                    "expert_weight_block_elements": 32,
                    "expert_weight_dtype": "mxfp4_e2m1",
                    "expert_weight_order": "ascending_logical_expert_id",
                    "expert_weight_tensors": bank,
                    "input_dtype": "bf16",
                    "second_input_dtype": "mxfp4_e2m1",
                },
                layer=layer,
            )
            feed_forward_output = builder.value(
                f"{prefix}.feed_forward_output", "bf16", (span, hidden), "activation"
            )
            builder.kernel(
                f"{prefix}.expert_reduce",
                "EXPERT_REDUCE",
                (expert_output, expert_weights, dispatched_ids),
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
        attributes={"epsilon": 1e-06},
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
    selected = builder.value("output.selected", "u32", (1,), "activation")
    builder.kernel(
        "token_selection",
        "ARGMAX",
        (logits,),
        (selected,),
        contract="greedy_lowest_token_id_argmax_v1",
        attributes={"input_dtype": "bf16", "output_dtype": "u32"},
    )
    next_token = builder.value("output.next_token", "u32", (1,), "output")
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
        # Every ROM region member is a checkpoint-bound weight, so no mutable
        # value can be hiding inside a mask image.
        for region in plan.regions:
            assert region.role in {
                "expert_bank",
                "expert_bank_scale",
                "global_weight",
                "global_weight_scale",
                "layer_weight",
                "layer_weight_scale",
            }
            for member in region.members:
                assert member.source_sha256
                assert member.bytes > 0
        # Mutable objects live only in SRAM, HBM, STATE or HOST.
        mutable = [
            d
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
            and d.permissions
            & int(Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT)
        ]
        assert mutable
        for descriptor in mutable:
            assert descriptor.payload["storage_class"] in {
                int(StorageClass.SRAM),
                int(StorageClass.HBM),
                int(StorageClass.STATE),
                int(StorageClass.HOST),
            }


# ---------------------------------------------------------------------------
# Zero copy
# ---------------------------------------------------------------------------
def test_rom_regions_are_zero_copy_checkpoint_ranges(qwen_build, qwen_graph, workspace):
    deployment, plan = qwen_build
    bindings = {
        t.tensor_id: t.binding for t in qwen_graph.tensors if t.binding is not None
    }
    checkpoint = (workspace / "qwen-checkpoint-l4-h64-s16.bin").stat().st_size
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
def _engine_dispatches(instructions) -> int:
    """Instructions that issue engine work, i.e. everything a loop repeats."""
    return sum(
        1
        for i in instructions
        if i.major not in (int(Major.CONTROL), int(Major.OBSERVATION))
    )


def _loops(deployment, *, symbolic: bool | None = None):
    from runtime.abi3.descriptors import SelectorKind

    out = []
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.LOOP_CONTROL:
            continue
        is_symbolic = (
            descriptor.payload["bound_selector_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
        )
        if symbolic is None or is_symbolic == symbolic:
            out.append(descriptor)
    return out


def test_qwen_program_is_loop_compressed(qwen_build, qwen_graph):
    deployment, _plan = qwen_build
    instructions = _instructions(deployment)
    analysis = analyze(qwen_graph)
    assert len(analysis.runs) == 1
    assert analysis.runs[0].length == 4
    # One body, not four: what compression removes is engine dispatches, so
    # that is what the count is taken over.  Control instructions are the loops
    # doing the removing.
    assert _engine_dispatches(instructions) < len(qwen_graph.kernels)
    setups = [i for i in instructions if i.major == Major.CONTROL and i.sub == 0x02]
    nexts = [i for i in instructions if i.major == Major.CONTROL and i.sub == 0x03]
    assert len(setups) == len(nexts)
    # Exactly one layer loop; the rest are token blocks.
    assert len(_loops(deployment, symbolic=False)) == 1
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
    assert _engine_dispatches(instructions) < len(deepseek_graph.kernels)
    assert len(_loops(deployment, symbolic=False)) == 2


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


# ---------------------------------------------------------------------------
# Tile mapping lives in the SCHEDULE descriptor, never in program loops
# ---------------------------------------------------------------------------
def _schedules(deployment):
    return [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.SCHEDULE
    ]


def test_schedule_payloads_are_real(qwen_build, deepseek_build):
    for deployment, plan in (qwen_build, deepseek_build):
        schedules = _schedules(deployment)
        assert schedules
        for descriptor in schedules:
            payload = descriptor.payload
            assert payload["tile_rows"] >= 1
            assert payload["tile_cols"] >= 1
            assert payload["tile_depth"] >= 1
            assert payload["issue_window"] >= 1
            assert payload["max_outstanding"] >= 1
            assert payload["resource_bound"] >= 1
            assert payload["engine_family"] in {
                int(Major.DMA),
                int(Major.TENSOR),
                int(Major.VECTOR),
                int(Major.ATTENTION),
                int(Major.ROUTE),
                int(Major.REDUCTION),
                int(Major.SELECTION),
            }
        # Every operator names one, and no operator shares a placeholder.
        operators = [
            d
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        ]
        ids = {d.descriptor_id for d in schedules}
        for operator in operators:
            assert operator.payload["schedule_id"] in ids


def test_rom_reading_operators_declare_bank_and_rom_bound(qwen_build):
    from compiler.backends.rom.common.program import ResourceBound

    deployment, plan = qwen_build
    rom_ids = {r.object_id for r in plan.regions}
    views = {
        d.descriptor_id: d.primary_object_id
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
    }
    schedules = {d.descriptor_id: d.payload for d in _schedules(deployment)}
    checked = 0
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        if descriptor.payload["engine_family"] != int(Major.TENSOR):
            continue
        reads_rom = any(
            views.get(descriptor.payload[f"input_view_{i}"]) in rom_ids
            for i in range(4)
        )
        if not reads_rom:
            continue
        payload = schedules[descriptor.payload["schedule_id"]]
        assert payload["bank_mask"] != 0
        assert payload["resource_bound"] == ResourceBound.ROM_READ
        checked += 1
    assert checked >= 8


def test_tile_mapping_is_not_a_program_loop(qwen_build, qwen_graph):
    """A program loop varies the work; a tile is a schedule field.

    Two loop kinds are legitimate: the layer run and the token block.  A third --
    one loop per output tile or per reduction tile -- would put the engine's own
    decomposition into the instruction stream, which is the retired-work failure
    ABI 3.0 exists to remove.
    """
    from runtime.abi3.descriptors import Symbol

    deployment, _plan = qwen_build
    layer_loops = _loops(deployment, symbolic=False)
    assert len(layer_loops) == len(analyze(qwen_graph).runs)
    for descriptor in layer_loops:
        assert descriptor.payload["max_iterations"] == 4  # the layer count
    block_loops = _loops(deployment, symbolic=True)
    assert block_loops, "a symbolic span must be carried by a token-block loop"
    for descriptor in block_loops:
        payload = descriptor.payload
        # Amendment A13: the loop counts blocks, so its divisor is the block and
        # its induction value is the block index the resolver reads.
        assert payload["step"] == 1
        assert payload["bound_divisor"] > 0
        assert Symbol(payload["bound_symbol_id"]) is Symbol.SPAN_TOKENS
        assert payload["max_iterations"] == payload["upper_bound"]
    schedules = _schedules(deployment)
    assert len(schedules) >= len(block_loops) // 4


def test_schedule_tiles_are_real_at_wider_shapes(tmp_path):
    """A shape wider than the lane array decomposes into several tiles."""
    graph = qwen_shaped_graph(tmp_path, layers=2, hidden=1024, span_max=256)
    capability = qwen3_rom_capability(max_context_positions=256, vocabulary_size=32)
    deployment, _plan = build_qwen3_rom_deployment(graph, capability=capability)
    require_admitted(deployment, capability)
    tensor_schedules = [
        d.payload
        for d in _schedules(deployment)
        if d.payload["engine_family"] == int(Major.TENSOR)
    ]
    assert tensor_schedules
    assert any(payload["tile_cols"] < 1024 for payload in tensor_schedules)
    assert any(payload["max_outstanding"] > 1 for payload in tensor_schedules)
    assert any(payload["issue_window"] > 1 for payload in tensor_schedules)


# ---------------------------------------------------------------------------
# Numeric contracts (TA-ABI3-OPCONV-1 amendments A7 and A8)
# ---------------------------------------------------------------------------
def test_execution_operators_declare_the_blocked_contract(qwen_build):
    from runtime.abi3.crc import sha256

    deployment, _plan = qwen_build
    blocked = sha256(b"bf16_bf16_fp32_blocked_rne_v1")
    sequential = sha256(b"bf16_bf16_fp32_sequential_rne_v1")
    digests = {
        d.payload["contract_digest"]
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.NUMERIC
    }
    assert blocked in digests
    assert sequential not in digests
    notes = deployment.notes["rom_lowering"]["numeric_contract_substitutions"]
    assert notes["bf16_bf16_fp32_sequential_rne_v1"] == (
        "bf16_bf16_fp32_blocked_rne_v1"
    )


def test_rmsnorm_declares_a_pairwise_tree_reduction(qwen_build):
    from runtime.abi3.constants import ReductionOrder
    from runtime.abi3.crc import sha256

    deployment, _plan = qwen_build
    target = sha256(b"qwen3_rmsnorm_fp32_bf16_v1")
    found = [
        d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.NUMERIC
        and d.payload["contract_digest"] == target
    ]
    assert found
    for payload in found:
        assert payload["reduction_order"] == int(ReductionOrder.PAIRWISE_TREE)


def test_rom_and_hbm_share_the_numeric_profile(qwen_graph, qwen_capability):
    rom, _ = build_qwen3_rom_deployment(qwen_graph, capability=qwen_capability)
    hbm, _ = build_qwen3_rom_deployment(
        qwen_graph, capability=qwen_capability, weight_storage_class=StorageClass.HBM
    )
    left = [
        d.encode()
        for d in rom.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.NUMERIC
    ]
    right = [
        d.encode()
        for d in hbm.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.NUMERIC
    ]
    assert left == right


# ---------------------------------------------------------------------------
# Operand conventions (TA-ABI3-OPCONV-1)
# ---------------------------------------------------------------------------
def _operators(deployment, family, sub):
    return [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["engine_family"] == int(family)
        and d.payload["engine_sub"] == sub
    ]


def test_expert_dispatch_declares_its_expert_bound(deepseek_build):
    from runtime.abi3.constants import Route

    deployment, _plan = deepseek_build
    operators = _operators(deployment, Major.ROUTE, int(Route.EXPERT_DISPATCH))
    assert operators
    for descriptor in operators:
        assert descriptor.payload["aux_id_0"] == 8


def test_routed_matmul_declares_its_expert_count(deepseek_build):
    deployment, _plan = deepseek_build
    operators = _operators(deployment, Major.TENSOR, int(TensorOp.ROUTED_MATMUL))
    assert operators
    for descriptor in operators:
        assert descriptor.payload["aux_id_0"] == 8


def test_attention_operators_carry_the_four_aux_slots(qwen_build, deepseek_build):
    from runtime.abi3.constants import NO_ID
    from runtime.abi3.descriptors import Symbol

    for deployment, _plan in (qwen_build, deepseek_build):
        operators = [
            d
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.OPERATOR
            and d.payload["engine_family"] == int(Major.ATTENTION)
        ]
        assert operators
        for descriptor in operators:
            assert descriptor.payload["aux_id_0"] >= 1
            assert descriptor.payload["aux_id_2"] == int(Symbol.CONTEXT_LENGTH)
            assert descriptor.payload["aux_id_3"] == int(Symbol.POSITION_START)
            assert descriptor.payload["aux_id_0"] != NO_ID


def test_head_rms_norm_declares_its_head_count(qwen_build):
    from runtime.abi3.constants import Vector

    deployment, _plan = qwen_build
    operators = _operators(deployment, Major.VECTOR, int(Vector.HEAD_RMS_NORM))
    assert operators
    for descriptor in operators:
        assert descriptor.payload["aux_id_0"] >= 1


# ---------------------------------------------------------------------------
# Publication and the CLI
# ---------------------------------------------------------------------------
def test_deployment_round_trips_through_disk(qwen_build, tmp_path, workspace):
    deployment, _plan = qwen_build
    root = tmp_path / "bundle"
    deployment.write(root)
    from runtime.abi3.deployment import Deployment as Bundle

    reloaded = Bundle.read(root)
    assert reloaded.table.encode() == deployment.table.encode()
    assert reloaded.program == deployment.program
    report = check_rom_inverse(reloaded, reader=_reader(workspace))
    assert report["status"] == "pass"


def test_cli_builds_verifies_and_proves(tmp_path, monkeypatch):
    import tools.build_rom_deployment as cli

    graph = qwen_shaped_graph(tmp_path)
    ir_path = tmp_path / "kernel_ir.v3.json"
    graph.write(ir_path)

    capability = qwen3_rom_capability(max_context_positions=16, vocabulary_size=32)
    monkeypatch.setattr(cli, "qwen3_rom_capability", lambda: capability)

    code = cli.main(
        [
            "qwen3-8b",
            "--ir",
            str(ir_path),
            "--output",
            str(tmp_path / "bundle"),
            "--checkpoint-root",
            str(tmp_path),
            "--verify",
            "--inverse",
            "--determinism",
            "--json",
        ]
    )
    assert code == 0
    assert (tmp_path / "bundle" / "deployment.json").is_file()
    assert (tmp_path / "bundle" / "descriptors.bin").is_file()
    assert (tmp_path / "bundle" / "program.bin").is_file()
    # Zero copy: the bundle never contains a weight image.
    written = sum(p.stat().st_size for p in (tmp_path / "bundle").iterdir())
    assert written < graph_checkpoint_bytes(graph)


def graph_checkpoint_bytes(graph) -> int:
    return sum(t.binding.bytes for t in graph.tensors if t.binding is not None)


def test_cli_reads_back_the_ir_it_was_given(tmp_path):
    import tools.build_rom_deployment as cli

    graph = qwen_shaped_graph(tmp_path)
    path = tmp_path / "kernel_ir.v3.json"
    graph.write(path)
    reloaded = cli.load_kernel_graph(path)
    assert reloaded.graph_id == graph.graph_id


def test_lowering_table_is_complete():
    from compiler.ir.v3.lowering import check_table_complete

    assert check_table_complete() == []


# ---------------------------------------------------------------------------
# Periodic layer stacks
# ---------------------------------------------------------------------------
def test_detect_spans_folds_an_alternating_stack():
    from compiler.backends.rom.common.program import _detect_spans

    published = json.loads(
        Path("configs/models/deepseek-v4-flash-0731.json").read_text()
    )["metadata"]["attention_sequence"]
    assert len(published) == 43
    spans = _detect_spans([(kind,) for kind in published])
    # window, window then a period-2 alternation, not 41 single-layer runs.
    assert len(spans) <= 3
    assert sum(period * groups for _start, period, groups in spans) == 43
    assert max(groups for _s, _p, groups in spans) >= 20
    # The compressed program emits at most this many source layers' bodies.
    emitted = sum(period for _start, period, _groups in spans)
    assert emitted <= 6


def test_alternating_layers_compress_into_one_periodic_loop(tmp_path):
    sequence = ("dense", "dense") + ("moe", "dense") * 4
    graph = deepseek_shaped_graph(tmp_path, sequence=sequence)
    analysis = analyze(graph)
    assert sum(run.layers_covered for run in analysis.runs) == len(sequence)
    periodic = [run for run in analysis.runs if run.period > 1]
    assert periodic, "an alternating stack must fold into a periodic run"
    assert max(run.groups for run in periodic) >= 4
    capability = deepseek_v4_rom_capability(
        max_context_positions=16,
        vocabulary_size=32,
        expert_count=8,
        experts_per_token=2,
        tile_rom_bytes=1 << 16,
        tiles_per_reticle=8,
    )
    deployment, plan = build_deepseek_v4_rom_deployment(
        graph, capability=capability, tile_rom_bytes=1 << 16, tiles_per_reticle=8
    )
    require_admitted(deployment, capability)
    assert check_rom_inverse(deployment, reader=_reader(tmp_path))["status"] == "pass"
    # Each ROM region striped by a periodic run has one slot per loop iteration.
    trips = {run.index: run.groups for run in analysis.runs}
    for region in plan.regions:
        if not region.key.startswith("rom.r"):
            continue
        run_index = int(region.key.split(".")[1][1:])
        assert region.slot_count == trips[run_index]


def test_non_uniform_weight_sizes_split_a_run(tmp_path):
    """Two layers whose projections differ in size cannot share a body."""
    from compiler.backends.rom.common.program import _kernel_signature

    graph = qwen_shaped_graph(tmp_path, layers=3)
    tensors = {t.tensor_id: t for t in graph.tensors}
    victim = tensors["model.layers.1.self_attn.q_proj.weight"]
    assert victim.binding is not None
    shrunk = Tensor(
        tensor_id=victim.tensor_id,
        dtype=victim.dtype,
        shape=victim.shape,
        role=victim.role,
        binding=CheckpointBinding(
            source_name=victim.binding.source_name,
            path=victim.binding.path,
            offset=victim.binding.offset,
            bytes=victim.binding.bytes // 2,
            sha256=victim.binding.sha256,
        ),
    )
    graph.tensors = tuple(
        shrunk if t.tensor_id == victim.tensor_id else t for t in graph.tensors
    )
    tensors[victim.tensor_id] = shrunk
    kernel = [k for k in graph.kernels if victim.tensor_id in k.inputs][0]
    other = [
        k
        for k in graph.kernels
        if "model.layers.0.self_attn.q_proj.weight" in k.inputs
    ][0]
    assert _kernel_signature(kernel, tensors) != _kernel_signature(other, tensors)
    analysis = analyze(graph)
    assert len(analysis.runs) > 1


# ---------------------------------------------------------------------------
# Block scales and routed expert banks
# ---------------------------------------------------------------------------
def test_block_scales_live_in_rom_beside_their_weight(deepseek_build):
    from runtime.abi3.descriptors import LayoutClass

    deployment, plan = deepseek_build
    scale_regions = [r for r in plan.regions if r.role.endswith("_scale")]
    assert scale_regions
    scale_objects = {r.object_id for r in scale_regions}
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_id not in scale_objects:
            continue
        assert descriptor.payload["storage_class"] == int(StorageClass.ROM)
        assert descriptor.permissions == int(Permission.READ | Permission.IMMUTABLE)
    scaled_views = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and d.payload["layout_class"] == int(LayoutClass.BLOCK_SCALED)
    ]
    assert scaled_views
    for descriptor in scaled_views:
        assert descriptor.payload["scale_block_elements"] > 0
        assert descriptor.payload["scale_object_id"] != 0xFFFFFFFF


def test_routed_expert_bank_is_one_region_and_one_view(deepseek_build, deepseek_graph):
    deployment, plan = deepseek_build
    banks = [r for r in plan.regions if r.role == "expert_bank"]
    assert banks
    routed = [
        k for k in deepseek_graph.kernels if "expert_weight_tensors" in k.attributes
    ]
    assert routed
    experts = len(routed[0].attributes["expert_weight_tensors"])
    for region in banks:
        # One slot per loop iteration, holding that layer's whole bank.
        assert len(region.members) == region.slot_count * experts
        assert region.slot_bytes % experts == 0
    bank_objects = {r.object_id for r in banks}
    views = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and d.primary_object_id in bank_objects
    ]
    assert views
    for descriptor in views:
        # The expert dimension is an addressing dimension, not a program loop.
        assert descriptor.payload["dim0"] == experts
        assert descriptor.payload["rank"] == 3
    operators = _operators(deployment, Major.TENSOR, int(TensorOp.ROUTED_MATMUL))
    assert operators
    view_ids = {d.descriptor_id for d in views}
    for descriptor in operators:
        # TA-ABI3-OPCONV-1: routed weights are slot 1.
        assert descriptor.payload["input_view_1"] in view_ids


def test_expert_bank_members_are_placed_in_ascending_expert_order(deepseek_build):
    _deployment, plan = deepseek_build
    for region in [r for r in plan.regions if r.role == "expert_bank"]:
        for slot in range(region.slot_count):
            members = [m for m in region.members if m.slot == slot]
            ids = [int(m.tensor_id.split(".experts.")[1].split(".")[0]) for m in members]
            assert ids == sorted(ids)
            assert ids == list(range(len(ids)))


# ---------------------------------------------------------------------------
# Memory capacity
# ---------------------------------------------------------------------------
def test_memory_capacity_is_proved(qwen_build, deepseek_build):
    for deployment, _plan in (qwen_build, deepseek_build):
        footprint = deployment.notes["memory_footprint"]
        declared = footprint["declared"]
        used = footprint["used"]
        assert used["rom"] <= declared["rom"]
        assert used.get("sram", 0) <= declared["sram"]
        assert footprint["session_bytes_in_hbm"] <= declared["hbm"]


def test_mutable_state_overflow_is_refused(qwen_graph):
    from compiler.backends.rom.qwen3 import qwen3_rom_capability as make

    capability = make(max_context_positions=16, vocabulary_size=32)
    capability.memory["hbm"] = {"bytes": 4096}
    capability.memory["sram"] = {"bytes": 4096, "banks": 4}
    with pytest.raises(RomLoweringError, match="does not fit the target"):
        build_qwen3_rom_deployment(qwen_graph, capability=capability)


def test_symbolic_extent_uses_the_declared_maximum(qwen_graph, qwen_capability):
    """``Symbolic.maximum`` is the extent's maximum, multiplier included."""
    from compiler.backends.rom.common.program import RomLowering
    from compiler.backends.rom.qwen3 import qwen3_rom_policy

    lowering = RomLowering(qwen_graph, qwen_capability, qwen3_rom_policy())
    assert lowering._extent(Symbolic("span_tokens", 1, 16)) == 16
    assert lowering._extent(Symbolic("span_tokens", 6, 96)) == 96
    assert lowering._extent(Symbolic("span_tokens", 6, 0)) == 6 * 16
    assert lowering._extent(7) == 7


# ---------------------------------------------------------------------------
# Execution: the token-block loop, the operand conventions, and ROM versus HBM
# ---------------------------------------------------------------------------
def _run(graph, root: Path, capability, storage_class, *, prompt=(1, 2, 3, 4), tokens=4):
    from runtime.sim.device import Device
    from runtime.sim.engines import load_engines
    from runtime.driver import GenerationDriver

    load_engines()
    deployment, _plan = build_qwen3_rom_deployment(
        graph, capability=capability, weight_storage_class=storage_class
    )
    device = Device(deployment, capability, root=root, verify=True)
    return GenerationDriver(device).generate(list(prompt), max_new_tokens=tokens)


@pytest.fixture(scope="module")
def execution_workspace(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("rom-execution")


@pytest.fixture(scope="module")
def execution_graph(execution_workspace: Path) -> KernelGraph:
    return qwen_shaped_graph(execution_workspace)


def test_rom_deployment_executes_and_generates_tokens(
    execution_graph, execution_workspace, qwen_capability
):
    result = _run(execution_graph, execution_workspace, qwen_capability, StorageClass.ROM)
    assert result.failure is None
    assert len(result.generated_token_ids) == 4
    assert all(0 <= t < 32 for t in result.generated_token_ids)


def test_rom_and_hbm_execution_produce_identical_tokens(
    execution_graph, execution_workspace, qwen_capability
):
    """The whole ROM-versus-HBM comparison rests on this.

    The two builds share every descriptor but the weight objects' storage class,
    so a token difference between them could only come from the memory
    technology -- which is exactly the measurement the program wants, and
    exactly why the tokens must agree when nothing else changes.
    """
    rom = _run(execution_graph, execution_workspace, qwen_capability, StorageClass.ROM)
    hbm = _run(execution_graph, execution_workspace, qwen_capability, StorageClass.HBM)
    assert rom.failure is None and hbm.failure is None
    left = list(rom.generated_token_ids)
    right = list(hbm.generated_token_ids)
    divergence = next(
        (i for i, (a, b) in enumerate(zip(left, right)) if a != b), None
    )
    assert divergence is None, (
        f"ROM and HBM diverge at token {divergence}: {left} vs {right}"
    )
    assert left == right


def test_token_block_loop_carries_the_request_span(
    execution_graph, execution_workspace, qwen_capability
):
    """A13: the last iteration presents the rows the request has, not the block.

    Without it a backend must dispatch one token at a time to stay correct.
    """
    from runtime.sim.device import Device
    from runtime.sim.engines import load_engines
    from runtime.abi3.constants import NO_ID

    load_engines()
    deployment, _plan = build_qwen3_rom_deployment(
        execution_graph, capability=qwen_capability
    )
    seen: list[tuple[int, ...]] = []

    def on_issue(pc, instruction, family, ctx):
        if instruction.descriptor_id == NO_ID:
            return
        descriptor = ctx.table[instruction.descriptor_id]
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            return
        view_id = descriptor.payload["output_view_0"]
        if view_id != NO_ID:
            seen.append(tuple(ctx.view(view_id).dims))

    device = Device(deployment, qwen_capability, root=execution_workspace, verify=False)
    device.on_issue = on_issue
    from runtime.driver import GenerationDriver

    GenerationDriver(device).generate([1, 2, 3, 4, 5], max_new_tokens=1)
    # The declared block is the whole 16-position context; the resolved extent
    # is the request's five rows.  A state window is the exception and stays at
    # its capacity, because attention reads the whole context.
    leading = {dims[0] for dims in seen if dims}
    assert 5 in leading, leading
    assert leading <= {1, 5, 16}, leading


def test_prefill_issues_one_dispatch_per_kernel_per_layer(
    execution_graph, execution_workspace, qwen_capability
):
    """One block covers the span, so the layer body runs once per layer."""
    from runtime.sim.device import Device
    from runtime.sim.engines import load_engines
    from runtime.driver import GenerationDriver
    from runtime.abi3.constants import Major as M

    load_engines()
    deployment, _plan = build_qwen3_rom_deployment(
        execution_graph, capability=qwen_capability
    )
    dispatches = []

    def on_issue(pc, instruction, family, ctx):
        dispatches.append(int(instruction.major))

    device = Device(deployment, qwen_capability, root=execution_workspace, verify=False)
    device.on_issue = on_issue
    GenerationDriver(device).generate([1, 2, 3, 4, 5], max_new_tokens=0)
    engine = [d for d in dispatches if d != int(M.CONTROL)]
    state = [d for d in engine if d == int(M.STATE)]
    work = len(engine) - len(state)
    # Exactly one dispatch per kernel that does engine work: not one per token,
    # and not one per tile.  The graph's own state kernels are emitted once each
    # at the transaction boundary rather than per layer.
    priced = [
        k
        for k in execution_graph.kernels
        if k.kind not in {"STATE_PREPARE", "STATE_COMMIT"}
    ]
    assert work == len(priced)
    assert len(state) == 2


def test_position_range_is_materialised_not_staged(qwen_build, qwen_graph):
    """A request's positions are a bound symbol, never a host window."""
    deployment, _plan = qwen_build
    generated = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and deployment.objects[d.descriptor_id].kind == "generated"
    ]
    assert generated
    kinds = {deployment.objects[d.descriptor_id].generator for d in generated}
    assert "arange_u32_v1" in kinds
    substituted = deployment.notes["rom_lowering"]["substituted_inputs"]
    assert substituted.get("input.positions") == "arange_u32_v1"
    for descriptor in generated:
        assert descriptor.payload["storage_class"] == int(StorageClass.ROM)
        assert descriptor.permissions == int(Permission.READ | Permission.IMMUTABLE)


def test_token_stream_reads_the_host_input_window(qwen_build):
    """The declared token input is a view of the window the host stages into."""
    deployment, _plan = qwen_build
    policy = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.GENERATION_POLICY
    )
    ring = policy.payload["token_ring_object_id"]
    embed = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["engine_family"] == int(Major.TENSOR)
        and d.payload["engine_sub"] == 0x03
    )
    views = {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
    }
    assert views[embed.payload["input_view_0"]].primary_object_id == ring


def test_contraction_operands_are_stated_as_matrices(qwen_build, qwen_graph):
    """TA-ABI3-OPCONV-1 section 2: ``[rows, K] x [N, K] -> [rows, N]``."""
    deployment, _plan = qwen_build
    views = {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
    }
    kernels = {k.index: k for k in qwen_graph.kernels}
    checked = 0
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        if descriptor.payload["engine_family"] != int(Major.TENSOR):
            continue
        if descriptor.payload["engine_sub"] != int(TensorOp.MATMUL):
            continue
        activation = views[descriptor.payload["input_view_0"]].payload
        weight = views[descriptor.payload["input_view_1"]].payload
        result = views[descriptor.payload["output_view_0"]].payload
        assert activation["rank"] == weight["rank"] == result["rank"] == 2
        assert activation["dim1"] == weight["dim1"]  # the shared reduction axis
        assert result["dim0"] == activation["dim0"]
        assert result["dim1"] == weight["dim0"]
        source = kernels[descriptor.payload["source_kernel_id"]]
        # A head-shaped result is folded, never relaid out.
        assert len(source.outputs) == 1
        checked += 1
    assert checked >= 8


def test_state_planes_share_one_fused_row(qwen_build):
    """Key and value are halves of one row, described rather than copied."""
    deployment, plan = qwen_build
    state = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.STATE
    )
    row_elements = state.payload["row_bytes"] // 2  # BF16
    prepared = state.payload["prepared_object_id"]
    planes = [
        d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and d.primary_object_id == prepared
        and d.payload["rank"] == 3
    ]
    assert planes
    offsets = set()
    for payload in planes:
        assert payload["stride0"] == row_elements
        assert payload["dim0"] == state.payload["capacity_rows"]
        offsets.add(payload["element_offset"])
    # Two distinct planes, both inside one row.
    assert len(offsets) >= 2
    assert max(offsets) < row_elements


def test_movement_operands_are_permuted_into_the_engine_order(qwen_build, qwen_graph):
    """DMA reads ``(index, source)``; both exporters emit ``(source, index)``."""
    from runtime.abi3.constants import DType, Dma

    deployment, _plan = qwen_build
    views = {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
    }
    movements = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["engine_family"] == int(Major.DMA)
        and d.payload["engine_sub"] in (int(Dma.GATHER), int(Dma.SCATTER))
    ]
    assert movements
    for descriptor in movements:
        index = views[descriptor.payload["input_view_0"]].payload
        assert index["dtype"] == int(DType.U32)
        assert index["rank"] == 1


def test_on_wafer_collectives_are_tile_scoped_and_not_degenerate(
    deepseek_build, deepseek_capability
):
    """Amendment A14: a wafer collective addresses the tile fabric.

    This replaces the check that pinned the pre-A14 workaround.  A wafer-scale
    logical accelerator is one node -- that is what "presented to the host as
    one device" means -- so while participants were counted in nodes, every
    collective on it was a collective over a single participant and the LINK
    engine refused all five as degenerate.  ``participant_scope`` says which
    fabric a collective spans, and ``participant_count`` is then derived from
    the admitted topology rather than asserted by the backend.
    """
    deployment, _plan = deepseek_build
    nodes = deepseek_capability.limits["max_nodes"]
    topology = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TOPOLOGY
    )
    tiles = topology.payload["reticle_count"] * topology.payload["tiles_per_reticle"]
    groups = topology.payload["route_group_count"]
    assert tiles > nodes, "a wafer has more tiles than the one node it declares"
    communications = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.COMMUNICATION
    ]
    assert communications
    for descriptor in communications:
        assert descriptor.payload["participant_scope"] == int(ParticipantScope.TILE)
    collectives = [
        d
        for d in communications
        if d.payload["group_id"] != NO_ID
    ]
    assert collectives
    for descriptor in collectives:
        # Derived, not declared: this is what the LINK engine will compute
        # from the admitted topology, so the two cannot disagree.
        expected = tiles // groups if groups > 1 else tiles
        assert descriptor.payload["participant_count"] == expected
        assert descriptor.payload["participant_count"] >= 2, (
            "a collective over one participant is degenerate, which is the "
            "failure amendment A14 exists to remove"
        )
        # A collective needs its participant array, and an array another
        # participant may touch must be explicitly exported.
        remote = deployment.table[descriptor.payload["remote_object_id"]]
        assert remote.permissions & Permission.REMOTE
        if descriptor.payload["byte_extent"]:
            assert remote.payload["size_bytes"] >= (
                descriptor.payload["participant_count"]
                * descriptor.payload["byte_extent"]
            )
    assert "on_wafer_fanout" not in deployment.notes["rom_lowering"]
