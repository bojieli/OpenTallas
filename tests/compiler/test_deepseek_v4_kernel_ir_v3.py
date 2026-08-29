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
from compiler.frontends.v3.deepseek_v4 import (
    ARCHITECTURAL_MAX_CONTEXT,
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
def test_every_weight_carries_a_checkpoint_binding(graph):
    weights = [t for t in graph.tensors if t.role == "weight"]
    assert weights
    for tensor in weights:
        binding = tensor.binding
        assert binding is not None, tensor.tensor_id
        assert binding.source_name == tensor.tensor_id
        assert binding.path.endswith(".safetensors")
        assert "/" not in binding.path
        assert binding.offset > 0
        assert binding.bytes > 0
        assert len(binding.sha256) == 64
        assert set(binding.sha256) <= set("0123456789abcdef")
        assert binding.transform == "identity"


def test_binding_ranges_do_not_overlap(graph):
    by_path: dict[str, list[tuple[int, int, str]]] = {}
    for tensor in graph.tensors:
        if tensor.binding is None:
            continue
        by_path.setdefault(tensor.binding.path, []).append(
            (tensor.binding.offset, tensor.binding.bytes, tensor.tensor_id)
        )
    for path, ranges in by_path.items():
        ranges.sort()
        for (start, length, name), (next_start, _, next_name) in zip(
            ranges, ranges[1:]
        ):
            assert start + length <= next_start, f"{name} overlaps {next_name} in {path}"


def test_bound_weights_cover_the_ordinary_path(graph, specs):
    ordinary = {spec.name for spec in specs if spec.scope in {"main", "global"}}
    bound = {t.tensor_id for t in graph.tensors if t.binding is not None}
    assert bound == ordinary
    total = sum(t.binding.bytes for t in graph.tensors if t.binding is not None)
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
    linked = 0
    for tensor in graph.tensors:
        if tensor.dtype == "mxfp4_e2m1" and tensor.role == "weight":
            assert tensor.scale_tensor_id is not None
            assert tensor.scale_block_elements == 32
            scale = by_id[tensor.scale_tensor_id]
            assert scale.dtype == "e8m0"
            assert scale.binding is not None
            assert scale.shape[1] * 32 == tensor.shape[1]
            linked += 1
        elif tensor.dtype == "fp8_e4m3fn" and tensor.role == "weight":
            assert tensor.scale_tensor_id is not None
            assert tensor.scale_block_elements == 128
            scale = by_id[tensor.scale_tensor_id]
            assert scale.dtype == "e8m0"
            assert scale.binding is not None
            linked += 1
    # 43 layers x 256 experts x {gate, up, down}
    assert linked >= LAYERS * 256 * 3


def test_mxfp4_weights_declare_the_architectural_shape(graph):
    for tensor in graph.tensors:
        if tensor.dtype == "mxfp4_e2m1" and tensor.binding is not None:
            # Two E2M1 elements share one stored byte.
            assert tensor.shape[0] * tensor.shape[1] == tensor.binding.bytes * 2


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
def test_the_first_release_is_the_ordinary_target_path(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    covered = {kernel.source_operation_id for kernel in graph.kernels}
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
    covered = {kernel.source_operation_id for kernel in graph.kernels}
    assert covered == ordinary


def test_emitted_kinds_follow_the_declared_lowering_plan(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    observed: dict[str, set[str]] = {}
    for kernel in graph.kernels:
        source_kind = node_kind[kernel.source_operation_id]
        observed.setdefault(source_kind, set()).add(kernel.kind)
    for source_kind, kinds in observed.items():
        assert kinds <= set(LOWERING_PLAN[source_kind]), source_kind


def test_numeric_contracts_name_a_qualified_reference(graph, contract):
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    owners = {
        kind: OPERATOR_CATALOG[kind].to_dict()["reference_owner"]
        for kind in OPERATOR_CATALOG
    }
    for kernel in graph.kernels:
        owner = owners[node_kind[kernel.source_operation_id]]
        assert kernel.numeric_contract.split("#")[0] == owner


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


def test_routed_experts_name_every_expert_weight(graph):
    declared = {t.tensor_id for t in graph.tensors}
    routed = [k for k in graph.kernels if k.kind == "ROUTED_MATMUL"]
    assert len(routed) == LAYERS * 3
    for kernel in routed:
        family = kernel.attributes["expert_weight_tensors"]
        assert len(family) == 256
        assert len(set(family)) == 256
        assert set(family) <= declared
        assert kernel.attributes["expert_weight_dtype"] == "mxfp4_e2m1"


def test_hash_and_biased_routing_split_at_layer_three(graph):
    hashed = {k.layer for k in graph.kernels if k.kind == "HASH_ROUTE"}
    biased = {k.layer for k in graph.kernels if k.kind == "BIASED_TOPK"}
    assert hashed == {0, 1, 2}
    assert biased == set(range(3, LAYERS))


def test_sparse_attention_and_indexing_per_compression_ratio(graph):
    assert len([k for k in graph.kernels if k.kind == "ATTENTION_SPARSE"]) == LAYERS
    index_topk = [k for k in graph.kernels if k.kind == "INDEX_TOPK"]
    assert len(index_topk) == RATIO_FOUR_LAYERS
    assert {k.attributes["top_k"] for k in index_topk} == {512}
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
    assert census["bound_weight_tensors"] == 67_612
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
    carried as an attribute; see the front end's contract-change note."""

    guarded = [
        kernel
        for kernel in graph.kernels
        if "execution_predicate" in kernel.attributes
    ]
    assert guarded
    for kernel in guarded:
        assert kernel.attributes["execution_predicate"].endswith("should_compress")
    kinds = {kernel.kind for kernel in guarded}
    assert {"COMPRESS_POOL", "CONVERT", "RMS_NORM", "KV_APPEND"} <= kinds


# ---------------------------------------------------------------------------
# Speculative profile
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def speculative_graph():
    return export_deepseek_v4_kernel_graph(include_speculative=True)


def test_speculative_profile_covers_every_source_kind(
    speculative_graph, graph, contract, specs
):
    assert check_neutral(speculative_graph) == []
    node_kind = {node["id"]: node["kind"] for node in contract["nodes"]}
    covered = {k.source_operation_id for k in speculative_graph.kernels}
    assert covered == set(node_kind)
    assert {node_kind[name] for name in covered} == set(OPERATOR_CATALOG)
    assert len(speculative_graph.kernels) > len(graph.kernels)

    bound = {t.tensor_id for t in speculative_graph.tensors if t.binding is not None}
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
