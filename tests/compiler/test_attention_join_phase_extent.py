"""DeepSeek's phase-selected sparse-attention KV row space.

The pinned model has two mutually exclusive main-attention layouts:

* prefill: complete current KV, then the valid compressed prefix;
* decode: all 128 physical circular-window slots, then that prefix.

There is no phase in which current KV and a second copy of the window are both
present.  The neutral graph states the ordered input subset in ``phase_inputs``
and both backends lower it with existing ABI 3.0 forward branches.  These tests
read the emitted wire descriptors, follow those branches for one static pass,
and independently check the selected operands, their sum, and the sparse
consumer's view in the uncompressed, ratio-four, and ratio-128 layer families.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from compiler.frontends.v3.deepseek_v4 import export_deepseek_v4_kernel_graph
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import Attention, Control, InstructionFlag, Major, NO_ID
from runtime.abi3.descriptors import (
    Comparison,
    ExtendedDescriptorType,
    Phase,
    PredicateKind,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import INSTRUCTION, Instruction, split_program
from runtime.sim.memory import iteration_extent


WINDOW = 128


@dataclass(frozen=True)
class Site:
    ratio: int
    join: str
    consumer: str
    prefill_inputs: tuple[int, ...]
    decode_inputs: tuple[int, ...]


SITES = {
    0: Site(
        ratio=0,
        join="main.layer00.attention_kv_view",
        consumer="main.layer00.sparse_attention",
        prefill_inputs=(0,),
        decode_inputs=(1,),
    ),
    4: Site(
        ratio=4,
        join="main.layer02.attention_kv_view",
        consumer="main.layer02.sparse_attention",
        prefill_inputs=(0, 2),
        decode_inputs=(1, 2),
    ),
    128: Site(
        ratio=128,
        join="main.layer03.attention_kv_view",
        consumer="main.layer03.sparse_attention",
        prefill_inputs=(0, 2),
        decode_inputs=(1, 2),
    ),
}


def _binding(*, phase: Phase, span: int, position: int) -> dict[Symbol, int]:
    return {
        Symbol.SPAN_TOKENS: span,
        Symbol.POSITION_START: position,
        Symbol.POSITION_END: position + span,
        Symbol.CONTEXT_LENGTH: position + span,
        Symbol.PHASE: int(phase),
    }


# Both sides of each optional compressed-prefix boundary are included.  The
# 200,000-position row is deliberately here as an extent/address-space check;
# it does not allocate or execute a full model context.
BINDINGS = {
    "prefill_1": _binding(phase=Phase.PREFILL, span=1, position=0),
    "prefill_160": _binding(phase=Phase.PREFILL, span=160, position=0),
    "decode_1": _binding(phase=Phase.DECODE, span=1, position=1),
    "decode_129": _binding(phase=Phase.DECODE, span=1, position=129),
    "decode_200000": _binding(phase=Phase.DECODE, span=1, position=200_000),
}


def _lower(lane: str, graph: KernelGraph):
    import importlib
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
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
        graph,
        Capability.from_dict(json.loads((root / capability).read_text())),
    )


def _resolve(table, view_id: int, symbols: dict[int, int]) -> tuple[int, ...]:
    """Resolve the view dimensions from the emitted ABI 3.0 descriptor."""

    payload = table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW).payload
    rank = payload["rank"]
    dims = [payload[f"dim{axis}"] for axis in range(rank)]
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
        step = iteration_extent(max(int(control["bound_divisor"]), 1), numerator, unit)
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
    """Evaluate the predicate kinds used by the selected paths."""

    if instruction.predicate_id == NO_ID:
        return True
    payload = table.get(
        instruction.predicate_id, ExtendedDescriptorType.PREDICATE
    ).payload
    kind = PredicateKind(payload["predicate_kind"])
    if kind is PredicateKind.ALWAYS:
        verdict = True
    elif kind is PredicateKind.PHASE_IS:
        verdict = symbols[int(Symbol.PHASE)] == int(payload["immediate"])
    elif kind is PredicateKind.COMPARE_SYMBOL:
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
    else:  # No selected join/consumer or forward phase branch uses another kind.
        raise AssertionError(f"static path cannot evaluate predicate kind {kind.name}")
    if instruction.flags & InstructionFlag.PREDICATE_INVERT:
        verdict = not verdict
    return verdict


def _static_path(
    table, stream: list[Instruction], symbols: dict[int, int]
) -> tuple[int, ...]:
    """Follow forward branches while treating loop records as fallthrough.

    One pass is sufficient for descriptor inspection: loop induction changes
    addresses, not which phase-specific operator descriptor a request selects.
    """

    path: list[int] = []
    pc = 0
    while pc < len(stream):
        instruction = stream[pc]
        path.append(pc)
        if (
            instruction.major == int(Major.CONTROL)
            and instruction.sub == int(Control.BRANCH)
            and _issues(table, instruction, symbols)
        ):
            assert pc < instruction.control_id <= len(stream), (
                f"non-forward branch {pc} -> {instruction.control_id}"
            )
            pc = instruction.control_id
            continue
        if (
            instruction.major == int(Major.CONTROL)
            and instruction.sub == int(Control.COMPLETE)
            and _issues(table, instruction, symbols)
        ):
            break
        pc += 1
    return tuple(path)


def _expected_parts(site: Site, binding: dict[Symbol, int]) -> tuple[int, ...]:
    phase = Phase(binding[Symbol.PHASE])
    base = binding[Symbol.SPAN_TOKENS] if phase is Phase.PREFILL else WINDOW
    groups = 0 if site.ratio == 0 else binding[Symbol.CONTEXT_LENGTH] // site.ratio
    return (base, *([groups] if groups else []))


def _measure(lane: str, graph: KernelGraph):
    deployment = _lower(lane, graph)
    table = deployment.table
    kernel_of = {kernel.index: kernel.kernel_id for kernel in graph.kernels}
    site_of_name = {
        name: (ratio, role)
        for ratio, site in SITES.items()
        for role, name in (("join", site.join), ("consumer", site.consumer))
    }
    operators = {}
    for index, descriptor in enumerate(table.descriptors()):
        if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
            continue
        name = kernel_of.get(descriptor.payload["source_kernel_id"], "")
        matched = site_of_name.get(name)
        if matched is None:
            continue
        ratio, role = matched
        if role == "consumer" and not (
            descriptor.payload["engine_family"] == int(Major.ATTENTION)
            and descriptor.payload["engine_sub"] == int(Attention.SPARSE)
        ):
            continue
        operators[index] = (ratio, role, descriptor.payload)

    _header, body = split_program(deployment.program)
    size = INSTRUCTION.size
    stream = [
        Instruction.decode(body[offset : offset + size])
        for offset in range(0, len(body), size)
    ]
    results = {}
    for case_name, raw_binding in BINDINGS.items():
        symbols = {int(key): int(value) for key, value in raw_binding.items()}
        measured = {ratio: {} for ratio in SITES}
        for pc in _static_path(table, stream, symbols):
            instruction = stream[pc]
            matched = operators.get(instruction.descriptor_id)
            if matched is None or not _issues(table, instruction, symbols):
                continue
            ratio, role, payload = matched
            if role == "join":
                assert "join_parts" not in measured[ratio], (
                    f"{lane}/{case_name}/ratio{ratio}: multiple join paths issue"
                )
                parts = tuple(
                    _resolve(table, payload[f"input_view_{slot}"], symbols)[0]
                    for slot in range(4)
                    if payload[f"input_view_{slot}"] != NO_ID
                )
                measured[ratio]["join_parts"] = parts
                measured[ratio]["join_out"] = _resolve(
                    table, payload["output_view_0"], symbols
                )[0]
            else:
                assert "attention_kv" not in measured[ratio], (
                    f"{lane}/{case_name}/ratio{ratio}: multiple sparse paths issue"
                )
                measured[ratio]["attention_kv"] = _resolve(
                    table, payload["input_view_1"], symbols
                )[0]
        results[case_name] = measured
    return results


@pytest.fixture(scope="module")
def graph() -> KernelGraph:
    """Always inspect a fresh source graph, never a worktree-local artefact."""

    return export_deepseek_v4_kernel_graph()


@pytest.fixture(scope="module")
def rows(graph: KernelGraph):
    return {lane: _measure(lane, graph) for lane in ("rom", "hbm")}


@pytest.mark.parametrize("ratio", sorted(SITES))
def test_neutral_phase_inputs_name_the_source_order(graph: KernelGraph, ratio: int):
    site = SITES[ratio]
    kernel = next(kernel for kernel in graph.kernels if kernel.kernel_id == site.join)
    selected = kernel.attributes["phase_inputs"]
    assert tuple(selected["prefill"]) == site.prefill_inputs
    assert tuple(selected["decode"]) == site.decode_inputs
    assert kernel.attributes["phase_symbol_binding"] == {
        "prefill": {"position_start": 0},
        "decode": {"span_tokens": 1},
    }
    assert "kv_fp8_qdq.output" in kernel.inputs[site.prefill_inputs[0]]
    assert "committed_window" in kernel.inputs[site.decode_inputs[0]]
    if ratio:
        assert "compress_kv_valid_view.output" in kernel.inputs[site.prefill_inputs[1]]
        assert site.prefill_inputs[1] == site.decode_inputs[1]


@pytest.mark.parametrize("lane", ["rom", "hbm"])
@pytest.mark.parametrize("ratio", sorted(SITES))
@pytest.mark.parametrize("case_name", sorted(BINDINGS))
def test_selected_join_and_sparse_consumer_have_exact_rows(
    lane: str, ratio: int, case_name: str, rows
):
    expected_parts = _expected_parts(SITES[ratio], BINDINGS[case_name])
    measured = rows[lane][case_name][ratio]
    assert measured["join_parts"] == expected_parts
    assert measured["join_out"] == sum(expected_parts)
    assert measured["attention_kv"] == measured["join_out"]


@pytest.mark.parametrize("ratio", sorted(SITES))
@pytest.mark.parametrize("case_name", sorted(BINDINGS))
def test_both_lanes_size_the_same_resource_the_same(ratio, case_name, rows):
    assert rows["rom"][case_name][ratio] == rows["hbm"][case_name][ratio]


def _edited_graph(graph: KernelGraph, edit) -> KernelGraph:
    body = graph.to_dict()
    edit(body)
    body.pop("graph_id", None)
    return KernelGraph.from_dict(body)


@pytest.mark.parametrize("lane", ["rom", "hbm"])
def test_a_mixed_symbol_join_without_phase_selection_is_refused(lane, graph):
    """Removing both phase authorities must not revive the old approximation."""

    def edit(body):
        kernel = next(
            kernel for kernel in body["kernels"] if kernel["kernel_id"] == SITES[4].join
        )
        kernel["attributes"].pop("phase_inputs")
        kernel["attributes"].pop("phase_symbol_binding")

    with pytest.raises(Exception, match="no single A18 extent"):
        _lower(lane, _edited_graph(graph, edit))


@pytest.mark.parametrize("lane", ["rom", "hbm"])
def test_a_wrong_prefill_extent_is_refused(lane, graph):
    """A phase split does not license a false declaration for either phase."""

    def edit(body):
        source = next(
            tensor["shape"][0]
            for tensor in body["tensors"]
            if tensor["tensor_id"].endswith("main.layer03.attention_kv_view.output")
        )
        target = next(
            tensor
            for tensor in body["tensors"]
            if tensor["tensor_id"].endswith("main.layer02.attention_kv_view.output")
        )
        target["shape"][0] = dict(source)

    with pytest.raises(Exception, match="does not match"):
        _lower(lane, _edited_graph(graph, edit))
