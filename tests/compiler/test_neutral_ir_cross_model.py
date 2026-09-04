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
from compiler.ir.v3.lowering import (
    INDEX_FAMILIES,
    abi_input_slots,
    KERNEL_TO_ENGINE,
    OPTIONAL_INPUT_SLOTS,
    check_index_family,
    check_operand_slots,
    check_phase_inputs,
    check_table_complete,
)

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
    # position and on-device selection must be common ground.
    #
    # ``VECTOR.ADD`` is deliberately *not* on this list.  Qwen's residual is a
    # plain elementwise add; DeepSeek has no plain residual at all -- every one
    # of its blocks joins through the multi-hyper-connection, which is
    # ``VECTOR.MHC``'s post sub-case, and the only ``ADD`` its graph ever
    # carried was the compressor's position-embedding add, which the frozen
    # ``COMPRESS_STATE_UPDATE`` sub-case performs itself.  Requiring the kind
    # to be shared asserted a coincidence, not an overlap.
    for kind in (
        "EMBEDDING_LOOKUP",
        "RMS_NORM",
        "MATMUL",
        "ROPE",
        "ARGMAX",
        "TOKEN_APPEND",
    ):
        assert kind in shared, f"{kind} should be shared by both models"
    assert "ADD" in qwen
    assert "HYPER_CONNECT_POST" in deepseek and "ADD" not in deepseek
    assert not (qwen - OPERATION_KINDS)
    assert not (deepseek - OPERATION_KINDS)


# ---------------------------------------------------------------------------
# Amendment A20: the two rules the frozen table owns
# ---------------------------------------------------------------------------
def test_a_declared_absent_operand_is_checked_against_the_frozen_row() -> None:
    """``absent_operands`` is a statement about the ABI row, not a hint.

    It is the static counterpart of ``operand_present_predicate``, and it exists
    so that a hole is placed rather than packed: the compressed-dense index
    leaves ``ROUTE.INDEX_TOPK``'s ``in0`` empty and keeps the window block in
    ``in1`` and the ratio in ``in2``.  A backend that packed them down would
    hand the engine a window block where the scores belong.  Which slots may be
    empty is frozen, so an exporter cannot widen it privately.
    """
    assert OPTIONAL_INPUT_SLOTS["INDEX_TOPK"] == frozenset({0, 1, 2})
    assert check_operand_slots("INDEX_TOPK", ("window", "ratio"), {}) == []
    assert (
        check_operand_slots(
            "INDEX_TOPK", ("window", "ratio"), {"absent_operands": [0]}
        )
        == []
    )
    # A kind the table does not list may not declare the attribute at all.
    refused = check_operand_slots("WINDOW_INDEX", (), {"absent_operands": [0]})
    assert refused and "does not make them optional" in refused[0]
    # And the slots plus the operands may not exceed the row.
    too_many = check_operand_slots(
        "INDEX_TOPK", ("a", "b", "c"), {"absent_operands": [0]}
    )
    assert too_many and "3 input slots" in too_many[0]
    # A slot named twice is a malformed statement, not a duplicate no-op.
    twice = check_operand_slots("INDEX_TOPK", ("w",), {"absent_operands": [0, 0]})
    assert twice and "names a slot twice" in twice[0]


def test_an_index_family_the_operator_does_not_produce_is_refused() -> None:
    """One rule at admission, so neither backend has to remember it.

    ``index_family`` was a comment that read like a contract: it named which
    released helper a kernel reproduces, and no engine, verifier or backend read
    it.  That is how twenty ratio-128 layers came to declare
    ``causal_compressed_dense`` while lowering to ``ROUTE.WINDOW_INDEX``, which
    emits a sliding-window position list -- every index of it a legal KV row, so
    no operand, bound or numeric check could see the substitution.
    """
    assert INDEX_FAMILIES["WINDOW_INDEX"] == frozenset({"causal_circular_window"})
    assert check_index_family("WINDOW_INDEX", {}) == []
    assert (
        check_index_family(
            "WINDOW_INDEX", {"index_family": "causal_circular_window"}
        )
        == []
    )
    for family in ("causal_compressed_dense", "causal_window_then_current_draft"):
        refused = check_index_family("WINDOW_INDEX", {"index_family": family})
        assert refused, family
        # The refusal has to name the family and the operator, or it sends the
        # reader looking for a defect in the wrong layer.
        assert family in refused[0]
        assert "WINDOW_INDEX" in refused[0]
        assert "causal_circular_window" in refused[0]
    # A kind that produces no index family may not claim one either.
    stray = check_index_family("MATMUL", {"index_family": "causal_circular_window"})
    assert stray and "no index family is" in stray[0]


def test_the_draft_window_family_is_implemented_on_its_own_kind() -> None:
    """Amendment A30's pair: each family refused on the other's kind.

    ``causal_window_then_current_draft`` stopped being a refusal and became an
    operator -- ``ROUTE.DSPARK_WINDOW_INDEX`` -- and the reason it may not be
    claimed on ``WINDOW_INDEX`` is unchanged by that.  The released
    ``get_dspark_topk_idxs`` broadcasts one row to every draft query, spans two
    disjoint address ranges and does not slide; ``ROUTE.WINDOW_INDEX`` slides,
    writes a different row per query and reduces it modulo the window.  Both
    name legal KV rows of the same fused operand, so the only thing that can
    tell a substitution apart is the subopcode -- which is why the two entries
    are separate and why this assertion is stated in both directions.
    """
    assert INDEX_FAMILIES["WINDOW_INDEX"] == frozenset({"causal_circular_window"})
    assert INDEX_FAMILIES["DSPARK_WINDOW_INDEX"] == frozenset(
        {"causal_window_then_current_draft"}
    )
    assert (
        check_index_family(
            "DSPARK_WINDOW_INDEX",
            {"index_family": "causal_window_then_current_draft"},
        )
        == []
    )
    refused = check_index_family(
        "DSPARK_WINDOW_INDEX", {"index_family": "causal_circular_window"}
    )
    assert refused
    assert "causal_circular_window" in refused[0]
    assert "DSPARK_WINDOW_INDEX" in refused[0]
    assert "causal_window_then_current_draft" in refused[0]
    # And the other direction is still refused, which A30 does not relax.
    assert check_index_family(
        "WINDOW_INDEX", {"index_family": "causal_window_then_current_draft"}
    )


@pytest.mark.parametrize("axis", [None, False, True, 0.0, "0", "not-an-axis"])
def test_phase_inputs_refuses_a_non_integer_axis_without_throwing(axis: object) -> None:
    attributes = {
        "axis": axis,
        "phase_inputs": {"prefill": [0], "decode": [1]},
        "phase_symbol_binding": {"prefill": "span", "decode": "window"},
    }

    errors = check_phase_inputs(
        "CONCAT", ("current", "window"), ("prefill", "decode"), attributes
    )

    assert errors == ["phase_inputs CONCAT axis must be a non-boolean integer"]


@pytest.mark.parametrize(
    ("phase_map", "problem"),
    [
        ([], "must map each kernel phase"),
        ({"prefill": [0]}, "covers phases"),
        ({"prefill": [], "decode": [1]}, "must be a non-empty list"),
        ({"prefill": [False], "decode": [1]}, "only IR input indices"),
        ({"prefill": [0, 0], "decode": [1]}, "names an input twice"),
        ({"prefill": [0], "decode": [2]}, "outside the 2 CONCAT inputs"),
    ],
)
def test_phase_inputs_refuses_malformed_phase_maps(
    phase_map: object, problem: str
) -> None:
    errors = check_phase_inputs(
        "CONCAT",
        ("current", "window"),
        ("prefill", "decode"),
        {
            "axis": 0,
            "phase_inputs": phase_map,
            "phase_symbol_binding": {"prefill": "span", "decode": "window"},
        },
    )

    assert errors
    assert any(problem in error for error in errors)


def test_a_published_graph_declares_only_families_the_abi_implements(
    graph: dict,
) -> None:
    for kernel in graph["kernels"]:
        assert check_index_family(kernel["kind"], kernel["attributes"]) == [], (
            kernel["kernel_id"]
        )
        assert (
            check_operand_slots(
                kernel["kind"], kernel["inputs"], kernel["attributes"]
            )
            == []
        ), kernel["kernel_id"]


def test_a_declared_hole_is_placed_and_never_packed_down() -> None:
    """One placement function, so both lanes put the hole in the same slot.

    The failure this prevents was measured: with the operands packed down, the
    ROM lane handed ``ROUTE.INDEX_TOPK`` the window block where the scores
    belong and the compression ratio where the window block belongs, and the
    engine said so -- "window view 2084 covers 1 query rows, expected 104".
    """
    assert abi_input_slots("INDEX_TOPK", ("scores", "win", "ratio"), {}) == [
        "scores",
        "win",
        "ratio",
    ]
    assert abi_input_slots(
        "INDEX_TOPK", ("win", "ratio"), {"absent_operands": [0]}
    ) == [None, "win", "ratio"]
    # The rule is not specific to A20's slot: ``VECTOR.COMPRESS`` sub-case 2
    # has an empty ``in1`` for the same structural reason, and both backends
    # keep that one in a private per-kind table today.
    assert abi_input_slots(
        "COMPRESS_STATE_UPDATE", ("packed", "ape"), {"absent_operands": [1]}
    ) == ["packed", None, "ape"]


def test_every_published_kernel_places_its_operands_the_same_way(graph: dict) -> None:
    for kernel in graph["kernels"]:
        slots = abi_input_slots(
            kernel["kind"], kernel["inputs"], kernel["attributes"]
        )
        # Every declared operand appears exactly once, in order, and the holes
        # are the ones the kernel declared.
        assert [s for s in slots if s is not None] == list(kernel["inputs"])
        holes = [i for i, s in enumerate(slots) if s is None]
        assert holes == list(kernel["attributes"].get("absent_operands", []))
