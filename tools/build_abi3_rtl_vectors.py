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

*Resolved operand views* are the one thing beyond the raw issue that the RTL
must reproduce, because amendments A4 and A13 make a view's element offset and
its leading extent functions of the loop and symbol bindings live at the
dispatch.  The golden value is not written here: for every issue the generator
calls ``runtime.sim.memory.ViewResolver.resolve`` -- the *same* resolver the
functional device uses -- with the loop bindings the device recorded in its own
trace at that instruction.  A hand-computed extent would prove only that this
file and the RTL agree with each other.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field as dc_field
import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Control,
    DType,
    Dma,
    Feature,
    Link,
    Major,
    NO_ID,
    Observation,
    ParticipantScope,
    Permission,
    Recovery,
    Reduction,
    Route,
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
from runtime.abi3.builder import DeploymentBuilder, DynamicTerm  # noqa: E402
from runtime.abi3.crc import record_crc, sha256  # noqa: E402
from runtime.abi3.deployment import Deployment, ObjectSource  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    CollectiveOp,
    Comparison,
    ExtendedDescriptorType,
    Phase,
    PredicateKind,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import Instruction, decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import (  # noqa: E402
    _FAMILY_DESCRIPTOR as FAMILY_DESCRIPTOR,
    verify_deployment,
)
from runtime.sim import engine as engine_module  # noqa: E402
from runtime.sim.device import Device  # noqa: E402

OUTPUT_DIR = ROOT / "testdata/compiler/abi3"

# RTL memory geometry.  The images are padded to these sizes so that both
# simulators read a fully initialised memory.
PROGRAM_WORDS = 2048      # 256-bit instruction records
HEADER_WORDS = 4096       # 32-bit words, 64 per case
DESC_WORDS = 2048         # 1536-bit descriptor prefixes
SYMBOL_WORDS = 1024       # 32-bit words, 16 per case
CASE_WORDS = 2048         # 32-bit words, CASE_STRIDE per case
ISSUE_WORDS = 2048        # 32-bit words, 2 per issue
VIEW_WORDS = 8192         # 32-bit words, VIEW_STRIDE per resolved view
META_WORDS = 8

CASE_STRIDE = 35
SYMBOL_STRIDE = 16
HEADER_STRIDE = 64
VIEW_STRIDE = 6

# Header (64) plus *both* 64-byte payload blocks.  A TENSOR_VIEW payload is 128
# bytes and its amendment-A4 dynamic terms begin at payload offset 72, so a
# 128-byte record prefix stops one block short of what view resolution needs.
DESCRIPTOR_PREFIX_BYTES = 192

# OPERATOR operand slots, in the order both the golden model and the RTL walk
# them (runtime/abi3/descriptors.OPERATOR_PAYLOAD).
OPERAND_FIELDS = (
    "input_view_0",
    "input_view_1",
    "input_view_2",
    "input_view_3",
    "output_view_0",
    "output_view_1",
)

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
    "views": [],
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
    """Force every dispatchable engine operation to a recording no-op.

    RTL 3.0 implements the control plane; engine datapaths are a separate
    deliverable.  A comparison against a golden model that *does* compute would
    not be well posed: a data-dependent engine fault would trap the reference on
    a program the RTL can only run to completion.  Every dispatchable
    ``(family, subopcode)`` is therefore bound to a no-op here, so the two sides
    differ in nothing but the datapath that neither is exercising.

    ``runtime.sim.engine.register`` is the public path but refuses to replace an
    existing implementation, so the binding is written directly.  The result is
    independent of whether the engine package has been imported: the vector set
    is identical either way, which is the property that keeps it reproducible.
    """
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

    def _noop(ctx, sub, descriptor):  # noqa: ANN001 - engine handler signature
        return None

    for family in dispatchable:
        for member in SUBOPCODES[family]:
            engine_module._REGISTRY[(int(family), int(member))] = _noop  # noqa: SLF001


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
        # One SCHEDULE per engine family.  The verifier's schedule-completeness
        # proof requires an operator's schedule to name that operator's own
        # family, so a single shared descriptor is not admissible.
        self.schedules: dict[int, int] = {}
        self.schedule = self.schedule_for(Major.TENSOR)
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

    def schedule_for(self, family: Major) -> int:
        """The SCHEDULE descriptor for one engine family, created on demand."""
        existing = self.schedules.get(int(family))
        if existing is not None:
            return existing
        sid = self.builder.schedule(
            engine_family=family,
            tile_rows=ROWS,
            tile_cols=COLS,
            tile_depth=COLS,
            key=f"sched.{family.name.lower()}",
        )
        self.schedules[int(family)] = sid
        return sid

    def op(self, family: Major, sub: int, *, key: str) -> int:
        """One OPERATOR descriptor reading view.in and writing view.out."""
        return self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=[self.view_in, self.view_weights],
            outputs=[self.view_out],
            numeric_profile_id=self.numeric,
            schedule_id=self.schedule_for(family),
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
    """Three nested loops running to completion under the *derived* work bound.

    This case was written when DeploymentBuilder._proved_work and
    Verifier._verify_control_flow both skipped ``work += multiplier`` for
    CONTROL.LOOP_SETUP: the proved bound omitted one retire per loop entry, and
    with nesting the deficit was large enough that the device's own retired-work
    check fired on a program the verifier had admitted.  Both now count the
    LOOP_SETUP retire, so the derived bound is sound and the program completes.
    The case is kept because a deep nest exercising the derived bound at its
    edge is worth pinning either way; the work-bound *trap* is covered by
    ``case_work_bound``.
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
            "three nested loops under the derived work bound, which now counts "
            "the LOOP_SETUP retire the earlier proof omitted"
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


# ---------------------------------------------------------------------------
# Amendment A13 - the partial final iteration of a block loop
# ---------------------------------------------------------------------------
# One block loop over a symbolic token extent, with the operand views indexed by
# its induction variable.  ``A13_BLOCK`` is the tile height T and the request's
# SPAN_TOKENS is N, so the loop runs ceil(N/T) times and the last iteration
# holds N - T*floor(N/T) rows.  ``A13_MAX_ITER`` bounds the object the verifier
# has to prove in range.
#
# A13 applies to a term only when that term walks the view's *leading* axis, and
# section 12.4 derives which terms those are rather than assuming it: one
# iteration advances by one whole block of leading rows, so
# ``term_stride == stride0 * bound_divisor``.  Every view built here that means
# to be clamped therefore states its loop's stride as
# ``bound_divisor * A13_ROW_ELEMENTS``, which is exactly ``stride0 * divisor``
# for a row-major ``[rows, A13_ROW_ELEMENTS]`` view.  ``A13_WIDE_BLOCK`` gives a
# second, different block so that a view indexed by two block loops must
# evaluate the condition against each loop's own divisor rather than one of
# them twice.  ``case_a13_non_leading_axis`` and ``case_a13_mixed_axes`` are the
# other side of the same rule.
A13_BLOCK = 4
A13_WIDE_BLOCK = 2 * A13_BLOCK
A13_MAX_ITER = 4
A13_ROW_ELEMENTS = COLS


class BlockWorkspace(Workspace):
    """A workspace with a token buffer big enough for a whole blocked span."""

    def __init__(self, name: str, capability: Capability) -> None:
        super().__init__(name, capability)
        # Room for an input and an output window, with headroom for a
        # leading extent wider than the block.
        size = A13_MAX_ITER * A13_BLOCK * A13_ROW_ELEMENTS * 2 * 8
        self.tokens = self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=size,
            source=ObjectSource.zeros(size),
            permissions=int(Permission.READ | Permission.WRITE),
            key="obj.tokens",
        )
        self.token_out_offset = A13_MAX_ITER * A13_BLOCK * A13_ROW_ELEMENTS

    def block_views(
        self,
        *,
        loop_ids: Sequence[int],
        strides: Sequence[int],
        dim0: int = A13_BLOCK,
        extra: Sequence[DynamicTerm] = (),
    ) -> tuple[int, int]:
        """An input and an output view indexed by the given block loops."""
        terms = [
            DynamicTerm.loop(loop_id, stride)
            for loop_id, stride in zip(loop_ids, strides)
        ] + list(extra)
        view_in = self.builder.tensor_view(
            object_id=self.tokens,
            dtype=DType.BF16,
            dims=[dim0, A13_ROW_ELEMENTS],
            dynamic=terms,
            key="view.block.in",
        )
        view_out = self.builder.tensor_view(
            object_id=self.tokens,
            dtype=DType.BF16,
            dims=[dim0, A13_ROW_ELEMENTS],
            element_offset=self.token_out_offset,
            dynamic=terms,
            permissions=int(Permission.READ | Permission.WRITE),
            key="view.block.out",
        )
        return view_in, view_out

    def block_operator(self, view_in: int, view_out: int, *, key: str) -> int:
        return self.builder.operator(
            engine_family=Major.TENSOR,
            engine_sub=Tensor.MATMUL,
            inputs=[view_in, self.view_weights],
            outputs=[view_out],
            numeric_profile_id=self.numeric,
            schedule_id=self.schedule,
            counter_class_id=self.counters,
            source_kernel_id=0,
            key=key,
        )


def _a13_block_case(
    cap: Capability,
    name: str,
    *,
    span: int,
    dim0: int = A13_BLOCK,
    divisor: int = A13_BLOCK,
    expect_admitted: bool = True,
    note: str,
) -> Case:
    """A block loop over SPAN_TOKENS with loop-indexed operand views."""
    w = BlockWorkspace(f"a3-{name}", cap)
    b = w.builder
    loop = b.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        bound_symbol=Symbol.SPAN_TOKENS,
        bound_divisor=divisor,
        max_iterations=A13_MAX_ITER,
        key="loop.block",
    )
    view_in, view_out = w.block_views(
        loop_ids=[loop],
        strides=[A13_BLOCK * A13_ROW_ELEMENTS],
        dim0=dim0,
    )
    op = w.block_operator(view_in, view_out, key="op.block")
    tail = w.op(Major.VECTOR, Vector.ADD, key="op.tail")
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    # A tail dispatch outside the loop: a case with zero iterations still has to
    # prove that it ran, rather than passing because nothing was compared.
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=tail, source_operation_id=1)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name=name,
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): span},
        expect_admitted=expect_admitted,
        run_program=expect_admitted,
        device_runs=expect_admitted,
        note=note,
    )


def case_a13_block_exact(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_block_exact", span=2 * A13_BLOCK,
        note="N divisible by T: every iteration is full and A13 must not clamp",
    )


def case_a13_block_partial(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_block_partial", span=2 * A13_BLOCK + 1,
        note="N = 9, T = 4: three iterations, the last holding one row",
    )


def case_a13_block_partial_mid(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_block_partial_mid", span=A13_BLOCK + 3,
        note="N = 7, T = 4: two iterations, the last holding three rows",
    )


def case_a13_block_short(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_block_short", span=A13_BLOCK - 1,
        note="N < T: one short iteration holding the whole span",
    )


def case_a13_block_empty(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_block_empty", span=0,
        note=(
            "N = 0: the ABI admits it as a zero-trip loop -- ceil(0/T) = 0 -- so "
            "the body never runs and no view is resolved.  The tail dispatch "
            "outside the loop keeps the case from passing vacuously"
        ),
    )


def case_a13_extent_below_block(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_extent_below_block", span=A13_BLOCK + 3, dim0=2,
        note=(
            "leading extent 2 under a block of 4: the final iteration's three "
            "remaining rows are not fewer than the extent, so dim0 is unchanged"
        ),
    )


def case_a13_extent_above_block(cap: Capability) -> Case:
    return _a13_block_case(
        cap, "a13_extent_above_block", span=A13_BLOCK + 1, dim0=A13_BLOCK + 2,
        expect_admitted=False,
        note=(
            "leading extent 6 over a block of 4: refused at admission.  This is "
            "the one shape on which wire format 12.4's formula and "
            "ViewResolver._remaining_rows disagree -- the prose compares "
            "remaining against dim0 alone and gives 5, the resolver bounds the "
            "clamp by bound_divisor and leaves 6.  Checked exhaustively over "
            "divisors 1-8, extents 1-11, bounds 0-19 and iterations 0-5, every "
            "one of the 1,027 disagreements has dim0 > bound_divisor and none "
            "is without it, so refusing that inequality makes the two "
            "statements of A13 the same rule.  The program is malformed "
            "independently of the clamp: iteration i covers bound_divisor rows, "
            "and a view indexed by the loop claiming more is claiming the next "
            "iteration's rows"
        ),
    )


def case_a13_symbol_term(cap: Capability) -> Case:
    """A4 without A13: a RUNTIME_SYMBOL term moves the window, nothing clamps."""
    w = BlockWorkspace("a3-a13-symbol", cap)
    b = w.builder
    view_in, view_out = w.block_views(
        loop_ids=[],
        strides=[],
        extra=[DynamicTerm.symbol(Symbol.GENERATION_INDEX, A13_ROW_ELEMENTS)],
    )
    op = w.block_operator(view_in, view_out, key="op.block")
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=op, source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="a13_symbol_term",
        deployment=w.finish(),
        symbols={int(Symbol.GENERATION_INDEX): 3},
        note="a symbol-indexed view: the offset moves, the extent does not",
    )


def case_a13_constant_loop(cap: Capability) -> Case:
    """A constant-bounded loop never has a partial iteration to state."""
    w = BlockWorkspace("a3-a13-constant", cap)
    b = w.builder
    loop = b.loop_control(
        lower_bound=0, upper_bound=3, step=1, key="loop.constant"
    )
    view_in, view_out = w.block_views(
        loop_ids=[loop], strides=[A13_BLOCK * A13_ROW_ELEMENTS]
    )
    op = w.block_operator(view_in, view_out, key="op.block")
    b.open_loop(loop)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a13_constant_loop",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 5},
        note=(
            "a constant-bounded loop: bound_selector_kind is not RUNTIME_SYMBOL, "
            "so no iteration is partial and the extent is never clamped"
        ),
    )


def case_a13_nested_blocks(cap: Capability) -> Case:
    """Two symbol-bounded block loops index one view: the smaller bound wins.

    Both loops have to *walk the leading axis* for the fold to be reachable at
    all, and section 12.4 makes that a property of the arithmetic: a term walks
    the leading axis exactly when one iteration advances by one whole block of
    it, ``term_stride == stride0 * bound_divisor``.  The two loops here use
    different blocks -- ``A13_BLOCK`` over SPAN_TOKENS and ``A13_WIDE_BLOCK``
    over CONTEXT_LENGTH -- and each states the stride its own block implies, so
    the condition has to be evaluated against each loop's own divisor: reusing
    one loop's divisor for both terms admits one of them wrongly.

    The case was written with the inner loop stepping a single row, which under
    the assumed rule still folded because *any* loop-induction term folded.
    Under the derived rule that stride walks the second axis, not the leading
    one, so the inner loop stopped contributing and the fold stopped happening:
    the case no longer tested what it was written to test.  The repair is the
    inner loop's block and stride, not the expectation -- the extents below are
    the ones the reference resolver produced before the refinement and produces
    again after it.
    """
    w = BlockWorkspace("a3-a13-nested", cap)
    b = w.builder
    outer = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.SPAN_TOKENS, bound_divisor=A13_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.outer",
    )
    inner = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.CONTEXT_LENGTH, bound_divisor=A13_WIDE_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.inner",
    )
    view_in, view_out = w.block_views(
        loop_ids=[outer, inner],
        strides=[
            A13_BLOCK * A13_ROW_ELEMENTS,
            A13_WIDE_BLOCK * A13_ROW_ELEMENTS,
        ],
    )
    op = w.block_operator(view_in, view_out, key="op.block")
    b.open_loop(outer)
    b.open_loop(inner)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a13_nested_blocks",
        deployment=w.finish(),
        symbols={
            int(Symbol.SPAN_TOKENS): 2 * A13_BLOCK + 1,
            int(Symbol.CONTEXT_LENGTH): A13_WIDE_BLOCK + 2,
        },
        note=(
            "two symbol-bounded loops walk one view's leading axis with "
            "different blocks -- 4 rows over SPAN_TOKENS = 9, 8 rows over "
            "CONTEXT_LENGTH = 10 -- so each term satisfies "
            "term_stride = stride0 * bound_divisor for its own divisor.  "
            "_remaining_rows folds them with min(): the outer loop's last "
            "iteration (one row) wins over the inner loop's (two rows)"
        ),
    )


def case_a13_four_terms(cap: Capability) -> Case:
    """A view carrying the maximum four dynamic terms, two of them block loops.

    MAX_DYNAMIC_TERMS is the boundary where a term walk that counts to the term
    count inclusive can wrap back onto term zero, so it is worth a vector of
    its own rather than being left to the two- and one-term cases.

    Both block loops state the stride their block implies -- one whole block of
    leading rows, ``stride0 * bound_divisor`` -- so both walk the leading axis
    and both fold, which is what this case says it exercises.  The inner loop
    previously stepped a single row and folded only because the assumed rule
    folded every loop-induction term; under the derived rule of section 12.4
    that is a walk along the second axis and it would silently stop
    contributing.
    """
    w = BlockWorkspace("a3-a13-four-terms", cap)
    b = w.builder
    outer = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.SPAN_TOKENS, bound_divisor=A13_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.outer",
    )
    inner = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.CONTEXT_LENGTH, bound_divisor=A13_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.inner",
    )
    view_in, view_out = w.block_views(
        loop_ids=[outer, inner],
        strides=[
            A13_BLOCK * A13_ROW_ELEMENTS,
            A13_BLOCK * A13_ROW_ELEMENTS,
        ],
        extra=[
            DynamicTerm.symbol(Symbol.GENERATION_INDEX, 1),
            DynamicTerm.symbol(Symbol.BATCH, 1),
        ],
    )
    op = w.block_operator(view_in, view_out, key="op.block")
    b.open_loop(outer)
    b.open_loop(inner)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return Case(
        name="a13_four_terms",
        deployment=w.finish(),
        symbols={
            int(Symbol.SPAN_TOKENS): A13_BLOCK + 1,
            int(Symbol.CONTEXT_LENGTH): A13_BLOCK + 2,
            int(Symbol.GENERATION_INDEX): 2,
            int(Symbol.BATCH): 1,
        },
        note=(
            "four dynamic terms, the A4 maximum: two symbol-bounded block "
            "loops that both walk the leading axis and are folded by min(), "
            "and two runtime symbols that move the offset without bounding "
            "the extent"
        ),
    )


# ---------------------------------------------------------------------------
# A13 and the axis a loop actually walks
# ---------------------------------------------------------------------------
# The other side of section 12.4's derived condition.  A13 clamps the leading
# extent because a block loop's final iteration holds fewer rows than the
# block; that is only a statement about the leading axis, and a view may
# perfectly well be indexed by a loop along some other one.  The DeepSeek mHC
# branch reduction is the shape that forced this to be derived rather than
# assumed: its leading axis is the four hyper-connection streams while its loop
# steps over tokens, so its term stride is one token block's rows rather than
# one whole block of the leading axis.  Clamping it would present four streams
# as one, and the admission rule -- which refuses dim0 > bound_divisor for a
# clamped term -- would have refused the deployment outright.
MHC_STREAMS = 4
MHC_TOKEN_BLOCK = 2
MHC_TOKENS = A13_MAX_ITER * MHC_TOKEN_BLOCK
MHC_STREAM_PLANE = MHC_TOKENS * A13_ROW_ELEMENTS


def case_a13_non_leading_axis(cap: Capability) -> Case:
    """A block loop over an axis that is not the view's leading one.

    The view is ``[4 streams, 2 tokens, 16 elements]`` over a buffer laid out
    stream-major, so ``stride0`` is one stream's whole token plane.  The loop
    blocks the *token* axis by ``MHC_TOKEN_BLOCK``, so its term stride is one
    token block's rows -- ``MHC_TOKEN_BLOCK * A13_ROW_ELEMENTS``, far short of
    ``stride0 * bound_divisor``.  The term therefore does not walk the leading
    axis and A13 does not reach it: the resolved leading extent stays at four
    streams on every iteration, including the final partial one, where
    SPAN_TOKENS = 7 over a block of 2 leaves one token.

    The case pins both halves of the refinement at once, because its leading
    extent of 4 exceeds its block of 2.  Under the assumed rule the admission
    check would have refused this deployment -- a leading extent above the
    block -- and the resolver would have clamped four streams down to one.
    Under the derived rule the deployment is admitted and nothing is clamped,
    which is the framing the operator actually needs.
    """
    w = BlockWorkspace("a3-a13-mhc", cap)
    b = w.builder
    buffer_elements = MHC_STREAMS * MHC_STREAM_PLANE
    size = buffer_elements * 2 * 2  # an input and an output buffer, bf16
    branches = b.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=size,
        source=ObjectSource.zeros(size),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.branches",
    )
    loop = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.SPAN_TOKENS, bound_divisor=MHC_TOKEN_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.tokens",
    )
    dims = [MHC_STREAMS, MHC_TOKEN_BLOCK, A13_ROW_ELEMENTS]
    strides = [MHC_STREAM_PLANE, A13_ROW_ELEMENTS, 1]
    terms = [DynamicTerm.loop(loop, MHC_TOKEN_BLOCK * A13_ROW_ELEMENTS)]
    view_in = b.tensor_view(
        object_id=branches,
        dtype=DType.BF16,
        dims=dims,
        strides=strides,
        dynamic=terms,
        key="view.mhc.in",
    )
    view_out = b.tensor_view(
        object_id=branches,
        dtype=DType.BF16,
        dims=dims,
        strides=strides,
        element_offset=buffer_elements,
        dynamic=terms,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.mhc.out",
    )
    op = b.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.MHC,
        inputs=[view_in],
        outputs=[view_out],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.VECTOR),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.mhc",
    )
    tail = w.op(Major.VECTOR, Vector.ADD, key="op.tail")
    b.open_loop(loop)
    b.emit(Major.VECTOR, Vector.MHC, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    b.emit(Major.VECTOR, Vector.ADD, descriptor_id=tail, source_operation_id=1)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a13_non_leading_axis",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): MHC_TOKENS - 1},
        note=(
            "the mHC branch reduction: the leading axis is four "
            "hyper-connection streams and the loop steps over tokens, so the "
            "term stride is one token block's rows and not stride0 * "
            "bound_divisor.  A13 does not apply -- the extent stays at four "
            "streams through the final partial iteration -- and the "
            "admission rule does not apply either, so a leading extent above "
            "the block is admitted here rather than refused"
        ),
    )


def case_a13_mixed_axes(cap: Capability) -> Case:
    """One view, two block loops, and only one of them walks the leading axis.

    Section 12.4 decides the question per *term*, not per view: the token loop
    steps by one whole block of leading rows and clamps, while the expert loop
    steps two streams within a row and does not, even though both are
    symbol-bounded and both have a partial final iteration.  A resolver that
    decided once for the whole view -- from the first term, or from any term --
    would clamp the expert loop's two-stream slice down to one row and be wrong
    on four of this case's six dispatches.
    """
    w = BlockWorkspace("a3-a13-mixed", cap)
    b = w.builder
    token_stride = MHC_STREAMS * A13_ROW_ELEMENTS   # one token, all streams
    expert_block = 2
    buffer_elements = A13_MAX_ITER * A13_BLOCK * token_stride
    size = buffer_elements * 2 * 2
    obj = b.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=size,
        source=ObjectSource.zeros(size),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.mixed",
    )
    tokens = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.SPAN_TOKENS, bound_divisor=A13_BLOCK,
        max_iterations=A13_MAX_ITER, key="loop.tokens",
    )
    experts = b.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.ACTIVE_EXPERT_COUNT, bound_divisor=expert_block,
        max_iterations=expert_block, key="loop.experts",
    )
    dims = [A13_BLOCK, expert_block, A13_ROW_ELEMENTS]
    strides = [token_stride, A13_ROW_ELEMENTS, 1]
    terms = [
        # stride0 * bound_divisor: one whole block of leading rows.  Clamps.
        DynamicTerm.loop(tokens, A13_BLOCK * token_stride),
        # two streams inside one row: not the leading axis.  Does not clamp.
        DynamicTerm.loop(experts, expert_block * A13_ROW_ELEMENTS),
    ]
    view_in = b.tensor_view(
        object_id=obj,
        dtype=DType.BF16,
        dims=dims,
        strides=strides,
        dynamic=terms,
        key="view.mixed.in",
    )
    view_out = b.tensor_view(
        object_id=obj,
        dtype=DType.BF16,
        dims=dims,
        strides=strides,
        element_offset=buffer_elements,
        dynamic=terms,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.mixed.out",
    )
    op = b.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.MHC,
        inputs=[view_in],
        outputs=[view_out],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.VECTOR),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.mixed",
    )
    b.open_loop(tokens)
    b.open_loop(experts)
    b.emit(Major.VECTOR, Vector.MHC, descriptor_id=op, source_operation_id=0)
    b.close_loop()
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a13_mixed_axes",
        deployment=w.finish(),
        symbols={
            int(Symbol.SPAN_TOKENS): 2 * A13_BLOCK + 1,
            int(Symbol.ACTIVE_EXPERT_COUNT): 2 * expert_block - 1,
        },
        note=(
            "one view indexed by two symbol-bounded block loops, both with a "
            "partial final iteration, of which only the token loop walks the "
            "leading axis: the expert loop steps two streams inside a row, so "
            "its partial iteration bounds nothing.  The clamp is a per-term "
            "decision and this is the vector that says so"
        ),
    )


# ---------------------------------------------------------------------------
# Amendment A14 - the scope of a collective's participants
# ---------------------------------------------------------------------------
# Wire format section 12.5 gives COMMUNICATION a ``participant_scope`` at
# payload offset 80, one byte, NODE = 0 / RETICLE = 1 / TILE = 2, taken out of a
# span that was reserved-zero before the amendment.  Nothing in the RTL reads
# it: a LINK instruction's whole admission in ot_a3_microsequencer.sv is the
# S_ENG_WAIT type check ``desc_type != expected_type`` against
# ``a3_family_descriptor_type(A3_MAJOR_LINK) = A3_DESC_COMMUNICATION``, after
# which the record goes straight to S_ISSUE and the payload is the fabric
# engine's business.  That is a claim about the RTL, and until these cases
# existed the vector set could not test it, because it issued no LINK at all.
#
# So the pair below emits the *same* LINK program twice -- once with the
# pre-amendment encoding (NODE, byte 80 zero) and once with the two scopes the
# amendment adds (RETICLE and TILE, byte 80 nonzero) -- and both must produce
# the identical issue sequence.  A resolver or decoder that had folded that byte
# into anything would separate them.  The descriptor image the simulators load
# is 192 bytes per record, so payload offset 80 is really in the memory both
# read; it is not elided by the prefix.
A14_RETICLES = 4
A14_TILES_PER_RETICLE = 8
A14_LINK_BYTES = 256
A14_LINK_EXTENT = 64


def _a14_link_object(builder: DeploymentBuilder) -> int:
    """A remote-addressable buffer for a collective to name."""
    return builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=A14_LINK_BYTES,
        source=ObjectSource.zeros(A14_LINK_BYTES),
        permissions=int(
            Permission.READ | Permission.WRITE | Permission.REMOTE
        ),
        key="obj.link",
    )


def _a14_link_program(b: DeploymentBuilder, collective: int, barrier: int,
                      matmul: int) -> None:
    """One collective, one compute dispatch, one barrier, in that order."""
    b.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=collective,
           source_operation_id=0)
    b.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul,
           source_operation_id=1)
    b.emit(Major.LINK, Link.BARRIER, descriptor_id=barrier,
           source_operation_id=2)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)


def case_a14_link_node_scope(cap: Capability) -> Case:
    """A collective over nodes: the encoding every pre-A14 program carries."""
    w = Workspace("a3-a14-node", cap)
    b = w.builder
    buf = _a14_link_object(b)
    collective = b.communication(
        collective_op=CollectiveOp.ALL_GATHER,
        local_object_id=buf,
        remote_object_id=buf,
        byte_extent=A14_LINK_EXTENT,
        participant_count=2,
        participant_scope=ParticipantScope.NODE,
        key="comm.collective",
    )
    barrier = b.communication(
        collective_op=CollectiveOp.POINT_TO_POINT,
        local_object_id=buf,
        remote_object_id=buf,
        byte_extent=A14_LINK_EXTENT,
        participant_count=2,
        participant_scope=ParticipantScope.NODE,
        key="comm.barrier",
    )
    matmul = w.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    _a14_link_program(b, collective, barrier, matmul)
    return Case(
        name="a14_link_node_scope",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        note=(
            "the first LINK instructions in the vector set: a collective and a "
            "barrier naming COMMUNICATION descriptors whose participant_scope "
            "is NODE, which is byte 80 = 0 and therefore byte-identical to the "
            "same program written before A14 existed.  It fixes the RTL's LINK "
            "admission -- the family-to-descriptor-type check -- and it is the "
            "control against which a14_link_wafer_scopes is read"
        ),
    )


def case_a14_link_wafer_scopes(cap: Capability) -> Case:
    """The same program on a wafer, scoped to reticles and to tiles.

    A ``WAFER_LOGICAL_DEVICE`` is presented to the host as one device, so it
    declares one node; before A14 every collective on it was a collective over
    a single participant and the fabric refused it as degenerate.  Here the
    collective is TILE-scoped over ``reticle_count * tiles_per_reticle`` = 32
    participants and the barrier is RETICLE-scoped over four, so byte 80 holds
    2 and 1 rather than 0.

    The instruction stream is character-for-character the one
    ``a14_link_node_scope`` emits.  Both cases must therefore record the same
    issue sequence, which is the whole claim: the scope byte reaches the
    fabric, not the microsequencer.
    """
    b = DeploymentBuilder(
        target_id="a3-a14-wafer",
        model_id="abi3-rtl3",
        backend="rtl3",
        capability=cap,
        # The deployment's own class, not the capability's.  Section 12.5's
        # admission rules read the TOPOLOGY descriptor the deployment carries,
        # and this one carries a wafer; the capability describes the machine
        # that admits it and is not an input to those two rules.
        topology_class=int(TopologyClass.WAFER_LOGICAL_DEVICE),
    )
    b.require(Feature.BF16_TENSOR)
    b.topology(
        topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
        node_count=1,
        reticle_count=A14_RETICLES,
        tiles_per_reticle=A14_TILES_PER_RETICLE,
        hbm_bytes_per_node=cap.memory["hbm"]["bytes"],
        sram_bytes_per_node=cap.memory["sram"]["bytes"],
        key="topology",
    )
    buf = _a14_link_object(b)
    collective = b.communication(
        collective_op=CollectiveOp.ALL_GATHER,
        local_object_id=buf,
        remote_object_id=buf,
        byte_extent=A14_LINK_EXTENT,
        participant_count=A14_RETICLES * A14_TILES_PER_RETICLE,
        participant_scope=ParticipantScope.TILE,
        key="comm.collective",
    )
    barrier = b.communication(
        collective_op=CollectiveOp.POINT_TO_POINT,
        local_object_id=buf,
        remote_object_id=buf,
        byte_extent=A14_LINK_EXTENT,
        participant_count=A14_RETICLES,
        participant_scope=ParticipantScope.RETICLE,
        key="comm.barrier",
    )
    act_bytes = ROWS * COLS * 2
    activations = b.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=act_bytes * 2,
        source=ObjectSource.zeros(act_bytes * 2),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.activations",
    )
    weight_bytes = 4 * COLS * COLS * 2
    weights = b.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=weight_bytes,
        source=ObjectSource.zeros(weight_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.weights",
    )
    view_in = b.tensor_view(
        object_id=activations, dtype=DType.BF16, dims=[ROWS, COLS],
        key="view.in",
    )
    view_weights = b.tensor_view(
        object_id=weights, dtype=DType.BF16, dims=[COLS, COLS],
        key="view.weights",
    )
    view_out = b.tensor_view(
        object_id=activations, dtype=DType.BF16, dims=[ROWS, COLS],
        element_offset=ROWS * COLS,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.out",
    )
    matmul = b.operator(
        engine_family=Major.TENSOR,
        engine_sub=Tensor.MATMUL,
        inputs=[view_in, view_weights],
        outputs=[view_out],
        numeric_profile_id=b.numeric(
            contract="bf16_bf16_fp32_sequential_rne_v1",
            input_dtype=DType.BF16,
            output_dtype=DType.BF16,
            key="num.matmul",
        ),
        schedule_id=b.schedule(
            engine_family=Major.TENSOR, tile_rows=ROWS, tile_cols=COLS,
            tile_depth=COLS, key="sched.tensor",
        ),
        counter_class_id=b.counter_class(
            int(CounterGroup.TENSOR), [counter_id(CounterGroup.TENSOR, 1)],
            key="ctr.tensor",
        ),
        source_kernel_id=0,
        key="op.matmul",
    )
    _a14_link_program(b, collective, barrier, matmul)
    return Case(
        name="a14_link_wafer_scopes",
        deployment=b.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        note=(
            "the same LINK program on a WAFER_LOGICAL_DEVICE with a TILE-scoped "
            "collective over 32 participants and a RETICLE-scoped barrier over "
            "four: participant_scope holds 2 and 1 at payload offset 80, a byte "
            "that was reserved-zero before A14.  The issue sequence must match "
            "a14_link_node_scope exactly, because the RTL admits a LINK on its "
            "descriptor type and hands the payload to the fabric"
        ),
    )


def case_a14_scope_unsupported(cap: Capability) -> Case:
    """RETICLE on a single chip: refused at admission, not at the instruction.

    Section 12.5's two admission rules both fire here -- a SINGLE_CHIP topology
    admits only NODE, and this one declares no reticles for a RETICLE scope to
    address.  A deployment that cannot run its own collectives is refused before
    it is activated, so this case reaches no device and resolves no view; what
    it pins is that the refusal happens at all.
    """
    w = Workspace("a3-a14-unsupported", cap)
    b = w.builder
    buf = _a14_link_object(b)
    collective = b.communication(
        collective_op=CollectiveOp.ALL_GATHER,
        local_object_id=buf,
        remote_object_id=buf,
        byte_extent=A14_LINK_EXTENT,
        participant_count=A14_RETICLES,
        participant_scope=ParticipantScope.RETICLE,
        key="comm.collective",
    )
    b.emit(Major.LINK, Link.COLLECTIVE, descriptor_id=collective,
           source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a14_scope_unsupported",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        expect_admitted=False,
        run_program=False,
        device_runs=False,
        note=(
            "a RETICLE-scoped collective on a SINGLE_CHIP topology declaring no "
            "reticles: refused at admission by both of section 12.5's rules, "
            "so the deployment never reaches a device"
        ),
    )


# ---------------------------------------------------------------------------
# Amendment A15 - a block scale may tile two axes
# ---------------------------------------------------------------------------
# Wire format section 12.6 gives TENSOR_VIEW a ``scale_block_rows`` at payload
# offset 104, four bytes, taken out of a span that was reserved-zero before the
# amendment.  ot_a3_view_resolver.sv reads dtype at 0, rank at 1,
# dynamic_term_count at 3, element_offset at 16, dim0 at 24, stride0 at 48 and
# four eight-byte terms at 72..103; the scale binding belongs to an engine
# datapath and the block reads none of it.  Offset 104 is the first byte past
# the term array, which makes it the exact place a resolver that walked one
# term too far would land -- and the slot counter is three bits precisely so
# that a walk to ``dynamic_term_count`` inclusive cannot wrap onto term zero.
#
# So the case below puts a two-dimensional block scale on a view that A13 also
# clamps, and carries an unscaled sibling with the identical geometry in the
# next operand slot.  Both must resolve to the same extents on every iteration.
A15_SCALE_BLOCK_ELEMENTS = A13_ROW_ELEMENTS // 2
A15_SCALE_BLOCK_ROWS = 2


def _a15_case(cap: Capability, name: str, *, scale_block_rows: int,
              expect_admitted: bool, note: str) -> Case:
    w = BlockWorkspace(f"a3-{name}", cap)
    b = w.builder
    code_bytes = A13_MAX_ITER * A13_BLOCK * A13_ROW_ELEMENTS
    codes = b.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=code_bytes,
        source=ObjectSource.zeros(code_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.codes",
    )
    # One E8M0 byte per (scale_block_rows x scale_block_elements) tile, which is
    # the layout the released DeepSeek checkpoint actually ships and the reason
    # A15 exists: A8's one-dimensional rule would demand ``scale_block_rows``
    # times as many codes as the file holds.
    scale_bytes = (
        (A13_MAX_ITER * A13_BLOCK) // max(scale_block_rows, 1)
    ) * (A13_ROW_ELEMENTS // A15_SCALE_BLOCK_ELEMENTS)
    scales = b.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=max(scale_bytes, 1),
        source=ObjectSource.zeros(max(scale_bytes, 1)),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.scales",
    )
    loop = b.loop_control(
        lower_bound=0,
        upper_bound=0,
        step=1,
        bound_symbol=Symbol.SPAN_TOKENS,
        bound_divisor=A13_BLOCK,
        max_iterations=A13_MAX_ITER,
        key="loop.block",
    )
    term = DynamicTerm.loop(loop, A13_BLOCK * A13_ROW_ELEMENTS)
    view_codes = b.tensor_view(
        object_id=codes,
        dtype=DType.FP8_E4M3FN,
        dims=[A13_BLOCK, A13_ROW_ELEMENTS],
        dynamic=[term],
        scale_object_id=scales,
        scale_block_elements=A15_SCALE_BLOCK_ELEMENTS,
        scale_block_rows=scale_block_rows,
        key="view.codes",
    )
    view_plain = b.tensor_view(
        object_id=w.tokens,
        dtype=DType.BF16,
        dims=[A13_BLOCK, A13_ROW_ELEMENTS],
        dynamic=[term],
        key="view.plain",
    )
    view_out = b.tensor_view(
        object_id=w.tokens,
        dtype=DType.BF16,
        dims=[A13_BLOCK, A13_ROW_ELEMENTS],
        element_offset=w.token_out_offset,
        dynamic=[term],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.out",
    )
    convert = b.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        inputs=[view_codes, view_plain],
        outputs=[view_out],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.VECTOR),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.convert",
    )
    b.open_loop(loop)
    b.emit(Major.VECTOR, Vector.CONVERT, descriptor_id=convert,
           source_operation_id=0)
    b.close_loop()
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name=name,
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 2 * A13_BLOCK + 1},
        expect_admitted=expect_admitted,
        run_program=expect_admitted,
        device_runs=expect_admitted,
        note=note,
    )


def case_a15_block_scale_rows(cap: Capability) -> Case:
    return _a15_case(
        cap, "a15_block_scale_rows",
        scale_block_rows=A15_SCALE_BLOCK_ROWS,
        expect_admitted=True,
        note=(
            "a 2 x 8 block scale on a view A13 also clamps: scale_block_rows "
            "holds 2 at payload offset 104, the first bytes past the dynamic "
            "term array and reserved-zero before A15.  The unscaled sibling in "
            "operand slot 1 states the identical geometry, so the two must "
            "resolve to the same extents -- 4, 4, 1 over a span of nine -- on "
            "every iteration"
        ),
    )


def case_a15_scale_rows_indivisible(cap: Capability) -> Case:
    return _a15_case(
        cap, "a15_scale_rows_indivisible",
        scale_block_rows=3,
        expect_admitted=False,
        note=(
            "a three-row scale block over a four-row leading extent: section "
            "12.6 requires rows % scale_block_rows == 0 for the scale index to "
            "be exact, so the view is refused at admission rather than trapped "
            "inside an operator that has already read weights"
        ),
    )


# ---------------------------------------------------------------------------
# Amendment A16 - operand slots the conventions make load-bearing
# ---------------------------------------------------------------------------
# A16 is a statement about engine datapaths -- which rotary contract an engine
# dispatches on, what a partial dequantisation carries, where an expert sum
# joins its base -- and the ABI 3.0 microsequencer has no datapath.  What it
# does have is the operand walk, ot_a3_microsequencer.sv's S_VIEW_SCAN over
# input_view_0..3 and output_view_0..1, and A16 is the first convention that
# needs the slots past the second input and the first output.  Until these two
# cases existed every operator in the vector set named two inputs and one
# output, so three of the six arms of that walk's multiplexer were never
# populated and a view resolved through them was never compared.
A16_NARROW_ELEMENTS = COLS // 2
A16_TOPK = 4


def case_a16_convert_carried_plane(cap: Capability) -> Case:
    """Operator conventions 16.2: a partial dequantisation reads three inputs.

    DeepSeek quantises the 448 non-rotary channels of a 512-wide KV vector and
    keeps the 64 rotary channels in BF16, so reconstructing the vector reads
    codes, block scales and a carried plane, and ``in2``'s presence is what
    selects the sub-case.  ``in0``'s last axis is a proper prefix of ``out0``'s
    and the carried plane matches the destination exactly, which is the shape
    reproduced here at 8 of 16 channels.
    """
    w = Workspace("a3-a16-convert", cap)
    b = w.builder
    code_bytes = ROWS * A16_NARROW_ELEMENTS
    codes = b.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=code_bytes,
        source=ObjectSource.zeros(code_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.codes",
    )
    scale_bytes = ROWS * (A16_NARROW_ELEMENTS // A15_SCALE_BLOCK_ELEMENTS)
    scales = b.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=scale_bytes,
        source=ObjectSource.zeros(scale_bytes),
        permissions=int(Permission.READ | Permission.IMMUTABLE),
        key="obj.scales",
    )
    view_codes = b.tensor_view(
        object_id=codes,
        dtype=DType.FP8_E4M3FN,
        dims=[ROWS, A16_NARROW_ELEMENTS],
        scale_object_id=scales,
        scale_block_elements=A15_SCALE_BLOCK_ELEMENTS,
        key="view.codes",
    )
    view_scales = b.tensor_view(
        object_id=scales,
        dtype=DType.E8M0_SCALE,
        dims=[ROWS, A16_NARROW_ELEMENTS // A15_SCALE_BLOCK_ELEMENTS],
        key="view.scales",
    )
    convert = b.operator(
        engine_family=Major.VECTOR,
        engine_sub=Vector.CONVERT,
        # in0 codes, in1 block scales, in2 the carried plane; out0 the whole
        # reconstructed row.  Slot 2 is the one no operator had ever named.
        inputs=[view_codes, view_scales, w.view_in],
        outputs=[w.view_out],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.VECTOR),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.convert",
    )
    b.emit(Major.VECTOR, Vector.CONVERT, descriptor_id=convert,
           source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a16_convert_carried_plane",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        note=(
            "a partial dequantisation: codes, block scales and a carried plane "
            "in input slots 0, 1 and 2.  It is the first operator in the set "
            "to name input_view_2, so it is the first to walk that arm of the "
            "RTL's operand multiplexer and resolve a view through it"
        ),
    )


def case_a16_route_biased_topk(cap: Capability) -> Case:
    """Operator conventions 14: BIASED_TOPK writes two outputs and reads aux0.

    The ``noaux_tc`` gate selects on ``scores + bias`` and re-gathers weights
    from the unbiased scores, so the operator states two inputs, two outputs and
    ``aux0 = k``.  The second output is the last arm of the RTL's operand walk,
    and ``aux_id_0`` -- which amendment A16.1 makes load-bearing for the
    rotary width -- sits at operator payload offset 48, immediately past the
    view slots the walk reads at 24..47.
    """
    w = Workspace("a3-a16-topk", cap)
    b = w.builder
    ids_bytes = ROWS * A16_TOPK * 4
    ids = b.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=ids_bytes,
        source=ObjectSource.zeros(ids_bytes),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.ids",
    )
    weight_bytes = ROWS * A16_TOPK * 2
    weights = b.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=weight_bytes,
        source=ObjectSource.zeros(weight_bytes),
        permissions=int(Permission.READ | Permission.WRITE),
        key="obj.weights.topk",
    )
    view_ids = b.tensor_view(
        object_id=ids, dtype=DType.U32, dims=[ROWS, A16_TOPK],
        permissions=int(Permission.READ | Permission.WRITE), key="view.ids",
    )
    view_weights = b.tensor_view(
        object_id=weights, dtype=DType.BF16, dims=[ROWS, A16_TOPK],
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.topk.weights",
    )
    topk = b.operator(
        engine_family=Major.ROUTE,
        engine_sub=Route.BIASED_TOPK,
        inputs=[w.view_in, w.view_weights],
        outputs=[view_ids, view_weights],
        aux=[A16_TOPK],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.ROUTE),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.topk",
    )
    b.emit(Major.ROUTE, Route.BIASED_TOPK, descriptor_id=topk,
           source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name="a16_route_biased_topk",
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): 4},
        note=(
            "two inputs, two outputs and a populated aux_id_0: the first "
            "operator in the set to name output_view_1, and the first to put a "
            "nonzero word immediately past the view slots the RTL's operand "
            "walk reads"
        ),
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


# ---------------------------------------------------------------------------
# Amendment A17 - the join axis a concatenation names in aux_id_0
# ---------------------------------------------------------------------------
# A17 is decoded nowhere in RTL 3.0, and these cases are here to prove that
# rather than to assume it.  ``ot_a3_microsequencer.sv``'s operand walk reads
# ``op_payload[223:192]`` through ``op_payload[383:352]`` -- OPERATOR payload
# bytes 24 through 47, the four input views and the two output views -- and no
# module in ``rtl/abi3`` indexes an operator payload above bit 383.  ``aux_id_0``
# begins at byte 48, bit 384.  So a program whose only distinguishing feature is
# a non-zero ``aux_id_0`` must issue and resolve views *identically* to the same
# program without one, and the pair below is what says so: same operands, same
# four-input walk, different join axis, and the golden control plane is
# recorded for each.
#
# The third case is the refusal.  A17's illegal axes are admission failures, so
# the vector set carries one the verifier must reject, in the same way
# ``a15_scale_rows_indivisible`` does: the header still has to be judged legal
# and the program still must never run.
A17_BLOCK_COLUMNS = COLS // 4


def _a17_case(
    cap: Capability,
    name: str,
    *,
    axis: int,
    expect_admitted: bool,
    note: str,
) -> Case:
    """One four-input ``REDUCTION.GROUPED_CONCAT`` joining on ``axis``."""
    w = Workspace(f"a3-{name}", cap)
    b = w.builder
    if axis == 1:
        # Four ``[ROWS, COLS/4]`` column blocks of one row-major buffer, joined
        # back into the ``[ROWS, COLS]`` row they came from: the shape of
        # DeepSeek's block-diagonal output projection, at four groups instead of
        # eight.
        blocks = [
            b.tensor_view(
                object_id=w.activations,
                dtype=DType.BF16,
                dims=[ROWS, A17_BLOCK_COLUMNS],
                strides=[COLS, 1],
                element_offset=index * A17_BLOCK_COLUMNS,
                key=f"view.block{index}",
            )
            for index in range(4)
        ]
        out_dims = [ROWS, COLS]
    else:
        # The axis-0 join, which is what ``aux_id_0 = 0`` and an absent
        # ``aux_id_0`` both mean: four row blocks stacked into one.
        blocks = [
            b.tensor_view(
                object_id=w.activations,
                dtype=DType.BF16,
                dims=[ROWS // 4, COLS],
                element_offset=index * (ROWS // 4) * COLS,
                key=f"view.block{index}",
            )
            for index in range(4)
        ]
        out_dims = [ROWS, COLS]
    joined = b.tensor_view(
        object_id=w.activations,
        dtype=DType.BF16,
        dims=out_dims,
        element_offset=ROWS * COLS,
        permissions=int(Permission.READ | Permission.WRITE),
        key="view.joined",
    )
    concat = b.operator(
        engine_family=Major.REDUCTION,
        engine_sub=Reduction.GROUPED_CONCAT,
        inputs=blocks,
        outputs=[joined],
        aux=[axis],
        numeric_profile_id=w.numeric,
        schedule_id=w.schedule_for(Major.REDUCTION),
        counter_class_id=w.counters,
        source_kernel_id=0,
        key="op.concat",
    )
    b.emit(Major.REDUCTION, Reduction.GROUPED_CONCAT, descriptor_id=concat,
           source_operation_id=0)
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return Case(
        name=name,
        deployment=w.finish(),
        symbols={int(Symbol.SPAN_TOKENS): ROWS},
        expect_admitted=expect_admitted,
        run_program=expect_admitted,
        device_runs=expect_admitted,
        note=note,
    )


def case_a17_join_axis_zero(cap: Capability) -> Case:
    return _a17_case(
        cap, "a17_join_axis_zero", axis=0, expect_admitted=True,
        note=(
            "four row blocks joined on axis 0 with aux_id_0 stated as 0 "
            "explicitly.  This is the operator REDUCTION.3 has always been, and "
            "it is the control against which the feature join is compared: the "
            "two differ only in operator payload byte 48"
        ),
    )


def case_a17_join_axis_one(cap: Capability) -> Case:
    return _a17_case(
        cap, "a17_join_axis_one", axis=1, expect_admitted=True,
        note=(
            "four column blocks joined on the feature axis with aux_id_0 = 1 "
            "(amendment A17).  The sequencer walks the same four input views "
            "and the same output view as the axis-zero sibling and resolves "
            "them to the same extents; aux_id_0 lives at operator payload byte "
            "48 and the operand walk stops at byte 47, so the join axis reaches "
            "the engine and never reaches the microsequencer"
        ),
    )


def case_a17_join_axis_undefined(cap: Capability) -> Case:
    return _a17_case(
        cap, "a17_join_axis_undefined", axis=2, expect_admitted=False,
        note=(
            "aux_id_0 = 2 on a rank-2 operand set: A17 defines join axes 0 and "
            "1 and nothing else, so the deployment is refused at admission "
            "rather than trapped inside an engine that has already read "
            "operands"
        ),
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


def declared_state_count(deployment: Deployment) -> int:
    """How many STATE descriptors a session over this deployment declares."""
    return len(deployment.table.ids_of_type(ExtendedDescriptorType.STATE))


def trapped_at_first_instruction(deployment: Deployment, trap_class: int) -> dict:
    """The observation a program that faults on its first instruction leaves.

    These deployments carry a deliberately corrupted image, so the golden model
    cannot execute them and the expectation is stated rather than run.  The one
    field that is not simply zero is the discard count: ADR-003 8.6 makes an
    abort discard the whole *declared* prepared state set, which is the
    ``len(session.states)`` runtime/sim/device.py adds on its failing path --
    not zero, and not only the slots the transaction reached.
    """
    return {
        "fetched": 1, "retired": 0, "predicated_off": 0, "issued": 0,
        "loop_iterations": 0, "branches": 0, "wait_events": 0,
        "state_prepares": 0, "state_commits": 0,
        "state_discards": declared_state_count(deployment),
        "state_reads": 0, "state_generation_advances": 0,
        "state_commits_applied": 0, "state_rows_committed": 0,
        "first_fault": 0, "issues": [], "views": [], "complete": False,
        "trap_class": trap_class,
    }


def negative_instruction_cases(cap: Capability) -> list[Case]:
    """Instruction-record defects, each on the first executed instruction."""
    cases: list[Case] = []

    w = _tiny(cap, "a3-neg-crc")
    crc_deployment = w.finish()
    cases.append(Case(
        name="negative_instruction_crc",
        deployment=crc_deployment,
        device_runs=False,
        corrupt=corrupt_instruction_crc(0),
        reference=trapped_at_first_instruction(crc_deployment, TRAP_INTEGRITY),
        note="one flipped CRC bit; admission fails on integrity, class 2",
    ))

    w = _tiny(cap, "a3-neg-opcode")
    deployment = w.finish()
    cases.append(Case(
        name="negative_illegal_opcode",
        deployment=deployment,
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {0: 0x11}, reseal=True),
        reference=trapped_at_first_instruction(deployment, TRAP_ILLEGAL),
        note="major opcode 0x11 is not in the frozen registry",
    ))

    w = _tiny(cap, "a3-neg-subopcode")
    deployment = w.finish()
    cases.append(Case(
        name="negative_illegal_subopcode",
        deployment=deployment,
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {1: 0x0D}, reseal=True),
        reference=trapped_at_first_instruction(deployment, TRAP_ILLEGAL),
        note="VECTOR subopcode 0x0d is beyond SQRT_SOFTPLUS",
    ))

    w = _tiny(cap, "a3-neg-flag")
    deployment = w.finish()
    cases.append(Case(
        name="negative_reserved_flag",
        deployment=deployment,
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {3: 0x01}, reseal=True),
        reference=trapped_at_first_instruction(deployment, TRAP_ILLEGAL),
        note="flag bit 8 is reserved and must be zero",
    ))

    w = _tiny(cap, "a3-neg-invert")
    deployment = w.finish()
    cases.append(Case(
        name="negative_invert_without_predicate",
        deployment=deployment,
        device_runs=False,
        corrupt=lambda image: patch_instruction(image, 0, {2: 0x02}, reseal=True),
        reference=trapped_at_first_instruction(deployment, TRAP_ILLEGAL),
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
    deployment = w.finish()
    return Case(
        name="negative_branch_out_of_range",
        deployment=deployment,
        device_runs=True,
        expect_admitted=False,
        reference=trapped_at_first_instruction(deployment, TRAP_ILLEGAL),
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
        note=(
            "runtime trip 9 exceeds the verified maximum 4: capability trap, "
            "reported by both against the LOOP_SETUP that raised it"
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
        note=(
            "state transaction trap: commit with no open prepare, reported by "
            "both against the instruction that raised it"
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
def resolved_views(
    device: Device, entry: dict[str, Any], symbols: dict[int, int]
) -> list[dict[str, Any]]:
    """Every operand view of one issued instruction, resolved by the simulator.

    The extents come from ``runtime.sim.memory.ViewResolver.resolve`` -- the
    device's own resolver, holding the A4 term arithmetic and the A13 partial
    final extent -- evaluated against the loop bindings the device recorded in
    its trace for exactly this instruction.  Nothing here recomputes them.
    """
    instruction = device.instructions[entry["pc"]]
    if FAMILY_DESCRIPTOR.get(instruction.major) != ExtendedDescriptorType.OPERATOR:
        return []
    operator = device.deployment.table.get(
        instruction.descriptor_id, ExtendedDescriptorType.OPERATOR
    )
    views: list[dict[str, Any]] = []
    for slot, field in enumerate(OPERAND_FIELDS):
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        resolved = device.views.resolve(view_id, entry["loops"], symbols)
        views.append({
            "index": int(entry["pc"]),
            "slot": slot,
            "operand": field,
            "descriptor_id": view_id,
            "dim0": int(resolved.dims[0]),
            "dims": [int(d) for d in resolved.dims],
            "element_offset": int(resolved.element_offset),
            "rank": len(resolved.dims),
            "loops": {str(k): int(v) for k, v in sorted(entry["loops"].items())},
        })
    return views


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
    symbols = effective_symbols(case)
    issues = []
    views: list[dict[str, Any]] = []
    for entry in trace:
        instruction = device.instructions[entry["pc"]]
        issues.append({
            "index": entry["pc"],
            "family": int(instruction.major),
            "sub": int(instruction.sub),
            "descriptor_id": int(instruction.descriptor_id),
            "mnemonic": instruction.mnemonic,
        })
        views.extend(resolved_views(device, entry, symbols))
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
        "views": views,
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
        case_a13_block_exact(capability),
        case_a13_block_partial(capability),
        case_a13_block_partial_mid(capability),
        case_a13_block_short(capability),
        case_a13_block_empty(capability),
        case_a13_extent_below_block(capability),
        case_a13_extent_above_block(capability),
        case_a13_symbol_term(capability),
        case_a13_constant_loop(capability),
        case_a13_nested_blocks(capability),
        case_a13_four_terms(capability),
        case_a13_non_leading_axis(capability),
        case_a13_mixed_axes(capability),
        case_a14_link_node_scope(capability),
        case_a14_link_wafer_scopes(capability),
        case_a14_scope_unsupported(capability),
        case_a15_block_scale_rows(capability),
        case_a15_scale_rows_indivisible(capability),
        case_a16_convert_carried_plane(capability),
        case_a16_route_biased_topk(capability),
        case_a17_join_axis_zero(capability),
        case_a17_join_axis_one(capability),
        case_a17_join_axis_undefined(capability),
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
    view_words: list[int] = []
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

        state_count = len(
            table.ids_of_type(ExtendedDescriptorType.STATE)
        )
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

        view_base = len(view_words) // VIEW_STRIDE
        for view in expectation["views"]:
            view_words.append(view["descriptor_id"] & 0xFFFFFFFF)
            view_words.append(view["slot"])
            view_words.append(view["dim0"] & 0xFFFFFFFF)
            view_words.append(view["element_offset"] & 0xFFFFFFFF)
            view_words.append((view["element_offset"] >> 32) & 0xFFFFFFFF)
            view_words.append(view["rank"])

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
            view_base,
            len(expectation["views"]),
            # ADR-003 8.6: an abort discards the whole declared state set, so
            # the device needs the session's state count, not just the slots a
            # transaction touched.
            state_count,
        ]
        if len(words) != CASE_STRIDE:
            raise SystemExit(f"case record is {len(words)} words, expected {CASE_STRIDE}")
        case_words.extend(words)

        records.append({
            "name": case.name,
            "note": case.note,
            "runs_program": case.run_program,
            "entrypoint_id": case.entrypoint_id,
            "phase": int(entry["phase"]),
            "symbols": {str(k): int(v) for k, v in sorted(symbols.items())},
            "instruction_count": instruction_count,
            "descriptor_count": len(table),
            "state_descriptor_count": state_count,
            "declared_retired_work": work,
            "admitted": report.admitted,
            "verifier_errors": list(report.errors),
            "python_rejects_image": python_rejects,
            "device_executed": case.device_runs,
            "program_sha256": hashlib.sha256(image).hexdigest(),
            "descriptor_table_sha256": hashlib.sha256(table.encode()).hexdigest(),
            "golden": {
                key: value for key, value in sorted(golden.items())
                if key not in {"issues", "views", "counters"}
            },
            "golden_counters": golden.get("counters", {}),
            "expected": {
                key: value for key, value in sorted(expectation.items())
                if key not in {"issues", "views", "counters", "message"}
            },
            "expected_issues": expectation["issues"],
            "expected_views": expectation["views"],
            "expected_header_legal": case.expect_header_legal,
            "expected_header_trap_class": int(case.expect_header_trap),
        })

    total_issues = sum(len(r["expected_issues"]) for r in records)
    total_views = sum(len(r["expected_views"]) for r in records)
    program_runs = sum(1 for r in records if r["runs_program"])
    trap_runs = sum(
        1 for r in records
        if r["runs_program"] and int(r["expected"]["trap_class"]) != 0
    )
    if total_views == 0:
        raise SystemExit(
            "no operand view was resolved by the golden model: the view "
            "comparison would pass without comparing anything"
        )
    meta = [
        len(cases), total_issues, positives, len(cases) - positives,
        total_views, 0, 0, 0,
    ]

    files = {
        "a3_program.hex": hex_lines(program_words, 256, PROGRAM_WORDS),
        "a3_header.hex": hex_lines(header_words, 32, HEADER_WORDS),
        "a3_descriptor.hex": hex_lines(
            desc_words, DESCRIPTOR_PREFIX_BYTES * 8, DESC_WORDS
        ),
        "a3_symbol.hex": hex_lines(symbol_words, 32, SYMBOL_WORDS),
        "a3_case.hex": hex_lines(case_words, 32, CASE_WORDS),
        "a3_issue.hex": hex_lines(issue_words, 32, ISSUE_WORDS),
        "a3_view.hex": hex_lines(view_words, 32, VIEW_WORDS),
        "a3_meta.hex": hex_lines(meta, 32, META_WORDS),
    }
    for name, payload in files.items():
        (out / name).write_text(payload, encoding="ascii")

    summary = {
        "schema": "opentallas.rtl.abi3_vectors.v1",
        "abi": {"major": 3, "minor": 0},
        "capability_digest": capability.digest,
        "engine_stub_policy": (
            "every dispatchable engine operation is a recording no-op: RTL 3.0 "
            "implements the control plane, so the comparison is the control "
            "plane"
        ),
        "case_count": len(cases),
        "positive_case_count": positives,
        "negative_case_count": len(cases) - positives,
        "issue_event_count": total_issues,
        "view_resolution_count": total_views,
        "view_reference": (
            "runtime.sim.memory.ViewResolver.resolve, evaluated against the "
            "loop bindings runtime.sim.device.Device recorded at each issue; "
            "amendments A4 (dynamic index terms) and A13 (partial final "
            "iteration of a block loop)"
        ),
        "header_admission_count": len(cases),
        "program_run_count": program_runs,
        "trap_count": trap_runs,
        "required_marker": (
            f"PASS: ABI3 RTL microsequencer cases={len(cases)} "
            f"headers={len(cases)} programs={program_runs} "
            f"issues={total_issues} views={total_views} traps={trap_runs}"
        ),
        "geometry": {
            "program_words": PROGRAM_WORDS,
            "header_words": HEADER_WORDS,
            "descriptor_words": DESC_WORDS,
            "symbol_words": SYMBOL_WORDS,
            "case_words": CASE_WORDS,
            "issue_words": ISSUE_WORDS,
            "view_words": VIEW_WORDS,
            "case_stride": CASE_STRIDE,
            "view_stride": VIEW_STRIDE,
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
        f"negative={len(cases) - positives} issues={total_issues} "
        f"views={total_views}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
