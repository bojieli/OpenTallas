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
from compiler.backends.hbm_sram.lower import lower_to_abi3, lower_with_plan
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
from runtime.abi3.verifier import require_admitted, verify_deployment

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
        states.append(
            StateResource(
                state_id=f"kv{index}",
                state_class="kv_cache",
                dtype="bf16",
                row_elements=kv,
                capacity_rows=span_max,
            )
        )

    emit("STATE_PREPARE", (), (), "exact_copy_v1",
         state_writes=tuple(s.state_id for s in states))
    emit("EMBEDDING_LOOKUP", ["embed", "tokens"], ["hidden0"],
         "exact_index_gather_v1")

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
        act(f"{p}.kv", (span_max, kv), role="state")
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
             "bf16_rms_norm_fp32_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wq"], [f"{p}.q"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wk"], [f"{p}.k"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n1", f"{p}.wv"], [f"{p}.v"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ROPE", [f"{p}.q", "rope"], [f"{p}.qr"], "bf16_rope_fp32_v1", **layer)
        emit("KV_APPEND", [f"{p}.k", f"{p}.v"], [f"{p}.kv"],
             "bf16_convert_rne_v1", state_writes=(f"kv{index}",), **layer)
        emit("ATTENTION_GQA", [f"{p}.qr", f"{p}.k", f"{p}.v", f"{p}.kv"],
             [f"{p}.attn"], "bf16_attention_fp32_v1",
             state_reads=(f"kv{index}",), **layer)
        emit("MATMUL", [f"{p}.attn", f"{p}.wo"], [f"{p}.o"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("ADD", [previous, f"{p}.o"], [f"{p}.res1"], "bf16_add_rne_v1", **layer)
        emit("RMS_NORM", [f"{p}.res1", f"{p}.norm2"], [f"{p}.n2"],
             "bf16_rms_norm_fp32_v1", **layer)
        emit("MATMUL", [f"{p}.n2", f"{p}.wg"], [f"{p}.g"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("MATMUL", [f"{p}.n2", f"{p}.wu"], [f"{p}.u"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("SILU_MUL", [f"{p}.g", f"{p}.u"], [f"{p}.act"],
             "bf16_silu_mul_fp32_v1", **layer)
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
         "bf16_rms_norm_fp32_v1")
    emit("LAST_TOKEN_SELECT", ["hidden.final", "last.index"], ["hidden.last"],
         "exact_index_gather_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("ARGMAX", ["logits"], ["token"], "exact_index_select_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_index_select_v1")
    emit("STATE_COMMIT", (), (), "exact_copy_v1",
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
    emit("STATE_PREPARE", (), (), "exact_copy_v1",
         state_writes=tuple(s.state_id for s in states))
    emit("EMBEDDING_LOOKUP", ["embed", "tokens"], ["hidden0"],
         "exact_index_gather_v1")

    previous = "hidden0"
    for index in range(layers):
        p = f"l{index}"
        weight(f"{p}.norm", (hidden,))
        weight(f"{p}.router", (hidden, experts))
        weight(f"{p}.bias", (experts,))
        weight(f"{p}.experts", (experts, hidden, ffn), "fp8_e4m3fn")
        weight(f"{p}.down", (ffn, hidden))
        act(f"{p}.n", (SPAN, hidden))
        act(f"{p}.scores", (SPAN, experts))
        act(f"{p}.index", (SPAN, topk), "u32")
        act(f"{p}.gate", (SPAN, topk))
        act(f"{p}.dispatch", (SPAN, hidden))
        act(f"{p}.expert", (SPAN, ffn))
        act(f"{p}.reduced", (SPAN, ffn))
        act(f"{p}.down", (SPAN, hidden))
        act(f"{p}.res", (SPAN, hidden))
        layer = {"layer": index}
        emit("RMS_NORM", [previous, f"{p}.norm"], [f"{p}.n"],
             "bf16_rms_norm_fp32_v1", **layer)
        emit("ROUTER_SCORE", [f"{p}.n", f"{p}.router"], [f"{p}.scores"],
             "bf16_bf16_fp32_sequential_rne_v1", **layer)
        emit("BIASED_TOPK", [f"{p}.scores", f"{p}.bias"],
             [f"{p}.index", f"{p}.gate"], "exact_router_topk_v1", **layer)
        emit("EXPERT_DISPATCH", [f"{p}.n", f"{p}.index"], [f"{p}.dispatch"],
             "exact_copy_v1", **layer)
        emit("ROUTED_MATMUL",
             [f"{p}.dispatch", f"{p}.experts", f"{p}.index", f"{p}.gate"],
             [f"{p}.expert"], "fp8_e4m3fn_bf16_fp32_sequential_rne_v1", **layer)
        emit("EXPERT_REDUCE", [f"{p}.expert", f"{p}.gate", f"{p}.index"],
             [f"{p}.reduced"], "bf16_expert_sum_fp32_v1", **layer)
        emit("MATMUL", [f"{p}.reduced", f"{p}.down"], [f"{p}.down"],
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
         "bf16_rms_norm_fp32_v1")
    emit("LAST_TOKEN_SELECT", ["hidden.final", "last.index"], ["hidden.last"],
         "exact_index_gather_v1")
    emit("VOCAB_PROJECT", ["hidden.last", "lm_head"], ["logits"],
         "bf16_bf16_fp32_sequential_rne_v1")
    emit("ARGMAX", ["logits"], ["token"], "exact_index_select_v1")
    emit("TOKEN_APPEND", ["token"], ["tokens.out"], "exact_index_select_v1")
    emit("STATE_COMMIT", (), (), "exact_copy_v1",
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


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------
def test_plan_bands_the_layers(dense, single_chip):
    plan = build_plan(dense, single_chip)
    assert plan.to_dict()["schema"] == PLAN_SCHEMA
    assert len(plan.bands) == 1
    assert plan.bands[0].layer_count == 4
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
    graph = dense_graph(layers=32)
    deployment = lower_to_abi3(graph, single_chip)
    report = require_admitted(deployment, single_chip)
    assert report.proved_retired_work > 100 * report.instruction_count


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
        assert loop.payload["bound_divisor"] > 1

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
    source = Path("compiler/backends/hbm_sram/lower.py").read_text().lower()
    for forbidden in ("qwen", "deepseek", "llama", "mistral"):
        assert forbidden not in source, f"{forbidden} must not appear in the emitter"


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
    assert len(plan.states) == 1, "one band, one physical KV resource"
    assert len(plan.states[0].members) == 4
    report = verify_deployment(deployment, single_chip)
    assert report.admitted
    assert report.state_resources == 1
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
    graph = read_kernel_graph(REAL_QWEN_IR)
    capability = single_chip_capability()
    deployment, plan = lower_with_plan(graph, capability)
    report = require_admitted(deployment, capability)
    assert report.instruction_count < 20000
    assert check_deployment(graph, deployment, capability)["ok"]
    print(
        json.dumps(
            {
                "instructions": report.instruction_count,
                "descriptors": report.descriptor_count,
                "proved_retired_work": report.proved_retired_work,
                "weight_objects": plan.proofs["weight_objects"],
                "bands": plan.proofs["bands"],
            },
            indent=2,
        )
    )
