"""Cross-model gate: both exporters must satisfy one neutral contract.

This is the property the whole program rests on. Qwen and DeepSeek are very
different models -- dense GQA against sparse MoE with a learned indexer, a
two-rate compressor and hyper-connections -- and if they needed two schemas or
two lowering tables, their results would be no more comparable than the four
divergent lanes this work replaced.

The tests are skipped, not failed, when an IR artifact has not been built, so
that a fresh checkout does not report a false failure; the program status
report separately records whether the artifacts exist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.ir.v3.kernel_ir import (
    DTYPES,
    KERNEL_IR_SCHEMA,
    OPERATION_KINDS,
    PHASES,
    ROLES,
    FORBIDDEN_TERMS,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE, check_table_complete

REPO = Path(__file__).resolve().parents[2]
MODELS = ("qwen3-8b", "deepseek-v4-flash-0731")


def _ir(model: str) -> dict:
    path = REPO / "build" / "ir-v3" / model / "kernel_ir.v3.json"
    if not path.exists():
        pytest.skip(f"neutral IR for {model} has not been built")
    return json.loads(path.read_text())


@pytest.fixture(params=MODELS)
def graph(request) -> dict:
    return _ir(request.param)


def test_the_lowering_table_covers_every_registered_kind() -> None:
    assert check_table_complete() == []


def test_both_models_declare_the_same_schema(graph: dict) -> None:
    assert graph["schema"] == KERNEL_IR_SCHEMA


def test_every_emitted_kind_has_a_frozen_lowering(graph: dict) -> None:
    kinds = {kernel["kind"] for kernel in graph["kernels"]}
    unregistered = sorted(kinds - OPERATION_KINDS)
    assert unregistered == [], f"kinds outside the neutral registry: {unregistered}"
    unlowered = sorted(kinds - set(KERNEL_TO_ENGINE))
    assert unlowered == [], f"kinds with no ABI 3.0 lowering: {unlowered}"


def test_operand_arity_matches_the_frozen_table(graph: dict) -> None:
    """A backend reads arity from the table, so the exporter must respect it."""
    problems = []
    for kernel in graph["kernels"]:
        spec = KERNEL_TO_ENGINE[kernel["kind"]]
        if len(kernel["inputs"]) > spec.inputs:
            problems.append(
                f"{kernel['kernel_id']} ({kernel['kind']}): "
                f"{len(kernel['inputs'])} inputs, table allows {spec.inputs}"
            )
        if len(kernel["outputs"]) > spec.outputs:
            problems.append(
                f"{kernel['kernel_id']} ({kernel['kind']}): "
                f"{len(kernel['outputs'])} outputs, table allows {spec.outputs}"
            )
    assert problems == [], problems[:10]


def test_no_backend_term_leaks_into_identifiers(graph: dict) -> None:
    """ADR-003 15: no ROM, HBM, SRAM, bank, stage, queue or address in the IR."""
    offenders = []
    for tensor in graph["tensors"]:
        lowered = tensor["tensor_id"].lower()
        offenders += [
            (tensor["tensor_id"], term)
            for term in FORBIDDEN_TERMS
            if term in lowered
        ]
    for kernel in graph["kernels"]:
        lowered = kernel["kernel_id"].lower()
        offenders += [
            (kernel["kernel_id"], term)
            for term in FORBIDDEN_TERMS
            if term in lowered
        ]
    assert offenders == [], offenders[:10]


def test_dtypes_and_roles_are_registered(graph: dict) -> None:
    for tensor in graph["tensors"]:
        assert tensor["dtype"] in DTYPES, tensor
        assert tensor["role"] in ROLES, tensor


def test_the_ir_is_single_assignment(graph: dict) -> None:
    producer: dict[str, str] = {}
    for kernel in graph["kernels"]:
        for name in kernel["outputs"]:
            assert name not in producer, (
                f"{name} produced by both {producer[name]} and {kernel['kernel_id']}"
            )
            producer[name] = kernel["kernel_id"]


def test_every_weight_carries_a_checkpoint_binding(graph: dict) -> None:
    missing = [
        tensor["tensor_id"]
        for tensor in graph["tensors"]
        if tensor["role"] == "weight" and not tensor.get("binding")
    ]
    assert missing == [], missing[:10]


def test_every_constant_is_bound_or_derived(graph: dict) -> None:
    """A constant is either checkpoint bytes or a declared generator.

    Amendment A9: a rotary coefficient table exists in no checkpoint, so
    requiring a binding for every constant made it undeclarable. It may name a
    deterministic generator instead -- but never neither, which would leave its
    contents unspecified.
    """
    unbound = [
        tensor["tensor_id"]
        for tensor in graph["tensors"]
        if tensor["role"] == "constant"
        and not tensor.get("binding")
        and not tensor.get("generator")
    ]
    assert unbound == [], unbound[:10]


def test_declared_generators_are_implemented_and_reproducible(graph: dict) -> None:
    """Every named generator must exist and be deterministic."""
    from runtime.sim.generators import digest_of, registered

    for tensor in graph["tensors"]:
        name = tensor.get("generator")
        if not name:
            continue
        assert name in registered(), f"{tensor['tensor_id']} names unknown {name}"
        parameters = tensor.get("generator_parameters", {})
        assert digest_of(name, parameters) == digest_of(name, parameters)


def test_bindings_name_a_real_file_and_a_plausible_extent(graph: dict) -> None:
    bound = [t for t in graph["tensors"] if t.get("binding")]
    assert bound, "no weight bindings at all"
    for tensor in bound:
        binding = tensor["binding"]
        assert binding["bytes"] > 0
        assert binding["offset"] >= 0
        assert len(binding["sha256"]) == 64
        assert binding["path"].endswith(".safetensors"), binding["path"]


def test_both_phases_have_an_entrypoint(graph: dict) -> None:
    phases = {entry["phase"] for entry in graph["entrypoints"]}
    assert phases == set(PHASES), phases


def test_state_references_resolve(graph: dict) -> None:
    declared = {state["state_id"] for state in graph["states"]}
    for kernel in graph["kernels"]:
        for name in (*kernel["state_reads"], *kernel["state_writes"]):
            assert name in declared, f"{kernel['kernel_id']} names unknown state {name}"


def test_the_two_models_share_operation_kinds_where_they_overlap() -> None:
    """Overlapping semantics must use the same neutral kind, not two spellings."""
    qwen = {k["kind"] for k in _ir("qwen3-8b")["kernels"]}
    deepseek = {k["kind"] for k in _ir("deepseek-v4-flash-0731")["kernels"]}
    shared = qwen & deepseek
    # Both are transformers: embedding, normalisation, contraction, rotary
    # position, residual add and on-device selection must be common ground.
    for kind in (
        "EMBEDDING_LOOKUP",
        "RMS_NORM",
        "MATMUL",
        "ROPE",
        "ADD",
        "ARGMAX",
        "TOKEN_APPEND",
    ):
        assert kind in shared, f"{kind} should be shared by both models"
    assert not (qwen - OPERATION_KINDS)
    assert not (deepseek - OPERATION_KINDS)
