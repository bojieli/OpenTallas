"""Acceptance tests for the shared HBM/SRAM ABI 3.0 backend.

The lane's claim is one backend, one code path, two deployment topologies.  The
tests below are the machine-checkable form of that claim:

* a dense transformer graph and a mixture-of-experts graph go through the same
  :func:`lower_to_abi3` with no model-specific input;
* the independent ABI 3.0 verifier admits every output;
* the program is loop-compressed -- growing the layer count by eight times does
  not grow the instruction count at all;
* weights are zero-copy views over the checkpoint bindings, never copies; and
* two clean builds are byte-identical.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from compiler.backends.hbm_sram.capability import (
    capability_for,
    cluster32_capability,
    profile_difference,
    single_chip_capability,
)
from compiler.backends.hbm_sram.check import check_deployment
from compiler.backends.hbm_sram.lower import (
    lower_to_abi3,
    lower_with_plan,
    shares_an_axis,
)
from compiler.backends.hbm_sram.plan import PLAN_SCHEMA, build_plan, read_kernel_graph
from compiler.ir.v3.kernel_ir import (
    BindingSegment,
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
from compiler.ir.v3.lowering import engine_for
from runtime.abi3.constants import (
    Major,
    NO_ID,
    Permission,
    Reduction,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.descriptors import ExtendedDescriptorType, SelectorKind, Symbol
from runtime.sim.device import loop_trip_count
from runtime.sim.memory import ViewResolver
from runtime.abi3.verifier import require_admitted, verify_deployment

#: The one published IR these tests still read.  A backend property is a
#: property of the lowering, so it belongs on the smallest graph that has the
#: shape; what the *published* graph declares is the exporter's own test's
#: subject.  The Qwen lane is the exception on purpose: it is the control
#: workload, and "the real 36-layer graph lowers and is admitted" is the claim
#: itself rather than a way of reaching some other property.
REAL_QWEN_IR = Path("build/ir-v3/qwen3-8b/kernel_ir.v3.json")


# ---------------------------------------------------------------------------
# Synthetic neutral graphs
# ---------------------------------------------------------------------------
class _Checkpoint:
    """A deterministic fake checkpoint: names, byte ranges and digests."""

    def __init__(self, shards: int = 1) -> None:
        self.shards = shards
        self.cursor = [0] * shards
        self.index = 0

    def bind(self, name: str, elements: int, dtype: str = "bf16") -> CheckpointBinding:
        width = {
            "bf16": 2,
            "fp32": 4,
            "u32": 4,
            "fp8_e4m3fn": 1,
            "e8m0": 1,
        }[dtype]
        shard = self.index % self.shards
        self.index += 1
        offset = self.cursor[shard]
        size = elements * width
        self.cursor[shard] = offset + size
        digest = hashlib.sha256(f"{name}:{offset}:{size}".encode()).hexdigest()
        return CheckpointBinding(
            source_name=name,
            path=f"checkpoint/model-{shard:05d}.safetensors",
            offset=offset,
            bytes=size,
            sha256=digest,
        )

    def bind_bank(
        self, name: str, elements: int, parts: int, dtype: str = "bf16"
    ) -> CheckpointBinding:
        """A bank the model addresses as one operand and the file stores apart.

        DeepSeek's routed experts are the case: one declared ``[E, N, K]``
        tensor whose payload is *E* separately named, separately authenticated
        checkpoint ranges.  They are laid down out of order here because the
        released checkpoint stores them that way -- interleaved with the other
        projections, lexicographically ordered, so expert 10 precedes expert 2 --
        and a contiguous fixture would let a backend that read only the
        binding's ``(path, offset, bytes)`` totals reconcile exactly while
        naming the wrong bytes.
        """
        parent = self.bind(name, elements, dtype)
        per = parent.bytes // parts
        assert per * parts == parent.bytes
        segments = []
        for part in range(parts):
            slot = (part * 3 + 1) % parts
            offset = parent.offset + slot * per
            segments.append(
                BindingSegment(
                    source_name=f"{name}.{part}",
                    path=parent.path,
                    offset=offset,
                    bytes=per,
                    sha256=hashlib.sha256(
                        f"{name}.{part}:{offset}:{per}".encode()
                    ).hexdigest(),
                )
            )
        return CheckpointBinding(
            source_name=parent.source_name,
            path=parent.path,
            offset=parent.offset,
            bytes=parent.bytes,
            sha256=parent.sha256,
            segments=tuple(segments),
        )


SPAN = Symbolic("span_tokens")


def dense_graph(
    *,
    layers: int = 4,
    hidden: int = 256,
    kv: int = 128,
    ffn: int = 512,
    vocab: int = 512,
    span_max: int = 512,
    shards: int = 1,
) -> KernelGraph:
    """A Qwen-shaped dense decoder: attention, GQA state, MLP, selection."""
    ck = _Checkpoint(shards)
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []
    states: list[StateResource] = []

    def weight(name: str, shape: tuple[int, ...], dtype: str = "bf16") -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        tensors.append(
            Tensor(
                tensor_id=name,
                dtype=dtype,
                shape=shape,
                role="weight",
                binding=ck.bind(name, elements, dtype),
            )
        )
        return name

    def act(name: str, shape: tuple, dtype: str = "bf16", role: str = "activation") -> str:
        tensors.append(Tensor(tensor_id=name, dtype=dtype, shape=shape, role=role))
        return name

    def emit(kind: str, ins, outs, contract: str, **kw) -> None:
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"k{len(kernels):04d}.{kind.lower()}",
                kind=kind,
                inputs=tuple(ins),
                outputs=tuple(outs),
                numeric_contract=contract,
                **kw,
            )
        )

    act("tokens", (SPAN, 1), "u32", role="input")
    weight("embed", (vocab, hidden))
    act("hidden0", (SPAN, hidden))
    for index in range(layers):
        for half in ("k", "v"):
            states.append(
                StateResource(
                    state_id=f"kv{index}{half}",
                    state_class="kv_cache",
                    dtype="bf16",
                    row_elements=kv,
                    capacity_rows=span_max,
                )
            )

    emit("STATE_PREPARE", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden0"],
         "lookup_bf16_token_embedding_v1")

    previous = "hidden0"
    for index in range(layers):
        p = f"l{index}"
        weight(f"{p}.norm1", (hidden,))
        weight(f"{p}.wq", (hidden, hidden))
        weight(f"{p}.wk", (hidden, kv))
        weight(f"{p}.wv", (hidden, kv))
        weight(f"{p}.wo", (hidden, hidden))
        weight(f"{p}.norm2", (hidden,))
        weight(f"{p}.wg", (hidden, ffn))
        weight(f"{p}.wu", (hidden, ffn))
        weight(f"{p}.wd", (ffn, hidden))
        act(f"{p}.n1", (SPAN, hidden))
        act(f"{p}.q", (SPAN, hidden))
        act(f"{p}.k", (SPAN, kv))
        act(f"{p}.v", (SPAN, kv))
        act(f"{p}.qr", (SPAN, hidden))
        act(f"kv{index}k", (span_max, kv), role="state")
        act(f"kv{index}v", (span_max, kv), role="state")
        act(f"{p}.attn", (SPAN, hidden))
        act(f"{p}.o", (SPAN, hidden))
        act(f"{p}.res1", (SPAN, hidden))
        act(f"{p}.n2", (SPAN, hidden))
        act(f"{p}.g", (SPAN, ffn))
        act(f"{p}.u", (SPAN, ffn))
        act(f"{p}.act", (SPAN, ffn))
        act(f"{p}.d", (SPAN, hidden))
        act(f"{p}.res2", (SPAN, hidden))
        layer = {"layer": index}
        emit("RMS_NORM", [previous, f"{p}.norm1"], [f"{p}.n1"],
             "qwen3_rmsnorm_fp32_bf16_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wq"], [f"{p}.q"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wk"], [f"{p}.k"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wv"], [f"{p}.v"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ROPE", [f"{p}.q", "rope"], [f"{p}.qr"], "qwen3_rope_fp32_bf16_v1",
             attributes={"rotary_width": 64}, **layer)
        emit("KV_APPEND", [f"{p}.k"], [f"kv{index}k"],
             "bf16_byte_preserving_state_v1", state_writes=(f"kv{index}k",), **layer)
        emit("KV_APPEND", [f"{p}.v"], [f"kv{index}v"],
             "bf16_byte_preserving_state_v1", state_writes=(f"kv{index}v",), **layer)
        emit("ATTENTION_GQA", [f"{p}.qr", f"kv{index}k", f"kv{index}v"],
             [f"{p}.attn"], "qwen3_gqa_fp32_softmax_bf16_v1",
             attributes={"group_size": 2, "mask_mode": 0},
             state_reads=(f"kv{index}k", f"kv{index}v"), **layer)
        emit("MATMUL", [f"{p}.attn", f"{p}.wo"], [f"{p}.o"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ADD", [previous, f"{p}.o"], [f"{p}.res1"], "bf16_add_rne_v1", **layer)
        emit("RMS_NORM", [f"{p}.res1", f"{p}.norm2"], [f"{p}.n2"],
             "qwen3_rmsnorm_fp32_bf16_v1", **layer)
        emit("MATMUL", [f"{p}.n2", f"{p}.wg"], [f"{p}.g"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n2", f"{p}.wu"], [f"{p}.u"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("SILU_MUL", [f"{p}.g", f"{p}.u"], [f"{p}.act"],
             "qwen3_silu_mul_bf16_v1", **layer)
        emit("MATMUL", [f"{p}.act", f"{p}.wd"], [f"{p}.d"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ADD", [f"{p}.res1", f"{p}.d"], [f"{p}.res2"], "bf16_add_rne_v1", **layer)
        previous = f"{p}.res2"

    weight("rope", (span_max, 64))
    weight("norm.final", (hidden,))
    weight("last.index", (1, 1), "u32")
    weight("lm_head", (hidden, vocab))
    act("hidden.final", (SPAN, hidden))
    act("hidden.last", (1, hidden))
    act("logits", (1, vocab))
    act("token", (1, 1), "u32")
    act("tokens.out", (1, 1), "u32", role="output")

    emit("RMS_NORM", [previous, "norm.final"], ["hidden.final"],
         "qwen3_rmsnorm_fp32_bf16_v1")
    emit("LAST_TOKEN_SELECT", ["hidden.final", "last.index"], ["hidden.last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_token_append_eos_v1")
    emit("STATE_COMMIT", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))

    return KernelGraph(
        model_id=f"synthetic-dense-{layers}L",
        source={"family": "dense", "layers": layers},
        symbols=(RuntimeSymbol("span_tokens", 1, span_max, 1),),
        tensors=tuple(tensors),
        states=tuple(states),
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
            Entrypoint("decode", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
        ),
        generation_policy={
            "eos_token_ids": [vocab - 1],
            "maximum_new_tokens": 64,
            "vocabulary_size": vocab,
        },
    )


def moe_graph(
    *,
    layers: int = 3,
    hidden: int = 256,
    ffn: int = 512,
    experts: int = 8,
    topk: int = 2,
    vocab: int = 512,
    span_max: int = 256,
    shards: int = 2,
) -> KernelGraph:
    """A DeepSeek-shaped graph: routing, expert dispatch, routed contraction."""
    ck = _Checkpoint(shards)
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []
    states: list[StateResource] = []

    def weight(
        name: str, shape: tuple[int, ...], dtype: str = "bf16", *, bank: int = 0
    ) -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        binding = (
            ck.bind_bank(name, elements, bank, dtype)
            if bank
            else ck.bind(name, elements, dtype)
        )
        tensors.append(
            Tensor(
                tensor_id=name,
                dtype=dtype,
                shape=shape,
                role="weight",
                binding=binding,
            )
        )
        return name

    def act(name: str, shape: tuple, dtype: str = "bf16", role: str = "activation") -> str:
        tensors.append(Tensor(tensor_id=name, dtype=dtype, shape=shape, role=role))
        return name

    def emit(kind: str, ins, outs, contract: str, **kw) -> None:
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"k{len(kernels):04d}.{kind.lower()}",
                kind=kind,
                inputs=tuple(ins),
                outputs=tuple(outs),
                numeric_contract=contract,
                **kw,
            )
        )

    act("tokens", (SPAN, 1), "u32", role="input")
    weight("embed", (vocab, hidden))
    act("hidden0", (SPAN, hidden))
    for index in range(layers):
        states.append(
            StateResource(
                state_id=f"kv{index}",
                state_class="compressed_kv",
                dtype="bf16",
                row_elements=hidden,
                capacity_rows=span_max,
            )
        )
    emit("STATE_PREPARE", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden0"],
         "lookup_bf16_token_embedding_v1")

    previous = "hidden0"
    for index in range(layers):
        p = f"l{index}"
        weight(f"{p}.norm", (hidden,))
        weight(f"{p}.router", (hidden, experts))
        weight(f"{p}.bias", (experts,))
        weight(f"{p}.experts", (experts, ffn, hidden), "fp8_e4m3fn", bank=experts)
        weight(f"{p}.wdown", (hidden, ffn))
        act(f"{p}.n", (SPAN, hidden))
        act(f"{p}.scores", (SPAN, experts))
        act(f"{p}.index", (SPAN, topk), "u32")
        act(f"{p}.gate", (SPAN, topk))
        act(f"{p}.dispatch", (SPAN, hidden))
        act(f"{p}.dispatched_ids", (SPAN, topk), "u32")
        act(f"{p}.expert", (SPAN, ffn))
        act(f"{p}.reduced", (SPAN, ffn))
        act(f"{p}.down", (SPAN, hidden))
        act(f"{p}.res", (SPAN, hidden))
        layer = {"layer": index}
        emit("RMS_NORM", [previous, f"{p}.norm"], [f"{p}.n"],
             "deepseek_rmsnorm_binary32_v1", **layer)
        emit("ROUTER_SCORE", [f"{p}.n", f"{p}.router"], [f"{p}.scores"],
             "routing_router_score_bf16_v1", **layer)
        emit("BIASED_TOPK", [f"{p}.scores", f"{p}.bias"],
             [f"{p}.index", f"{p}.gate"], "selection_biased_topk_route_indices_v1",
             attributes={"top_k": topk}, **layer)
        emit("EXPERT_DISPATCH", [f"{p}.n", f"{p}.index"],
             [f"{p}.dispatch", f"{p}.dispatched_ids"], "dispatch_routed_experts_bf16_v1",
             attributes={"expert_count": experts}, **layer)
        emit("ROUTED_MATMUL",
             [f"{p}.dispatch", f"{p}.experts", f"{p}.dispatched_ids", f"{p}.gate"],
             [f"{p}.expert"], "matrix_dense_fp8_linear_bf16_block_scaled_contraction_v1",
             attributes={"expert_count": experts}, **layer)
        emit("EXPERT_REDUCE", [f"{p}.expert", f"{p}.gate", f"{p}.index"],
             [f"{p}.reduced"], "dispatch_reduce_expert_outputs_bf16_v1", **layer)
        emit("MATMUL", [f"{p}.reduced", f"{p}.wdown"], [f"{p}.down"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ADD", [previous, f"{p}.down"], [f"{p}.res"], "bf16_add_rne_v1", **layer)
        previous = f"{p}.res"

    weight("norm.final", (hidden,))
    weight("last.index", (1, 1), "u32")
    weight("lm_head", (hidden, vocab))
    act("hidden.final", (SPAN, hidden))
    act("hidden.last", (1, hidden))
    act("logits", (1, vocab))
    act("token", (1, 1), "u32")
    act("tokens.out", (1, 1), "u32", role="output")
    emit("RMS_NORM", [previous, "norm.final"], ["hidden.final"],
         "deepseek_rmsnorm_binary32_v1")
    emit("LAST_TOKEN_SELECT", ["hidden.final", "last.index"], ["hidden.last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_token_append_eos_v1")
    emit("STATE_COMMIT", (), (), "bf16_byte_preserving_state_v1",
         state_writes=tuple(s.state_id for s in states))

    return KernelGraph(
        model_id=f"synthetic-moe-{layers}L",
        source={"family": "moe", "layers": layers, "experts": experts},
        symbols=(RuntimeSymbol("span_tokens", 1, span_max, 1),),
        tensors=tuple(tensors),
        states=tuple(states),
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
            Entrypoint("decode", ("tokens",), ("tokens.out",),
                       tuple(s.state_id for s in states)),
        ),
        generation_policy={
            "eos_token_ids": [vocab - 1],
            "maximum_new_tokens": 32,
            "vocabulary_size": vocab,
        },
    )


def movement_graph(
    *,
    hidden: int = 64,
    mult: int = 4,
    vocab: int = 64,
    span_max: int = 64,
    window: int = 8,
    selected: int = 16,
    ratio: int = 4,
) -> KernelGraph:
    """A graph carrying the movement shapes, and nothing else.

    Four backend properties are about *movement*: a broadcast that shares one
    row across an inserted axis, a select that is an offset rather than a
    gather, a width-axis concatenation that names its join axis (amendment
    A17), and a hyper-connection whose token axis stays leading.  Each is a
    property of the lowering, not of any model, so each is exercised here on
    the smallest graph that has the shape -- rather than through a 3,000-kernel
    published IR, where an unrelated refusal anywhere upstream takes all four
    down at once and none of them is what failed.
    """
    ck = _Checkpoint(1)
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []

    def weight(name: str, shape: tuple[int, ...], dtype: str = "bf16") -> str:
        elements = 1
        for dim in shape:
            elements *= dim
        tensors.append(
            Tensor(
                tensor_id=name,
                dtype=dtype,
                shape=shape,
                role="weight",
                binding=ck.bind(name, elements, dtype),
            )
        )
        return name

    def act(name: str, shape: tuple, dtype: str = "bf16", role: str = "activation") -> str:
        tensors.append(Tensor(tensor_id=name, dtype=dtype, shape=shape, role=role))
        return name

    def emit(kind: str, ins, outs, contract: str, **kw) -> None:
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"{kind.lower()}.{len(kernels):02d}",
                kind=kind,
                inputs=tuple(ins),
                outputs=tuple(outs),
                numeric_contract=contract,
                **kw,
            )
        )

    coefficients = (2 + mult) * mult
    act("tokens", (SPAN, 1), "u32", role="input")
    act("position", (1,), "i32", role="input")
    weight("embed", (vocab, hidden))
    act("hidden", (SPAN, hidden))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden"],
         "lookup_bf16_token_embedding_v1")

    # -- the broadcast: one embedding read once per stream ----------------
    act("streams", (SPAN, mult, hidden))
    emit("BROADCAST", ["hidden"], ["streams"], "structural_hc_expand_bf16_v1",
         attributes={"axis": 1, "extent": mult})

    # -- the packed coefficient block and its two planes ------------------
    weight("hc.fn", (coefficients, mult * hidden), "fp32")
    weight("hc.scale", (3,), "fp32")
    weight("hc.base", (coefficients,), "fp32")
    act("hc.weights", (SPAN, 2, mult), "fp32")
    act("hc.comb", (SPAN, mult, mult), "fp32")
    emit("HYPER_CONNECT_PRE", ["streams", "hc.fn", "hc.scale", "hc.base"],
         ["hc.weights", "hc.comb"], "hyper_connection_hc_pre_bf16_v1",
         attributes={"hc_mult": mult, "sinkhorn_iterations": 20, "epsilon": 1e-06,
                     "coefficient_layout": "pre_then_post"})
    act("hc.pre", (SPAN, mult), "fp32")
    act("hc.post", (SPAN, mult), "fp32")
    emit("SELECT", ["hc.weights"], ["hc.pre"], "hyper_connection_hc_pre_bf16_v1",
         attributes={"axis": 1, "index": 0})
    emit("SELECT", ["hc.weights"], ["hc.post"], "hyper_connection_hc_pre_bf16_v1",
         attributes={"axis": 1, "index": 1})

    # -- the branch, and the post-combination over the streams ------------
    weight("branch.w", (hidden, hidden))
    act("branch", (SPAN, hidden))
    act("merged", (SPAN, mult, hidden))
    emit("MATMUL", ["hidden", "branch.w"], ["branch"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("HYPER_CONNECT_POST", ["branch", "streams", "hc.post", "hc.comb"],
         ["merged"], "vector_hc_post_bf16_v1",
         attributes={"hc_mult": mult, "post_width": mult,
                     "combination_width": mult * mult})

    # -- a state update, whose in1 the convention requires to stay empty --
    states = (
        StateResource(
            state_id="compressor",
            state_class="compressed_kv",
            dtype="fp32",
            row_elements=hidden,
            capacity_rows=span_max,
        ),
    )
    # The shapes are the ones the published IR declares for this operation:
    # a packed ``[tokens, 2, W]`` projection, an absolute position table of
    # ``[ratio, W]``, and two ``[tokens, 2 * ratio, W]`` pools.
    weight("compress.kv", (hidden, hidden), "fp32")
    weight("compress.gate", (hidden, hidden), "fp32")
    weight("ape", (ratio, hidden), "fp32")
    act("packed", (SPAN, 2, hidden), "fp32")
    act("pool.kv", (SPAN, 2 * ratio, hidden), "fp32")
    act("pool.scores", (SPAN, 2 * ratio, hidden), "fp32")
    emit("STATE_PREPARE", (), (), "bf16_byte_preserving_state_v1",
         state_writes=("compressor",))
    emit("COMPRESS_PROJECT", ["hidden", "compress.kv", "compress.gate"], ["packed"],
         "compression_compress_project_bf16_v1",
         attributes={"ratio": ratio, "overlap": True})
    emit("COMPRESS_STATE_UPDATE", ["packed", "ape"], ["pool.kv", "pool.scores"],
         "compression_state_compress_state_update_f32_raw_window_transaction_v1",
         attributes={"ratio": ratio, "overlap": True},
         state_reads=("compressor",), state_writes=("compressor",))

    # -- the width-axis join: two index vectors of different widths -------
    act("window.a", (SPAN, window), "u32")
    act("window.b", (SPAN, selected), "u32")
    act("joined", (SPAN, window + selected), "u32")
    emit("WINDOW_INDEX", ["position"], ["window.a"], "indexing_window_indices_v1",
         attributes={"window_size": window, "padding_index": -1})
    emit("WINDOW_INDEX", ["position"], ["window.b"], "indexing_window_indices_v1",
         attributes={"window_size": selected, "padding_index": -1})
    # Amendment A19 folded the index-selection join into ``ROUTE.INDEX_TOPK``,
    # so the contract that named it is no longer in the graph's union.  The
    # compressed *dense* index still joins a window block on the feature axis
    # and still names one, which is what this case is about.
    emit("CONCAT", ["window.a", "window.b"], ["joined"],
         "indexing_compressed_dense_indices_window_then_compressed_indices_v1",
         attributes={"axis": 1, "segment_widths": [window, selected]})

    # -- an epilogue, so the graph is a program ---------------------------
    weight("norm.final", (hidden,))
    weight("last.index", (1, 1), "u32")
    weight("lm_head", (hidden, vocab))
    act("final", (SPAN, hidden))
    act("hidden.last", (1, hidden))
    act("logits", (1, vocab))
    act("token", (1, 1), "u32")
    act("tokens.out", (1, 1), "u32", role="output")
    emit("RMS_NORM", ["branch", "norm.final"], ["final"],
         "qwen3_rmsnorm_fp32_bf16_v1")
    emit("LAST_TOKEN_SELECT", ["final", "last.index"], ["hidden.last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_token_append_eos_v1")

    emit("STATE_COMMIT", (), (), "bf16_byte_preserving_state_v1",
         state_writes=("compressor",))

    return KernelGraph(
        model_id="synthetic-movement",
        source={"family": "movement"},
        symbols=(RuntimeSymbol("span_tokens", 1, span_max, 1),),
        tensors=tuple(tensors),
        states=states,
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens", "position"), ("tokens.out",),
                       ("compressor",)),
            Entrypoint("decode", ("tokens", "position"), ("tokens.out",),
                       ("compressor",)),
        ),
        generation_policy={
            "eos_token_ids": [vocab - 1],
            "maximum_new_tokens": 8,
            "vocabulary_size": vocab,
        },
    )


def alternating_graph(*, pairs: int = 4, hidden: int = 256, span_max: int = 512):
    """A stack that alternates two layer structures, as a sparse/dense model does."""
    ck = _Checkpoint(1)
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []

    def weight(name, shape):
        elements = 1
        for dim in shape:
            elements *= dim
        tensors.append(
            Tensor(name, "bf16", shape, "weight", binding=ck.bind(name, elements))
        )

    def act(name, shape, dtype="bf16", role="activation"):
        tensors.append(Tensor(name, dtype, shape, role))

    def emit(kind, ins, outs, contract, **kw):
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"k{len(kernels):04d}.{kind.lower()}",
                kind=kind,
                inputs=tuple(ins),
                outputs=tuple(outs),
                numeric_contract=contract,
                **kw,
            )
        )

    act("tokens", (SPAN, 1), "u32", role="input")
    weight("embed", (512, hidden))
    act("hidden0", (SPAN, hidden))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden0"],
         "lookup_bf16_token_embedding_v1")
    previous = "hidden0"
    for index in range(2 * pairs):
        p = f"l{index}"
        weight(f"{p}.norm", (hidden,))
        weight(f"{p}.w", (hidden, hidden))
        act(f"{p}.n", (SPAN, hidden))
        act(f"{p}.y", (SPAN, hidden))
        act(f"{p}.res", (SPAN, hidden))
        layer = {"layer": index}
        emit("RMS_NORM", [previous, f"{p}.norm"], [f"{p}.n"],
             "qwen3_rmsnorm_fp32_bf16_v1", **layer)
        emit("MATMUL", [f"{p}.n", f"{p}.w"], [f"{p}.y"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        if index % 2 == 1:
            # the odd layers carry one extra elementwise stage
            act(f"{p}.y2", (SPAN, hidden))
            emit("SILU_MUL", [f"{p}.y", f"{p}.n"], [f"{p}.y2"],
                 "qwen3_silu_mul_bf16_v1", **layer)
            emit("ADD", [previous, f"{p}.y2"], [f"{p}.res"], "bf16_add_rne_v1", **layer)
        else:
            emit("ADD", [previous, f"{p}.y"], [f"{p}.res"], "bf16_add_rne_v1", **layer)
        previous = f"{p}.res"
    act("logits", (1, 512))
    act("token", (1, 1), "u32")
    act("out", (1, 1), "u32", role="output")
    weight("index", (1, 1))
    weight("lm_head", (hidden, 512))
    act("last", (1, hidden))
    emit("LAST_TOKEN_SELECT", [previous, "index"], ["last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["out"], "exact_token_append_eos_v1")
    return KernelGraph(
        model_id=f"synthetic-alternating-{pairs}",
        source={"family": "alternating"},
        symbols=(RuntimeSymbol("span_tokens", 1, span_max, 1),),
        tensors=tuple(tensors),
        states=(),
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("out",), ()),
            Entrypoint("decode", ("tokens",), ("out",), ()),
        ),
        generation_policy={"eos_token_ids": [511], "maximum_new_tokens": 8,
                           "vocabulary_size": 512},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def dense():
    return dense_graph()


@pytest.fixture(scope="module")
def moe():
    return moe_graph()


@pytest.fixture(scope="module")
def single_chip():
    return single_chip_capability()


@pytest.fixture(scope="module")
def cluster():
    return cluster32_capability()


# ---------------------------------------------------------------------------
# Neutrality of the fixtures themselves
# ---------------------------------------------------------------------------
def test_fixture_graphs_are_neutral(dense, moe):
    assert check_neutral(dense) == []
    assert check_neutral(moe) == []


def test_every_fixture_kernel_kind_has_a_frozen_lowering(dense, moe):
    for graph in (dense, moe):
        for kernel in graph.kernels:
            engine = engine_for(kernel.kind)
            assert engine.family and engine.family >= 0


# ---------------------------------------------------------------------------
# Capability profiles
# ---------------------------------------------------------------------------
def test_profiles_differ_only_in_topology_nodes_and_link():
    report = profile_difference()
    assert report["unexpected"] == []
    assert report["identical_feature_bits"]
    assert report["identical_engines"]
    assert report["identical_memory"]
    assert "topology_class" in report["differing"]
    assert "limits.max_nodes" in report["differing"]
    assert any(k.startswith("link.") for k in report["differing"])


def test_single_chip_still_advertises_the_inter_chip_endpoint(single_chip):
    from runtime.abi3.constants import Feature

    assert int(Feature.INTER_CHIP_ENDPOINT) in single_chip.features
    assert single_chip.limits["max_nodes"] == 1


def test_capability_lookup_rejects_unknown_profiles():
    with pytest.raises(KeyError):
        capability_for("wafer")


def test_profiles_map_to_capability_records_not_factories():
    from compiler.backends.hbm_sram.capability import PROFILES
    from runtime.abi3.capability import Capability

    assert set(PROFILES) == {"single-chip", "cluster-32"}
    for name, profile in PROFILES.items():
        assert isinstance(profile, Capability), name
        assert profile.digest == capability_for(name).digest


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------
def test_plan_bands_the_layers(dense, single_chip):
    plan = build_plan(dense, single_chip)
    assert plan.to_dict()["schema"] == PLAN_SCHEMA
    assert len(plan.bands) == 1
    assert plan.bands[0].layer_count == 4
    assert plan.bands[0].period == 1
    assert not plan.bands[0].degraded
    assert plan.proofs["sram_fits"]
    assert plan.proofs["hbm_fits"]
    assert plan.proofs["sram_banks_disjoint"]
    assert plan.proofs["max_loop_depth"] <= plan.proofs["capability_loop_depth"]


def test_plan_weight_objects_are_role_stacks(dense, single_chip):
    plan = build_plan(dense, single_chip)
    role_groups = [g for g in plan.weight_groups if g.group_id.startswith("wr")]
    assert role_groups, "per-layer weights must become role objects"
    for group in role_groups:
        assert len(group.segments) == 4  # one per layer
        stride = group.segments[1].element_offset
        for index, segment in enumerate(group.segments):
            assert segment.element_offset == index * stride
    # a few objects, not one per tensor
    assert len(plan.weight_groups) < len(plan.weight_placements)


def test_plan_stride_survives_a_sharded_checkpoint(single_chip):
    """Layers straddling shard files must still get a constant stride."""
    graph = dense_graph(layers=4, shards=3)
    plan = build_plan(graph, single_chip)
    assert len(plan.bands) == 1
    assert plan.bands[0].layer_count == 4
    for group in plan.weight_groups:
        if not group.group_id.startswith("wr"):
            continue
        stride = group.segments[1].element_offset
        assert stride > 0
        assert [s.element_offset for s in group.segments] == [
            index * stride for index in range(len(group.segments))
        ]


def test_plan_is_deterministic(dense, single_chip):
    first = build_plan(dense, single_chip)
    second = build_plan(dense, single_chip)
    assert first.plan_id == second.plan_id


# ---------------------------------------------------------------------------
# Lowering and verification
# ---------------------------------------------------------------------------
def test_dense_deployment_is_admitted(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    report = require_admitted(deployment, single_chip)
    assert report.admitted
    assert report.instruction_count < 400
    assert report.loop_depth <= single_chip.limits["max_loop_depth"]
    assert report.proved_retired_work <= report.declared_retired_work


def test_moe_deployment_is_admitted_on_one_chip(moe, single_chip):
    deployment = lower_to_abi3(moe, single_chip)
    report = require_admitted(deployment, single_chip)
    assert report.admitted


def test_moe_deployment_is_admitted_on_the_cluster(moe, cluster):
    deployment = lower_to_abi3(moe, cluster, topology=TopologyClass.CLUSTER_32)
    report = require_admitted(deployment, cluster)
    assert report.admitted
    assert deployment.topology_class == int(TopologyClass.CLUSTER_32)


def test_dense_deployment_is_admitted_on_the_cluster(dense, cluster):
    deployment = lower_to_abi3(dense, cluster)
    require_admitted(deployment, cluster)


def test_exactly_one_topology_descriptor(dense, single_chip, moe, cluster):
    for graph, capability in ((dense, single_chip), (moe, cluster)):
        deployment = lower_to_abi3(graph, capability)
        ids = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)
        assert len(ids) == 1


def test_cluster_emits_link_traffic_and_single_chip_does_not(moe, cluster, single_chip):
    from runtime.abi3.records import decode_body, split_program

    def link_instructions(deployment):
        _, body = split_program(deployment.program)
        return [i for i in decode_body(body) if i.major == int(Major.LINK)]

    clustered = lower_to_abi3(moe, cluster)
    alone = lower_to_abi3(moe, single_chip)
    links = link_instructions(clustered)
    assert links, "a 32-node deployment must move data between chips"
    assert not link_instructions(alone)
    classes = set()
    for instruction in links:
        descriptor = clustered.table[instruction.descriptor_id]
        assert descriptor.descriptor_type == ExtendedDescriptorType.COMMUNICATION
        classes.add(descriptor.payload["route_class"])
        assert descriptor.payload["participant_count"] == 32
    # Every traffic class the plan declares is accounted for, and a class is
    # accounted for in one of two ways: it emitted a transfer, or the kernels
    # that named it turned out to be replicated on every node and had nothing
    # to move.  The second is not silence -- the deployment says so, with a
    # count -- because "this cluster performs no expert-dispatch transfer" is a
    # fact a comparison of two machines has to be able to read off.
    from compiler.backends.hbm_sram.lower import _LINK_OP
    from compiler.backends.hbm_sram.plan import build_plan

    route_class = {name: spec[2] for name, spec in _LINK_OP.items()}
    replicated = clustered.notes["replicated_link_sites"]
    assert replicated, "a plan that shards only output columns replicates most kernels"
    declared = {
        plan.link_class
        for plan in build_plan(moe, cluster).kernels
        if plan.link_class
    }
    unaccounted = {
        name
        for name in declared
        if route_class[name] not in classes and name not in replicated
    }
    assert not unaccounted, sorted(unaccounted)
    # The transfer that does happen is the one that has to: a node-sharded
    # contraction's output columns, gathered back into a whole row.
    assert route_class["activation_transfer"] in classes
    assert route_class["coordinated_commit"] in classes


# ---------------------------------------------------------------------------
# Loop compression -- the reason ABI 3.0 exists
# ---------------------------------------------------------------------------
def test_instruction_count_is_independent_of_layer_count(single_chip):
    counts = {}
    for layers in (4, 8, 32):
        graph = dense_graph(layers=layers)
        deployment = lower_to_abi3(graph, single_chip)
        report = require_admitted(deployment, single_chip)
        counts[layers] = report.instruction_count
    assert counts[4] == counts[8] == counts[32], counts
    # A flat expansion of the 32-layer graph would need at least one command per
    # tile of every contraction; the loop-compressed program is three orders of
    # magnitude smaller than that.
    assert counts[32] < 400


def test_loop_compression_ratio_is_large(single_chip):
    """The program is small; the work it retires is not.

    A flat expansion would need one command per (layer, token block, kernel);
    the loop-compressed program describes the same work in a body that does not
    mention either the layer count or the context length.
    """
    layers, span = 32, 8192
    graph = dense_graph(layers=layers, span_max=span)
    deployment, plan = lower_with_plan(graph, single_chip)
    report = require_admitted(deployment, single_chip)
    body_kernels = len(plan.bands[0].body_kernels)
    blocks = span // plan.proofs["token_block_rows"]
    flat = layers * blocks * body_kernels
    assert report.instruction_count < 100
    assert report.proved_retired_work >= flat
    ratio = report.proved_retired_work / report.instruction_count
    assert ratio > 100, (ratio, report.proved_retired_work, report.instruction_count)


def test_layer_loop_moves_the_weight_window(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    loop_ids = set(deployment.table.ids_of_type(ExtendedDescriptorType.LOOP_CONTROL))
    moving = 0
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
            continue
        for slot in range(descriptor.payload["dynamic_term_count"]):
            if descriptor.payload[f"term{slot}_kind"] == int(
                SelectorKind.LOOP_INDUCTION
            ):
                assert descriptor.payload[f"term{slot}_index"] in loop_ids
                moving += 1
    assert moving > 0


def test_symbolic_token_extents_are_bound(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    symbol_loops = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL
        and d.payload["bound_selector_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
    ]
    assert symbol_loops, "token loops must be bound by span_tokens"
    for loop in symbol_loops:
        assert loop.payload["bound_symbol_id"] == int(Symbol.SPAN_TOKENS)
        assert loop.payload["max_iterations"] > 0
        # The divisor is the token block.  It is one by default: a view's
        # extents are static while the token count is not, so a larger block
        # would present rows the request does not have.
        assert loop.payload["bound_divisor"] >= 1
        # The induction variable counts *blocks*, so the step is one.  It is
        # emphatically not the divisor: Device._loop_trip computes
        # ceil(ceil(span / divisor) / step), having already divided by the
        # divisor, so a step of divisor divides twice and yields one iteration
        # at every span.  This assertion previously read
        # ``step == bound_divisor`` and is what let that through.
        assert loop.payload["step"] == 1

    symbol_views = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and any(
            d.payload[f"term{s}_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
            for s in range(d.payload["dynamic_term_count"])
        )
    ]
    assert symbol_views, "at least one view must be a function of a runtime symbol"


def test_token_loop_steps_by_the_block_it_advances(dense, single_chip):
    """A view's row term advances by exactly one block of its loop.

    The device bounds a partial final iteration from the loop's divisor, so the
    divisor and the stride a view moves by have to describe the same block.  If
    they disagreed the last iteration of a request would read the wrong rows,
    and the disagreement would be silent.
    """
    deployment = lower_to_abi3(dense, single_chip)
    loops = {
        d.descriptor_id: d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL
    }
    checked = 0
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
            continue
        payload = descriptor.payload
        for slot in range(payload["dynamic_term_count"]):
            if payload[f"term{slot}_kind"] != int(SelectorKind.LOOP_INDUCTION):
                continue
            loop = loops.get(payload[f"term{slot}_index"])
            if loop is None or loop["bound_selector_kind"] != int(
                SelectorKind.RUNTIME_SYMBOL
            ):
                continue
            block = loop["bound_divisor"]
            assert loop["step"] == 1
            # dim0 is one block of rows, and the term moves by one block.
            assert payload["dim0"] == block, (payload["dim0"], block)
            assert payload[f"term{slot}_stride"] == block * payload["stride0"]
            checked += 1
    assert checked, "no token-loop view to check"


def test_the_token_loop_covers_every_row_of_the_span(dense, single_chip):
    """Across all its iterations the loop must present exactly `span` rows.

    Checking the encoding field by field is not enough: the two assertions above
    both held while the loop ran a single iteration at every prompt length,
    because the step was the divisor and the device had already divided by the
    divisor before applying it.  Every gate used a prompt that fits in one
    block, so nothing noticed until the ROM lane encoded the same loop
    differently.  This asserts the property that actually matters -- that the
    rows presented add up to the request -- at spans on both sides of a block
    boundary.
    """
    deployment = lower_to_abi3(dense, single_chip)
    # resolve() reads descriptors and bindings, never bytes, so no device
    # memory is needed -- and the synthetic fixture has no checkpoint to map.
    resolver = ViewResolver(deployment, None)
    loops = {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL
        and d.payload["bound_selector_kind"] == int(SelectorKind.RUNTIME_SYMBOL)
    }
    assert loops
    checked = 0
    for view in deployment.table.descriptors():
        if view.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
            continue
        payload = view.payload
        if payload["dynamic_term_count"] < 1:
            continue
        if payload["term0_kind"] != int(SelectorKind.LOOP_INDUCTION):
            continue
        loop = loops.get(payload["term0_index"])
        if loop is None:
            continue
        block = loop.payload["bound_divisor"]
        for span in (1, block - 1, block, block + 1, 2 * block, 3 * block + 7):
            if span < 1:
                continue
            symbols = {int(Symbol.SPAN_TOKENS): span}
            trip = loop_trip_count(loop.payload, symbols)
            rows = sum(
                resolver.resolve(
                    view.descriptor_id,
                    loops={loop.descriptor_id: i},
                    symbols=symbols,
                ).dims[0]
                for i in range(trip)
            )
            assert rows == span, (view.descriptor_id, span, trip, rows)
            checked += 1
    assert checked, "no token-loop view to check"


def test_alternating_layer_structures_band_with_period_two(single_chip):
    """A model that alternates two layer forms compresses without reordering.

    Two interleaved single-layer bands would run every even layer before every
    odd one and break the residual chain, so the repeating unit has to be the
    *pair*.
    """
    graph = alternating_graph(pairs=4)
    plan = build_plan(graph, single_chip)
    assert [b.period for b in plan.bands] == [2]
    assert plan.bands[0].layer_count == 4
    assert plan.proofs["layers_covered"] == 8
    deployment = lower_to_abi3(graph, single_chip)
    report = require_admitted(deployment, single_chip)
    assert report.instruction_count < 120
    assert check_deployment(graph, deployment, single_chip)["ok"]


def test_band_carries_the_residual_in_one_buffer(dense, single_chip):
    """The value entering a band and the value leaving it are one buffer.

    Emitted as a loop, a body that read one buffer and wrote another would
    re-read the prologue's value every iteration, collapsing the stack to one
    layer applied N times.
    """
    plan = build_plan(dense, single_chip)
    keys = plan.activation_keys
    live_in = keys["hidden0"]
    per_layer = [keys[f"l{i}.res2"] for i in range(4)]
    assert len(set(per_layer)) == 1, per_layer
    assert live_in == per_layer[0]


def test_state_views_bind_the_prepared_image(dense, single_chip):
    """A transaction reads what it has just appended, not the last commit."""
    deployment, plan = lower_with_plan(dense, single_chip)
    prepared = {
        deployment.table[d.descriptor_id].payload["prepared_object_id"]
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.STATE
    }
    committed = {
        deployment.table[d.descriptor_id].payload["committed_object_id"]
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.STATE
    }
    touched = set()
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        for slot in (*range(4), *range(4)):
            pass
        views = [descriptor.payload[f"input_view_{i}"] for i in range(4)]
        views += [descriptor.payload[f"output_view_{i}"] for i in range(2)]
        for vid in views:
            if vid == 0xFFFFFFFF:
                continue
            touched.add(deployment.table[vid].primary_object_id)
    assert touched & prepared, "no operator reads or writes the prepared image"
    assert not (touched & committed), (
        "an operator addresses the committed image; the commit publishes it, "
        "execution runs against the prepared one"
    )


def test_the_ring_is_appended_past_the_staged_request(dense, single_chip):
    """The host stages a request from element zero; the device appends past it.

    Both halves matter: reading the window at an offset would look for a token
    where the host wrote none, and appending at the generation counter would
    overwrite the very token the host had just staged.
    """
    deployment = lower_to_abi3(dense, single_chip)
    host_objects = {
        d.descriptor_id
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and d.payload["storage_class"] == int(StorageClass.HOST)
    }
    offsets = set()
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.TENSOR_VIEW:
            continue
        if descriptor.primary_object_id not in host_objects:
            continue
        for slot in range(descriptor.payload["dynamic_term_count"]):
            if descriptor.payload[f"term{slot}_kind"] == int(
                SelectorKind.RUNTIME_SYMBOL
            ):
                offsets.add(descriptor.payload[f"term{slot}_index"])
    assert int(Symbol.POSITION_END) in offsets
    assert int(Symbol.POSITION_START) not in offsets
    assert int(Symbol.GENERATION_INDEX) not in offsets


def test_every_schedule_states_a_complete_tile_mapping(dense, moe, single_chip):
    """A cycle model cannot time an operation whose tile shape says nothing.

    An embedding lookup has no contraction axis and attention's depth is the
    head dimension, so zero is a tempting default for both -- and it is the one
    value that means "unstated".
    """
    for graph in (dense, moe):
        deployment = lower_to_abi3(graph, single_chip)
        schedules = [
            d
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.SCHEDULE
        ]
        assert schedules
        for descriptor in schedules:
            payload = descriptor.payload
            for field in ("tile_rows", "tile_cols", "tile_depth"):
                assert payload[field] > 0, (descriptor.descriptor_id, field)
            assert payload["issue_window"] > 0
            assert payload["resource_bound"] > 0
            assert payload["max_outstanding"] > 0


def test_every_resident_object_states_an_address(dense, single_chip):
    """A cycle model that must invent an address reports its own placement."""
    deployment, plan = lower_with_plan(dense, single_chip)
    objects = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
    ]
    addressed = [d for d in objects if d.payload["base_address"] > 0]
    # Only the first object of each address space may legitimately sit at zero.
    assert len(objects) - len(addressed) <= 3
    spans = sorted(
        (d.payload["base_address"], d.payload["size_bytes"])
        for d in objects
        if d.payload["storage_class"] == int(StorageClass.HBM)
    )
    for (base, size), (next_base, _) in zip(spans, spans[1:]):
        assert base + size <= next_base, "two HBM objects overlap"


# ---------------------------------------------------------------------------
# Zero-copy weights
# ---------------------------------------------------------------------------
def test_weights_are_zero_copy_views_over_the_checkpoint(dense, single_chip):
    deployment, plan = lower_with_plan(dense, single_chip)
    bound = {
        t.tensor_id: t.binding for t in dense.tensors if t.binding is not None
    }
    declared_bytes = sum(b.bytes for b in bound.values())

    weight_objects = [
        descriptor
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
        and descriptor.payload["storage_class"] == int(StorageClass.HBM)
        and descriptor.permissions & Permission.IMMUTABLE
    ]
    assert weight_objects
    total = 0
    seen: set[tuple[str, int, int]] = set()
    for descriptor in weight_objects:
        source = deployment.objects[descriptor.descriptor_id]
        assert source.kind == "segments"
        for segment in source.segments:
            key = (segment.path, segment.offset, segment.bytes)
            assert key not in seen, "a checkpoint range is materialised twice"
            seen.add(key)
            assert segment.sha256 is not None
            total += segment.bytes
    assert total == declared_bytes
    # A handful of objects, not one per tensor.
    assert len(weight_objects) <= len(bound) // 2


def test_a_segmented_binding_is_placed_one_authenticated_range_per_member(
    moe, single_chip
):
    """A bank the checkpoint stores apart is placed as the ranges it is.

    A routed expert stack is one operand and *E* checkpoint tensors.  Its
    binding carries both: the totals, and the segments those totals are made
    of.  Reducing it to the totals reconciles byte for byte -- the object is
    the right size, every byte is accounted for once, the digest is the
    binding's own -- and names a single contiguous run starting at expert 0,
    which is not where the other experts are.  Nothing downstream complains,
    which is exactly why this is checked here.
    """
    deployment, _plan = lower_with_plan(moe, single_chip)
    banks = [
        t
        for t in moe.tensors
        if t.binding is not None and t.binding.segments
    ]
    assert banks
    materialised: dict[tuple[str, int, int], str] = {}
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        source = deployment.objects.get(descriptor.descriptor_id)
        if source is None or source.kind != "segments":
            continue
        for segment in source.segments:
            materialised[(segment.path, segment.offset, segment.bytes)] = segment.sha256
    for tensor in banks:
        binding = tensor.binding
        assert len(binding.segments) > 1
        for segment in binding.segments:
            key = (segment.path, segment.offset, segment.bytes)
            assert key in materialised, f"{segment.source_name} is placed nowhere"
            assert materialised[key] == segment.sha256
        # The flattened range is not what the object names: it is the total,
        # and the segments are not laid down in ascending file order.
        assert (binding.path, binding.offset, binding.bytes) not in materialised
        assert [s.offset for s in binding.segments] != sorted(
            s.offset for s in binding.segments
        )


def test_weight_objects_are_never_writable(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        if not descriptor.permissions & Permission.IMMUTABLE:
            continue
        assert not descriptor.permissions & Permission.WRITE


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_two_builds_are_byte_identical(dense, single_chip):
    first = lower_to_abi3(dense, single_chip)
    second = lower_to_abi3(dense, single_chip)
    assert first.program == second.program
    assert first.table.encode() == second.table.encode()
    assert first.deployment_digest == second.deployment_digest
    assert first.manifest() == second.manifest()


def test_cluster_build_is_deterministic(moe, cluster):
    first = lower_to_abi3(moe, cluster)
    second = lower_to_abi3(moe, cluster)
    assert first.program == second.program
    assert first.deployment_digest == second.deployment_digest


def test_deployment_round_trips_through_disk(dense, single_chip, tmp_path):
    from runtime.abi3.deployment import Deployment

    deployment = lower_to_abi3(dense, single_chip)
    deployment.write(tmp_path / "deployment")
    reloaded = Deployment.read(tmp_path / "deployment")
    assert reloaded.deployment_digest == deployment.deployment_digest
    require_admitted(reloaded, single_chip)


# ---------------------------------------------------------------------------
# One backend, one code path
# ---------------------------------------------------------------------------
def test_lowering_never_names_a_model():
    """No model name may reach executable code in the emitter.

    Prose may name the models -- the design has to be explained -- but a string
    literal, identifier or attribute naming one is how a backend acquires a
    per-model code path, so the check is run over the parsed module with
    docstrings and comments removed.
    """
    import ast

    module = ast.parse(Path("compiler/backends/hbm_sram/lower.py").read_text())
    docstrings = set()
    for node in ast.walk(module):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef)):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))
    names: list[str] = []
    for node in ast.walk(module):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) not in docstrings:
                names.append(node.value)
        elif isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
    blob = " ".join(names).lower()
    for forbidden in ("qwen", "deepseek", "llama", "mistral"):
        assert forbidden not in blob, f"{forbidden} reaches executable code"


def test_the_same_call_serves_both_graphs(dense, moe, single_chip, cluster):
    dense_deployment = lower_to_abi3(dense, single_chip)
    moe_deployment = lower_to_abi3(moe, cluster)
    assert dense_deployment.backend == moe_deployment.backend
    assert dense_deployment.topology_class != moe_deployment.topology_class


# ---------------------------------------------------------------------------
# Kernel coverage and state discipline
# ---------------------------------------------------------------------------
def test_every_kernel_reaches_an_operator(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    covered = set()
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type == ExtendedDescriptorType.OPERATOR:
            covered.add(descriptor.payload["source_kernel_id"])
    from runtime.abi3.records import decode_body, split_program

    _, body = split_program(deployment.program)
    for instruction in decode_body(body):
        if instruction.source_operation_id != 0xFFFFFFFF:
            covered.add(instruction.source_operation_id)
    expected = {
        k.index
        for k in dense.kernels
        if k.layer is None or k.layer == 0
    }
    assert expected <= covered


def test_state_resources_are_merged_and_closed(dense, single_chip):
    deployment, plan = lower_with_plan(dense, single_chip)
    # Eight declared resources -- a key and a value cache per layer -- become
    # two physical resources, one per role, each with one member per layer.
    assert len(dense.states) == 8
    assert len(plan.states) == 2
    assert all(len(s.members) == 4 for s in plan.states)
    report = verify_deployment(deployment, single_chip)
    assert report.admitted
    assert report.state_resources == 2
    assert report.checks["state_discipline"]


# ---------------------------------------------------------------------------
# The independent checker
# ---------------------------------------------------------------------------
def test_independent_checker_accepts_the_dense_build(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    report = check_deployment(dense, deployment, single_chip)
    assert report["ok"], report["errors"]
    assert report["verifier"]["admitted"]


def test_independent_checker_accepts_the_cluster_build(moe, cluster):
    deployment = lower_to_abi3(moe, cluster)
    report = check_deployment(moe, deployment, cluster)
    assert report["ok"], report["errors"]
    assert report["actual"]["link_instructions"] > 0


def test_independent_checker_rejects_a_tampered_deployment(dense, single_chip):
    deployment = lower_to_abi3(dense, single_chip)
    victim = next(
        oid
        for oid, source in deployment.objects.items()
        if source.kind == "segments"
    )
    source = deployment.objects[victim]
    deployment.objects[victim] = type(source)(
        kind="zero", size_bytes=source.size_bytes
    )
    report = check_deployment(dense, deployment, single_chip)
    assert not report["ok"]
    assert any("zero-copy" in e or "segments" in e for e in report["errors"])


def test_checker_does_not_import_the_lowering():
    source = Path("compiler/backends/hbm_sram/check.py").read_text()
    assert "from .lower" not in source
    assert "import lower" not in source
    assert "from .plan" not in source


# ---------------------------------------------------------------------------
# The real Qwen IR, when the frontend lane publishes it
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not REAL_QWEN_IR.exists(), reason="Qwen IR not published yet")
def test_real_qwen_ir_lowers_and_is_admitted():
    """The 691-kernel, 36-layer Qwen graph compiles to a handful of instructions.

    The ABI 2.5 backend expanded one forward step of this model into 924,386
    commands.  The bound asserted here is three orders of magnitude below that;
    the actual figure is printed so a regression is visible even while it still
    passes.
    """
    graph = read_kernel_graph(REAL_QWEN_IR)
    capability = single_chip_capability()
    deployment, plan = lower_with_plan(graph, capability)
    report = require_admitted(deployment, capability)
    assert report.instruction_count < 1000
    assert report.loop_depth <= capability.limits["max_loop_depth"]
    assert check_deployment(graph, deployment, capability)["ok"]
    # 36 layers, one band, one loop: the layer count is nowhere in the program.
    assert plan.proofs["bands"] == 1
    assert plan.proofs["layers_covered"] == 36
    assert plan.proofs["degraded_bands"] == 0
    # 16 GB of weights, described rather than copied.
    assert plan.proofs["weight_bytes"] > 16_000_000_000
    assert plan.proofs["hbm_fits"] and plan.proofs["sram_fits"]
    print(
        json.dumps(
            {
                "instructions": report.instruction_count,
                "descriptors": report.descriptor_count,
                "proved_retired_work": report.proved_retired_work,
                "weight_objects": plan.proofs["weight_objects"],
                "weight_segments": plan.proofs["weight_segments"],
                "weight_bytes": plan.proofs["weight_bytes"],
                "bands": plan.proofs["bands"],
            },
            indent=2,
        )
    )


@pytest.mark.skipif(not REAL_QWEN_IR.exists(), reason="Qwen IR not published yet")
def test_real_qwen_ir_is_deterministic():
    graph = read_kernel_graph(REAL_QWEN_IR)
    capability = single_chip_capability()
    first = lower_to_abi3(graph, capability)
    second = lower_to_abi3(graph, capability)
    assert first.program == second.program
    assert first.table.encode() == second.table.encode()
    assert first.deployment_digest == second.deployment_digest


# ---------------------------------------------------------------------------
# The command line
# ---------------------------------------------------------------------------
def test_cli_builds_verifies_and_reports(tmp_path):
    import tools.build_hbm_sram_deployment as cli

    graph = dense_graph(layers=6)
    ir = tmp_path / "kernel_ir.v3.json"
    graph.write(ir)
    out = tmp_path / "deployment"
    status = cli.main(
        [
            "--ir",
            str(ir),
            "--profile",
            "single-chip",
            "--out",
            str(out),
            "--check-determinism",
            "--json",
        ]
    )
    assert status == 0
    report = json.loads((out / "build_report.json").read_text())
    assert report["verifier"]["admitted"]
    assert report["checker"]["ok"]
    assert report["deterministic"] is True
    assert report["neutrality_errors"] == []
    assert (out / "deployment.json").exists()
    assert (out / "descriptors.bin").exists()
    assert (out / "program.bin").exists()
    assert (out / "physical_plan.json").exists()


def test_cli_serves_the_cluster_profile(tmp_path):
    import tools.build_hbm_sram_deployment as cli

    graph = moe_graph(layers=3)
    ir = tmp_path / "kernel_ir.v3.json"
    graph.write(ir)
    out = tmp_path / "cluster"
    assert cli.main(["--ir", str(ir), "--profile", "cluster-32", "--out", str(out)]) == 0
    report = json.loads((out / "build_report.json").read_text())
    assert report["node_count"] == 32
    assert report["program"]["link_instructions"] > 0


# ---------------------------------------------------------------------------
# BROADCAST: an inserted axis is read through a zero stride, never written
# ---------------------------------------------------------------------------
def test_a_shared_axis_is_readable_but_never_writable():
    """A zero stride on an axis of extent above one names one location.

    Reading it repeats that location, which is the whole point.  Writing it
    would make the axis an alias, so the emitter refuses to mark such a view
    writable rather than leaving the surviving value to store order.
    """
    assert shares_an_axis([3, 4, 5], [20, 0, 1])
    assert not shares_an_axis([3, 4, 5], [20, 5, 1])
    # An axis of extent one reaches one element whatever its stride, so a zero
    # there is a degenerate axis and not a shared one.
    assert not shares_an_axis([3, 1, 5], [5, 0, 1])


def test_the_hyper_connection_expansion_moves_no_duplicate_rows():
    """A broadcast reads one row through a stride-zero axis.

    The mHC expansion is ``unsqueeze(2).repeat(1, 1, hc_mult, 1)``.  Expressed
    as a ``CONCAT`` it reached ``REDUCTION.GROUPED_CONCAT``, which joined on
    axis 0 and therefore refused a ``[tokens, streams, width]`` result --
    correctly, because the join it would have performed puts four consecutive
    *tokens* where four *streams* belong.  As a ``BROADCAST`` it is one movement
    whose source names the row once per stream through a stride of zero.

    That is a property of the movement, not of the model that needs it, so it
    is checked on the smallest graph that has the shape.
    """
    graph = movement_graph()
    kernel = next(k for k in graph.kernels if k.kind == "BROADCAST")
    assert len(kernel.inputs) == 1
    assert kernel.attributes["axis"] == 1
    extent = kernel.attributes["extent"]

    capability = cluster32_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)

    operators = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["source_kernel_id"] == kernel.index
    ]
    assert len(operators) == 1
    payload = operators[0].payload
    assert payload["engine_family"] == int(Major.DMA)

    def axes(view_id: int):
        view = deployment.table.get(
            view_id, ExtendedDescriptorType.TENSOR_VIEW
        ).payload
        rank = view["rank"]
        return (
            [view[f"dim{a}"] for a in range(rank)],
            [view[f"stride{a}"] for a in range(rank)],
        )

    source_dims, source_strides = axes(payload["input_view_0"])
    result_dims, result_strides = axes(payload["output_view_0"])
    assert source_dims == result_dims
    assert source_dims[1] == extent
    # The inserted axis is shared on the way in and dense on the way out.
    assert source_strides[1] == 0
    assert result_strides[1] == source_strides[2] * source_dims[2]
    assert not shares_an_axis(result_dims, result_strides)


def _broadcast_graph(*, extent: int = 4, result_shape=None) -> KernelGraph:
    """The smallest graph that carries one BROADCAST, for the neutral checks."""
    span, width = Symbolic("span_tokens", 1, 64), 8
    shape = result_shape if result_shape is not None else (span, extent, width)
    tensors = (
        Tensor(tensor_id="tokens", dtype="u32", shape=(span, 1), role="input"),
        Tensor(tensor_id="hidden", dtype="bf16", shape=(span, width),
               role="activation"),
        Tensor(tensor_id="streams", dtype="bf16", shape=shape, role="activation"),
        Tensor(tensor_id="out", dtype="u32", shape=(1, 1), role="output"),
    )
    kernels = (
        Kernel(index=0, kernel_id="k0", kind="BROADCAST", inputs=("hidden",),
               outputs=("streams",), numeric_contract="structural_hc_expand_bf16_v1",
               attributes={"axis": 1, "extent": extent}),
    )
    return KernelGraph(
        model_id="synthetic-broadcast",
        source={"family": "broadcast"},
        symbols=(RuntimeSymbol("span_tokens", 1, 64, 1),),
        tensors=tensors,
        states=(),
        kernels=kernels,
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("out",), ()),
            Entrypoint("decode", ("tokens",), ("out",), ()),
        ),
        generation_policy={"eos_token_ids": [0], "maximum_new_tokens": 1,
                           "vocabulary_size": 8},
    )


def test_a_well_formed_broadcast_is_neutral():
    assert check_neutral(_broadcast_graph()) == []


@pytest.mark.parametrize(
    "shape_factory, fragment",
    [
        # the inserted axis is the wrong size
        (lambda span, width: (span, 3, width), "declares"),
        # the axis was inserted in the wrong place
        (lambda span, width: (4, span, width), "declares"),
        # a concatenation, which is what the defect said this operation was
        (lambda span, width: (span, 4 * width), "declares"),
    ],
)
def test_a_broadcast_whose_result_is_not_the_inserted_axis_is_rejected(
    shape_factory, fragment
):
    span, width = Symbolic("span_tokens", 1, 64), 8
    errors = check_neutral(
        _broadcast_graph(result_shape=shape_factory(span, width))
    )
    assert errors and any(fragment in e and "BROADCAST" in e for e in errors)


def test_a_broadcast_must_state_its_axis_and_extent():
    graph = _broadcast_graph()
    stripped = Kernel(
        index=0, kernel_id="k0", kind="BROADCAST", inputs=("hidden",),
        outputs=("streams",), numeric_contract="structural_hc_expand_bf16_v1",
        attributes={},
    )
    graph = KernelGraph(
        model_id=graph.model_id, source=graph.source, symbols=graph.symbols,
        tensors=graph.tensors, states=graph.states, kernels=(stripped,),
        entrypoints=graph.entrypoints,
        generation_policy=graph.generation_policy,
    )
    errors = check_neutral(graph)
    assert any("'axis'" in e for e in errors)


# ---------------------------------------------------------------------------
# SELECT: the inverse of a broadcast
# ---------------------------------------------------------------------------
def _select_graph(*, axis: int = 1, index: int = 1, result_shape=None) -> KernelGraph:
    """The smallest graph that carries one SELECT, for the neutral checks."""
    span, planes, width = Symbolic("span_tokens", 1, 64), 2, 4
    shape = result_shape if result_shape is not None else (span, width)
    tensors = (
        Tensor(tensor_id="tokens", dtype="u32", shape=(span, 1), role="input"),
        Tensor(tensor_id="packed", dtype="fp32", shape=(span, planes, width),
               role="activation"),
        Tensor(tensor_id="plane", dtype="fp32", shape=shape, role="activation"),
        Tensor(tensor_id="out", dtype="u32", shape=(1, 1), role="output"),
    )
    kernels = (
        Kernel(index=0, kernel_id="k0", kind="SELECT", inputs=("packed",),
               outputs=("plane",),
               numeric_contract="hyper_connection_hc_pre_bf16_v1",
               attributes={"axis": axis, "index": index}),
    )
    return KernelGraph(
        model_id="synthetic-select",
        source={"family": "select"},
        symbols=(RuntimeSymbol("span_tokens", 1, 64, 1),),
        tensors=tensors,
        states=(),
        kernels=kernels,
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("out",), ()),
            Entrypoint("decode", ("tokens",), ("out",), ()),
        ),
        generation_policy={"eos_token_ids": [0], "maximum_new_tokens": 1,
                           "vocabulary_size": 8},
    )


def test_a_well_formed_select_is_neutral():
    assert check_neutral(_select_graph()) == []


@pytest.mark.parametrize(
    "axis, index, result_shape, fragment",
    [
        # the dropped axis is still in the result
        (1, 0, None, None),
        # index outside the axis
        (1, 5, None, "outside axis"),
        # axis outside the source rank
        (7, 0, None, "outside the rank"),
    ],
)
def test_select_rejects_an_index_or_axis_the_source_does_not_have(
    axis, index, result_shape, fragment
):
    errors = check_neutral(
        _select_graph(axis=axis, index=index, result_shape=result_shape)
    )
    if fragment is None:
        assert errors == []
        return
    assert errors and any(fragment in e and "SELECT" in e for e in errors)


def test_a_select_whose_result_keeps_the_dropped_axis_is_rejected():
    span, planes, width = Symbolic("span_tokens", 1, 64), 2, 4
    errors = check_neutral(_select_graph(result_shape=(span, planes, width)))
    assert errors and any("SELECT of index" in e for e in errors)


def test_a_select_may_not_drop_a_runtime_symbol():
    span = Symbolic("span_tokens", 1, 64)
    errors = check_neutral(_select_graph(axis=0, index=0, result_shape=(2, 4)))
    assert errors and any("static extent" in e for e in errors)


def test_a_selected_coefficient_plane_is_an_offset_not_a_gather():
    """Two planes of one packed block differ only by an element offset.

    ``HYPER_CONNECT_PRE``'s first output view is the packed
    ``[tokens, 2, streams]`` pre/post block the frozen ``VECTOR.MHC`` row
    names.  Its two planes go to different consumers -- the pre plane weights
    the branch reduction, the post plane is ``HYPER_CONNECT_POST``'s third
    operand -- so the neutral IR has to be able to name one plane of a tensor.
    On a machine whose operands are strided views that costs an offset and a
    dropped axis, which is what this checks: same object, same strides, offsets
    zero and ``streams``.
    """
    graph = movement_graph()
    capability = single_chip_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)
    selects = [k for k in graph.kernels if k.kind == "SELECT"]
    assert [k.attributes["index"] for k in selects] == [0, 1]
    assert len({k.inputs[0] for k in selects}) == 1
    planes = []
    for kernel in selects:
        operators = [
            d
            for d in deployment.table.descriptors()
            if d.descriptor_type == ExtendedDescriptorType.OPERATOR
            and d.payload["source_kernel_id"] == kernel.index
        ]
        assert len(operators) == 1
        payload = operators[0].payload
        assert payload["engine_family"] == int(Major.DMA)
        planes.append(
            deployment.table.get(
                payload["input_view_0"], ExtendedDescriptorType.TENSOR_VIEW
            )
        )
    pre, post = planes
    assert pre.primary_object_id == post.primary_object_id
    assert pre.payload["rank"] == post.payload["rank"] == 2
    for axis in range(2):
        assert pre.payload[f"dim{axis}"] == post.payload[f"dim{axis}"]
        assert pre.payload[f"stride{axis}"] == post.payload[f"stride{axis}"]
    streams = pre.payload["dim1"]
    assert pre.payload["element_offset"] == 0
    assert post.payload["element_offset"] == streams
    # The packed block's row is two planes wide, so one plane is strided.
    assert pre.payload["stride0"] == 2 * streams


def test_a_state_update_leaves_the_projection_slot_empty():
    """``VECTOR.COMPRESS`` sub-case 2 binds ``in0`` and ``in2``, never ``in1``.

    The operand convention's ``in1`` is the projection matrix and a state
    update has none; its ``in2`` is the position embedding, which is exactly
    what the absolute-position table is.  A required hole is a stated slot, not
    a missing operand, so packing the two operands down into ``in0`` and
    ``in1`` puts the position table where the projection belongs -- and the
    engine refuses that outright, which is what it did.
    """
    graph = movement_graph()
    capability = single_chip_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)
    kernel = next(k for k in graph.kernels if k.kind == "COMPRESS_STATE_UPDATE")
    assert len(kernel.inputs) == 2
    operator = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["source_kernel_id"] == kernel.index
    )
    payload = operator.payload
    assert payload["engine_family"] == int(Major.VECTOR)
    assert payload["aux_id_0"] == 2, "the sub-case selector"
    assert payload["input_view_0"] != NO_ID
    assert payload["input_view_1"] == NO_ID
    assert payload["input_view_2"] != NO_ID
    assert payload["input_view_3"] == NO_ID
    position = deployment.table.get(
        payload["input_view_2"], ExtendedDescriptorType.TENSOR_VIEW
    ).payload
    ape = next(t for t in graph.tensors if t.tensor_id == "ape")
    assert [position[f"dim{a}"] for a in range(position["rank"])] == list(ape.shape)


def test_an_axis_one_concatenation_is_one_operator_naming_its_join_axis():
    """A width-axis join is one operator that states the axis, not a movement.

    This test used to assert the opposite -- one ``DMA.TRANSFER`` per column
    window -- because ``REDUCTION.GROUPED_CONCAT`` joined on axis 0 only, and a
    width join puts operands of *different widths* side by side, which axis 0
    cannot express at all.  Amendment A17 gives the operator a join axis in
    ``aux_id_0``, so the hand-expansion is no longer the spelling: it is one
    lane emitting transfers where the other emits ``REDUCTION.3``, which is the
    divergence the shared IR exists to prevent.

    The property the movement form was protecting has not gone away, so it is
    asserted here of the operator instead: input *i* occupies its own column
    range of the result, in **input-slot order**, the ranges tile the row
    exactly once, and no row is duplicated.  Under A17 that is a consequence of
    the descriptor rather than of a traversal -- the operand widths sum to the
    output's and every operand agrees on the axis the join does not consume --
    which is precisely why it is now checkable at admission.
    """
    graph = movement_graph()
    capability = single_chip_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)
    kernel = next(k for k in graph.kernels if k.kind == "CONCAT")
    assert kernel.attributes["axis"] == 1
    operators = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["source_kernel_id"] == kernel.index
    ]
    assert len(operators) == 1, "one join is one operator, not one per input"
    payload = operators[0].payload
    assert payload["engine_family"] == int(Major.REDUCTION)
    assert payload["engine_sub"] == int(Reduction.GROUPED_CONCAT)
    # The whole of A17: the axis travels in aux_id_0, and an unstated axis
    # would be read as a row join -- silently the wrong operation.
    assert payload["aux_id_0"] == 1

    def view(view_id: int):
        return deployment.table.get(
            view_id, ExtendedDescriptorType.TENSOR_VIEW
        ).payload

    slots = [payload[f"input_view_{s}"] for s in range(4)]
    assert [s != NO_ID for s in slots] == [True, True, False, False]
    sources = [view(s) for s in slots[: len(kernel.inputs)]]
    result = view(payload["output_view_0"])
    tensors = {t.tensor_id: t for t in graph.tensors}

    # Slot order is the graph's input order, so the descriptor states the
    # column order and no backend has to choose one.
    widths = [tensors[name].shape[1] for name in kernel.inputs]
    assert [s["dim1"] for s in sources] == widths
    # The ranges tile the result's row exactly once: the sum of the inputs'
    # widths is the output's, which is what makes each input's block one
    # contiguous run and nothing a duplicate.
    assert result["dim1"] == sum(widths)
    assert result["dim1"] == tensors[kernel.outputs[0]].shape[1]
    # Every operand agrees on the extent the join does not consume.
    assert {s["dim0"] for s in sources} == {result["dim0"]}
    # Rank 2 on every operand -- A17 defines a feature join for nothing else.
    assert {s["rank"] for s in sources} == {2}
    assert result["rank"] == 2


def test_the_hyper_connection_post_operands_keep_the_token_axis_leading():
    """A batch axis is inserted after the tokens, never before them.

    ``VECTOR.MHC``'s ``HYPER_CONNECT_POST`` row states ``[batch, span, ...]``
    and the neutral IR is token-major, so the backend inserts the missing axis.
    Putting it first would name the same elements but would defeat amendment
    A13: a leading extent of one is never the partial final iteration's row
    count, so a 104-token span would be presented as a whole 512-row block.
    """
    graph = movement_graph()
    capability = single_chip_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)
    kernel = next(k for k in graph.kernels if k.kind == "HYPER_CONNECT_POST")
    assert len(kernel.inputs) == 4
    operator = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["source_kernel_id"] == kernel.index
    )
    payload = operator.payload
    loops = {
        d.descriptor_id: d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL
    }
    view_ids = [payload[f"input_view_{s}"] for s in range(4)]
    view_ids.append(payload["output_view_0"])
    for view_id in view_ids:
        view = deployment.table.get(
            view_id, ExtendedDescriptorType.TENSOR_VIEW
        ).payload
        assert view["dim1"] == 1, "the batch axis is the second, not the first"
        row = next(
            loops[view[f"term{s}_index"]]
            for s in range(view["dynamic_term_count"])
            if view[f"term{s}_kind"] == int(SelectorKind.LOOP_INDUCTION)
            and view[f"term{s}_index"] in loops
        )
        assert view["dim0"] == row["bound_divisor"]


# ---------------------------------------------------------------------------
# Block scales: the one operand class with no descriptor of its own
# ---------------------------------------------------------------------------
def block_scaled_graph(
    *,
    layers: int = 3,
    hidden: int = 256,
    out: int = 128,
    block: int = 32,
    span_max: int = 64,
    shards: int = 2,
) -> KernelGraph:
    """A stack of block-scaled projections, one per layer.

    The point of the fixture is the *pair*: every layer's weight is FP8 with an
    E8M0 code per ``block`` elements of its row, and the scale is a checkpoint
    tensor of its own.  Nothing else in this file declares a scale, which is
    how a scale object laid out in checkpoint order rather than in the weight's
    order stayed invisible.  ``shards=2`` and the interleaved cursor put the
    scales somewhere other than beside their weights, exactly as a released
    checkpoint does.
    """
    ck = _Checkpoint(shards)
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []

    def act(name: str, shape: tuple, dtype: str = "bf16", role: str = "activation") -> str:
        tensors.append(Tensor(tensor_id=name, dtype=dtype, shape=shape, role=role))
        return name

    def scaled_weight(name: str, rows: int, cols: int) -> str:
        # A scale per ``block`` columns and per whole row: the A8 case, which
        # is what MXFP4's 32-element blocks along the reduction axis are.
        scale_id = f"{name}.scale"
        tensors.append(
            Tensor(
                tensor_id=scale_id,
                dtype="e8m0",
                shape=(rows, cols // block),
                role="weight",
                binding=ck.bind(scale_id, rows * (cols // block), "e8m0"),
            )
        )
        tensors.append(
            Tensor(
                tensor_id=name,
                dtype="fp8_e4m3fn",
                shape=(rows, cols),
                role="weight",
                binding=ck.bind(name, rows * cols, "fp8_e4m3fn"),
                scale_tensor_id=scale_id,
                scale_block_elements=block,
            )
        )
        return name

    def emit(kind: str, ins, outs, contract: str, **kw) -> None:
        kernels.append(
            Kernel(
                index=len(kernels),
                kernel_id=f"k{len(kernels):04d}.{kind.lower()}",
                kind=kind,
                inputs=tuple(ins),
                outputs=tuple(outs),
                numeric_contract=contract,
                **kw,
            )
        )

    act("tokens", (SPAN, 1), "u32", role="input")
    tensors.append(
        Tensor(
            tensor_id="embed",
            dtype="bf16",
            shape=(64, hidden),
            role="weight",
            binding=ck.bind("embed", 64 * hidden, "bf16"),
        )
    )
    act("hidden0", (SPAN, hidden))
    emit("EMBEDDING_LOOKUP", ["tokens", "embed"], ["hidden0"],
         "lookup_bf16_token_embedding_v1")

    previous = "hidden0"
    for index in range(layers):
        p = f"l{index}"
        scaled_weight(f"{p}.proj", out, hidden)
        tensors.append(
            Tensor(
                tensor_id=f"{p}.back",
                dtype="bf16",
                shape=(hidden, out),
                role="weight",
                binding=ck.bind(f"{p}.back", hidden * out, "bf16"),
            )
        )
        act(f"{p}.mid", (SPAN, out))
        act(f"{p}.res", (SPAN, hidden))
        layer = {"layer": index}
        emit("MATMUL", [previous, f"{p}.proj"], [f"{p}.mid"],
             "matrix_dense_fp8_linear_bf16_block_scaled_contraction_v1", **layer)
        emit("MATMUL", [f"{p}.mid", f"{p}.back"], [f"{p}.res"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        previous = f"{p}.res"

    tensors.append(
        Tensor(
            tensor_id="last.index",
            dtype="u32",
            shape=(1, 1),
            role="weight",
            binding=ck.bind("last.index", 1, "u32"),
        )
    )
    tensors.append(
        Tensor(
            tensor_id="lm_head",
            dtype="bf16",
            shape=(hidden, 64),
            role="weight",
            binding=ck.bind("lm_head", hidden * 64, "bf16"),
        )
    )
    act("hidden.last", (1, hidden))
    act("logits", (1, 64))
    act("token", (1, 1), "u32")
    act("tokens.out", (1, 1), "u32", role="output")
    emit("LAST_TOKEN_SELECT", [previous, "last.index"], ["hidden.last"],
         "lookup_bf16_token_embedding_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "lm_head_bf16_vocabulary_projection_v1")
    emit("ARGMAX", ["logits"], ["token"], "greedy_lowest_token_id_argmax_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_token_append_eos_v1")

    return KernelGraph(
        model_id=f"synthetic-block-scaled-{layers}L",
        source={"family": "block_scaled", "layers": layers},
        symbols=(RuntimeSymbol("span_tokens", 1, span_max, 1),),
        tensors=tuple(tensors),
        states=(),
        kernels=tuple(kernels),
        entrypoints=(
            Entrypoint("prefill", ("tokens",), ("tokens.out",), ()),
            Entrypoint("decode", ("tokens",), ("tokens.out",), ()),
        ),
        generation_policy={
            "eos_token_ids": [63],
            "maximum_new_tokens": 8,
            "vocabulary_size": 64,
        },
    )


def _scale_code_span(view_payload, block: int, row_block: int) -> tuple[int, int]:
    """The code offset and count ``_block_scales`` derives from a view.

    Amendments A8 and A15 give a block scale no descriptor: the engine splits
    the *weight view's* element offset into a row and a column of the view's
    own row-major space and indexes the scale object with it.  Reproducing that
    arithmetic here is the point -- the test asserts the placement the engine
    will actually read, not the placement the planner intended.
    """
    rank = int(view_payload["rank"])
    width = int(view_payload[f"dim{rank - 1}"])
    rows = 1
    for axis in range(rank - 1):
        rows *= int(view_payload[f"dim{axis}"])
    per_row = width // block
    row_origin, column_origin = divmod(int(view_payload["element_offset"]), width)
    offset = (row_origin // row_block) * per_row + column_origin // block
    return offset, (rows // row_block) * per_row


def test_a_block_scale_object_is_the_weight_object_divided_by_the_block():
    """Every layer's scale lies where its weight's own offset points.

    A block scale is the one operand a view names but does not describe: the
    engine reads the scale object at ``element_offset // block`` of the weight
    view and nowhere else.  So a scale object grouped by *checkpoint
    adjacency*, while its weights are grouped by role in layer order, is not a
    different layout -- it is a different tensor's codes.  Layer 0 read
    whatever sat at code zero of the adjacency run and produced a number;
    layer 1 asked for a code past the end of an object that holds one layer's
    worth, which is where the DeepSeek MoE lane stopped.

    The property is checked on the emitted views rather than on the plan,
    because the view is what the engine reads.
    """
    layers = 3
    graph = block_scaled_graph(layers=layers)
    capability = single_chip_capability()
    deployment, plan = lower_with_plan(graph, capability)
    require_admitted(deployment, capability)
    placements = {p.tensor_id: p for p in plan.weight_placements}

    scaled = [
        t
        for t in graph.tensors
        if t.scale_tensor_id and t.role == "weight"
    ]
    assert len(scaled) == layers, "one block-scaled weight per layer"

    objects = {
        d.descriptor_id: d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.MEMORY_OBJECT
    }
    views = [
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.TENSOR_VIEW
        and d.payload["scale_object_id"] != NO_ID
    ]
    assert views, "the block-scaled weights must reach a block-scaled view"

    loops = {
        d.descriptor_id: d.payload
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.LOOP_CONTROL
    }
    for view in views:
        payload = dict(view.payload)
        block = int(payload["scale_block_elements"])
        row_block = max(int(payload["scale_block_rows"]), 1)
        scale_object = objects[payload["scale_object_id"]]
        # A layer band moves the weight window by a loop term, so the last
        # layer is the furthest read and the one an under-sized scale object
        # loses.  Walk every iteration the loop can take.
        strides = [
            int(payload[f"term{s}_stride"])
            for s in range(int(payload["dynamic_term_count"]))
            if payload[f"term{s}_kind"] == int(SelectorKind.LOOP_INDUCTION)
            and payload[f"term{s}_index"] in loops
        ]
        base = int(payload["element_offset"])
        for iteration in range(layers):
            payload["element_offset"] = base + iteration * sum(strides)
            offset, count = _scale_code_span(payload, block, row_block)
            assert offset + count <= scale_object["size_bytes"], (
                f"view {view.descriptor_id} iteration {iteration} needs code "
                f"{offset + count} of a {scale_object['size_bytes']}-code object"
            )

    # A companion object holds bytes that used to sit in an adjacency run, so
    # the placement has to stay a partition: every bound tensor placed exactly
    # once, and the objects' bytes still summing to the checkpoint's.
    placed = [p.tensor_id for p in plan.weight_placements]
    bound = {
        t.tensor_id
        for t in graph.tensors
        if t.binding is not None and t.role in {"weight", "constant"}
    }
    assert len(placed) == len(set(placed)), "a tensor is placed twice"
    assert set(placed) == bound, "a bound tensor is placed nowhere"
    assert sum(g.size_bytes for g in plan.weight_groups) == sum(
        t.binding.bytes
        for t in graph.tensors
        if t.binding is not None and t.role in {"weight", "constant"}
    )

    # And the codes it reads are its own: the placement of each layer's scale
    # is exactly the code the weight's placement addresses.
    for tensor in scaled:
        weight = placements[tensor.tensor_id]
        scale = placements[tensor.scale_tensor_id]
        cols = int(tensor.shape[-1])
        per_row = cols // int(tensor.scale_block_elements)
        assert scale.element_offset == (weight.element_offset // cols) * per_row
        assert scale.layer_stride_elements == (
            weight.layer_stride_elements // cols
        ) * per_row


def test_a_quantised_activation_carries_its_scale_into_the_view():
    """A scale the plan holds in the arena is bound, not dropped.

    A weight's scale is a placed checkpoint tensor; a quantised activation's is
    produced at run time and lives in the activation arena beside its codes.
    Both are addressed the same way -- the consumer's own element offset
    divided by the block -- so both must be named on the consumer's view.
    Binding only the weight case is silent: the FP8 codes are read as though
    every block scaled by one, which is a number, and a wrong number is the one
    failure this lane cannot see.
    """
    graph = block_scaled_graph(layers=2)
    tensors = {t.tensor_id: t for t in graph.tensors}
    # Quantise the layer-0 input and feed the codes to the projection.
    codes = Tensor(
        tensor_id="q.codes",
        dtype="fp8_e4m3fn",
        shape=(SPAN, 256),
        role="activation",
        scale_tensor_id="q.codes.scale",
        scale_block_elements=32,
    )
    scale = Tensor(
        tensor_id="q.codes.scale",
        dtype="e8m0",
        shape=(SPAN, 8),
        role="activation",
    )
    quantise = Kernel(
        index=len(graph.kernels),
        kernel_id="k9999.quantize",
        kind="QUANTIZE",
        inputs=("hidden0",),
        outputs=("q.codes", "q.codes.scale"),
        numeric_contract="matrix_dense_fp8_linear_bf16_activation_quantize_v1",
        layer=0,
    )
    kernels = []
    for kernel in graph.kernels:
        if kernel.kind == "MATMUL" and kernel.inputs[0] == "hidden0":
            kernels.append(quantise)
            kernel = Kernel(
                index=kernel.index,
                kernel_id=kernel.kernel_id,
                kind=kernel.kind,
                inputs=("q.codes", kernel.inputs[1]),
                outputs=kernel.outputs,
                numeric_contract=kernel.numeric_contract,
                layer=kernel.layer,
            )
        kernels.append(kernel)
    kernels = tuple(
        Kernel(
            index=position,
            kernel_id=k.kernel_id,
            kind=k.kind,
            inputs=k.inputs,
            outputs=k.outputs,
            numeric_contract=k.numeric_contract,
            attributes=k.attributes,
            layer=k.layer,
            state_reads=k.state_reads,
            state_writes=k.state_writes,
        )
        for position, k in enumerate(kernels)
    )
    graph = KernelGraph(
        model_id=graph.model_id,
        source=graph.source,
        symbols=graph.symbols,
        tensors=(*graph.tensors, codes, scale),
        states=graph.states,
        kernels=kernels,
        entrypoints=graph.entrypoints,
        generation_policy=graph.generation_policy,
    )
    check_neutral(graph)
    capability = single_chip_capability()
    deployment = lower_to_abi3(graph, capability)
    require_admitted(deployment, capability)

    operator = next(
        d
        for d in deployment.table.descriptors()
        if d.descriptor_type == ExtendedDescriptorType.OPERATOR
        and d.payload["source_kernel_id"]
        == next(
            k.index
            for k in graph.kernels
            if k.kind == "MATMUL" and k.inputs[0] == "q.codes"
        )
    )
    activation = deployment.table.get(
        operator.payload["input_view_0"], ExtendedDescriptorType.TENSOR_VIEW
    ).payload
    assert activation["scale_object_id"] != NO_ID, (
        "the quantised activation's block scale must reach its consumer's view"
    )
    assert activation["scale_block_elements"] == 32
    weight = deployment.table.get(
        operator.payload["input_view_1"], ExtendedDescriptorType.TENSOR_VIEW
    ).payload
    assert weight["scale_object_id"] != NO_ID
    # Two different objects: the arena holds one, the checkpoint the other.
    assert activation["scale_object_id"] != weight["scale_object_id"]
