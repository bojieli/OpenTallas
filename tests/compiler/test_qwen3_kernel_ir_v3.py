"""Qwen3-8B Tensor Kernel IR v3 export.

Every assertion here is about the one document both ABI 3.0 backends consume:
it must be neutral, structurally complete, an exact census of the released
architecture, byte-bound to the locked checkpoint, and deterministic.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from compiler.frontends.v3.qwen3 import (
    DEFAULT_CHECKPOINT_LOCK,
    DEFAULT_SNAPSHOT,
    GENERATION_POLICY_ID,
    KERNEL_CENSUS,
    KERNEL_COUNT,
    MAX_CONTEXT_TOKENS,
    NUMERIC_CONTRACT_BY_KIND,
    NUMERIC_PROFILE,
    TENSOR_TOTAL,
    Qwen3KernelIRError,
    export_qwen3_kernel_graph,
    verify_checkpoint_bindings,
)
from compiler.ir.v3.kernel_ir import (
    KERNEL_IR_SCHEMA,
    Symbolic,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from compiler.qwen3.constants import LAYER_COUNT, PAYLOAD_BYTES, TENSOR_COUNT
from compiler.tensor_accelerator.qwen_chat import EOS_TOKEN_IDS
from runtime.abi3.capability import canonical_json

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "build_qwen3_kernel_ir_v3.py"
HAS_REAL_SOURCES = DEFAULT_SNAPSHOT.is_dir() and DEFAULT_CHECKPOINT_LOCK.is_file()
REAL = pytest.mark.skipif(
    not HAS_REAL_SOURCES, reason="pinned Qwen3-8B checkpoint unavailable"
)

# Qwen3-8B: 36 layers, hidden 4096, intermediate 12288, 32 query heads,
# 8 KV heads, head_dim 128, vocabulary 151936.
HIDDEN = 4096
INTERMEDIATE = 12288
QUERY_HEADS = 32
KEY_VALUE_HEADS = 8
HEAD_DIM = 128
VOCABULARY = 151936

#: One decoder layer, in emission order.  Nineteen kernels per layer times 36
#: layers, plus the embedding gather, plus the six-kernel tail
#: (final norm, last-token select, vocabulary projection, argmax, token append,
#: atomic state commit) is 1 + 684 + 6 == 691.
LAYER_KINDS = (
    "RMS_NORM",
    "MATMUL",
    "MATMUL",
    "MATMUL",
    "HEAD_RMS_NORM",
    "HEAD_RMS_NORM",
    "ROPE",
    "ROPE",
    "STATE_PREPARE",
    # Amendment A11: the key plane and the value plane are appended by two
    # independent movements, which is what the hardware does.
    "KV_APPEND",
    "KV_APPEND",
    "ATTENTION_GQA",
    "MATMUL",
    "ADD",
    "RMS_NORM",
    "MATMUL",
    "MATMUL",
    "SILU_MUL",
    "MATMUL",
    "ADD",
)
TAIL_KINDS = (
    "RMS_NORM",
    "LAST_TOKEN_SELECT",
    "VOCAB_PROJECT",
    "ARGMAX",
    "TOKEN_APPEND",
    "STATE_COMMIT",
)


@pytest.fixture(scope="module")
def graph():
    if not HAS_REAL_SOURCES:  # pragma: no cover - guarded by REAL
        pytest.skip("pinned Qwen3-8B checkpoint unavailable")
    return export_qwen3_kernel_graph()


@pytest.fixture(scope="module")
def lock() -> dict:
    if not HAS_REAL_SOURCES:  # pragma: no cover - guarded by REAL
        pytest.skip("pinned Qwen3-8B checkpoint unavailable")
    return json.loads(DEFAULT_CHECKPOINT_LOCK.read_text())


@REAL
def test_export_is_neutral(graph) -> None:
    assert check_neutral(graph) == []
    document = graph.to_dict()
    assert document["schema"] == KERNEL_IR_SCHEMA
    assert document["model_id"] == "qwen3-8b"
    assert graph.numeric_profile == NUMERIC_PROFILE


@REAL
def test_neutrality_checker_is_live(graph) -> None:
    """A backend term anywhere in an identifier must fail the same check."""

    graph.tensors = graph.tensors + (
        Tensor(
            tensor_id="layer.0.attention.sram_slot",
            dtype="bf16",
            shape=(1,),
            role="activation",
        ),
    )
    try:
        errors = check_neutral(graph)
        assert any("sram" in error for error in errors)
    finally:
        graph.tensors = graph.tensors[:-1]
        graph._index = {t.tensor_id: t for t in graph.tensors}
    assert check_neutral(graph) == []


@REAL
def test_kernel_census_matches_the_architecture(graph) -> None:
    census = Counter(kernel.kind for kernel in graph.kernels)
    assert dict(sorted(census.items())) == dict(sorted(KERNEL_CENSUS.items()))
    assert len(graph.kernels) == KERNEL_COUNT == 728

    # 1 embedding + 36 * 19 layer kernels + a 6-kernel tail.
    assert census["EMBEDDING_LOOKUP"] == 1
    # 36 input norms + 36 post-attention norms + 1 final norm.
    assert census["RMS_NORM"] == 2 * LAYER_COUNT + 1 == 73
    # Qwen3 normalises every query head and every key head.
    assert census["HEAD_RMS_NORM"] == 2 * LAYER_COUNT == 72
    # q, k, v, o, gate, up, down per layer; the LM head is VOCAB_PROJECT.
    assert census["MATMUL"] == 7 * LAYER_COUNT == 252
    assert census["VOCAB_PROJECT"] == 1
    # Q and K rotate independently: the ABI 3.0 ROPE op has one output.
    assert census["ROPE"] == 2 * LAYER_COUNT == 72
    # One prepared extent, one append and one attention per layer.
    assert census["STATE_PREPARE"] == LAYER_COUNT == 36
    assert census["KV_APPEND"] == 2 * LAYER_COUNT == 72
    assert census["ATTENTION_GQA"] == LAYER_COUNT == 36
    # Attention and MLP residuals.
    assert census["ADD"] == 2 * LAYER_COUNT == 72
    assert census["SILU_MUL"] == LAYER_COUNT == 36
    # ADR-003 section 8.6: one atomic commit over the whole declared state set.
    assert census["STATE_COMMIT"] == 1
    assert census["ARGMAX"] == census["TOKEN_APPEND"] == 1


@REAL
def test_layer_structure_repeats_exactly(graph) -> None:
    # The prologue is the embedding lookup plus the rotary coefficient gather
    # that amendment A9 made expressible; both precede layer 0.
    PROLOGUE_KINDS_COUNT = 2
    prologue = {k.kind for k in graph.kernels[:PROLOGUE_KINDS_COUNT]}
    assert prologue == {"EMBEDDING_LOOKUP", "GATHER"}
    assert all(k.layer is None for k in graph.kernels[:PROLOGUE_KINDS_COUNT])
    for layer in range(LAYER_COUNT):
        start = PROLOGUE_KINDS_COUNT + layer * len(LAYER_KINDS)
        window = graph.kernels[start : start + len(LAYER_KINDS)]
        assert tuple(k.kind for k in window) == LAYER_KINDS
        assert {k.layer for k in window} == {layer}
    tail = graph.kernels[PROLOGUE_KINDS_COUNT + LAYER_COUNT * len(LAYER_KINDS) :]
    assert tuple(k.kind for k in tail) == TAIL_KINDS
    assert all(k.layer is None for k in tail)
    assert graph.kernels[-1].kind == "STATE_COMMIT"


@REAL
def test_every_kind_lowers_to_one_abi3_engine_operation(graph) -> None:
    for kernel in graph.kernels:
        assert kernel.kind in KERNEL_TO_ENGINE, kernel.kernel_id
        engine = KERNEL_TO_ENGINE[kernel.kind]
        # The frozen table's arity is the operand contract the backends build
        # descriptors from, so every emitted kernel must match it exactly.
        assert len(kernel.inputs) == engine.inputs, kernel.kernel_id
        assert len(kernel.outputs) == engine.outputs, kernel.kernel_id
        assert kernel.numeric_contract == NUMERIC_CONTRACT_BY_KIND[kernel.kind]
        assert kernel.counter_class
        assert kernel.source_operation_id
        assert kernel.phases == ("prefill", "decode")


@REAL
def test_tensor_inventory(graph) -> None:
    assert len(graph.tensors) == TENSOR_TOTAL == 1165
    roles = Counter(tensor.role for tensor in graph.tensors)
    assert roles == {
        # +1 for the gathered rotary coefficient rows (amendment A9).
        # Key and value planes are appended separately (amendment A11).
        "activation": 689,
        "weight": TENSOR_COUNT,
        "state": 2 * LAYER_COUNT,
        "input": 2,
        # The rotary coefficient table is a derived constant with a generator.
        "constant": 1,
        "output": 2,
    }
    ids = [tensor.tensor_id for tensor in graph.tensors]
    assert len(set(ids)) == len(ids)

    span = Symbolic("span_tokens", 1, MAX_CONTEXT_TOKENS)
    assert graph.tensor("input.token_ids").shape == (span,)
    assert graph.tensor("sequence.embedding").shape == (span, HIDDEN)
    assert graph.tensor("layer.7.attention.query").shape == (
        span,
        QUERY_HEADS,
        HEAD_DIM,
    )
    assert graph.tensor("layer.7.attention.key").shape == (
        span,
        KEY_VALUE_HEADS,
        HEAD_DIM,
    )
    assert graph.tensor("layer.7.feed_forward.gate").shape == (span, INTERMEDIATE)
    assert graph.tensor("output.logits").shape == (1, VOCABULARY)
    assert {symbol.name for symbol in graph.symbols} == {
        "span_tokens",
        "context_tokens",
    }
    for symbol in graph.symbols:
        assert symbol.maximum == MAX_CONTEXT_TOKENS
        assert symbol.minimum == 1


@REAL
def test_dataflow_is_single_assignment_and_topologically_ordered(graph) -> None:
    available = {
        tensor.tensor_id
        for tensor in graph.tensors
        if tensor.role in {"input", "weight", "constant", "state"}
    }
    produced: set[str] = set()
    for kernel in graph.kernels:
        missing = sorted(set(kernel.inputs) - available)
        assert not missing, f"{kernel.kernel_id} reads unproduced {missing}"
        for name in kernel.outputs:
            assert name not in produced, name
            produced.add(name)
            available.add(name)
    outputs = {t.tensor_id for t in graph.tensors if t.role == "output"}
    assert outputs <= produced


@REAL
def test_state_resources_and_transaction_order(graph) -> None:
    assert len(graph.states) == LAYER_COUNT
    for layer, state in enumerate(graph.states):
        assert state.state_id == f"key_value_cache.layer.{layer}"
        assert state.state_class == "kv_cache"
        assert state.dtype == "bf16"
        # One row is this layer's key and value for one token.
        assert state.row_elements == 2 * KEY_VALUE_HEADS * HEAD_DIM == 2048
        assert state.capacity_rows == MAX_CONTEXT_TOKENS
        assert state.initialization == "zero"

    by_state: dict[str, list[tuple[int, str]]] = {
        state.state_id: [] for state in graph.states
    }
    for kernel in graph.kernels:
        for name in set(kernel.state_reads) | set(kernel.state_writes):
            by_state[name].append((kernel.index, kernel.kind))
    for layer, state in enumerate(graph.states):
        sequence = by_state[state.state_id]
        assert [kind for _, kind in sequence] == [
            "STATE_PREPARE",
            "KV_APPEND",
            "KV_APPEND",
            "ATTENTION_GQA",
            "STATE_COMMIT",
        ]
        assert [index for index, _ in sequence] == sorted(
            index for index, _ in sequence
        )
        prepare = next(k for k in graph.kernels if k.index == sequence[0][0])
        assert prepare.layer == layer
    commit = graph.kernels[-1]
    assert commit.kind == "STATE_COMMIT"
    assert commit.state_writes == tuple(s.state_id for s in graph.states)


@REAL
def test_entrypoints_cover_prefill_and_decode(graph) -> None:
    phases = {entry.phase: entry for entry in graph.entrypoints}
    assert set(phases) == {"prefill", "decode"}
    for entry in graph.entrypoints:
        assert entry.inputs == ("input.token_ids", "input.positions")
        assert entry.outputs == ("output.logits", "output.next_token")
        assert entry.states == tuple(s.state_id for s in graph.states)
        assert entry.generation_policy == GENERATION_POLICY_ID


@REAL
def test_generation_policy_records_the_official_eos_set(graph) -> None:
    official = json.loads((DEFAULT_SNAPSHOT / "generation_config.json").read_text())
    expected = official["eos_token_id"]
    assert graph.generation_policy["eos_token_ids"] == expected == [151645, 151643]
    # The repository constant is confirmed by the checkpoint, not trusted.
    assert tuple(graph.generation_policy["eos_token_ids"]) == EOS_TOKEN_IDS
    assert graph.generation_policy["eos_token_strings"] == [
        "<|im_end|>",
        "<|endoftext|>",
    ]
    assert graph.generation_policy["selection_mode"] == "greedy_argmax_lowest_id"
    assert graph.generation_policy["vocabulary_size"] == VOCABULARY
    assert graph.generation_policy["include_eos_in_output"] is True


@REAL
def test_every_weight_is_bound_to_the_locked_checkpoint(graph, lock) -> None:
    locked = {
        record["name"]: (shard, record)
        for shard in lock["shards"]
        for record in shard["tensors"]
    }
    shard_sizes = {shard["path"]: shard["file_size_bytes"] for shard in lock["shards"]}
    weights = [t for t in graph.tensors if t.role == "weight"]
    assert len(weights) == TENSOR_COUNT == 399
    total = 0
    for tensor in weights:
        binding = tensor.binding
        assert binding is not None, tensor.tensor_id
        assert binding.source_name == tensor.tensor_id
        assert binding.transform == "identity"
        shard, record = locked[tensor.tensor_id]
        # 8-byte length prefix + JSON header + the header's data_offsets start.
        start = record["data_offsets"][0]
        assert binding.offset == 8 + shard["header_length_bytes"] + start
        assert binding.bytes == record["size_bytes"]
        assert binding.sha256 == record["payload_sha256"]
        assert binding.path == shard["path"]
        assert binding.offset + binding.bytes <= shard_sizes[binding.path]
        # bf16 payload of exactly the declared shape.
        elements = 1
        for extent in tensor.shape:
            assert isinstance(extent, int)
            elements *= extent
        assert binding.bytes == elements * 2
        total += binding.bytes
    assert total == PAYLOAD_BYTES == 16_381_470_720


@REAL
def test_every_checkpoint_weight_has_exactly_one_consumer(graph) -> None:
    weights = {t.tensor_id for t in graph.tensors if t.role == "weight"}
    uses = Counter(
        name for kernel in graph.kernels for name in kernel.inputs if name in weights
    )
    assert set(uses) == weights
    assert set(uses.values()) == {1}


@REAL
def test_sampled_bindings_resolve_to_real_bytes(graph) -> None:
    names = [
        "model.embed_tokens.weight",
        "model.layers.0.input_layernorm.weight",
        "model.layers.0.self_attn.q_norm.weight",
        "model.layers.0.self_attn.k_norm.weight",
        "model.layers.12.self_attn.q_proj.weight",
        "model.layers.23.mlp.gate_proj.weight",
        "model.layers.35.mlp.down_proj.weight",
        "model.layers.35.post_attention_layernorm.weight",
        "model.norm.weight",
        "lm_head.weight",
    ]
    report = verify_checkpoint_bindings(graph, tensor_names=names)
    assert report["checked_tensors"] == len(names)
    # The sample spans every shard of the release.
    assert len(report["shards"]) == 5


@REAL
def test_one_whole_shard_of_bindings_resolves(graph, lock) -> None:
    shard = lock["shards"][0]
    names = sorted(record["name"] for record in shard["tensors"])
    assert len(names) == shard["tensor_count"] == 81
    report = verify_checkpoint_bindings(graph, tensor_names=names)
    assert report["shards"] == [shard["path"]]
    assert report["checked_bytes"] == sum(
        record["size_bytes"] for record in shard["tensors"]
    )


@REAL
def test_a_corrupted_binding_is_rejected(graph) -> None:
    from dataclasses import replace

    tensor = graph.tensor("model.norm.weight")
    broken = replace(
        tensor, binding=replace(tensor.binding, sha256="0" * 64)
    )
    index = graph.tensors.index(tensor)
    graph.tensors = graph.tensors[:index] + (broken,) + graph.tensors[index + 1 :]
    graph._index = {t.tensor_id: t for t in graph.tensors}
    try:
        with pytest.raises(Qwen3KernelIRError):
            verify_checkpoint_bindings(graph, tensor_names=["model.norm.weight"])
    finally:
        graph.tensors = graph.tensors[:index] + (tensor,) + graph.tensors[index + 1 :]
        graph._index = {t.tensor_id: t for t in graph.tensors}


@REAL
def test_export_is_deterministic(graph) -> None:
    again = export_qwen3_kernel_graph()
    assert again.graph_id == graph.graph_id
    assert canonical_json(again.to_dict()) == canonical_json(graph.to_dict())
    assert len(again.kernels) == len(graph.kernels)


@REAL
def test_written_document_is_byte_identical_and_self_identifying(
    graph, tmp_path: Path
) -> None:
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    assert graph.write(first) == graph.graph_id
    assert export_qwen3_kernel_graph().write(second) == graph.graph_id
    payload = first.read_bytes()
    assert payload == second.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == hashlib.sha256(
        second.read_bytes()
    ).hexdigest()
    document = json.loads(payload)
    assert document["graph_id"] == graph.graph_id
    assert len(document["kernels"]) == KERNEL_COUNT
    assert len(document["tensors"]) == TENSOR_TOTAL


@REAL
def test_command_line_export(tmp_path: Path, graph) -> None:
    output = tmp_path / "kernel_ir.v3.json"
    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--output",
            str(output),
            "--verify-bindings",
            "sample",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert graph.graph_id in result.stdout
    assert output.is_file()
    body = json.loads(output.read_text())
    assert body["graph_id"] == graph.graph_id
    # Re-running with --check must accept the file it just wrote.
    again = subprocess.run(
        [sys.executable, str(TOOL), "--output", str(output), "--check",
         "--verify-bindings", "none"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    )
    assert again.returncode == 0, again.stderr
