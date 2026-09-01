"""The compressed attention join's row space, on both lanes, in both phases.

DeepSeek's ``ATTENTION_KV_VIEW`` joins three operands whose extents are
functions of *two* runtime symbols -- ``span_tokens + 128 +
context_length / ratio`` -- and amendment A18 states an extent as an affine
image of one.  The exporter declared ``attention_rows_ratioN``, which is that
sum with the span's group count substituted for the context's.  In prefill the
span *is* the context and the substitution is exact; at every decode step it is
short by every committed compression group, and the two backends were short by
different amounts:

* ROM declared ``1 + 128 + 0`` and its operands supplied ``1 + 128 + 8``;
* HBM declared the same ``129`` and resolved its compressed operand against the
  *span* as well, presenting a whole 128-group block, so its operands supplied
  ``1 + 128 + 128``.

Both are the project's recurring defect: legal values, no trap, nothing
refused, and a wrong answer -- discovered at decode step 1 of a functional run
rather than at lowering.  These tests hold the three things that close it.

1. Each backend *derives* a join's output extent from its operands and refuses
   a declaration that disagrees, instead of taking the exporter's word.
2. A join whose sum has no A18 image in some phase, and which declares no phase
   binding to collapse it, is refused by both backends.
3. The two lanes resolve the join and its consumer to the *same* number of rows
   at prefill and at decode.  Comparability is the point of the program, and a
   resource whose size the lanes disagree about is not one resource.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.descriptors import (
    Comparison,
    ExtendedDescriptorType,
    PredicateKind,
    SelectorKind,
    Symbol,
)
from runtime.abi3.constants import Control, InstructionFlag, Major, NO_ID
from runtime.abi3.records import INSTRUCTION, Instruction, split_program
from runtime.sim.memory import iteration_extent

REPO = Path(__file__).resolve().parents[2]
IR = REPO / "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json"

#: The join, and the one operator that reads its result.
JOIN = "main.layer02.attention_kv_view"
CONSUMER = "main.layer02.sparse_attention"

#: 32 prompt tokens, then the first and the third decode step -- the workload
#: ``TA-DS-CHAT-1-P32`` runs, bound exactly as ``runtime.driver`` binds it.
BINDINGS = {
    "prefill": {
        Symbol.SPAN_TOKENS: 32,
        Symbol.POSITION_START: 0,
        Symbol.POSITION_END: 32,
        Symbol.CONTEXT_LENGTH: 32,
        Symbol.PHASE: 0,
    },
    "decode_1": {
        Symbol.SPAN_TOKENS: 1,
        Symbol.POSITION_START: 32,
        Symbol.POSITION_END: 33,
        Symbol.CONTEXT_LENGTH: 33,
        Symbol.PHASE: 1,
    },
    "decode_3": {
        Symbol.SPAN_TOKENS: 1,
        Symbol.POSITION_START: 34,
        Symbol.POSITION_END: 35,
        Symbol.CONTEXT_LENGTH: 35,
        Symbol.PHASE: 1,
    },
    # The step that crosses a compression-group boundary: at ``start_pos``
    # 35 the compressor's ``(start_pos + 1) % 4 == 0`` fires, the committed
    # prefix grows from eight groups to nine, and the join's row space grows
    # with it.  A four-token generation from a 32-token prompt stops one step
    # short of this, so the executed captures do not reach it and it is stated
    # here instead of assumed.
    "decode_4": {
        Symbol.SPAN_TOKENS: 1,
        Symbol.POSITION_START: 35,
        Symbol.POSITION_END: 36,
        Symbol.CONTEXT_LENGTH: 36,
        Symbol.PHASE: 1,
    },
    # And a much longer context, where the window no longer covers it: the
    # extent is still one affine function of the context and both lanes still
    # have to agree on it.
    "decode_long": {
        Symbol.SPAN_TOKENS: 1,
        Symbol.POSITION_START: 4095,
        Symbol.POSITION_END: 4096,
        Symbol.CONTEXT_LENGTH: 4096,
        Symbol.PHASE: 1,
    },
}

#: ``span + window + committed groups``, computed here from the bindings rather
#: than typed in, so the expectation is the join's own definition.
WINDOW = 128
RATIO = 4


def _expected(binding: dict[Symbol, int]) -> int:
    return (
        int(binding[Symbol.SPAN_TOKENS])
        + WINDOW
        + int(binding[Symbol.CONTEXT_LENGTH]) // RATIO
    )


def _lower(lane: str, graph: KernelGraph):
    import importlib

    module, function, capability = {
        "rom": (
            "compiler.backends.rom.deepseek_v4",
            "lower_to_abi3",
            "configs/hardware/abi3_capability/rom_deepseek_v4.json",
        ),
        "hbm": (
            "compiler.backends.hbm_sram.lower",
            "lower_to_abi3",
            "configs/hardware/abi3_capability/hbm_sram_cluster_32.json",
        ),
    }[lane]
    lower = getattr(importlib.import_module(module), function)
    return lower(
        graph, Capability.from_dict(json.loads((REPO / capability).read_text()))
    )


def _resolve(table, view_id: int, symbols: dict[int, int]) -> tuple[int, ...]:
    """The dims ``runtime.sim.memory.ViewResolver`` would present.

    The same arithmetic, restated over the descriptor payload so that the test
    reads the wire format rather than a device.
    """
    payload = table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW).payload
    rank = payload["rank"]
    dims = [payload[f"dim{a}"] for a in range(rank)]
    axis = int(payload["extent_axis"])
    unit = max(int(payload["extent_unit"]), 1)
    numerator = max(int(payload["extent_numerator"]), 1)
    bias = int(payload["extent_bias"])
    leading: int | None = None
    for slot in range(payload["dynamic_term_count"]):
        if payload[f"term{slot}_kind"] != int(SelectorKind.LOOP_INDUCTION):
            continue
        try:
            loop = table.get(
                payload[f"term{slot}_index"], ExtendedDescriptorType.LOOP_CONTROL
            )
        except Exception:  # pragma: no cover - not a loop descriptor
            continue
        control = loop.payload
        if control["bound_selector_kind"] != int(SelectorKind.RUNTIME_SYMBOL):
            continue
        step = iteration_extent(
            max(int(control["bound_divisor"]), 1), numerator, unit
        )
        if step is None:
            continue
        if int(payload[f"term{slot}_stride"]) != int(payload[f"stride{axis}"]) * step:
            continue
        bound = symbols.get(int(control["bound_symbol_id"]))
        if bound is None or bound <= 0:
            continue
        extent = (numerator * int(bound)) // unit + bias
        if extent <= 0 or extent >= step + bias:
            continue
        leading = extent if leading is None else min(leading, extent)
    if leading is not None and 0 < leading < dims[axis]:
        dims[axis] = leading
    return tuple(dims)


def _issues(table, instruction: Instruction, symbols: dict[int, int]) -> bool:
    if instruction.predicate_id == NO_ID:
        return True
    payload = table.get(
        instruction.predicate_id, ExtendedDescriptorType.PREDICATE
    ).payload
    if payload["predicate_kind"] == int(PredicateKind.PHASE_IS):
        value = symbols[int(Symbol.PHASE)]
    else:
        value = symbols[int(payload["selector_index"])]
    immediate = int(payload["immediate"])
    verdict = {
        Comparison.EQ: value == immediate,
        Comparison.NE: value != immediate,
        Comparison.LT: value < immediate,
        Comparison.LE: value <= immediate,
        Comparison.GT: value > immediate,
        Comparison.GE: value >= immediate,
    }[Comparison(payload["comparison"])]
    if instruction.flags & InstructionFlag.PREDICATE_INVERT:
        return not verdict
    return verdict


def _wait_events(table, instruction: Instruction) -> set[int]:
    if instruction.wait_set_id == NO_ID:
        return set()
    wait = table.get(
        instruction.wait_set_id, ExtendedDescriptorType.EVENT_WAIT_SET
    ).payload
    return {
        int(wait[f"producer_{slot}"])
        for slot in range(int(wait["producer_count"]))
    }


def _rows(lane: str, graph: KernelGraph) -> dict[str, dict[str, int]]:
    """``phase -> {"join_in", "join_out", "attention_kv"}`` row counts."""
    deployment = _lower(lane, graph)
    table = deployment.table
    kernel_of = {k.index: k.kernel_id for k in graph.kernels}
    operators = {}
    for index, descriptor in enumerate(table.descriptors()):
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        name = kernel_of.get(descriptor.payload["source_kernel_id"], "")
        if name in (JOIN, CONSUMER):
            operators[index] = (descriptor.payload, name)
    _header, body = split_program(deployment.program)
    size = INSTRUCTION.size
    stream = [
        Instruction.decode(body[i * size : (i + 1) * size])
        for i in range(len(body) // size)
    ]
    results: dict[str, dict[str, int]] = {}
    for phase, binding in BINDINGS.items():
        symbols = {int(k): int(v) for k, v in binding.items()}
        seen: dict[str, int] = {}
        for instruction in stream:
            if instruction.descriptor_id not in operators:
                continue
            payload, name = operators[instruction.descriptor_id]
            if not _issues(table, instruction, symbols):
                continue
            if name == JOIN:
                assert "join_out" not in seen, (
                    f"{lane}/{phase}: two join paths issue for one request"
                )
                inputs = [
                    _resolve(table, payload[f"input_view_{slot}"], symbols)[0]
                    for slot in range(4)
                    if payload[f"input_view_{slot}"] != NO_ID
                ]
                seen["join_in"] = sum(inputs)
                seen["join_out"] = _resolve(
                    table, payload["output_view_0"], symbols
                )[0]
            else:
                assert "attention_kv" not in seen, (
                    f"{lane}/{phase}: two attention paths issue for one request"
                )
                seen["attention_kv"] = _resolve(
                    table, payload["input_view_1"], symbols
                )[0]
        results[phase] = seen
    return results


@pytest.fixture(scope="module")
def graph() -> KernelGraph:
    if not IR.exists():  # pragma: no cover - build artefact
        pytest.skip(f"{IR} has not been built; run `make abi3-ir`")
    return KernelGraph.read(IR)


@pytest.fixture(scope="module")
def rows(graph: KernelGraph) -> dict[str, dict[str, dict[str, int]]]:
    return {lane: _rows(lane, graph) for lane in ("rom", "hbm")}


@pytest.mark.parametrize("lane", ["rom", "hbm"])
@pytest.mark.parametrize("phase", sorted(BINDINGS))
def test_join_output_is_the_sum_of_its_operands(lane, phase, rows):
    """A17, at the extents the request actually binds.

    This is the equality the engine checks one dispatch after admission, and
    the one that failed at decode step 1: ``output view ... dims (129, 512)
    differ from the axis-0 concatenation (137, 512)``.
    """
    measured = rows[lane][phase]
    assert measured, f"{lane}/{phase}: no join path issues at all"
    assert measured["join_out"] == measured["join_in"]
    assert measured["join_out"] == _expected(BINDINGS[phase])


@pytest.mark.parametrize("phase", sorted(BINDINGS))
def test_both_lanes_size_the_same_resource_the_same(phase, rows):
    """The comparability half of the defect.

    ROM said 137 rows and HBM said 257 for the same decode step of the same
    graph.  Two lanes that disagree about the size of one resource are not
    comparing anything, whichever of them is right.
    """
    assert rows["rom"][phase] == rows["hbm"][phase]


@pytest.mark.parametrize("kernel_id", [JOIN, CONSUMER])
def test_hbm_conditional_paths_have_a_causal_or_join(kernel_id, graph):
    """Every mutually exclusive producer is waited under its own predicate."""

    deployment = _lower("hbm", graph)
    source = next(k.index for k in graph.kernels if k.kernel_id == kernel_id)
    _header, body = split_program(deployment.program)
    size = INSTRUCTION.size
    stream = [
        Instruction.decode(body[i * size : (i + 1) * size])
        for i in range(len(body) // size)
    ]
    indexed = [
        (index, instruction)
        for index, instruction in enumerate(stream)
        if instruction.source_operation_id == source
    ]
    producers = [
        (index, instruction)
        for index, instruction in indexed
        if instruction.major != int(Major.CONTROL)
        and instruction.predicate_id != NO_ID
        and instruction.signal_event_id != NO_ID
    ]
    waits = [
        (index, instruction)
        for index, instruction in indexed
        if instruction.major == int(Major.CONTROL)
        and instruction.sub == int(Control.WAIT)
    ]
    joins = [
        (index, instruction)
        for index, instruction in indexed
        if instruction.major == int(Major.CONTROL)
        and instruction.sub == int(Control.NOP)
        and instruction.signal_event_id != NO_ID
    ]
    assert producers
    assert len(joins) == 1
    join_index, join = joins[0]
    assert join.predicate_id == NO_ID
    for producer_index, producer in producers:
        matching = [
            (wait_index, wait)
            for wait_index, wait in waits
            if producer.signal_event_id in _wait_events(deployment.table, wait)
            and wait.predicate_id == producer.predicate_id
            and bool(wait.flags & InstructionFlag.PREDICATE_INVERT)
            == bool(producer.flags & InstructionFlag.PREDICATE_INVERT)
        ]
        assert len(matching) == 1
        assert producer_index < matching[0][0] < join_index


@pytest.mark.parametrize("lane", ["rom", "hbm"])
@pytest.mark.parametrize("phase", sorted(BINDINGS))
def test_the_consumer_reads_the_rows_the_join_wrote(lane, phase, rows):
    """The propagation the split cannot stop at the producer.

    ``ATTENTION.SPARSE`` gathers rows of the join by index and bounds those
    indices by its own operand's resolved extent.  A consumer holding the
    prefill function at decode would present 129 of 137 rows and refuse the
    eight rebased compressed indices its own selector had just produced.
    """
    measured = rows[lane][phase]
    assert measured["attention_kv"] == measured["join_out"]


def _stripped(field: str) -> KernelGraph:
    body = json.loads(IR.read_text())
    removed = 0
    for kernel in body["kernels"]:
        if field in kernel.get("attributes", {}):
            del kernel["attributes"][field]
            removed += 1
    assert removed, f"no kernel declares {field!r}"
    body.pop("graph_id", None)
    import tempfile

    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(body, handle)
    handle.close()
    return KernelGraph.read(Path(handle.name))


@pytest.mark.parametrize("lane", ["rom", "hbm"])
def test_a_join_with_no_phase_binding_is_refused(lane, graph):
    """The refusal that should have caught this at the first decode attempt.

    Without the phase binding the sum is over two symbols in every phase, so
    there is no A18 image of it at all -- and the exporter's declared
    ``attention_rows_ratioN`` is a guess a backend used to accept.  Both lanes
    now refuse the lowering rather than emit a view the engine will reject.
    """
    with pytest.raises(Exception) as excinfo:
        _lower(lane, _stripped("phase_symbol_binding"))
    assert "no single A18 extent" in str(excinfo.value)


@pytest.mark.parametrize("lane", ["rom", "hbm"])
def test_a_declared_extent_that_is_not_the_sum_is_refused(lane):
    """A join whose output symbol disagrees with its operands.

    The window layers join ``span + 128`` and declare ``attention_rows_window``.
    Relabelling that output ``attention_rows_ratio4`` -- the exact substitution
    this defect was -- must be refused rather than lowered.
    """
    body = json.loads(IR.read_text())
    patched = 0
    for tensor in body["tensors"]:
        if tensor.get("tensor_id", "").endswith(
            "main.layer00.attention_kv_view.output"
        ):
            tensor["shape"][0]["symbol"] = "attention_rows_ratio4"
            tensor["shape"][0]["maximum"] = 327808
            patched += 1
    assert patched == 1
    body.pop("graph_id", None)
    import tempfile

    handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(body, handle)
    handle.close()
    with pytest.raises(Exception) as excinfo:
        _lower(lane, KernelGraph.read(Path(handle.name)))
    assert "operands sum to" in str(excinfo.value)
