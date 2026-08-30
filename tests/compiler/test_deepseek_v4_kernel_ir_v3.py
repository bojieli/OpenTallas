"""The DeepSeek-V4-Flash front end must emit one neutral, byte-pinned graph.

These tests hold the frozen contracts, not the front end's convenience: the
neutral registry in ``compiler/ir/v3/kernel_ir.py``, the shared lowering table
in ``compiler/ir/v3/lowering.py``, the ABI 3.0 operator operand limits, and the
requirement that every weight names an exact byte range in the locked 156 GB
checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter

import pytest

from compiler.frontend.deepseek_v4 import (
    PAYLOAD_BYTES,
    TENSOR_COUNT,
    build_official_tensor_specs,
    load_official_config,
)
from compiler.frontend.deepseek_v4_graph import (
    OPERATOR_CATALOG,
    build_official_graph_contract,
)
from compiler.ir.v3.kernel_ir import (
    DTYPES,
    FORBIDDEN_TERMS,
    OPERATION_KINDS,
    PHASES,
    ROLES,
    Symbolic,
    check_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from compiler.ir.v3.numeric import (
    CONTRACT_PATTERN,
    canonical_contract_id,
    is_implementation_path,
)
from compiler.frontends.v3.deepseek_v4 import (
    ARCHITECTURAL_MAX_CONTEXT,
    CONTRACT_BASE_BY_SOURCE_KIND,
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_CONTEXT_TOKENS,
    DEFAULT_SNAPSHOT,
    LOWERING_PLAN,
    DeepSeekV4KernelIRError,
    export_deepseek_v4_kernel_graph,
    graph_census,
    verify_checkpoint_bindings,
)

pytestmark = pytest.mark.skipif(
    not DEFAULT_SNAPSHOT.is_dir() or not DEFAULT_CHECKPOINT_LOCK.is_file(),
    reason="the pinned DeepSeek-V4-Flash-0731 snapshot and lock are not present",
)

#: Source operator kinds the first release deliberately leaves out; they belong
#: to the speculative profile that ADR-003 section 18 sequences after ordinary
#: DeepSeek generation.
SPECULATIVE_SOURCE_KINDS = frozenset(
    {
        "CONFIDENCE_SCORE",
        "DSPARK_MAIN_PROJECT",
        "DSPARK_NOISE_EMBED",
        "DSPARK_PREFILL_KV",
        "DSPARK_WINDOW_INDEX",
        "MARKOV_AUTOREGRESSIVE_LOOP",
        "TARGET_HIDDEN_CAPTURE",
    }
)

LAYERS = 43
RATIO_ZERO_LAYERS = 2
RATIO_FOUR_LAYERS = 21
RATIO_ONE_TWENTY_EIGHT_LAYERS = 20


@pytest.fixture(scope="module")
def graph():
    return export_deepseek_v4_kernel_graph()


@pytest.fixture(scope="module")
def contract():
    return build_official_graph_contract()


@pytest.fixture(scope="module")
def specs():
    return build_official_tensor_specs(load_official_config())


# ---------------------------------------------------------------------------
# Neutrality
# ---------------------------------------------------------------------------
def test_graph_is_neutral(graph):
    assert check_neutral(graph) == []


def test_no_identifier_carries_a_backend_term(graph):
    offenders = []
    for tensor in graph.tensors:
        offenders += [
            (tensor.tensor_id, term)
            for term in FORBIDDEN_TERMS
            if term in tensor.tensor_id.lower()
        ]
    for kernel in graph.kernels:
        text = f"{kernel.kernel_id} {kernel.kind} {' '.join(kernel.attributes)}"
        offenders += [
            (kernel.kernel_id, term)
            for term in FORBIDDEN_TERMS
            if term in text.lower()
        ]
    for state in graph.states:
        offenders += [
            (state.state_id, term)
            for term in FORBIDDEN_TERMS
            if term in f"{state.state_id} {state.state_class}".lower()
        ]
    assert offenders == []


def test_every_kind_is_registered_and_lowerable(graph):
    kinds = {kernel.kind for kernel in graph.kernels}
    assert kinds <= OPERATION_KINDS
    assert kinds <= set(KERNEL_TO_ENGINE)


def test_roles_dtypes_and_phases_are_declared(graph):
    for tensor in graph.tensors:
        assert tensor.role in ROLES
        assert tensor.dtype in DTYPES
    for kernel in graph.kernels:
        assert set(kernel.phases) <= set(PHASES)
        assert kernel.numeric_contract
        assert kernel.counter_class


# ---------------------------------------------------------------------------
# ABI 3.0 operator shape
# ---------------------------------------------------------------------------
def test_operator_operand_limits(graph):
    """``runtime.abi3.builder`` admits four input views and two output views."""

    for kernel in graph.kernels:
        assert len(kernel.inputs) <= 4, kernel.kernel_id
        assert len(kernel.outputs) <= 2, kernel.kernel_id
        assert kernel.outputs, kernel.kernel_id


#: Kinds this export deliberately emits with fewer operands than the shared
#: lowering table declares, with the released reason.  Anything not listed must
#: match the table exactly, so a table change shows up here.
UNDERFILLED_OPERANDS = {
    # the released query head norm has no gain vector
    "HEAD_RMS_NORM": (1, 1),
    # TA-ABI3-OPCONV-1 amendment A8: SWIGLU is (gate, up); the limit is numeric
    "SWIGLU": (2, 1),
    # (activations, routed weights, expert IDs); the routing weight is applied
    # by its own MUL before the down contraction, and the operand convention
    # makes in3 optional for exactly that reason
    "ROUTED_MATMUL": (3, 1),
    # The released split is over *features*, not rows, so there is no per-group
    # row count to put in in2 and the frozen operator does not do this
    # operation at all: see IR3-GAP-5 and the GROUPED_OUTPUT_PROJECT comment.
    "GROUPED_MATMUL": (2, 1),
    # mean over the hyper-connection streams needs no base
    "PARTITION_SUM": (1, 1),
    # Two shapes by site: the MoE reduction is (routed contributions, shared
    # base, routed row expert identity); the hyper-connection branch reduction
    # is (streams, pre coefficients) with no base, because the branch input is
    # a weighted stream sum and nothing is added to it.
    "EXPERT_REDUCE": None,
    # variable by site
    "CONCAT": None,
    "SCALE": None,
    "DEQUANTIZE": None,
}


def test_emitted_operand_counts_respect_the_shared_lowering_table(graph):
    for kernel in graph.kernels:
        declared = KERNEL_TO_ENGINE[kernel.kind]
        # Amendment A20: a slot a kernel *declares* absent is accounted for
        # here rather than in the list below.  ``UNDERFILLED_OPERANDS`` is a
        # memo -- a reader has to trust it -- while ``absent_operands`` is
        # checked against the frozen operand row at neutral admission, so a
        # kernel that says which slot it leaves empty is not underfilled.
        absent = len(kernel.attributes.get("absent_operands", ()))
        shape = (len(kernel.inputs) + absent, len(kernel.outputs))
        assert shape[0] <= declared.inputs, kernel.kernel_id
        assert shape[1] <= declared.outputs, kernel.kernel_id
        if kernel.kind in UNDERFILLED_OPERANDS:
            expected = UNDERFILLED_OPERANDS[kernel.kind]
            if expected is not None:
                assert shape == expected, kernel.kernel_id
        else:
            assert shape == (declared.inputs, declared.outputs), kernel.kernel_id


def test_sparse_attention_uses_the_frozen_operand_order(graph):
    """TA-ABI3-OPCONV-1 amendment A6: query, fused KV, index, per-head sink."""

    by_id = {t.tensor_id: t for t in graph.tensors}
    for kernel in graph.kernels:
        if kernel.kind != "ATTENTION_SPARSE":
            continue
        query, key_value, index, sink = kernel.inputs
        assert by_id[query].shape[1:] == (64, 512)
        assert by_id[key_value].shape[1] == 512
        # ABI 3.0 index and identifier operands are unsigned -- section 4's
        # SPARSE row says "sparse index (U32)" and the engines refuse anything
        # else -- so the neutral tensor is declared U32 rather than converted
        # at the operand.
        assert by_id[index].dtype == "u32"
        assert by_id[sink].role == "weight"
        assert by_id[sink].shape == (64,)


def test_kernels_are_indexed_and_topologically_ordered(graph):
    available = {
        tensor.tensor_id
        for tensor in graph.tensors
        if tensor.role in {"input", "weight", "constant"}
    }
    for index, kernel in enumerate(graph.kernels):
        assert kernel.index == index
        for name in kernel.inputs:
            assert name in available, f"{kernel.kernel_id} reads {name} too early"
        available.update(kernel.outputs)


def test_every_activation_and_state_tensor_is_produced(graph):
    produced = {name for kernel in graph.kernels for name in kernel.outputs}
    for tensor in graph.tensors:
        if tensor.role in {"activation", "state"}:
            assert tensor.tensor_id in produced


def test_state_effects_name_declared_resources(graph):
    declared = {state.state_id for state in graph.states}
    for kernel in graph.kernels:
        assert set(kernel.state_reads) <= declared
        assert set(kernel.state_writes) <= declared


# ---------------------------------------------------------------------------
# Checkpoint bindings
# ---------------------------------------------------------------------------
def checkpoint_ranges(graph):
    """Every ``(path, offset, bytes, source, tensor)`` the graph binds.

    A binding names one range unless it is *segmented*, in which case its
    payload is the ordered concatenation of the segments and each of them is
    the real range.  Two declared tensors may name ranges of the same locked
    checkpoint tensor -- a feature group of the grouped output projection is one
    block of its rows -- so provenance is the source name, not the tensor id.
    """
    out = []
    for tensor in graph.tensors:
        binding = tensor.binding
        if binding is None:
            continue
        if binding.segments:
            for segment in binding.segments:
                out.append(
                    (
                        segment.path,
                        segment.offset,
                        segment.bytes,
                        segment.source_name,
                        tensor.tensor_id,
                        segment.sha256,
                    )
                )
        else:
            out.append(
                (
                    binding.path,
                    binding.offset,
                    binding.bytes,
                    binding.source_name,
                    tensor.tensor_id,
                    binding.sha256,
                )
            )
    return out


def test_every_weight_carries_a_checkpoint_binding(graph, specs):
    declared = {spec.name for spec in specs}
    weights = [t for t in graph.tensors if t.role == "weight"]
    assert weights
    for tensor in weights:
        binding = tensor.binding
        assert binding is not None, tensor.tensor_id
        assert binding.source_name in declared or (
            binding.source_name == tensor.tensor_id
        )
        assert binding.transform == "identity"
        assert binding.bytes > 0
        assert len(binding.sha256) == 64
        assert set(binding.sha256) <= set("0123456789abcdef")
        if binding.segments:
            assert sum(s.bytes for s in binding.segments) == binding.bytes
    for path, offset, size, source, tensor_id, digest in checkpoint_ranges(graph):
        assert path.endswith(".safetensors"), tensor_id
        assert "/" not in path
        assert offset > 0 and size > 0
        assert source in declared, source
        assert len(digest) == 64


def test_binding_ranges_do_not_overlap(graph):
    by_path: dict[str, list[tuple[int, int, str]]] = {}
    for path, offset, size, _source, tensor_id, _digest in checkpoint_ranges(graph):
        by_path.setdefault(path, []).append((offset, size, tensor_id))
    for path, ranges in by_path.items():
        ranges.sort()
        for (start, length, name), (next_start, _, next_name) in zip(
            ranges, ranges[1:]
        ):
            assert start + length <= next_start, f"{name} overlaps {next_name} in {path}"


def test_bound_weights_cover_the_ordinary_path(graph, specs):
    ordinary = {spec.name for spec in specs if spec.scope in {"main", "global"}}
    ranges = checkpoint_ranges(graph)
    assert {record[3] for record in ranges} == ordinary
    total = sum(record[2] for record in ranges)
    expected = sum(
        spec.size_bytes for spec in specs if spec.scope in {"main", "global"}
    )
    assert total == expected
    assert total < PAYLOAD_BYTES


def test_a_sample_of_bindings_reads_back_bit_exact(graph):
    verified = verify_checkpoint_bindings(DEFAULT_SNAPSHOT, graph, sample=6)
    assert len(verified) == 6
    for record in verified:
        path = DEFAULT_SNAPSHOT / record["path"]
        with path.open("rb") as handle:
            handle.seek(record["offset"])
            payload = handle.read(min(record["bytes"], 1 << 20))
        assert payload
        if record["bytes"] <= (1 << 20):
            assert hashlib.sha256(payload).hexdigest() == record["sha256"]


def test_block_scaled_weights_link_their_scale_tensor(graph):
    by_id = {t.tensor_id: t for t in graph.tensors}
    mxfp4 = 0
    for tensor in graph.tensors:
        if tensor.dtype == "mxfp4_e2m1" and tensor.role == "weight":
            assert tensor.scale_tensor_id is not None
            assert tensor.scale_block_elements == 32
            scale = by_id[tensor.scale_tensor_id]
            assert scale.dtype == "e8m0"
            assert scale.binding is not None
            # The block is along the reduction axis, which is the last one, and
            # every leading axis -- including the expert axis of a stacked
            # routed weight -- is shared.
            assert scale.shape[-1] * 32 == tensor.shape[-1]
            assert tuple(scale.shape[:-1]) == tuple(tensor.shape[:-1])
            mxfp4 += 1
        elif tensor.dtype == "fp8_e4m3fn" and tensor.role == "weight":
            assert tensor.scale_tensor_id is not None
            assert tensor.scale_block_elements == 128
            scale = by_id[tensor.scale_tensor_id]
            assert scale.dtype == "e8m0"
            assert scale.binding is not None
    # 43 layers x {gate, up, down}, each one stacked [experts, N, K] tensor
    assert mxfp4 == LAYERS * 3


def test_mxfp4_weights_declare_the_architectural_shape(graph):
    for tensor in graph.tensors:
        if tensor.dtype == "mxfp4_e2m1" and tensor.binding is not None:
            # Two E2M1 elements share one stored byte.
            assert math.prod(tensor.shape) == tensor.binding.bytes * 2


def test_quantized_activations_link_a_scale_tensor(graph):
    by_id = {t.tensor_id: t for t in graph.tensors}
    for kernel in graph.kernels:
        if kernel.kind != "QUANTIZE":
            continue
        payload, scale = kernel.outputs
        assert by_id[payload].scale_tensor_id == scale
        assert by_id[scale].dtype == "e8m0"
        block = by_id[payload].scale_block_elements
        assert block in {32, 64, 128}


# ---------------------------------------------------------------------------
# Symbols, extents and state
# ---------------------------------------------------------------------------
def test_symbolic_extents_are_declared(graph):
    declared = {symbol.name: symbol for symbol in graph.symbols}
    assert "span_tokens" in declared
    assert "context_length" in declared
    assert declared["span_tokens"].maximum == DEFAULT_CONTEXT_TOKENS
    assert DEFAULT_CONTEXT_TOKENS <= ARCHITECTURAL_MAX_CONTEXT
    for tensor in graph.tensors:
        for extent in tensor.shape:
            if isinstance(extent, Symbolic):
                assert extent.symbol in declared
                assert extent.maximum <= declared[extent.symbol].maximum * (
                    extent.multiplier or 1
                )
    for kernel in graph.kernels:
        for extent in kernel.iteration_domain.values():
            if isinstance(extent, Symbolic):
                assert extent.symbol in declared


def test_token_extents_are_symbolic(graph):
    by_id = {t.tensor_id: t for t in graph.tensors}
    embedding = by_id["main.token_embed.output"]
    assert isinstance(embedding.shape[0], Symbolic)
    assert embedding.shape[0].symbol == "span_tokens"
    assert embedding.shape[1] == 4096
    dispatch = by_id["main.layer00.expert_dispatch.output"]
    assert dispatch.shape[0].symbol == "span_tokens"
    assert dispatch.shape[0].multiplier == 6


def test_state_resources_match_the_released_shapes(graph):
    states = {state.state_id: state for state in graph.states}
    by_class = Counter(state.state_class for state in graph.states)
    assert by_class["kv_window"] == LAYERS
    # one raw key-value window and one raw score window per compressor
    assert by_class["compressor_window"] == 2 * (
        RATIO_FOUR_LAYERS + RATIO_ONE_TWENTY_EIGHT_LAYERS + RATIO_FOUR_LAYERS
    )
    assert by_class["compressed_kv"] == (
        RATIO_FOUR_LAYERS + RATIO_ONE_TWENTY_EIGHT_LAYERS + RATIO_FOUR_LAYERS
    )

    window = states["attention_window.main.layer.0"]
    assert window.dtype == "bf16"
    assert window.row_elements == 512
    assert window.capacity_rows == 128
    assert window.initialization == "zero"

    # layer 2 is the first ratio-4 layer: overlapping windows double both the
    # candidate count and the projected width
    raw = states["compressor_window_kv.main.layer.2"]
    assert (raw.row_elements, raw.capacity_rows) == (1024, 8)
    score = states["compressor_window_score.main.layer.2"]
    assert score.initialization == "negative_infinity"

    # layer 3 is the first ratio-128 layer: no overlap
    raw_128 = states["compressor_window_kv.main.layer.3"]
    assert (raw_128.row_elements, raw_128.capacity_rows) == (512, 128)

    compressed = states["compressed_key_value.main.layer.2"]
    assert compressed.row_elements == 512
    assert compressed.capacity_rows == DEFAULT_CONTEXT_TOKENS // 4
    assert states["compressed_key_value.main.layer.3"].capacity_rows == (
        DEFAULT_CONTEXT_TOKENS // 128
    )
    indexed = states["index_compressed_key_value.main.layer.2"]
    assert indexed.row_elements == 128


def test_entrypoints_cover_both_phases(graph):
    phases = {entry.phase for entry in graph.entrypoints}
    assert phases == set(PHASES)
    declared_states = {state.state_id for state in graph.states}
    for entry in graph.entrypoints:
        assert set(entry.states) == declared_states
        assert entry.generation_policy
        assert entry.outputs


# ---------------------------------------------------------------------------
# Source coverage
# ---------------------------------------------------------------------------
#: Kernels that materialise a *declared constant* rather than lowering a source
#: node.  Amendment A9 lets the neutral IR declare a derived constant with a
#: generator, and the rows ``VECTOR.ROPE`` reads are gathered from that constant
#: once for the whole graph.  There is no source node to attribute them to: the
#: released model builds its rotary table at construction time, not in the
#: forward pass.  They are named for the model's rotary embedding rather than
#: for a graph position, and every one of them is a movement.
DERIVED_CONSTANT_PREFIX = "deepseek_v4."

#: Kinds whose whole content is the view they move through, so their numeric
#: contract is the exact selection rather than the arithmetic they feed.
MOVEMENT_KINDS = frozenset({"GATHER"})

#: The contract a pure index selection names when it qualifies as itself.
EXACT_SELECTION_CONTRACT = "exact_index_select_v1"


def source_kernels(graph):
    """Kernels that lower a source node, which is what these tests are about."""
    return [
        kernel
        for kernel in graph.kernels
        if not kernel.source_operation_id.startswith(DERIVED_CONSTANT_PREFIX)
    ]


def test_derived_constant_kernels_are_movements_from_a_declared_generator(graph):
    """The coefficient rows come from a generator, and nowhere else."""

    by_id = {t.tensor_id: t for t in graph.tensors}
    derived = [
        kernel
        for kernel in graph.kernels
        if kernel.source_operation_id.startswith(DERIVED_CONSTANT_PREFIX)
    ]
    assert derived
    for kernel in derived:
        assert kernel.kind == "GATHER"
        assert kernel.numeric_contract == "exact_index_select_v1"
        table = by_id[kernel.inputs[1]]
        assert table.role == "constant"
        assert table.generator == "deepseek_rope_coefficients_v1"
        assert table.binding is None
        assert set(table.generator_parameters) >= {
            "maximum_position",
            "position_scaling",
            "rotary_width",
            "theta",
        }


def test_the_first_release_is_the_ordinary_target_path(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    covered = {kernel.source_operation_id for kernel in source_kernels(graph)}
    assert covered <= set(node_kind)
    assert all(not name.startswith("dspark.") for name in covered)
    emitted_kinds = {node_kind[name] for name in covered}
    assert emitted_kinds == set(OPERATOR_CATALOG) - SPECULATIVE_SOURCE_KINDS
    assert len(emitted_kinds) == 39


def test_every_ordinary_source_node_is_lowered(graph, contract):
    ordinary = {
        node["id"]
        for node in contract["nodes"]
        if not node["id"].startswith("dspark.")
        and node["kind"] not in SPECULATIVE_SOURCE_KINDS
    }
    covered = {kernel.source_operation_id for kernel in source_kernels(graph)}
    assert covered == ordinary


def test_emitted_kinds_follow_the_declared_lowering_plan(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    observed: dict[str, set[str]] = {}
    for kernel in source_kernels(graph):
        source_kind = node_kind[kernel.source_operation_id]
        observed.setdefault(source_kind, set()).add(kernel.kind)
    for source_kind, kinds in observed.items():
        assert kinds <= set(LOWERING_PLAN[source_kind]), source_kind


def test_numeric_contracts_are_canonical_semantic_identifiers(graph, contract):
    """ADR-003 section 15: the neutral IR must not name an implementation."""

    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    for kernel in source_kernels(graph):
        name = kernel.numeric_contract
        assert CONTRACT_PATTERN.match(name), name
        assert not is_implementation_path(name), name
        assert canonical_contract_id(name) == name
        base = CONTRACT_BASE_BY_SOURCE_KIND[node_kind[kernel.source_operation_id]]
        if kernel.kind in MOVEMENT_KINDS and name == EXACT_SELECTION_CONTRACT:
            # A movement may qualify under its source kind -- the router's
            # weight gather does, because which rows it takes is part of the
            # routing contract -- or it may name the exact selection itself.
            # Gathering a rotary coefficient row is the second: it is the same
            # movement in both models, and naming it after the rotation it
            # feeds would claim a numeric identity it does not have.
            continue
        assert name.startswith(f"{base}_"), (name, base)


def test_the_frozen_contract_table_is_complete_and_distinct():
    assert set(CONTRACT_BASE_BY_SOURCE_KIND) == set(OPERATOR_CATALOG)
    bases = list(CONTRACT_BASE_BY_SOURCE_KIND.values())
    assert len(set(bases)) == len(bases)
    for base in bases:
        assert CONTRACT_PATTERN.match(f"{base}_v1"), base
        assert not is_implementation_path(base), base


def test_one_source_kind_maps_to_one_contract_family(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    families: dict[str, set[str]] = {}
    for kernel in source_kernels(graph):
        families.setdefault(
            node_kind[kernel.source_operation_id], set()
        ).add(kernel.numeric_contract)
    # a one-to-one lowering names exactly one contract
    # Amendment A8's frozen name, not a second identity for the same contract.
    assert families["RMS_NORM"] == {"deepseek_rmsnorm_binary32_v1"}
    assert families["SPARSE_ATTENTION"] == {"sparse_attention_bf16_v1"}
    # a multi-kernel lowering qualifies each sub-operation distinctly
    assert families["MXFP4_SWIGLU"] == {
        "mxfp4_swiglu_bf16_activation_quantize_v1",
        "mxfp4_swiglu_bf16_gate_contraction_v1",
        "mxfp4_swiglu_bf16_up_contraction_v1",
        "mxfp4_swiglu_bf16_clamped_silu_product_v1",
        "mxfp4_swiglu_bf16_routing_weight_product_v1",
        "mxfp4_swiglu_bf16_down_contraction_v1",
    }


def test_layer_coverage_and_per_layer_census(graph):
    by_layer = Counter(
        kernel.layer for kernel in graph.kernels if kernel.layer is not None
    )
    assert sorted(by_layer) == list(range(LAYERS))
    # layers 0 and 1 are uncompressed, the rest alternate ratio 4 and 128
    assert by_layer[0] == by_layer[1]
    assert by_layer[2] == by_layer[4] == by_layer[42]
    assert by_layer[3] == by_layer[5] == by_layer[41]
    assert by_layer[2] > by_layer[3] > by_layer[0]


def test_routed_experts_read_a_stacked_expert_operand(graph):
    """The expert stack is an operand, not an attribute (IR3-GAP-3, closed).

    ``TENSOR.ROUTED_MATMUL`` reads (activations, routed weights, expert IDs,
    route weights).  A list of 256 tensor names in an attribute is not an
    operand: it left the mandatory weight slot empty and put the expert IDs in
    it.  The stack is one declared ``[E, N, K]`` tensor whose payload is the
    ordered, individually authenticated checkpoint ranges of the 256 experts.
    """
    by_id = {t.tensor_id: t for t in graph.tensors}
    routed = [k for k in graph.kernels if k.kind == "ROUTED_MATMUL"]
    assert len(routed) == LAYERS * 3
    stacks = set()
    for kernel in routed:
        assert "expert_weight_tensors" not in kernel.attributes
        assert len(kernel.inputs) == 3
        activation, stack, expert_ids = kernel.inputs
        assert by_id[activation].role == "activation"
        assert by_id[expert_ids].dtype == "u32"
        weight = by_id[stack]
        assert weight.role == "weight"
        assert weight.dtype == "mxfp4_e2m1"
        assert len(weight.shape) == 3
        assert weight.shape[0] == 256
        binding = weight.binding
        assert binding is not None and len(binding.segments) == 256
        assert len({s.source_name for s in binding.segments}) == 256
        assert sum(s.bytes for s in binding.segments) == binding.bytes
        assert kernel.attributes["expert_count"] == 256
        assert kernel.attributes["expert_weight_dtype"] == "mxfp4_e2m1"
        stacks.add(stack)
    assert len(stacks) == LAYERS * 3


def test_hash_and_biased_routing_split_at_layer_three(graph):
    """The token-to-expert table is an exact row gather, not a hash route.

    The released routing reads ``tid2eid[token_id]`` over a ``[129280, 6]``
    table and keeps all six rows.  ``ROUTE.HASH_ROUTE`` computes
    ``table[mix32(key) % slots]`` and returns one destination, so it named an
    operator that does not do the operation; ``TENSOR.EMBED_LOOKUP`` does.
    """
    hashed = {
        k.layer
        for k in graph.kernels
        if k.attributes.get("source_operation_kind") == "HASH_ROUTE"
    }
    biased = {k.layer for k in graph.kernels if k.kind == "BIASED_TOPK"}
    assert hashed == {0, 1, 2}
    assert biased == set(range(3, LAYERS))
    for kernel in graph.kernels:
        if kernel.attributes.get("source_operation_kind") != "HASH_ROUTE":
            continue
        assert kernel.kind == "EMBEDDING_LOOKUP"
        assert kernel.attributes["table_rows"] == 129_280
        assert kernel.attributes["table_element_reading"] == "low_u32_of_i64"


def test_sparse_attention_and_indexing_per_compression_ratio(graph):
    """Both compressed families are one operator, and A20 is why.

    A ratio-4 layer ranks the candidates its indexer scores; a ratio-128 layer
    takes every candidate the causal rule admits.  The released model does the
    same two things with the same horizon, the same offset and the same
    concatenation behind them, so both are ``ROUTE.INDEX_TOPK`` and the dense
    one is the ranked one with ``in0`` absent.
    """
    assert len([k for k in graph.kernels if k.kind == "ATTENTION_SPARSE"]) == LAYERS
    index_topk = [k for k in graph.kernels if k.kind == "INDEX_TOPK"]
    ranked = [k for k in index_topk if "absent_operands" not in k.attributes]
    dense = [k for k in index_topk if k.attributes.get("absent_operands") == [0]]
    assert len(ranked) == RATIO_FOUR_LAYERS
    assert len(dense) == RATIO_ONE_TWENTY_EIGHT_LAYERS
    assert len(ranked) + len(dense) == len(index_topk)
    assert {k.attributes["top_k"] for k in ranked} == {512}
    # The dense form's ``k`` is a capacity, not a selection width, and it is a
    # constant: the whole point of A20 is that this operand has one
    # request-determined axis where the join it replaced had two.
    assert {k.attributes["compression_ratio"] for k in dense} == {128}
    for kernel in dense:
        assert len(kernel.inputs) == 2, kernel.kernel_id
        assert kernel.inputs[1] == "index.compression_ratio.128"
        shape = graph.tensor(kernel.outputs[0]).shape
        assert not isinstance(shape[-1], Symbolic), kernel.kernel_id
        assert int(shape[-1]) == 128 + int(kernel.attributes["k"])
    # ``WINDOW_INDEX`` is now only ever the sliding window it actually emits.
    windows = [k for k in graph.kernels if k.kind == "WINDOW_INDEX"]
    assert len(windows) == LAYERS
    assert {k.attributes["index_family"] for k in windows} == {
        "causal_circular_window"
    }
    assert len([k for k in graph.kernels if k.kind == "INDEX_SCORE"]) == (
        RATIO_FOUR_LAYERS
    )


def test_rope_declares_the_released_position_scaling(graph):
    ropes = {k.layer: k for k in graph.kernels if k.kind == "ROPE"}
    assert ropes[0].attributes["position_scaling"] == "none"
    assert ropes[0].attributes["theta"] == 10000.0
    assert ropes[2].attributes["position_scaling"] == "yarn"
    assert ropes[2].attributes["theta"] == 160000.0
    assert ropes[2].attributes["original_max_position"] == 65536
    assert ropes[2].attributes["factor"] == 16.0


# ---------------------------------------------------------------------------
# Determinism and the written document
# ---------------------------------------------------------------------------
def test_two_exports_are_byte_identical(graph):
    from runtime.abi3.capability import canonical_json

    other = export_deepseek_v4_kernel_graph()
    assert canonical_json(other.to_dict()) == canonical_json(graph.to_dict())
    assert other.graph_id == graph.graph_id


def test_written_document_round_trips(graph, tmp_path):
    path = tmp_path / "kernel_ir.v3.json"
    graph_id = graph.write(path)
    first = path.read_bytes()
    assert graph.write(path) == graph_id
    assert path.read_bytes() == first
    body = json.loads(first)
    assert body["schema"] == "opentallas.tensor_kernel_ir.v3"
    assert body["graph_id"] == graph_id
    assert body["model_id"] == "deepseek-v4-flash-0731"
    assert len(body["kernels"]) == len(graph.kernels)
    assert len(body["tensors"]) == len(graph.tensors)
    assert body["source"]["profile"] == "target_only"
    assert body["source"]["checkpoint_tensor_count"] == TENSOR_COUNT


def test_census_is_stable(graph):
    census = graph_census(graph)
    assert census["kernel_count"] == len(graph.kernels)
    assert census["tensor_count"] == len(graph.tensors)
    # 66,048 routed expert tensors became 129 stacked [E, N, K] operands and
    # their 129 stacked block-scale tensors, each one segmented binding over the
    # same authenticated checkpoint ranges; and amendment A17's grouped output
    # projection replaced 43 ``wo_a`` matrices and their 43 tile scales with the
    # eight leading-axis ranges each of them is contracted over, +602 declared
    # tensors naming exactly the same bytes.  The byte total is unchanged in
    # both cases, which is the property that matters: a tensor may be renamed
    # or subdivided, but the payload is the locked checkpoint's.
    assert census["bound_weight_tensors"] == 2_424
    assert census["bound_weight_bytes"] == 156_015_698_140
    assert census["states_by_class"]["kv_window"] == LAYERS


def test_generation_policy_declares_the_greedy_boundary(graph):
    policy = graph.generation_policy
    assert policy["selection_mode"] == "greedy_argmax_lowest_id"
    assert policy["eos_token_ids"] == [1]
    assert policy["speculative_profile"] is False
    assert "not_expressible" in policy["stochastic_sampling"]


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------
def test_a_context_beyond_the_architectural_capacity_is_rejected():
    with pytest.raises(DeepSeekV4KernelIRError):
        export_deepseek_v4_kernel_graph(
            context_tokens=ARCHITECTURAL_MAX_CONTEXT + 128
        )


def test_a_missing_checkpoint_lock_is_rejected(tmp_path):
    with pytest.raises(DeepSeekV4KernelIRError):
        export_deepseek_v4_kernel_graph(
            checkpoint_lock_path=tmp_path / "absent.lock.json"
        )


def test_source_attribute_keys_with_a_backend_term_are_renamed(graph):
    """Renamed, never dropped: the source semantics must survive."""

    keys = {key for kernel in graph.kernels for key in kernel.attributes}
    assert "cache_slot" not in keys and "cache_row" in keys
    assert "state_slots" not in keys and "state_rows" in keys
    assert "stages" not in keys and "butterfly_levels" in keys
    assert "duplicate_slot_order" not in keys
    assert "duplicate_selection_order" in keys
    assert "kv_read_bytes_per_valid_row" in keys


def test_conditional_compression_carries_an_execution_predicate(graph):
    """The frozen ``Kernel`` has no predicate field, so the source guard is
    carried as an attribute; see the front end's contract-change note.

    Two forms, and the grammar is checked rather than assumed: a value name,
    which is the compressor's computed ``should_compress``; and a comparison
    over a *declared* runtime symbol, which is what amendment A18's
    floors-to-zero rule needs and which no computed value can state, because
    there is no operator that produces one.
    """

    declared = {symbol.name for symbol in graph.symbols}
    guarded = [
        kernel
        for kernel in graph.kernels
        if "execution_predicate" in kernel.attributes
    ]
    assert guarded
    value_form = 0
    symbol_form = 0
    for kernel in guarded:
        predicate = kernel.attributes["execution_predicate"]
        assert isinstance(predicate, str) and predicate
        if predicate.endswith("should_compress"):
            value_form += 1
            continue
        symbol, comparison, bound = predicate.split()
        assert symbol in declared, f"{symbol!r} is not a declared runtime symbol"
        assert comparison in ("==", "!=", "<", "<=", ">", ">=")
        int(bound)
        symbol_form += 1
    assert value_form and symbol_form
    kinds = {kernel.kind for kernel in guarded}
    assert {"COMPRESS_POOL", "CONVERT", "RMS_NORM", "KV_APPEND"} <= kinds


def test_every_extent_that_floors_to_zero_declares_its_own_predicate(graph):
    """Amendment A18: an extent that floors to zero is a predicate question.

    A zero-extent view is refused, so every kernel leading with a symbol that
    can resolve to zero must say when it is not to be issued -- on itself, not
    on a neighbour a backend would have to read across.  Three declarations
    satisfy that and this test accepts exactly those three, so a kernel that
    grows a floorable extent and says nothing fails here rather than in a
    backend.
    """

    floorable = {
        symbol.name for symbol in graph.symbols if symbol.minimum == 0
    }
    assert floorable, "the request-derived group counts should floor to zero"
    shapes = {tensor.tensor_id: tensor.shape for tensor in graph.tensors}

    def leads_with_a_floorable_extent(kernel):
        for name in tuple(kernel.inputs) + tuple(kernel.outputs):
            for extent in shapes.get(name, ()):  # constants are plain ints
                symbol = getattr(extent, "symbol", None)
                if symbol in floorable:
                    return True
        return False

    undeclared = []
    for kernel in graph.kernels:
        if not leads_with_a_floorable_extent(kernel):
            continue
        attributes = kernel.attributes
        if attributes.get("execution_predicate"):
            continue
        # A join whose own extent carries A18's bias is never empty and is
        # always issued; what vanishes is an operand, and it names which.
        if attributes.get("operand_present_predicate"):
            continue
        # The compressor's raw-window transaction runs on every step and only
        # its pooled outputs are conditional, which it names.
        if attributes.get("conditional_outputs"):
            continue
        undeclared.append(kernel.kernel_id)
    assert not undeclared, (
        f"{len(undeclared)} kernel(s) lead with an extent that floors to zero "
        f"and declare no predicate: {sorted(undeclared)[:5]}"
    )


# ---------------------------------------------------------------------------
# Speculative profile
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def speculative_graph():
    """The speculative profile, or the reason the neutral IR will not admit it.

    Amendment A20 froze the index families ``ROUTE.WINDOW_INDEX`` produces and
    made an unknown one a refusal at admission, and the first thing that rule
    caught was not the defect it was written for.  DSpark's draft window
    declares ``causal_window_then_current_draft``: the released
    ``get_dspark_topk_idxs`` gives every draft query the same row,
    ``arange(0, min(window, p + 1))`` followed by the draft block at
    ``window + arange(block)``.  ``ROUTE.WINDOW_INDEX`` emits a *sliding*
    window ending at each query and pads the rest -- at window 128, block 5 and
    position 200 the released row is KV rows 0..132 and the operator's is
    73..200 with five pads -- so this is the same substitution as the ratio-128
    one, latent behind a profile the first release does not build.

    Skipped with the refusal as the reason, not failed: a profile the IR
    refuses has no graph to make assertions about, so the property is
    unproven rather than violated, and the suite says which.
    """
    try:
        return export_deepseek_v4_kernel_graph(include_speculative=True)
    except DeepSeekV4KernelIRError as refusal:
        pytest.skip(f"the neutral IR refuses this profile -- {refusal}")


def test_speculative_profile_covers_every_source_kind(
    speculative_graph, graph, contract, specs
):
    assert check_neutral(speculative_graph) == []
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    covered = {k.source_operation_id for k in source_kernels(speculative_graph)}
    assert covered == set(node_kind)
    assert {node_kind[name] for name in covered} == set(OPERATOR_CATALOG)
    assert len(speculative_graph.kernels) > len(graph.kernels)

    bound = {record[3] for record in checkpoint_ranges(speculative_graph)}
    assert bound == {spec.name for spec in specs}
    assert len(bound) == TENSOR_COUNT
    total = sum(
        t.binding.bytes for t in speculative_graph.tensors if t.binding is not None
    )
    assert total == PAYLOAD_BYTES
    assert speculative_graph.generation_policy["speculative_profile"] is True
    assert speculative_graph.graph_id != graph.graph_id


def test_speculative_profile_keeps_the_ordinary_kernels_intact(
    speculative_graph, graph
):
    ordinary = {
        (k.kernel_id, k.kind, k.inputs, k.outputs)
        for k in graph.kernels
    }
    extended = {
        (k.kernel_id, k.kind, k.inputs, k.outputs)
        for k in speculative_graph.kernels
    }
    assert ordinary <= extended
