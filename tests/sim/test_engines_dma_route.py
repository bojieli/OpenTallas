"""DMA, REDUCTION and ROUTE engine conformance.

Every case is a real deployment executed on the functional device, and every
expected result is computed independently in the test (plain NumPy or plain
Python) rather than by calling the engine a second time.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Control,
    DType,
    Dma,
    Feature,
    Major,
    NO_ID,
    Permission,
    Reduction,
    ReductionOrder,
    Route,
    StorageClass,
    TopologyClass,
    TrapClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, Symbol
from runtime.sim.device import Device

# Importing an engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.dma  # noqa: F401
import runtime.sim.engines.reduction  # noqa: F401
import runtime.sim.engines.route  # noqa: F401


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def widen(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint16).astype(np.uint32) << 16).view(
        np.float32
    )


def narrow(values: np.ndarray) -> np.ndarray:
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    return (upper + increment.astype(np.uint32)).astype(np.uint16)


def capability() -> Capability:
    cap = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(f)
            for f in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 16,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 4096,
            "max_expert_ids": 1024,
            "max_topk": 64,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=("bf16_bf16_fp32_sequential_rne_v1",),
        engines={"dma": {"queues": 1}, "route": {"queues": 1}},
        memory={"sram": {"bytes": 1 << 26}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class Build:
    """A minimal single-transaction deployment builder for engine tests."""

    def __init__(self, name: str = "engine-test") -> None:
        self.capability = capability()
        self.builder = DeploymentBuilder(
            target_id=name, model_id=name, backend="test", capability=self.capability
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=1 << 26,
            sram_bytes_per_node=1 << 26,
        )
        self._initial: dict[int, bytes] = {}

    def object_of(self, values: np.ndarray) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self.scratch(len(data))
        self._initial[oid] = data
        return oid

    def scratch(self, nbytes: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def view(self, oid: int, dtype: DType, dims, *, writable: bool = False, **kw):
        return self.builder.tensor_view(
            object_id=oid,
            dtype=dtype,
            dims=list(dims),
            permissions=int(Permission.READ | Permission.WRITE)
            if writable
            else int(Permission.READ),
            **kw,
        )

    def input_view(self, values: np.ndarray, dtype: DType) -> int:
        return self.view(self.object_of(values), dtype, values.shape)

    def output_view(self, dims, dtype: DType, itemsize: int) -> int:
        count = int(np.prod(dims))
        return self.view(
            self.scratch(count * itemsize), dtype, dims, writable=True
        )

    def finish(self) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=Phase.PREFILL,
            generation_policy_id=NO_ID,
        )
        device = Device(self.builder.finish(), self.capability)
        for oid, data in self._initial.items():
            device.memory[oid].write(0, data)
        return device


def read(device: Device, view_id: int, symbols=None) -> np.ndarray:
    view = device.views.resolve(view_id, {}, symbols or {})
    return np.array(device.views.read_array(view))


def run(device: Device, symbols=None):
    return device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols or {}
    )


def emit_op(
    build: Build,
    family: Major,
    sub: int,
    inputs,
    outputs,
    *,
    aux=(),
    numeric_profile_id: int = NO_ID,
):
    # The verifier requires every engine operator to carry a tile mapping,
    # because a deployment without one cannot be timed. These unit tests do not
    # care about the schedule's contents, so one per family is supplied here
    # rather than repeated at every call site.
    schedules = build.__dict__.setdefault("_default_schedules", {})
    schedule = schedules.get(int(family))
    if schedule is None:
        schedule = build.builder.schedule(
            engine_family=family,
            tile_rows=1,
            tile_cols=1,
            tile_depth=1,
            bank_mask=0b1,
            max_outstanding=1,
        )
        schedules[int(family)] = schedule
    op = build.builder.operator(
        engine_family=family,
        engine_sub=sub,
        inputs=list(inputs),
        outputs=list(outputs),
        aux=list(aux),
        numeric_profile_id=numeric_profile_id,
        schedule_id=schedule,
    )
    build.builder.emit(family, sub, descriptor_id=op)
    return op


def numeric_fp32(build: Build, order: ReductionOrder, scale_bits: int = 0) -> int:
    return build.builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
        reduction_order=order,
        scale_bits=scale_bits,
    )


# ---------------------------------------------------------------------------
# DMA
# ---------------------------------------------------------------------------
def test_transfer_moves_codes_without_conversion():
    source = np.arange(12, dtype=np.uint16).reshape(3, 4) + 0x3F00
    build = Build()
    src = build.input_view(source, DType.BF16)
    dst = build.output_view((3, 4), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.TRANSFER, [src], [dst])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, dst), source)
    assert result.counters["dma.transfers"] == 1


def test_transfer_reads_a_stride_zero_axis_as_a_shared_broadcast():
    """A ``DMA.TRANSFER`` whose source axis has stride zero repeats one row.

    This is how ``unsqueeze(axis).repeat(extent)`` is expressed without a new
    opcode and without four copies of the source in memory: the verifier bounds
    a view by ``(dim - 1) * stride``, so a zero-stride axis reaches no further
    than the source does, and the engine reads the same elements once per step
    of that axis.  ``REDUCTION.GROUPED_CONCAT`` cannot say this -- joining four
    copies of ``[tokens, width]`` on axis 0 gives ``[4 * tokens, width]``, four
    consecutive *tokens* where four *streams* belong.
    """
    tokens, streams, width = 3, 4, 5
    source = (np.arange(tokens * width, dtype=np.uint16) + 0x3F00).reshape(
        tokens, width
    )
    build = Build()
    src = build.view(
        build.object_of(source),
        DType.BF16,
        (tokens, streams, width),
        strides=[width, 0, 1],
    )
    dst = build.output_view((tokens, streams, width), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.TRANSFER, [src], [dst])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = np.repeat(source[:, None, :], streams, axis=1)
    assert np.array_equal(read(device, dst), expected)
    # Every stream holds the token's own row, not the next token's.
    for stream in range(streams):
        assert np.array_equal(read(device, dst)[:, stream, :], source)


def test_grouped_concat_would_have_misplaced_a_broadcast():
    """The engine's shape check is the only thing between reshape and nonsense.

    Four copies of a ``[tokens, width]`` tensor concatenated on axis 0 are
    ``[4 * tokens, width]``.  Reshaping that to ``[tokens, 4, width]`` -- which
    is exactly what a lenient implementation would do -- yields four
    *consecutive tokens* in the four stream slots of token 0.  The check refuses
    it, and this records what the refusal is protecting against.
    """
    tokens, streams, width = 3, 4, 5
    source = (np.arange(tokens * width, dtype=np.uint16) + 0x3F00).reshape(
        tokens, width
    )
    build = Build()
    views = [build.input_view(source, DType.BF16) for _ in range(streams)]
    out = build.output_view((tokens, streams, width), DType.BF16, 2)
    emit_op(build, Major.REDUCTION, Reduction.GROUPED_CONCAT, views, [out])
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "differ from the concatenation" in result.message
    reshaped = np.concatenate([source] * streams, axis=0).reshape(
        tokens, streams, width
    )
    broadcast = np.repeat(source[:, None, :], streams, axis=1)
    assert not np.array_equal(reshaped, broadcast)


def test_transfer_refuses_a_storage_conversion():
    build = Build()
    src = build.input_view(np.arange(4, dtype=np.uint16), DType.BF16)
    dst = build.output_view((4,), DType.U32, 4)
    emit_op(build, Major.DMA, Dma.TRANSFER, [src], [dst])
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "VECTOR.CONVERT" in result.message


def test_fill_writes_an_immediate_and_a_view_supplied_code():
    build = Build()
    immediate_out = build.output_view((5,), DType.U32, 4)
    emit_op(build, Major.DMA, Dma.FILL, [], [immediate_out], aux=[7])
    code = build.input_view(np.array([0x3F80], dtype=np.uint16), DType.BF16)
    view_out = build.output_view((2, 3), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.FILL, [code], [view_out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, immediate_out), np.full(5, 7, np.uint32))
    assert np.array_equal(read(device, view_out), np.full((2, 3), 0x3F80, np.uint16))
    assert result.counters["dma.transfers"] == 2


def test_fill_rejects_an_immediate_wider_than_the_element():
    build = Build()
    out = build.output_view((4,), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.FILL, [], [out], aux=[0x1FFFF])
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS


def test_gather_selects_rows_and_counts_the_elements_moved():
    rows = np.arange(24, dtype=np.uint16).reshape(6, 4)
    indices = np.array([5, 0, 3], dtype=np.uint32)
    build = Build()
    index_view = build.input_view(indices, DType.U32)
    source = build.input_view(rows, DType.BF16)
    out = build.output_view((3, 4), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.GATHER, [index_view, source], [out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, out), rows[[5, 0, 3]])
    assert result.counters["dma.gather_elements"] == 12


def test_gather_traps_on_an_out_of_range_index():
    build = Build()
    index_view = build.input_view(np.array([0, 6], dtype=np.uint32), DType.U32)
    source = build.input_view(np.zeros((4, 2), dtype=np.uint16), DType.BF16)
    out = build.output_view((2, 2), DType.BF16, 2)
    emit_op(build, Major.DMA, Dma.GATHER, [index_view, source], [out])
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert "row 6" in result.message


def test_scatter_writes_selected_rows_and_preserves_the_rest():
    destination = np.full((4, 2), 0x1111, dtype=np.uint16)
    values = np.array([[1, 2], [3, 4], [5, 6]], dtype=np.uint16)
    indices = np.array([3, 1, 1], dtype=np.uint32)
    build = Build()
    index_view = build.input_view(indices, DType.U32)
    value_view = build.input_view(values, DType.BF16)
    dest_object = build.object_of(destination)
    dest_view = build.view(dest_object, DType.BF16, (4, 2), writable=True)
    emit_op(build, Major.DMA, Dma.SCATTER, [index_view, value_view], [dest_view])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = destination.copy()
    for slot, row in enumerate(indices):
        expected[row] = values[slot]
    assert np.array_equal(read(device, dest_view), expected)
    assert result.counters["dma.scatter_elements"] == 6


# ---------------------------------------------------------------------------
# REDUCTION
# ---------------------------------------------------------------------------
def sequential_sum(values: np.ndarray) -> np.ndarray:
    total = np.zeros(values.shape[1:], dtype=np.float32)
    for row in values:
        total = np.add(total, row, dtype=np.float32)
    return total


def pairwise_sum(values: np.ndarray) -> np.ndarray:
    current = [np.asarray(row, dtype=np.float32) for row in values]
    while len(current) > 1:
        folded = [
            np.add(current[i], current[i + 1], dtype=np.float32)
            for i in range(0, len(current) - 1, 2)
        ]
        if len(current) % 2:
            folded.append(current[-1])
        current = folded
    return current[0]


def blocked_sum(values: np.ndarray) -> np.ndarray:
    if values.shape[0] < 8:
        return sequential_sum(values)
    lanes = [np.asarray(values[i], dtype=np.float32) for i in range(8)]
    index = 8
    while index + 8 <= values.shape[0]:
        for lane in range(8):
            lanes[lane] = np.add(lanes[lane], values[index + lane], dtype=np.float32)
        index += 8
    for lane in range(values.shape[0] - index):
        lanes[lane] = np.add(lanes[lane], values[index + lane], dtype=np.float32)
    half = [np.add(lanes[i], lanes[i + 4], dtype=np.float32) for i in range(4)]
    quarter = [np.add(half[i], half[i + 2], dtype=np.float32) for i in range(2)]
    return np.add(quarter[0], quarter[1], dtype=np.float32)


@pytest.mark.parametrize(
    "order,oracle",
    [
        (ReductionOrder.SEQUENTIAL_ASCENDING, sequential_sum),
        (ReductionOrder.PAIRWISE_TREE, pairwise_sum),
        (ReductionOrder.BLOCKED_ASCENDING, blocked_sum),
    ],
)
def test_ordered_sum_follows_the_declared_reduction_order(order, oracle):
    rng = np.random.default_rng(4)
    terms = rng.uniform(-1e3, 1e3, size=(19, 5)).astype(np.float32)
    build = Build()
    src = build.input_view(terms, DType.FP32)
    out = build.output_view((5,), DType.FP32, 4)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.ORDERED_SUM,
        [src],
        [out],
        numeric_profile_id=numeric_fp32(build, order),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, out), oracle(terms))
    assert result.counters["reduction.elements"] == 19 * 5
    assert result.counters["reduction.ordered_sums"] == 5


def test_ordered_sum_starts_from_the_base_accumulator():
    terms = np.array([[1.0, 2.0], [4.0, 8.0]], dtype=np.float32)
    base = np.array([100.0, 200.0], dtype=np.float32)
    build = Build()
    src = build.input_view(terms, DType.FP32)
    base_view = build.input_view(base, DType.FP32)
    out = build.output_view((2,), DType.FP32, 4)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.ORDERED_SUM,
        [src, base_view],
        [out],
        numeric_profile_id=numeric_fp32(build, ReductionOrder.SEQUENTIAL_ASCENDING),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, out), np.array([105.0, 210.0], np.float32))


def test_ordered_sum_rounds_a_bf16_output_once():
    terms = np.array([[1.0], [0.00390625], [0.00390625]], dtype=np.float32)
    build = Build()
    src = build.input_view(terms, DType.FP32)
    out = build.output_view((1,), DType.BF16, 2)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.ORDERED_SUM,
        [src],
        [out],
        numeric_profile_id=build.builder.numeric(
            contract="bf16_bf16_fp32_sequential_rne_v1",
            input_dtype=DType.FP32,
            output_dtype=DType.BF16,
        ),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    # 1 + 2^-8 + 2^-8 = 1.0078125 rounds once, to nearest even, to 1.0078125.
    assert np.array_equal(widen(read(device, out)), np.float32([1.0078125]))


def test_expert_sum_weights_contributions_in_slot_order():
    contributions = np.array(
        [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0], [7.0, 8.0, 9.0]], dtype=np.float32
    )
    weights = np.array([0.5, 0.25, 0.125], dtype=np.float32)
    base = np.array([1.0, 1.0, 1.0], dtype=np.float32)
    build = Build()
    value_view = build.input_view(contributions, DType.FP32)
    weight_view = build.input_view(weights, DType.FP32)
    base_view = build.input_view(base, DType.FP32)
    out = build.output_view((3,), DType.FP32, 4)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.EXPERT_SUM,
        [value_view, weight_view, base_view],
        [out],
        numeric_profile_id=numeric_fp32(build, ReductionOrder.SEQUENTIAL_ASCENDING),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = base.copy()
    for expert in range(3):
        expected = expected + weights[expert] * contributions[expert]
    assert np.allclose(read(device, out), expected, rtol=0, atol=0)
    assert result.counters["route.expert_reductions"] == 3


def test_vocab_gather_reorders_partitions_and_moves_codes():
    partitions = np.arange(12, dtype=np.uint16).reshape(3, 4)
    order = np.array([2, 0, 1], dtype=np.uint32)
    build = Build()
    src = build.input_view(partitions, DType.BF16)
    order_view = build.input_view(order, DType.U32)
    out = build.output_view((12,), DType.BF16, 2)
    emit_op(
        build, Major.REDUCTION, Reduction.VOCAB_GATHER, [src, order_view], [out]
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, out), partitions[[2, 0, 1]].reshape(12))
    assert result.counters["reduction.elements"] == 12


def test_vocab_gather_traps_on_an_unknown_partition():
    build = Build()
    src = build.input_view(np.zeros((2, 2), dtype=np.uint16), DType.BF16)
    order_view = build.input_view(np.array([0, 4], dtype=np.uint32), DType.U32)
    out = build.output_view((4,), DType.BF16, 2)
    emit_op(
        build, Major.REDUCTION, Reduction.VOCAB_GATHER, [src, order_view], [out]
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS


def test_grouped_concat_joins_three_inputs_along_the_leading_axis():
    first = np.array([[1, 2]], dtype=np.uint16)
    second = np.array([[3, 4], [5, 6]], dtype=np.uint16)
    third = np.array([[7, 8]], dtype=np.uint16)
    build = Build()
    views = [build.input_view(part, DType.BF16) for part in (first, second, third)]
    out = build.output_view((4, 2), DType.BF16, 2)
    emit_op(build, Major.REDUCTION, Reduction.GROUPED_CONCAT, views, [out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(
        read(device, out), np.concatenate([first, second, third], axis=0)
    )
    assert result.counters["reduction.elements"] == 8


def test_partition_sum_reduces_only_the_active_partitions():
    partials = np.array(
        [[1.0, 1.0], [2.0, 2.0], [4.0, 4.0], [1000.0, 1000.0]], dtype=np.float32
    )
    build = Build()
    src = build.input_view(partials, DType.FP32)
    out = build.output_view((2,), DType.FP32, 4)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.PARTITION_SUM,
        [src],
        [out],
        aux=[int(Symbol.VOCABULARY_PARTITIONS)],
        numeric_profile_id=numeric_fp32(build, ReductionOrder.SEQUENTIAL_ASCENDING),
    )
    device = build.finish()
    result = run(device, {int(Symbol.VOCABULARY_PARTITIONS): 3})
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, out), np.array([7.0, 7.0], np.float32))
    assert result.counters["reduction.elements"] == 6


def test_partition_sum_traps_when_the_symbol_exceeds_the_view():
    build = Build()
    src = build.input_view(np.zeros((2, 2), dtype=np.float32), DType.FP32)
    out = build.output_view((2,), DType.FP32, 4)
    emit_op(
        build,
        Major.REDUCTION,
        Reduction.PARTITION_SUM,
        [src],
        [out],
        aux=[int(Symbol.VOCABULARY_PARTITIONS)],
        numeric_profile_id=numeric_fp32(build, ReductionOrder.SEQUENTIAL_ASCENDING),
    )
    result = run(build.finish(), {int(Symbol.VOCABULARY_PARTITIONS): 5})
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS


# ---------------------------------------------------------------------------
# ROUTE
# ---------------------------------------------------------------------------
def test_topk_ranks_by_score_and_breaks_ties_toward_the_lower_id():
    scores = np.array(
        [[0.5, 2.0, 2.0, 1.0], [4.0, 0.0, -1.0, 3.0]], dtype=np.float32
    )
    build = Build()
    score_view = build.input_view(scores, DType.FP32)
    ids = build.output_view((2, 2), DType.U32, 4)
    weights = build.output_view((2, 2), DType.FP32, 4)
    emit_op(build, Major.ROUTE, Route.TOPK, [score_view], [ids, weights])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert np.array_equal(read(device, ids), np.array([[1, 2], [0, 3]], np.uint32))
    assert np.array_equal(
        read(device, weights), np.array([[2.0, 2.0], [4.0, 3.0]], np.float32)
    )
    assert result.counters["route.topk_candidates"] == 8
    assert result.counters["route.selected_experts"] == 4


def test_biased_topk_selects_with_the_bias_and_reports_unbiased_weights():
    scores = np.array([[0.10, 0.20, 0.30, 0.40]], dtype=np.float32)
    bias = np.array([1.0, 0.0, 0.0, -1.0], dtype=np.float32)
    build = Build()
    score_view = build.input_view(scores, DType.FP32)
    bias_view = build.input_view(bias, DType.FP32)
    ids = build.output_view((1, 2), DType.U32, 4)
    weights = build.output_view((1, 2), DType.FP32, 4)
    emit_op(
        build,
        Major.ROUTE,
        Route.BIASED_TOPK,
        [score_view, bias_view],
        [ids, weights],
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    biased = scores[0] + bias
    expected_ids = np.argsort(-biased, kind="stable")[:2]
    assert np.array_equal(read(device, ids)[0], expected_ids.astype(np.uint32))
    # The gate value is the unbiased score, never the score the bias ranked.
    assert np.array_equal(read(device, weights)[0], scores[0][expected_ids])


def test_weight_normalize_scales_each_group_to_the_routed_factor():
    weights = np.array([[1.0, 3.0], [2.0, 2.0]], dtype=np.float32)
    scale = np.float32(2.5)
    build = Build()
    src = build.input_view(weights, DType.FP32)
    out = build.output_view((2, 2), DType.FP32, 4)
    emit_op(
        build,
        Major.ROUTE,
        Route.WEIGHT_NORMALIZE,
        [src],
        [out],
        numeric_profile_id=numeric_fp32(
            build,
            ReductionOrder.SEQUENTIAL_ASCENDING,
            scale_bits=int(scale.view(np.uint32)),
        ),
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    got = read(device, out)
    expected = weights / weights.sum(axis=1, keepdims=True) * float(scale)
    assert np.allclose(got, expected, rtol=1e-6, atol=0)
    assert result.counters["reduction.ordered_sums"] == 2


def test_weight_normalize_traps_on_a_non_positive_group_sum():
    build = Build()
    src = build.input_view(np.array([[1.0, -1.0]], dtype=np.float32), DType.FP32)
    out = build.output_view((1, 2), DType.FP32, 4)
    emit_op(
        build,
        Major.ROUTE,
        Route.WEIGHT_NORMALIZE,
        [src],
        [out],
        numeric_profile_id=numeric_fp32(build, ReductionOrder.SEQUENTIAL_ASCENDING),
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE


def test_expert_dispatch_replicates_rows_in_group_slot_order():
    ids = np.array([[2, 0], [1, 3]], dtype=np.uint32)
    tokens = np.array([[10, 11, 12], [20, 21, 22]], dtype=np.uint16)
    build = Build()
    id_view = build.input_view(ids, DType.U32)
    token_view = build.input_view(tokens, DType.BF16)
    out = build.output_view((4, 3), DType.BF16, 2)
    emit_op(
        build,
        Major.ROUTE,
        Route.EXPERT_DISPATCH,
        [id_view, token_view],
        [out],
        aux=[4],
    )
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = np.array([tokens[0], tokens[0], tokens[1], tokens[1]], np.uint16)
    assert np.array_equal(read(device, out), expected)
    assert result.counters["route.dispatched_bytes"] == 4 * 3 * 2


def test_expert_dispatch_rejects_an_id_outside_the_declared_expert_count():
    build = Build()
    id_view = build.input_view(np.array([[0, 9]], dtype=np.uint32), DType.U32)
    token_view = build.input_view(np.zeros((1, 2), dtype=np.uint16), DType.BF16)
    out = build.output_view((2, 2), DType.BF16, 2)
    emit_op(
        build,
        Major.ROUTE,
        Route.EXPERT_DISPATCH,
        [id_view, token_view],
        [out],
        aux=[4],
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert result.trap_class == TrapClass.DESCRIPTOR_OR_ADDRESS
    assert result.counters["route.rejected_ids"] == 1


def test_expert_dispatch_requires_a_declared_expert_count():
    build = Build()
    id_view = build.input_view(np.array([[0, 1]], dtype=np.uint32), DType.U32)
    token_view = build.input_view(np.zeros((1, 2), dtype=np.uint16), DType.BF16)
    out = build.output_view((2, 2), DType.BF16, 2)
    emit_op(
        build, Major.ROUTE, Route.EXPERT_DISPATCH, [id_view, token_view], [out]
    )
    result = run(build.finish())
    assert result.status == CompletionStatus.FAILED
    assert "aux_id_0" in result.message


def test_index_topk_selects_causally_and_emits_ascending_padded_slots():
    scores = np.array(
        [
            [9.0, 1.0, 5.0, 7.0],
            [1.0, 9.0, 5.0, 7.0],
            [1.0, 2.0, 9.0, 7.0],
            [1.0, 2.0, 3.0, 9.0],
        ],
        dtype=np.float32,
    )
    build = Build()
    src = build.input_view(scores, DType.FP32)
    out = build.output_view((4, 2), DType.U32, 4)
    emit_op(build, Major.ROUTE, Route.INDEX_TOPK, [src], [out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    got = read(device, out)
    expected = np.array(
        [
            [0, NO_ID],  # only position 0 is visible
            [0, 1],  # scores 1, 2, 9 -> positions 2 and 1, in address order
            [1, 2],
            [2, 3],
        ],
        dtype=np.uint32,
    )
    assert np.array_equal(got, expected)
    assert result.counters["route.topk_candidates"] == 1 + 2 + 3 + 4


def test_hash_route_uses_the_frozen_mixer():
    def mix32(key: int) -> int:
        mask = 0xFFFFFFFF
        value = key & mask
        value ^= value >> 16
        value = (value * 0x85EBCA6B) & mask
        value ^= value >> 13
        value = (value * 0xC2B2AE35) & mask
        value ^= value >> 16
        return value

    keys = np.array([0, 1, 2, 99, 123456], dtype=np.uint32)
    table = np.array([40, 41, 42], dtype=np.uint32)
    build = Build()
    key_view = build.input_view(keys, DType.U32)
    table_view = build.input_view(table, DType.U32)
    out = build.output_view((5,), DType.U32, 4)
    emit_op(build, Major.ROUTE, Route.HASH_ROUTE, [key_view, table_view], [out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = np.array(
        [table[mix32(int(key)) % len(table)] for key in keys], dtype=np.uint32
    )
    assert np.array_equal(read(device, out), expected)
    assert result.counters["route.hash_lookups"] == 5


def test_window_index_emits_the_visible_window_with_tail_padding():
    positions = np.array([0, 3, 7], dtype=np.uint32)
    build = Build()
    src = build.input_view(positions, DType.U32)
    out = build.output_view((3, 4), DType.U32, 4)
    emit_op(build, Major.ROUTE, Route.WINDOW_INDEX, [src], [out])
    device = build.finish()
    result = run(device)
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = np.array(
        [
            [0, NO_ID, NO_ID, NO_ID],
            [0, 1, 2, 3],
            [4, 5, 6, 7],
        ],
        dtype=np.uint32,
    )
    assert np.array_equal(read(device, out), expected)
    assert result.counters["route.topk_candidates"] == 1 + 4 + 4
