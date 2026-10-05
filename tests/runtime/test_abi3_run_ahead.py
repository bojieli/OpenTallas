"""The golden device under seeded asynchronous completion (section 3.2).

``runtime.sim.run_ahead.RunAheadPolicy`` defers the retirement accounting of
every engine instruction by a seeded delay, in a seeded order, bounded by the
front end's 16-per-queue and 32-per-die limits.  What it may change is
timing: when ``instructions.retired`` advances, the ``queue.max_occupancy``
counter, and which waits stall.  Everything the RTL campaign compares must
be invariant, and this file holds that invariance over every constructed
program of the microsequencer campaign, plus the two AM-C10 rules the golden
model adopts in lockstep with the RTL: a wait under acquire requires its
producers *published* (trap 13 otherwise), and a pending producer stalls.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    CompletionStatus,
    Control,
    InstructionFlag,
    Major,
    Tensor,
    TrapClass,
    Vector,
)
from runtime.abi3.descriptors import Phase  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.run_ahead import (  # noqa: E402
    MAX_OUTSTANDING,
    QUEUE_DEPTH,
    RunAheadPolicy,
    queue_for,
    xorshift32,
)
from tools import build_abi3_rtl_vectors as vectors  # noqa: E402

# The recording no-op engines the campaign runs with: the instruction stream
# is what is compared, not the arithmetic.
vectors._install_engine_stubs()  # noqa: SLF001


def _observe(case: Any, capability: Any, policy: RunAheadPolicy | None) -> dict[str, Any]:
    """What the RTL campaign compares, plus the trace, for one execution."""
    device = Device(case.deployment, capability, verify=False, trace=True, run_ahead=policy)
    session = device.create_session()
    mark = len(device.trace)
    result = device.run_transaction(
        session, entrypoint_id=case.entrypoint_id, symbols=dict(case.symbols)
    )
    trace = [
        (entry["pc"], entry["descriptor"], tuple(sorted(entry["loops"].items())))
        for entry in device.trace[mark:]
    ]
    symbols = vectors.effective_symbols(case)
    views = []
    for entry in device.trace[mark:]:
        views.extend(
            (view["descriptor_id"], view["slot"], view["extent"], view["element_offset"],
             view["rank"], view["extent_axis"])
            for view in vectors.resolved_views(device, entry, symbols)
        )
    counters = {
        key: value
        for key, value in sorted(result.counters.items())
        if key != "queue.max_occupancy"
    }
    return {
        "status": int(result.status),
        "trap_class": int(result.trap_class),
        "first_fault": int(result.first_fault_instruction),
        "retired": int(result.retired),
        "fetched": int(result.fetched),
        "predicated_off": int(result.predicated_off),
        "message": result.message,
        "trace": trace,
        "views": views,
        "counters": counters,
        "produced": tuple(result.produced_tokens),
        "max_occupancy": int(result.counters.get("queue.max_occupancy", 0)),
    }


def _constructed_cases() -> tuple[list[Any], Any]:
    capability = vectors.rtl_capability()
    cases = [
        function(capability)
        for name, function in sorted(vars(vectors).items())
        if name.startswith("case_") and callable(function)
    ]
    cases.extend(vectors.negative_instruction_cases(capability))
    cases.extend(vectors.header_cases(capability))
    runnable = [case for case in cases if case.run_program and case.device_runs]
    assert len(runnable) >= 40, "the constructed vector set shrank"
    return runnable, capability


POLICIES = [
    RunAheadPolicy(seed=seed, max_delay=delay)
    for seed in (1, 2, 3)
    for delay in (1, 8, 64)
]


def test_run_ahead_is_invariant_over_every_constructed_program() -> None:
    """Same status, trap, counters, trace and views under every policy."""
    cases, capability = _constructed_cases()
    exercised_depth = 0
    completed = 0
    issued = 0
    for case in cases:
        baseline = _observe(case, capability, None)
        assert baseline["max_occupancy"] == 0, case.name
        completed += baseline["status"] == int(CompletionStatus.SUCCESS)
        issued += len(baseline["trace"])
        for policy in POLICIES:
            observed = _observe(case, capability, policy)
            exercised_depth = max(exercised_depth, observed["max_occupancy"])
            for key in (
                "status", "trap_class", "first_fault", "retired", "fetched",
                "predicated_off", "message", "trace", "views", "counters",
                "produced",
            ):
                assert observed[key] == baseline[key], (case.name, policy, key)
    assert exercised_depth >= 2, "no constructed program ran ahead at all"
    assert completed >= 30 and issued >= 100, "the comparison would be vacuous"


def _two_instruction_program(*, release: bool) -> tuple[Any, Any]:
    capability = vectors.rtl_capability()
    workspace = vectors.Workspace("a3-acquire", capability)
    builder = workspace.builder
    matmul = workspace.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    event = builder.new_event()
    builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul,
                 signal_event_id=event, source_operation_id=0)
    builder.emit(Major.CONTROL, Control.WAIT,
                 wait_set_id=builder.wait_set([event], key="wait.one"))
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    deployment = workspace.finish()
    device = Device(deployment, capability, verify=False, trace=True)
    if not release:
        # The builder sets SIGNAL_RELEASE on every producer; strip it on the
        # decoded instruction to make the producer unpublished.
        device.instructions[0].flags &= ~int(InstructionFlag.SIGNAL_RELEASE)
    assert bool(device.instructions[1].flags & InstructionFlag.WAIT_ACQUIRE)
    return device, capability


def test_acquire_wait_on_an_unpublished_producer_traps_13() -> None:
    """AM-C10, second clause: published is required under acquire."""
    device, _ = _two_instruction_program(release=False)
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.INTERNAL_INVARIANT
    assert result.first_fault_instruction == 1
    assert "has not been published (acquire)" in result.message
    assert result.retired == 1


def test_acquire_wait_on_a_released_producer_passes() -> None:
    device, _ = _two_instruction_program(release=True)
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS
    assert result.retired == 3


def _independent_program(tensor_ops: int, vector_ops: int) -> tuple[Any, Any]:
    capability = vectors.rtl_capability()
    workspace = vectors.Workspace("a3-independent", capability)
    builder = workspace.builder
    matmul = workspace.op(Major.TENSOR, Tensor.MATMUL, key="op.matmul")
    add = workspace.op(Major.VECTOR, Vector.SILU_MUL, key="op.silu")
    for index in range(tensor_ops):
        builder.emit(Major.TENSOR, Tensor.MATMUL, descriptor_id=matmul,
                     source_operation_id=index)
    for index in range(vector_ops):
        builder.emit(Major.VECTOR, Vector.SILU_MUL, descriptor_id=add,
                     source_operation_id=tensor_ops + index)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return workspace.finish(), capability


@pytest.mark.parametrize(
    ("tensor_ops", "vector_ops", "expected"),
    [(40, 0, QUEUE_DEPTH), (40, 40, MAX_OUTSTANDING), (3, 0, 3)],
)
def test_outstanding_bounds_hold_and_are_reported(
    tensor_ops: int, vector_ops: int, expected: int
) -> None:
    """Issue stalls at 16 per queue and 32 per die; the counter says so."""
    deployment, capability = _independent_program(tensor_ops, vector_ops)
    policy = RunAheadPolicy(seed=5, max_delay=10_000)
    device = Device(deployment, capability, verify=False, run_ahead=policy)
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols={}
    )
    assert result.status == CompletionStatus.SUCCESS
    assert result.counters["queue.max_occupancy"] == expected
    assert result.retired == tensor_ops + vector_ops + 1
    without = Device(deployment, capability, verify=False)
    baseline = without.run_transaction(
        without.create_session(), entrypoint_id=0, symbols={}
    )
    assert "queue.max_occupancy" not in baseline.counters
    assert baseline.retired == result.retired


def test_queue_mapping_matches_the_rtl_package() -> None:
    """rtl/abi3/ot_a3_pkg.sv a3_queue_base and a3_queue_index_mask."""
    assert queue_for(int(Major.TENSOR), 0) == 0
    assert queue_for(int(Major.TENSOR), 3) == 3
    assert queue_for(int(Major.TENSOR), 5) == 1
    assert queue_for(int(Major.VECTOR), 0) == 4
    assert queue_for(int(Major.ATTENTION), 1) == 9
    assert queue_for(int(Major.REDUCTION), 3) == 11
    assert queue_for(int(Major.ROUTE), 7) == 12
    assert queue_for(int(Major.SELECTION), 0) == 13
    assert queue_for(int(Major.DMA), 3) == 17
    assert queue_for(int(Major.LINK), 2) == 20
    assert queue_for(int(Major.STATE), 0) == 22
    assert queue_for(int(Major.OBSERVATION), 0) == 22
    assert queue_for(int(Major.RECOVERY), 0) == 22


def test_xorshift32_matches_the_checkers() -> None:
    """The generator the RTL checkers transcribe: x ^= x<<13; x ^= x>>17; x ^= x<<5."""
    assert xorshift32(1) == 270369
    assert xorshift32(270369) == 67634689
    state = 0x9E3779B9 | 1
    for _ in range(1000):
        state = xorshift32(state)
        assert 0 < state < 1 << 32
