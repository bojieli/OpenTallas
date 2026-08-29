#!/usr/bin/env python3
"""Build ABI 3.0 RTL correlation vectors from real deployments.

Every vector in this set is a *real* ABI 3.0 program: it is built with
``runtime.abi3.builder.DeploymentBuilder``, admitted (or deliberately rejected)
by ``runtime.abi3.verifier``, and executed by ``runtime.sim.device.Device``.
The generator emits two things from the same artifact:

* memory images the RTL testbench and the Verilator harness load directly --
  the 256-byte program header, the 32-byte instruction records, the descriptor
  records, and the request-bound runtime symbols; and
* the golden control-plane observation the RTL must reproduce exactly --
  retired, fetched, predicated-off, issued and loop-iteration counts, the
  engine-issue sequence (family, subopcode, descriptor ID, instruction index),
  the state commit/discard decision and the trap class.

Engine datapaths are out of scope for RTL 3.0, so the golden model's engine
registry is populated here with recording no-ops through the public
``runtime.sim.engine.register`` decorator.  That makes the comparison exactly
the control plane: the same instruction stream, the same issue order, the same
descriptor IDs, with no engine arithmetic on either side.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field as dc_field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Control,
    DType,
    Dma,
    Feature,
    Major,
    NO_ID,
    Observation,
    Permission,
    Recovery,
    Reduction,
    Selection,
    State,
    StateClass,
    StorageClass,
    TopologyClass,
    Tensor,
    Vector,
    CounterGroup,
    counter_id,
)
from runtime.abi3.builder import DeploymentBuilder  # noqa: E402
from runtime.abi3.crc import record_crc, sha256  # noqa: E402
from runtime.abi3.deployment import Deployment, ObjectSource  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    Comparison,
    ExtendedDescriptorType,
    Phase,
    PredicateKind,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import Instruction, decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.sim import engine as engine_module  # noqa: E402
from runtime.sim.device import Device  # noqa: E402

OUTPUT_DIR = ROOT / "testdata/compiler/abi3"

# RTL memory geometry.  The images are padded to these sizes so that both
# simulators read a fully initialised memory.
PROGRAM_WORDS = 1024      # 256-bit instruction records
HEADER_WORDS = 2048       # 32-bit words, 64 per case
DESC_WORDS = 1024         # 1024-bit descriptor prefixes
SYMBOL_WORDS = 512        # 32-bit words, 16 per case
CASE_WORDS = 1024         # 32-bit words, 32 per case
ISSUE_WORDS = 2048        # 32-bit words, 2 per issue
META_WORDS = 8

CASE_STRIDE = 32
SYMBOL_STRIDE = 16
HEADER_STRIDE = 64

DESCRIPTOR_PREFIX_BYTES = 128   # header (64) plus the first payload block (64)

IDLE_OBSERVATION: dict[str, Any] = {
    "status": 1,
    "trap_class": 0,
    "first_fault": 0xFFFFFFFF,
    "complete": False,
    "fetched": 0,
    "retired": 0,
    "predicated_off": 0,
    "issued": 0,
    "loop_iterations": 0,
    "branches": 0,
    "wait_events": 0,
    "state_prepares": 0,
    "state_commits": 0,
    "state_discards": 0,
    "state_reads": 0,
    "state_generation_advances": 0,
    "state_commits_applied": 0,
    "state_rows_committed": 0,
    "issues": [],
}

TRAP_NONE = 0
TRAP_ADMISSION = 1
TRAP_INTEGRITY = 2
TRAP_ILLEGAL = 5
TRAP_CAPABILITY = 4


# ---------------------------------------------------------------------------
# Recording engine stubs
# ---------------------------------------------------------------------------
def _install_engine_stubs() -> None:
    """Register a recording no-op for every dispatchable engine operation."""
    from runtime.abi3.constants import SUBOPCODES

    dispatchable = (
        Major.DMA,
        Major.TENSOR,
        Major.VECTOR,
        Major.ATTENTION,
        Major.ROUTE,
        Major.REDUCTION,
        Major.SELECTION,
        Major.LINK,
    )
    for family in dispatchable:
        for member in SUBOPCODES[family]:
            if (int(family), int(member)) in engine_module.implemented():
                continue

            @engine_module.register(family, int(member))
            def _stub(ctx, sub, descriptor):  # noqa: ANN001
                return None


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def rtl_capability() -> Capability:
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=(
            int(Feature.HOST_QUEUE_ABI),
            int(Feature.DEPLOYMENT_DESCRIPTOR_ABI),
            int(Feature.DETERMINISTIC_MICROSEQUENCER),
            int(Feature.BF16_TENSOR),
            int(Feature.TRANSACTIONAL_STATE),
            int(Feature.ON_DEVICE_SELECTION),
        ),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 20,
            "max_retired_work": 1 << 32,
            "max_events": 256,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 64,
            "max_expert_ids": 1024,
            "max_topk": 16,
            "max_vocabulary": 32,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=(
            "bf16_bf16_fp32_sequential_rne_v1",
            "bf16_add_rne_v1",
            "exact_index_select_v1",
        ),
        engines={
            "tensor": {"lanes": 8, "queues": 1},
            "vector": {"lanes": 8, "queues": 1},
            "dma": {"queues": 1},
            "reduction": {"queues": 1},
            "selection": {"queues": 1},
            "state": {"queues": 1},
        },
        memory={
            "sram": {"bytes": 1 << 16, "banks": 2},
            "hbm": {"bytes": 1 << 20},
            "rom": {"bytes": 1 << 20},
        },
        technology_view="rtl3",
    )
    capability.validate()
    return capability


ROWS = 8
COLS = 16
CAPACITY_ROWS = 64


class Workspace:
    """A deployment builder pre-loaded with the objects every case shares."""

    def __init__(self, name: str, capability: Capability) -> None:
        self.capability = capability
        self.builder = DeploymentBuilder(
            target_id=name,
            model_id="abi3-rtl3",
            backend="rtl3",
            capability=capability,
        )
        b = self.builder
        b.require(Feature.BF16_TENSOR)
        b.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
            sram_bytes_per_node=capability.memory["sram"]["bytes"],
            key="topology",
        )
        weight_bytes = 4 * COLS * COLS * 2
        self.weights = b.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=weight_bytes,
            source=ObjectSource.zeros(weight_bytes),
            permissions=int(Permission.READ | Permission.IMMUTABLE),
            key="obj.weights",
        )
        act_bytes = ROWS * COLS * 2
        self.activations = b.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=act_bytes * 2,
            source=ObjectSource.zeros(act_bytes * 2),
            permissions=int(Permission.READ | Permission.WRITE),
            key="obj.activations",
        )
        kv_bytes = CAPACITY_ROWS * COLS * 2
        self.kv_committed = b.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=kv_bytes,
            source=ObjectSource.zeros(kv_bytes),
            permissions=int(Permission.READ | Permission.STATE_COMMIT),
            key="obj.kv.committed",
        )
        self.kv_prepared = b.memory_object(
            storage_class=StorageClass.STATE,
            size_bytes=kv_bytes,
            source=ObjectSource.zeros(kv_bytes),
            permissions=int(Permission.READ | Permission.STATE_PREPARE),
            key="obj.kv.prepared",
        )
        self.numeric = b.numeric(
            contract="bf16_bf16_fp32_sequential_rne_v1",
            input_dtype=DType.BF16,
            output_dtype=DType.BF16,
            key="num.matmul",
        )
        self.schedule = b.schedule(
            engine_family=Major.TENSOR,
            tile_rows=ROWS,
            tile_cols=COLS,
            tile_depth=COLS,
            key="sched.tensor",
        )
        self.view_in = b.tensor_view(
            object_id=self.activations,
            dtype=DType.BF16,
            dims=[ROWS, COLS],
            key="view.in",
        )
        self.view_out = b.tensor_view(
            object_id=self.activations,
            dtype=DType.BF16,
            dims=[ROWS, COLS],
            element_offset=ROWS * COLS,
            permissions=int(Permission.READ | Permission.WRITE),
            key="view.out",
        )
        self.view_weights = b.tensor_view(
            object_id=self.weights,
            dtype=DType.BF16,
            dims=[COLS, COLS],
            key="view.weights",
        )
        self.view_kv = b.tensor_view(
            object_id=self.kv_prepared,
            dtype=DType.BF16,
            dims=[CAPACITY_ROWS, COLS],
            permissions=int(Permission.READ | Permission.WRITE),
            key="view.kv",
        )
        self.counters = b.counter_class(
            int(CounterGroup.TENSOR),
            [counter_id(CounterGroup.TENSOR, 1)],
            key="ctr.tensor",
        )
        self.state = b.state(
            state_class=StateClass.KV_CACHE,
            committed_object_id=self.kv_committed,
            prepared_object_id=self.kv_prepared,
            row_bytes=COLS * 2,
            capacity_rows=CAPACITY_ROWS,
            element_dtype=DType.BF16,
            view_descriptor_id=self.view_kv,
            key="state.kv",
        )

    def op(self, family: Major, sub: int, *, key: str) -> int:
        """One OPERATOR descriptor reading view.in and writing view.out."""
        return self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=[self.view_in, self.view_weights],
            outputs=[self.view_out],
            numeric_profile_id=self.numeric,
            schedule_id=self.schedule,
            counter_class_id=self.counters,
            source_kernel_id=0,
            key=key,
        )

    def finish(self, **kwargs: Any) -> Deployment:
        return self.builder.finish(**kwargs)


@dataclass
class Case:
    """One RTL vector: a program image, its request, and its golden result."""

    name: str
    deployment: Deployment
    entrypoint_id: int = 0
    symbols: dict[int, int] = dc_field(default_factory=dict)
    run_program: bool = True
    device_runs: bool = True
    expect_admitted: bool = True
    corrupt: Callable[[bytes], bytes] | None = None
    corrupt_header: Callable[[bytes], bytes] | None = None
    expect_header_legal: bool = True
    expect_header_trap: int = TRAP_NONE
    reference: dict[str, Any] = dc_field(default_factory=dict)
    note: str = ""


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def patch_instruction(image: bytes, index: int, patch: dict[int, int],
                      *, reseal: bool) -> bytes:
    """Patch bytes of one 32-byte instruction, optionally re-stamping its CRC."""
    data = bytearray(image)
    base = 256 + index * 32
    for offset, value in patch.items():
        data[base + offset] = value
    if reseal:
        record = bytes(data[base : base + 32])
        crc = record_crc(record, 28)
        data[base + 28 : base + 32] = crc.to_bytes(4, "little")
    return bytes(data)


def corrupt_instruction_crc(index: int) -> Callable[[bytes], bytes]:
    def _apply(image: bytes) -> bytes:
        data = bytearray(image)
        base = 256 + index * 32
        data[base + 28] ^= 0x01
        return bytes(data)

    return _apply


def patch_header(patch: dict[int, int], *, reseal: bool) -> Callable[[bytes], bytes]:
    def _apply(image: bytes) -> bytes:
        data = bytearray(image)
        for offset, value in patch.items():
            data[offset] = value
        if reseal:
            crc = record_crc(bytes(data[:256]), 252)
            data[252:256] = crc.to_bytes(4, "little")
        return bytes(data)

    return _apply


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------
def case_linear(cap: Capability) -> Case:
    """Straight line: state prepare, four engine ops, commit, complete."""
    w = Workspace("a3-linear", cap)
    b = w.builder
    dma = w.op(Major.DMA, Dma.TRANSFER, key="op.dma")
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    reduce_op = w.op(Major.REDUCTION, Reduction.ORDERED_SUM, key="op.reduce")

    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    e_dma = b.new_event()
    b.emit(Major.DMA, Dma.TRANSFER, descriptor_id=dma, signal_event_id=e_dma,
           source_operation_id=0)
    e_mm = b.new_event()
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul,
           wait_set_id=b.wait_set([e_dma], key="wait.dma"),
           signal_event_id=e_mm, source_operation_id=1)
    e_add = b.new_event()
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add,
           wait_set_id=b.wait_set([e_mm], key="wait.mm"),
           signal_event_id=e_add, source_operation_id=2)
    b.emit(Major.REDUCTION, Reduction.ORDERED_SUM, descriptor_id=reduce_op,
           wait_set_id=b.wait_set([e_dma, e_mm, e_add], key="wait.all"),
           source_operation_id=3)
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="linear",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        note="straight-line issue order, multi-producer wait set, one commit",
    )


def case_constant_loop(cap: Capability) -> Case:
    """A constant-bounded loop of four iterations around one engine op."""
    w = Workspace("a3-loop-constant", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    loop = b.loop_control(lower_bound=0, upper_bound=4, step=1, key="loop.tile")
    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=0)
    b.close_loop()
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="loop_constant",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 2},
        note="constant trip count, four iterations, one issue per iteration",
    )


def case_nested_loops(cap: Capability) -> Case:
    """Three-deep nesting with a step-2 inner loop."""
    w = Workspace("a3-loop-nested", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    outer = b.loop_control(lower_bound=0, upper_bound=3, step=1, key="loop.outer")
    middle = b.loop_control(lower_bound=0, upper_bound=2, step=1, key="loop.middle")
    inner = b.loop_control(lower_bound=0, upper_bound=6, step=2, key="loop.inner")
    b.open_loop(outer)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.open_loop(middle)
    b.open_loop(inner)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=1)
    b.close_loop()
    b.close_loop()
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    # The declared bound is raised explicitly: the builder's proof does not
    # count LOOP_SETUP retires (see case work_bound_deficit below), so the
    # derived bound is one short of what this program actually retires.
    return Case(
        name="loop_nested",
        deployment=w.finish(max_retired_work=4096),
        note="three-deep nesting, non-unit step, 3*2*3 inner issues",
    )


def case_work_bound_deficit(cap: Capability) -> Case:
    """Nested loops with the *derived* work bound: an admitted program that traps.

    DeploymentBuilder._proved_work and Verifier._verify_control_flow both skip
    ``work += multiplier`` for CONTROL.LOOP_SETUP, so the proved bound omits one
    retire per loop entry.  With nesting the deficit is large enough that the
    device's own retired-work check fires on a program the verifier admitted.
    This case pins that behaviour so the RTL and the golden model agree on it.
    """
    w = Workspace("a3-work-deficit", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    outer = b.loop_control(lower_bound=0, upper_bound=3, step=1, key="loop.outer")
    middle = b.loop_control(lower_bound=0, upper_bound=2, step=1, key="loop.middle")
    inner = b.loop_control(lower_bound=0, upper_bound=6, step=2, key="loop.inner")
    b.open_loop(outer)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.open_loop(middle)
    b.open_loop(inner)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=1)
    b.close_loop()
    b.close_loop()
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="work_bound_deficit",
        deployment=w.finish(),
        note=(
            "admitted by the verifier, trapped by its own work bound: the "
            "proof does not count LOOP_SETUP retires"
        ),
    )


def case_symbol_loop(cap: Capability) -> Case:
    """A symbol-bounded loop: trip count comes from the request, not the program."""
    w = Workspace("a3-loop-symbol", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    loop = b.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        bound_symbol=Symbol.CONTEXT_LENGTH,
        bound_divisor=2,
        max_iterations=8,
        key="loop.context",
    )
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=0)
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="loop_symbol",
        deployment=w.finish(),
        symbols={int(Symbol.CONTEXT_LENGTH): 5},
        note="ceil(5/2)=3 iterations from a request symbol, maximum 8",
    )


def case_zero_trip(cap: Capability) -> Case:
    """A symbol-bounded loop whose runtime trip count is zero."""
    w = Workspace("a3-loop-zero", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    loop = b.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        bound_symbol=Symbol.SPARSE_INDEX_COUNT,
        max_iterations=8,
        key="loop.sparse",
    )
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=0)
    b.close_loop()
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=1)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="loop_zero_trip",
        deployment=w.finish(),
        symbols={int(Symbol.SPARSE_INDEX_COUNT): 0},
        note="zero-trip loop skips its body and its LOOP_NEXT",
    )


def _predicate_program(cap: Capability, name: str, phase: Phase, entry: int,
                       symbols: dict[int, int], note: str) -> Case:
    w = Workspace(name, cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    sel = w.op(Major.SELECTION, Selection.ARGMAX, key="op.argmax")
    loop = b.loop_control(lower_bound=0, upper_bound=4, step=1, key="loop.tile")
    p_prefill = b.predicate(kind=PredicateKind.PHASE_IS, immediate=int(Phase.PREFILL),
                            key="pred.prefill")
    p_span = b.predicate(kind=PredicateKind.COMPARE_SYMBOL,
                         comparison=Comparison.GT,
                         selector_kind=SelectorKind.RUNTIME_SYMBOL,
                         selector_index=int(Symbol.SPAN_TOKENS),
                         immediate=1, key="pred.span")
    p_first = b.predicate(kind=PredicateKind.LOOP_FIRST, selector_index=loop,
                          key="pred.first")
    p_last = b.predicate(kind=PredicateKind.LOOP_LAST, selector_index=loop,
                         key="pred.last")
    p_index = b.predicate(kind=PredicateKind.COMPARE_LOOP,
                          comparison=Comparison.GE,
                          selector_kind=SelectorKind.LOOP_INDUCTION,
                          selector_index=loop, immediate=2, key="pred.index")

    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, predicate_id=p_prefill,
           source_operation_id=0)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, predicate_id=p_prefill,
           invert_predicate=True, source_operation_id=1)
    b.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=sel,
           predicate_id=p_span, source_operation_id=2)
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, predicate_id=p_first,
           source_operation_id=3)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, predicate_id=p_last,
           source_operation_id=4)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, predicate_id=p_index,
           source_operation_id=5)
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    b.entrypoint(entrypoint_id=1, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name=name,
        deployment=w.finish(),
        entrypoint_id=entry,
        symbols=symbols,
        note=note,
    )


def case_predicate_prefill(cap: Capability) -> Case:
    return _predicate_program(
        cap, "predicate_prefill", Phase.PREFILL, 0,
        {int(Symbol.SPAN_TOKENS): 4},
        "phase, symbol, loop-first, loop-last and loop-compare predicates",
    )


def case_predicate_decode(cap: Capability) -> Case:
    case = _predicate_program(
        cap, "predicate_decode", Phase.DECODE, 1,
        {int(Symbol.SPAN_TOKENS): 1},
        "same program, decode entrypoint: the inverted and symbol predicates flip",
    )
    return case


def case_branch(cap: Capability) -> Case:
    """A predicated forward branch over an engine instruction."""
    w = Workspace("a3-branch", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    taken = b.predicate(kind=PredicateKind.COMPARE_SYMBOL,
                        comparison=Comparison.EQ,
                        selector_index=int(Symbol.PHASE),
                        immediate=int(Phase.DECODE), key="pred.decode")
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.CONTROL, Control.BRANCH, control_id=4, predicate_id=taken)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=1)
    b.emit(Major.CONTROL, Control.NOP)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=2)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="branch_forward",
        deployment=w.finish(),
        note="forward branch taken by a phase predicate",
    )


def case_state_discard(cap: Capability) -> Case:
    """Prepare then discard, then prepare and commit: both decisions in one run."""
    w = Workspace("a3-state", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    b.emit(Major.STATE, State.READ, descriptor_id=w.state)
    b.emit(Major.STATE, State.DISCARD, descriptor_id=w.state)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.STATE, State.GENERATION_ADVANCE, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="state_discard_then_commit",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 3},
        note="discard releases the prepare; the later commit stages three rows",
    )


def case_observation(cap: Capability) -> Case:
    """Observation and recovery families with control fences."""
    w = Workspace("a3-observation", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    counters = b.counter_class(
        int(CounterGroup.INSTRUCTION),
        [counter_id(CounterGroup.INSTRUCTION, 1), counter_id(CounterGroup.INSTRUCTION, 2)],
        key="ctr.instruction",
    )
    b.emit(Major.CONTROL, Control.NOP)
    b.emit(Major.OBSERVATION, Observation.COUNTER_SNAPSHOT, descriptor_id=counters)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.CONTROL, Control.FENCE)
    b.emit(Major.OBSERVATION, Observation.TRACE_CHECKPOINT, descriptor_id=counters)
    b.emit(Major.RECOVERY, Recovery.DRAIN)
    b.emit(Major.CONTROL, Control.ASSERT)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="observation_recovery",
        deployment=w.finish(),
        note="observation and recovery issue through the same engine port",
    )


def case_events(cap: Capability) -> Case:
    """A loop that signals per iteration, then a wait set over every producer."""
    w = Workspace("a3-events", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    reduce_op = w.op(Major.REDUCTION, Reduction.ORDERED_SUM, key="op.reduce")
    events = [b.new_event() for _ in range(4)]
    for slot, event in enumerate(events):
        b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul,
               signal_event_id=event, source_operation_id=slot)
    b.emit(Major.CONTROL, Control.WAIT,
           wait_set_id=b.wait_set(events, key="wait.fan"))
    b.emit(Major.REDUCTION, Reduction.ORDERED_SUM, descriptor_id=reduce_op,
           wait_set_id=b.wait_set(events[:2], key="wait.pair"),
           source_operation_id=4)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="events_fanin",
        deployment=w.finish(),
        note="four single-assignment events, a CONTROL.WAIT and a partial wait set",
    )


def case_mixed(cap: Capability) -> Case:
    """Everything at once: loops, predicates, events, state, branch."""
    w = Workspace("a3-mixed", cap)
    b = w.builder
    dma = w.op(Major.DMA, Dma.GATHER, key="op.gather")
    matmul = w.op(Major.TENSOR, Tensor.GROUPED_MATMUL, key="op.gmm")
    add = w.op(Major.VECTOR, Vector.SILU_MUL, key="op.silu")
    sel = w.op(Major.SELECTION, Selection.TOKEN_APPEND, key="op.append")
    loop = b.loop_control(lower_bound=0, upper_bound=3, step=1, key="loop.layer")
    p_last = b.predicate(kind=PredicateKind.LOOP_LAST, selector_index=loop,
                         key="pred.last")
    e_dma = b.new_event()
    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    b.emit(Major.DMA, Dma.GATHER, descriptor_id=dma, signal_event_id=e_dma,
           source_operation_id=0)
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.GROUPED_MATMUL, descriptor_id=matmul,
           wait_set_id=b.wait_set([e_dma], key="wait.dma"), source_operation_id=1)
    b.emit(Major.VECTOR, Vector.SILU_MUL, descriptor_id=add, predicate_id=p_last,
           source_operation_id=2)
    b.close_loop()
    b.emit(Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=sel,
           source_operation_id=3)
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="mixed",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 1},
        note="loop, predicate, repeated wait on one event, staged commit",
    )


# ---------------------------------------------------------------------------
# Negative programs
# ---------------------------------------------------------------------------
def _tiny(cap: Capability, name: str) -> Workspace:
    w = Workspace(name, cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return w


def negative_instruction_cases(cap: Capability) -> list[Case]:
    """Instruction-record defects, each on the first executed instruction."""
    empty = {
        "fetched": 1, "retired": 0, "predicated_off": 0, "issued": 0,
        "loop_iterations": 0, "branches": 0, "wait_events": 0,
        "state_prepares": 0, "state_commits": 0, "state_discards": 0,
        "state_reads": 0, "state_generation_advances": 0,
        "state_commits_applied": 0, "state_rows_committed": 0,
        "first_fault": 0, "issues": [], "complete": False,
    }
    cases: list[Case] = []

    w = _tiny(cap, "a3-neg-crc")
    cases.append(Case(
        name="negative_instruction_crc",
        deployment=w.finish(),
        device_runs=False,
        corrupt=corrupt_instruction_crc(0),
        reference=dict(empty, trap_class=TRAP_INTEGRITY),
        note="one flipped CRC bit; admission fails on integrity, class 2",
    ))

    w = _tiny(cap, "a3-neg-opcode")
    cases.append(Case(
        name="negative_illegal_opcode",
        deployment=w.finish(),
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {0: 0x11}, reseal=True),
        reference=dict(empty, trap_class=TRAP_ILLEGAL),
        note="major opcode 0x11 is not in the frozen registry",
    ))

    w = _tiny(cap, "a3-neg-subopcode")
    cases.append(Case(
        name="negative_illegal_subopcode",
        deployment=w.finish(),
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {1: 0x0D}, reseal=True),
        reference=dict(empty, trap_class=TRAP_ILLEGAL),
        note="VECTOR subopcode 0x0d is beyond SQRT_SOFTPLUS",
    ))

    w = _tiny(cap, "a3-neg-flag")
    cases.append(Case(
        name="negative_reserved_flag",
        deployment=w.finish(),
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {3: 0x01}, reseal=True),
        reference=dict(empty, trap_class=TRAP_ILLEGAL),
        note="flag bit 8 is reserved and must be zero",
    ))

    w = _tiny(cap, "a3-neg-invert")
    cases.append(Case(
        name="negative_invert_without_predicate",
        deployment=w.finish(),
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {2: 0x02}, reseal=True),
        reference=dict(empty, trap_class=TRAP_ILLEGAL),
        note="PREDICATE_INVERT without PREDICATED",
    ))
    return cases


def case_branch_out_of_range(cap: Capability) -> Case:
    """A branch target outside the authenticated body."""
    w = Workspace("a3-neg-branch", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    b.emit(Major.CONTROL, Control.BRANCH, control_id=99)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="negative_branch_out_of_range",
        deployment=w.finish(),
        device_runs=True,
        expect_admitted=False,
        reference={
            "fetched": 1, "retired": 0, "predicated_off": 0, "issued": 0,
            "loop_iterations": 0, "branches": 0, "wait_events": 0,
            "state_prepares": 0, "state_commits": 0, "state_discards": 0,
            "state_reads": 0, "state_generation_advances": 0,
            "state_commits_applied": 0, "state_rows_committed": 0,
            "trap_class": TRAP_ILLEGAL, "first_fault": 0, "issues": [],
            "complete": False,
        },
        note=(
            "RTL rejects the branch record at admission; the golden model "
            "transfers control first and faults at the target index"
        ),
    )


def case_loop_over_maximum(cap: Capability) -> Case:
    """A runtime trip count above the loop's declared maximum."""
    w = Workspace("a3-neg-trip", cap)
    b = w.builder
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    loop = b.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        bound_symbol=Symbol.CONTEXT_LENGTH,
        max_iterations=4,
        key="loop.context",
    )
    b.emit(Major.CONTROL, Control.NOP)
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul, source_operation_id=0)
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="negative_loop_over_maximum",
        deployment=w.finish(),
        symbols={int(Symbol.CONTEXT_LENGTH): 9},
        reference={"first_fault": 1},
        note=(
            "runtime trip 9 exceeds the verified maximum 4: capability trap. "
            "The golden model raises this trap without an instruction index; "
            "the RTL reports the LOOP_SETUP that raised it"
        ),
    )


def case_trap_mid_transaction(cap: Capability) -> Case:
    """A trap after a staged commit: nothing may reach the committed cursor."""
    w = Workspace("a3-neg-trap", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    b.emit(Major.STATE, State.PREPARE, descriptor_id=w.state)
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=0)
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.TRAP)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="negative_trap_mid_transaction",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 5},
        note="explicit TRAP after a staged commit; no state may be applied",
    )


def case_commit_without_prepare(cap: Capability) -> Case:
    w = Workspace("a3-neg-commit", cap)
    b = w.builder
    b.emit(Major.STATE, State.COMMIT, descriptor_id=w.state)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="negative_commit_without_prepare",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 2},
        expect_admitted=False,
        reference={"first_fault": 0},
        note=(
            "state transaction trap: commit with no open prepare. The golden "
            "model raises it without an instruction index; the RTL reports the "
            "instruction that raised it"
        ),
    )


def case_wait_unsignalled(cap: Capability) -> Case:
    w = Workspace("a3-neg-wait", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    ghost = b.new_event()
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add,
           wait_set_id=b.wait_set([ghost], key="wait.ghost"),
           source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="negative_wait_unsignalled",
        deployment=w.finish(),
        expect_admitted=False,
        note="wait on an event no instruction signals: internal-invariant trap",
    )


def case_work_bound(cap: Capability) -> Case:
    w = Workspace("a3-neg-work", cap)
    b = w.builder
    add = w.op(Major.VECTOR, Vector.ADD, key="op.add")
    for slot in range(6):
        b.emit(Major.VECTOR, Vector.ADD, descriptor_id=add, source_operation_id=slot)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="negative_work_bound",
        deployment=w.finish(max_retired_work=3),
        expect_admitted=False,
        note="declared retired-work bound of three: watchdog trap on the fourth",
    )


def header_cases(cap: Capability) -> list[Case]:
    """Program-header defects: the body is never reached."""
    out: list[Case] = []
    specs = [
        ("negative_header_magic", patch_header({3: 0x00}, reseal=True),
         TRAP_ADMISSION, "magic is not OTTA3PG"),
        ("negative_header_version", patch_header({8: 0x04}, reseal=True),
         TRAP_ADMISSION, "ABI major 4 is not implemented"),
        ("negative_header_instruction_bytes", patch_header({12: 0x40}, reseal=True),
         TRAP_ADMISSION, "instruction size is not 32 bytes"),
        ("negative_header_zero_count", patch_header({16: 0, 17: 0, 18: 0, 19: 0},
                                                    reseal=True),
         TRAP_ADMISSION, "instruction count must be nonzero"),
        ("negative_header_reserved", patch_header({204: 0x01}, reseal=True),
         TRAP_ADMISSION, "reserved bytes 204..251 must be zero"),
        ("negative_header_crc", patch_header({252: 0xFF}, reseal=False),
         TRAP_INTEGRITY, "header CRC32C mismatch"),
    ]
    for name, patch, trap, note in specs:
        w = _tiny(cap, name)
        out.append(Case(
            name=name,
            deployment=w.finish(),
            run_program=False,
            device_runs=False,
            corrupt_header=patch,
            expect_header_legal=False,
            expect_header_trap=trap,
            note=note,
        ))
    return out


# ---------------------------------------------------------------------------
# Golden execution
# ---------------------------------------------------------------------------
def run_golden(case: Case, capability: Capability) -> dict[str, Any]:
    """Execute one case on the golden device and return the observation."""
    device = Device(case.deployment, capability, verify=False, trace=True)
    session = device.create_session()
    mark = len(device.trace)
    result = device.run_transaction(
        session, entrypoint_id=case.entrypoint_id, symbols=dict(case.symbols)
    )
    trace = device.trace[mark:]
    counters = result.counters
    issues = []
    for entry in trace:
        instruction = device.instructions[entry["pc"]]
        issues.append({
            "index": entry["pc"],
            "family": int(instruction.major),
            "sub": int(instruction.sub),
            "descriptor_id": int(instruction.descriptor_id),
            "mnemonic": instruction.mnemonic,
        })
    success = result.status == 0
    return {
        "status": int(result.status),
        "trap_class": int(result.trap_class),
        "first_fault": int(result.first_fault_instruction),
        "complete": bool(success),
        "fetched": int(result.fetched),
        "retired": int(result.retired),
        "predicated_off": int(result.predicated_off),
        "issued": int(counters.get("instructions.issued", 0)),
        "loop_iterations": int(counters.get("control.loop_iterations", 0)),
        "branches": int(counters.get("control.branches_taken", 0)),
        "wait_events": int(counters.get("queue.wait_events", 0)),
        "state_prepares": int(counters.get("state.prepares", 0)),
        "state_commits": int(counters.get("state.commits", 0)),
        "state_discards": int(counters.get("state.discards", 0)),
        "state_reads": int(counters.get("state.reads", 0)),
        "state_generation_advances": int(
            counters.get("state.generation_advances", 0)
        ),
        "state_commits_applied": int(counters.get("state.commits", 0)) if success else 0,
        "state_rows_committed": int(counters.get("state.rows_committed", 0)),
        "issues": issues,
        "message": result.message,
        "counters": {k: int(v) for k, v in sorted(counters.items())},
    }


def effective_symbols(case: Case) -> dict[int, int]:
    """The symbol bindings the golden model sees, including its defaults."""
    entry = next(
        e for e in case.deployment.entrypoints
        if e["entrypoint_id"] == case.entrypoint_id
    )
    symbols = dict(case.symbols)
    symbols.setdefault(int(Symbol.PHASE), int(entry["phase"]))
    symbols.setdefault(int(Symbol.GENERATION_INDEX), 0)
    return symbols


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def le_words(blob: bytes) -> list[int]:
    return [
        int.from_bytes(blob[i : i + 4], "little") for i in range(0, len(blob), 4)
    ]


def hex_lines(values: list[int], width_bits: int, total: int) -> str:
    digits = width_bits // 4
    padded = values + [0] * (total - len(values))
    if len(padded) > total:
        raise SystemExit(f"image overflow: {len(values)} words exceed {total}")
    return "".join(f"{value:0{digits}x}\n" for value in padded)


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    _install_engine_stubs()
    capability = rtl_capability()

    cases: list[Case] = [
        case_linear(capability),
        case_constant_loop(capability),
        case_nested_loops(capability),
        case_symbol_loop(capability),
        case_work_bound_deficit(capability),
        case_zero_trip(capability),
        case_predicate_prefill(capability),
        case_predicate_decode(capability),
        case_branch(capability),
        case_state_discard(capability),
        case_observation(capability),
        case_events(capability),
        case_mixed(capability),
    ]
    positives = len(cases)
    cases.extend(negative_instruction_cases(capability))
    cases.append(case_branch_out_of_range(capability))
    cases.append(case_loop_over_maximum(capability))
    cases.append(case_trap_mid_transaction(capability))
    cases.append(case_commit_without_prepare(capability))
    cases.append(case_wait_unsignalled(capability))
    cases.append(case_work_bound(capability))
    cases.extend(header_cases(capability))

    program_words: list[int] = []
    header_words: list[int] = []
    desc_words: list[int] = []
    symbol_words: list[int] = []
    case_words: list[int] = []
    issue_words: list[int] = []
    records: list[dict[str, Any]] = []

    for case in cases:
        image = case.deployment.program
        header_blob = image[:256]
        body = image[256:]
        if case.corrupt is not None:
            image = case.corrupt(image)
            body = image[256:]
        if case.corrupt_header is not None:
            image = case.corrupt_header(image)
            header_blob = image[:256]

        report = verify_deployment(case.deployment, capability)
        if report.admitted != case.expect_admitted:
            raise SystemExit(
                f"{case.name}: verifier admitted={report.admitted}, expected "
                f"{case.expect_admitted}: {report.errors}"
            )

        python_rejects = None
        if case.corrupt is not None or case.corrupt_header is not None:
            try:
                split_program(image)
                decode_body(image[256:])
                python_rejects = ""
            except Exception as exc:  # the normative decoder must fail closed
                python_rejects = f"{type(exc).__name__}: {exc}"
            if not python_rejects:
                raise SystemExit(f"{case.name}: corrupted image was accepted")

        if case.device_runs:
            golden = run_golden(case, capability)
        else:
            golden = dict(IDLE_OBSERVATION)
            golden.update(case.reference)
            golden.setdefault("status", 1)
            golden.setdefault("message", "not executable by the golden model")
            golden.setdefault("counters", {})

        expectation = dict(golden)
        for key, value in case.reference.items():
            expectation[key] = value

        # One 256-bit word per 32-byte instruction record.
        program_base = len(program_words)
        for offset in range(0, len(body), 32):
            program_words.append(int.from_bytes(body[offset : offset + 32], "little"))
        header_base = len(header_words)
        header_words.extend(le_words(header_blob))

        desc_base = len(desc_words)
        table = case.deployment.table
        for index in range(len(table)):
            record = table._records[index]  # noqa: SLF001
            prefix = record[:DESCRIPTOR_PREFIX_BYTES]
            prefix = prefix + bytes(DESCRIPTOR_PREFIX_BYTES - len(prefix))
            desc_words.append(int.from_bytes(prefix, "little"))

        symbols = effective_symbols(case)
        symbol_base = len(symbol_words)
        mask = 0
        for index in range(SYMBOL_STRIDE):
            value = symbols.get(index)
            symbol_words.append(0 if value is None else int(value) & 0xFFFFFFFF)
            if value is not None:
                mask |= 1 << index

        issue_base = len(issue_words) // 2
        for issue in expectation["issues"]:
            issue_words.append((issue["family"] << 8) | issue["sub"])
            issue_words.append(issue["descriptor_id"] & 0xFFFFFFFF)

        entry = next(
            e for e in case.deployment.entrypoints
            if e["entrypoint_id"] == case.entrypoint_id
        )
        header = case.deployment.program[:256]
        instruction_count = int.from_bytes(header[16:20], "little")
        entrypoint_count = int.from_bytes(header[20:24], "little")
        work = int.from_bytes(header[184:192], "little")

        flags = 0
        if case.expect_header_legal:
            flags |= 1
        if case.run_program:
            flags |= 2
        if expectation.get("complete"):
            flags |= 4

        header_declared_count = int.from_bytes(header_blob[16:20], "little")
        header_declared_entries = int.from_bytes(header_blob[20:24], "little")

        words = [
            program_base,
            instruction_count,
            desc_base,
            len(table),
            symbol_base,
            mask,
            header_base,
            int(entry["first_instruction"]),
            work & 0xFFFFFFFF,
            (work >> 32) & 0xFFFFFFFF,
            flags,
            int(case.expect_header_trap),
            header_declared_count if case.expect_header_legal else 0,
            header_declared_entries if case.expect_header_legal else 0,
            int(expectation["trap_class"]),
            int(expectation["first_fault"]) & 0xFFFFFFFF,
            int(expectation["fetched"]),
            int(expectation["retired"]),
            int(expectation["predicated_off"]),
            int(expectation["issued"]),
            int(expectation["loop_iterations"]),
            int(expectation["branches"]),
            int(expectation["wait_events"]),
            int(expectation["state_prepares"]),
            int(expectation["state_commits"]),
            int(expectation["state_discards"]),
            int(expectation["state_reads"]),
            int(expectation["state_generation_advances"]),
            int(expectation["state_commits_applied"]),
            int(expectation["state_rows_committed"]),
            issue_base,
            len(expectation["issues"]),
        ]
        if len(words) != CASE_STRIDE:
            raise SystemExit(f"case record is {len(words)} words, expected {CASE_STRIDE}")
        case_words.extend(words)

        records.append({
            "name": case.name,
            "note": case.note,
            "entrypoint_id": case.entrypoint_id,
            "phase": int(entry["phase"]),
            "symbols": {str(k): int(v) for k, v in sorted(symbols.items())},
            "instruction_count": instruction_count,
            "descriptor_count": len(table),
            "declared_retired_work": work,
            "admitted": report.admitted,
            "verifier_errors": list(report.errors),
            "python_rejects_image": python_rejects,
            "device_executed": case.device_runs,
            "program_sha256": hashlib.sha256(image).hexdigest(),
            "descriptor_table_sha256": hashlib.sha256(table.encode()).hexdigest(),
            "golden": {
                key: value for key, value in sorted(golden.items())
                if key not in {"issues", "counters"}
            },
            "golden_counters": golden.get("counters", {}),
            "expected": {
                key: value for key, value in sorted(expectation.items())
                if key not in {"issues", "counters", "message"}
            },
            "expected_issues": expectation["issues"],
            "expected_header_legal": case.expect_header_legal,
            "expected_header_trap_class": int(case.expect_header_trap),
        })

    total_issues = sum(len(r["expected_issues"]) for r in records)
    meta = [len(cases), total_issues, positives, len(cases) - positives, 0, 0, 0, 0]

    files = {
        "a3_program.hex": hex_lines(program_words, 256, PROGRAM_WORDS),
        "a3_header.hex": hex_lines(header_words, 32, HEADER_WORDS),
        "a3_descriptor.hex": hex_lines(desc_words, 1024, DESC_WORDS),
        "a3_symbol.hex": hex_lines(symbol_words, 32, SYMBOL_WORDS),
        "a3_case.hex": hex_lines(case_words, 32, CASE_WORDS),
        "a3_issue.hex": hex_lines(issue_words, 32, ISSUE_WORDS),
        "a3_meta.hex": hex_lines(meta, 32, META_WORDS),
    }
    for name, payload in files.items():
        (out / name).write_text(payload, encoding="ascii")

    summary = {
        "schema": "opentallas.rtl.abi3_vectors.v1",
        "abi": {"major": 3, "minor": 0},
        "capability_digest": capability.digest,
        "case_count": len(cases),
        "positive_case_count": positives,
        "negative_case_count": len(cases) - positives,
        "issue_event_count": total_issues,
        "geometry": {
            "program_words": PROGRAM_WORDS,
            "header_words": HEADER_WORDS,
            "descriptor_words": DESC_WORDS,
            "symbol_words": SYMBOL_WORDS,
            "case_words": CASE_WORDS,
            "issue_words": ISSUE_WORDS,
            "case_stride": CASE_STRIDE,
            "descriptor_prefix_bytes": DESCRIPTOR_PREFIX_BYTES,
        },
        "image_sha256": {
            name: hashlib.sha256(payload.encode("ascii")).hexdigest()
            for name, payload in sorted(files.items())
        },
        "cases": records,
    }
    (out / "abi3_rtl_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"abi3 rtl vectors: cases={len(cases)} positive={positives} "
        f"negative={len(cases) - positives} issues={total_issues}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
