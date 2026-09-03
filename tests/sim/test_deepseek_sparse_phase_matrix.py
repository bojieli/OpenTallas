"""Differential ABI 3.0 qualification of DeepSeek's sparse-attention join.

This is an interacting-operator gate, not complete-model token evidence.  Every
case executes real descriptors on the functional device and compares three
boundaries with independent source-pinned references:

* the phase-selected KV layout;
* the physical window plus ranked/dense compressed indices; and
* the bit-exact BF16 sparse-attention output.

The cross product covers prefill spans 1, 32, 129, 160 and 256; decode query
positions 1, 127, 128, 129 and 200,000; and compression ratios 0, 4 and 128.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pytest

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Attention,
    CompletionStatus,
    Control,
    DType,
    Feature,
    Major,
    NO_ID,
    Permission,
    Reduction,
    Route,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, Symbol
from runtime.reference.attention_kv_view import attention_kv_view_bf16
from runtime.reference.compressed_kv import (
    CompressedKVState,
    compressed_kv_valid_view_bf16,
)
from runtime.reference.indexing import compressed_dense_indices, window_indices
from runtime.reference.kv_window import KV_WINDOW_PROFILE, KVWindowState
from runtime.reference.selection import index_topk_indices
from runtime.reference.sparse_attention import (
    SPARSE_ATTENTION_BLOCK_SIZE,
    SPARSE_ATTENTION_SCALE_BINARY32,
    sparse_attention_bf16,
)
from runtime.sim.device import Device

# Imports register the handlers exercised by the descriptor program below.
import runtime.sim.engines.attention  # noqa: F401
import runtime.sim.engines.reduction  # noqa: F401
import runtime.sim.engines.route  # noqa: F401


WINDOW = 128
DIM = 2
SESSION = f"{1:064x}"
PREFILL_SPANS = (1, 32, 129, 160, 256)
DECODE_POSITIONS = (1, 127, 128, 129, 200_000)
RATIOS = (0, 4, 128)


def _capability() -> Capability:
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(feature)
            for feature in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_instructions": 64,
            "max_descriptors": 128,
            "max_loop_depth": 2,
            "max_loop_trip": 1 << 18,
            "max_retired_work": 1 << 20,
            "max_events": 32,
            "max_event_id": 63,
            "max_state_resources": 4,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 262_144,
            "max_expert_ids": 1024,
            "max_topk": 65_536,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=("qwen3_gqa_fp32_softmax_bf16_v1",),
        engines={
            "attention": {"queues": 1},
            "reduction": {"queues": 1},
            "route": {"queues": 1},
        },
        memory={"sram": {"bytes": 1 << 24}},
        technology_view="deepseek-sparse-phase-differential",
    )
    capability.validate()
    return capability


class Build:
    def __init__(self) -> None:
        self.capability = _capability()
        self.builder = DeploymentBuilder(
            target_id="deepseek-sparse-phase-differential",
            model_id="deepseek-v4-flash-0731",
            backend="test",
            capability=self.capability,
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=1 << 24,
            sram_bytes_per_node=1 << 24,
        )
        self.initial: dict[int, bytes] = {}
        self.schedules: dict[int, int] = {}

    def scratch(self, size: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=size,
            source=ObjectSource.zeros(size),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def input(self, values: np.ndarray, dtype: DType) -> int:
        values = np.ascontiguousarray(values)
        object_id = self.scratch(values.nbytes)
        self.initial[object_id] = values.tobytes()
        return self.view(object_id, dtype, values.shape)

    def output(self, shape: tuple[int, ...], dtype: DType, itemsize: int) -> int:
        return self.view(
            self.scratch(int(np.prod(shape)) * itemsize),
            dtype,
            shape,
            writable=True,
        )

    def view(
        self,
        object_id: int,
        dtype: DType,
        shape: tuple[int, ...],
        *,
        writable: bool = False,
    ) -> int:
        return self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(shape),
            permissions=int(Permission.READ | Permission.WRITE)
            if writable
            else int(Permission.READ),
        )

    def schedule(self, family: Major) -> int:
        cached = self.schedules.get(int(family))
        if cached is not None:
            return cached
        schedule = self.builder.schedule(
            engine_family=family,
            tile_rows=1,
            tile_cols=1,
            tile_depth=1,
            bank_mask=1,
            max_outstanding=1,
        )
        self.schedules[int(family)] = schedule
        return schedule

    def emit(
        self,
        family: Major,
        sub: int,
        inputs: list[int],
        outputs: list[int],
        *,
        aux: list[int] | None = None,
        numeric_profile_id: int = NO_ID,
    ) -> None:
        operator = self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=inputs,
            outputs=outputs,
            aux=aux or [],
            numeric_profile_id=numeric_profile_id,
            schedule_id=self.schedule(family),
        )
        self.builder.emit(family, sub, descriptor_id=operator)

    def finish(self, phase: Phase) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=phase,
            generation_policy_id=NO_ID,
        )
        device = Device(self.builder.finish(), self.capability)
        for object_id, data in self.initial.items():
            device.memory[object_id].write(0, data)
        return device


@dataclass(frozen=True)
class ReferenceCase:
    phase: Phase
    span: int
    position: int
    context: int
    ratio: int
    current: np.ndarray
    window: np.ndarray
    compressed: np.ndarray
    layout: np.ndarray


def _row(tag: int) -> tuple[int, ...]:
    """Finite, deterministic BF16 codes without host-float dependence."""

    return tuple(0x3E00 + ((tag * 17 + column * 29) % 0x100) for column in range(DIM))


def _window_state(
    *, phase: Phase, span: int, position: int
) -> tuple[KVWindowState, tuple[tuple[int, ...], ...]]:
    context = position + span
    physical = [(0,) * DIM for _ in range(WINDOW)]
    first = max(0, context - WINDOW)
    for absolute in range(first, context):
        physical[absolute % WINDOW] = _row(absolute)
    current = (
        tuple(_row(absolute) for absolute in range(span))
        if phase is Phase.PREFILL
        else (_row(position),)
    )
    state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=(tuple((row,) for row in physical),),
        session_ids=(SESSION,),
        lane_active=(True,),
        next_positions=(context,),
        versions=(1,),
    )
    return state, current


def _compressed_view(ratio: int, context: int):
    if ratio == 0:
        return None
    groups = context // ratio
    capacity = max(1, (context + ratio - 1) // ratio)
    state = CompressedKVState(
        ratio=ratio,
        bf16_codes=(tuple((_row(1_000_000 + group),) for group in range(capacity)),),
        session_ids=(SESSION,),
        lane_active=(True,),
        next_positions=(context,),
        valid_prefix_lengths=(groups,),
        versions=(1,),
    )
    return compressed_kv_valid_view_bf16(
        state,
        active_session_ids=(SESSION,),
    )


def _reference_case(phase: Phase, value: int, ratio: int) -> ReferenceCase:
    span = value if phase is Phase.PREFILL else 1
    position = 0 if phase is Phase.PREFILL else value
    context = position + span
    state, current_codes = _window_state(
        phase=phase,
        span=span,
        position=position,
    )
    compressed_view = _compressed_view(ratio, context)
    result = attention_kv_view_bf16(
        (current_codes,),
        state,
        expected_window_state_versions=state.versions,
        active_session_ids=(SESSION,),
        start_pos=position,
        compression_ratio=ratio,
        compressed_view=compressed_view,
    )
    window = np.asarray(
        tuple(heads[0] for heads in state.bf16_codes[0]), dtype=np.uint16
    )
    compressed = (
        np.empty((0, DIM), dtype=np.uint16)
        if compressed_view is None
        else np.asarray(
            tuple(heads[0] for heads in compressed_view.bf16_codes[0]),
            dtype=np.uint16,
        ).reshape(-1, DIM)
    )
    return ReferenceCase(
        phase=phase,
        span=span,
        position=position,
        context=context,
        ratio=ratio,
        current=np.asarray(current_codes, dtype=np.uint16),
        window=window,
        compressed=compressed,
        layout=np.asarray(result.bf16_codes[0], dtype=np.uint16),
    )


def _score_codes(span: int, candidates: int) -> np.ndarray:
    # Codes within one positive normal exponent bin preserve integer ordering.
    rows = np.empty((span, candidates), dtype=np.uint16)
    for query in range(span):
        columns = np.arange(candidates, dtype=np.uint32)
        rows[query] = (0x3F00 + ((columns * 37 + query * 19) % 0x70)).astype(np.uint16)
    return rows


def _expected_indices(case: ReferenceCase, scores: np.ndarray | None) -> np.ndarray:
    window = window_indices(WINDOW, 1, case.span, case.position)[0]
    if case.ratio == 0 or not len(case.compressed):
        # A direct WINDOW_INDEX consumer preserves chronological circular-slot
        # order; after wrap that order is deliberately not numerically sorted.
        expected = np.full((case.span, WINDOW), -1, dtype=np.int64)
        window_rows = np.asarray(window, dtype=np.int64)
        expected[:, : window_rows.shape[1]] = window_rows
        return expected
    elif case.ratio == 4:
        assert scores is not None
        top_k = min(3, len(case.compressed))
        compressed = index_topk_indices(
            (tuple(tuple(int(code) for code in row) for row in scores),),
            top_k=top_k,
            compression_ratio=case.ratio,
            start_position=case.position,
            offset=case.span if case.phase is Phase.PREFILL else WINDOW,
        )[0]
        width = WINDOW + top_k
    else:
        compressed = compressed_dense_indices(
            case.ratio,
            1,
            case.span,
            case.position,
            case.span if case.phase is Phase.PREFILL else WINDOW,
        )[0]
        width = WINDOW + len(case.compressed)

    expected = np.full((case.span, width), -1, dtype=np.int64)
    for query in range(case.span):
        joined = sorted(
            index for index in (*window[query], *compressed[query]) if index >= 0
        )
        expected[query, : len(joined)] = joined
    return expected


def _read(device: Device, view_id: int) -> np.ndarray:
    view = device.views.resolve(view_id, {}, {})
    return np.array(device.views.read_array(view))


def _execute(case: ReferenceCase):
    build = Build()
    base = case.current if case.phase is Phase.PREFILL else case.window
    layout_inputs = [build.input(base, DType.BF16)]
    if len(case.compressed):
        layout_inputs.append(build.input(case.compressed, DType.BF16))
    layout_view = build.output(case.layout.shape, DType.BF16, 2)
    build.emit(
        Major.REDUCTION,
        Reduction.GROUPED_CONCAT,
        layout_inputs,
        [layout_view],
        aux=[0],
    )

    positions = (
        np.arange(case.span, dtype=np.uint32)
        if case.phase is Phase.PREFILL
        else np.asarray([case.position], dtype=np.uint32)
    )
    position_view = build.input(positions, DType.U32)
    window_view = build.output((case.span, WINDOW), DType.U32, 4)
    build.emit(
        Major.ROUTE,
        Route.WINDOW_INDEX,
        [position_view],
        [window_view],
        aux=[WINDOW, 0, int(Symbol.CONTEXT_LENGTH)],
    )

    scores = None
    index_view = window_view
    if case.ratio and len(case.compressed):
        ratio_view = build.input(np.asarray([case.ratio], dtype=np.uint32), DType.U32)
        if case.ratio == 4:
            scores = _score_codes(case.span, len(case.compressed))
            score_view = build.input(scores, DType.BF16)
            selected = min(3, len(case.compressed))
        else:
            score_view = NO_ID
            selected = len(case.compressed)
        index_view = build.output((case.span, WINDOW + selected), DType.U32, 4)
        build.emit(
            Major.ROUTE,
            Route.INDEX_TOPK,
            [score_view, window_view, ratio_view],
            [index_view],
            aux=[
                selected,
                0,
                int(Symbol.CONTEXT_LENGTH),
                int(Symbol.POSITION_START),
            ],
        )

    query = np.asarray(
        [[_row(2_000_000 + case.position + query)] for query in range(case.span)],
        dtype=np.uint16,
    )
    sinks = np.asarray([0.125], dtype=np.float32)
    query_view = build.input(query, DType.BF16)
    sink_view = build.input(sinks, DType.FP32)
    output_view = build.output(query.shape, DType.BF16, 2)
    numeric = build.builder.numeric(
        contract="qwen3_gqa_fp32_softmax_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    build.emit(
        Major.ATTENTION,
        Attention.SPARSE,
        [query_view, layout_view, index_view, sink_view],
        [output_view],
        aux=[
            NO_ID,
            SPARSE_ATTENTION_BLOCK_SIZE,
            int(Symbol.CONTEXT_LENGTH),
            int(Symbol.POSITION_START),
        ],
        numeric_profile_id=numeric,
    )

    device = build.finish(case.phase)
    result = device.run_transaction(
        device.create_session(),
        entrypoint_id=0,
        symbols={
            int(Symbol.SPAN_TOKENS): case.span,
            int(Symbol.POSITION_START): case.position,
            int(Symbol.POSITION_END): case.context,
            int(Symbol.CONTEXT_LENGTH): case.context,
            int(Symbol.PHASE): int(case.phase),
        },
    )
    return device, result, layout_view, index_view, output_view, query, sinks, scores


CASES = tuple(
    (Phase.PREFILL, span, ratio) for span in PREFILL_SPANS for ratio in RATIOS
) + tuple(
    (Phase.DECODE, position, ratio) for position in DECODE_POSITIONS for ratio in RATIOS
)


@pytest.mark.parametrize(
    "phase,value,ratio",
    CASES,
    ids=lambda value: value.name.lower() if isinstance(value, Phase) else str(value),
)
def test_layout_indices_and_sparse_output_match_independent_references(
    phase: Phase, value: int, ratio: int
) -> None:
    case = _reference_case(phase, value, ratio)
    (
        device,
        result,
        layout_view,
        index_view,
        output_view,
        query,
        sinks,
        scores,
    ) = _execute(case)
    assert result.status == CompletionStatus.SUCCESS, result.message

    actual_layout = _read(device, layout_view)
    assert np.array_equal(actual_layout, case.layout)

    expected_indices = _expected_indices(case, scores)
    actual_indices = _read(device, index_view)
    expected_u32 = np.where(expected_indices < 0, NO_ID, expected_indices).astype(
        np.uint32
    )
    assert np.array_equal(actual_indices, expected_u32)

    expected_output = sparse_attention_bf16(
        (
            tuple(
                tuple(tuple(int(code) for code in head) for head in row)
                for row in query
            ),
        ),
        (tuple(tuple(int(code) for code in row) for row in case.layout),),
        tuple(int(code) for code in sinks.view(np.uint32)),
        (tuple(tuple(int(index) for index in row) for row in expected_indices),),
        scale_binary32=SPARSE_ATTENTION_SCALE_BINARY32,
    )
    assert np.array_equal(
        _read(device, output_view),
        np.asarray(expected_output.values[0], dtype=np.uint16),
    )
