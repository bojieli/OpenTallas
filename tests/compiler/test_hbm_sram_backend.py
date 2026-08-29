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
from runtime.abi3.constants import Major, Permission, StorageClass, TopologyClass
from runtime.abi3.descriptors import ExtendedDescriptorType, SelectorKind, Symbol
from runtime.sim.device import loop_trip_count
from runtime.sim.memory import ViewResolver
from runtime.abi3.verifier import require_admitted, verify_deployment

REAL_QWEN_IR = Path("build/ir-v3/qwen3-8b/kernel_ir.v3.json")
REAL_DEEPSEEK_IR = Path(
    "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"
)


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
        width = {"bf16": 2, "fp32": 4, "u32": 4, "fp8_e4m3fn": 1}[dtype]
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
            "max_new_tokens": 64,
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
        weight(f"{p}.experts", (experts, ffn, hidden), "fp8_e4m3fn")
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
             "normalization_rms_norm_bf16_v1", **layer)
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
         "normalization_rms_norm_bf16_v1")
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
            "max_new_tokens": 32,
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
        generation_policy={"eos_token_ids": [511], "max_new_tokens": 8,
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
    # expert dispatch, sparse/route gather, activation transfer, reduction and
    # the coordinated commit must all be represented.
    assert len(classes) >= 4


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


@pytest.mark.skipif(
    not REAL_DEEPSEEK_IR.is_file(), reason="the DeepSeek neutral IR is not built"
)
def test_the_hyper_connection_expansion_moves_no_duplicate_rows():
    """``main.hc_expand`` reads one embedding through a stride-zero axis.

    The mHC expansion is ``unsqueeze(2).repeat(1, 1, hc_mult, 1)``.  Expressed
    as a ``CONCAT`` it reached ``REDUCTION.GROUPED_CONCAT``, which joins on axis
    0 and therefore refused a ``[tokens, streams, width]`` result -- correctly,
    because the join it would have performed puts four consecutive *tokens*
    where four *streams* belong.  As a ``BROADCAST`` it is one movement whose
    source names the embedding once per stream through a stride of zero.
    """
    graph = read_kernel_graph(REAL_DEEPSEEK_IR)
    kernel = next(k for k in graph.kernels if k.kernel_id == "main.hc_expand")
    assert kernel.kind == "BROADCAST"
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
        generation_policy={"eos_token_ids": [0], "max_new_tokens": 1,
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
