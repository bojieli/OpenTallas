"""Correctness-bound shared-resource timing for ABI 3.0 batches.

The functional batch scheduler owns ABI admission, session isolation, numeric
execution, token selection and EOS retirement.  This module does not duplicate
any of those semantics.  It captures the exact trace span emitted by every
authenticated submission and interleaves those spans over one set of modeled
sequencers, queues, engines, memory ports and fabric resources.

Two gates are intentionally ordered:

1. every generated token and the terminal EOS reason must equal an independent
   expected stream for this same full-model execution;
2. only then may request-start/token-commit intervals from a characterized
   target-cycle timebase qualify as TPOT.

Host wall time, retired-instruction pseudo-time and analytical projections are
never used by this path.
"""

from __future__ import annotations

import copy
import hashlib
import math
from dataclasses import dataclass, field as dc_field, replace
from typing import Any, Mapping, Sequence

from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import (
    CompletionStatus,
    Link,
    NO_ID,
    TopologyClass,
)
from runtime.abi3.records import Completion
from runtime.cycle.fabric import ClusterFabric, FabricTiming, WaferFabric, build_fabric
from runtime.cycle.machine import Provenance
from runtime.cycle.model import (
    CLUSTER_WIDE,
    TILED_FAMILIES,
    CycleModel,
    FunctionalTraceSpan,
    MemorySystem,
    ScheduledLink,
    TileMapping,
    TraceStep,
    TracingDevice,
    _EngineUnit,
    _Queue,
    tile_mapping,
)
from runtime.sim.batch import (
    BatchError,
    BatchLaneSubmission,
    BatchScheduler,
    BatchWaveResult,
)
from runtime.sim.counters import CounterSet
from runtime.sim.device import Session


CYCLE_BATCH_SCHEMA = "opentallas.abi3.cycle_batch_execution.v1"
TIMING_RECORD_SCHEMA = "opentallas.abi3.bound_token_timing.v1"


class TimingBindingError(BatchError):
    """A target-cycle record is not the record for its functional execution."""


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _trace_step_identity(step: TraceStep) -> dict[str, Any]:
    """Stable architectural identity of a trace step, excluding timed fields."""

    return {
        "index": int(step.index),
        "kind": step.kind,
        "node": int(step.node),
        "pc": int(step.pc),
        "major": int(step.major),
        "sub": int(step.sub),
        "mnemonic": step.mnemonic,
        "family": step.family,
        "descriptor_id": int(step.descriptor_id),
        "wait_set_id": int(step.wait_set_id),
        "wait_producers": [int(value) for value in step.wait_producers],
        "signal_event_id": int(step.signal_event_id),
        "counter_delta": dict(sorted(step.counter_delta.items())),
        "accesses": [
            {
                "object_id": int(access.object_id),
                "storage_class": int(access.storage_class),
                "address": int(access.address),
                "nbytes": int(access.nbytes),
                "write": bool(access.write),
                "view_id": int(access.view_id),
            }
            for access in step.accesses
        ],
        "trapped": bool(step.trapped),
        "predicate_taken": step.predicate_taken,
        "operator_id": int(step.operator_id),
        "schedule_id": int(step.schedule_id),
        "schedule": None
        if step.schedule is None
        else dict(sorted(step.schedule.items())),
        "operand_dims": {
            name: [int(value) for value in dims]
            for name, dims in sorted(step.operand_dims.items())
        },
        "operand_objects": dict(sorted(step.operand_objects.items())),
        "numeric_profile_id": int(step.numeric_profile_id),
        "contract_digest": step.contract_digest,
    }


def _trace_digest(trace: FunctionalTraceSpan) -> str:
    return _digest([_trace_step_identity(step) for step in trace.steps])


def _result_digest(trace: FunctionalTraceSpan) -> str:
    """Digest functional facts only; host timing is deliberately excluded."""

    result = trace.result
    return _digest(
        {
            "status": int(result.status),
            "trap_class": int(result.trap_class),
            "first_fault_instruction": int(result.first_fault_instruction),
            "retired": int(result.retired),
            "fetched": int(result.fetched),
            "predicated_off": int(result.predicated_off),
            "selected_token": int(result.selected_token),
            "eos_reason": int(result.eos_reason),
            "produced_tokens": [int(token) for token in result.produced_tokens],
            "counters": dict(sorted(result.counters.items())),
            "node_counters": [
                dict(sorted(counters.items())) for counters in result.node_counters
            ],
            "message": result.message,
        }
    )


@dataclass(frozen=True, slots=True)
class BoundTokenTiming:
    """Target-cycle interval bound to one exact ABI completion and trace."""

    schema: str
    deployment_id: int
    deployment_generation: int
    deployment_digest: str
    capability_digest: str
    cost_table_id: str
    cost_table_digest: str
    technology_view: str
    batch_execution_id: str | None
    physical_batch_size: int
    lane_index: int
    wave_index: int
    session_id: int
    session_generation_start: int
    session_generation_end: int
    transaction_id: int
    request_descriptor_id: int
    request_descriptor_digest: str
    submission_digest: str
    trace_start: int
    trace_stop: int
    trace_digest: str
    functional_result_digest: str
    status: int
    produced_token_count: int
    produced_token_id: int
    eos_reason: int
    request_start_tick: int
    token_commit_tick: int
    completion_digest: str

    def to_dict(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
        }


@dataclass(slots=True)
class _LaneCursor:
    lane: int
    trace: FunctionalTraceSpan
    steps: tuple[TraceStep, ...]
    request_start: int
    position: int = 0
    ready_at: int = 0
    end_at: int = 0
    events: dict[int, int] = dc_field(default_factory=dict)

    @property
    def done(self) -> bool:
        return self.position >= len(self.steps)

    @property
    def step(self) -> TraceStep:
        return self.steps[self.position]


def _empty_totals() -> dict[str, int]:
    return {
        "issue_cycles": 0,
        "fetch_cycles": 0,
        "wait_stall": 0,
        "queue_stall": 0,
        "compute": 0,
        "memory_stall": 0,
        "transaction_cycles": 0,
        "tiles": 0,
        "tile_issue": 0,
        "tile_padding": 0,
        "tile_pipeline_stall": 0,
    }


@dataclass(slots=True)
class _NodeTimingState:
    queues: dict[str, _Queue]
    engines: dict[str, _EngineUnit]
    memory: MemorySystem
    counters: CounterSet
    totals: dict[str, int]
    fabric_timings: list[FabricTiming]
    tiles_seen: dict[str, list[TileMapping]]
    seq_free: int = 0
    rr_cursor: int = 0
    issue_count: int = 0
    cross_lane_transitions: int = 0
    cross_lane_overlap_events: int = 0
    issue_order_digest: bytes = b"\x00" * 32
    first_issue_samples: list[dict[str, Any]] = dc_field(default_factory=list)
    last_issue_samples: list[dict[str, Any]] = dc_field(default_factory=list)
    previous_lane: int | None = None
    previous_completion: int = 0

    def record_issue(
        self,
        *,
        lane: int,
        step: TraceStep,
        sequencer_start: int,
        sequencer_end: int,
        completion: int,
    ) -> None:
        row = {
            "ordinal": self.issue_count,
            "lane_index": int(lane),
            "trace_step": int(step.index),
            "kind": step.kind,
            "family": step.family,
            "sequencer_start_tick": int(sequencer_start),
            "sequencer_end_tick": int(sequencer_end),
            "operation_completion_tick": int(completion),
        }
        if self.previous_lane is not None and self.previous_lane != lane:
            self.cross_lane_transitions += 1
            if sequencer_start < self.previous_completion:
                self.cross_lane_overlap_events += 1
        self.previous_lane = lane
        self.previous_completion = completion
        self.issue_order_digest = hashlib.sha256(
            self.issue_order_digest + canonical_json(row)
        ).digest()
        self.issue_count += 1
        if len(self.first_issue_samples) < 16:
            self.first_issue_samples.append(row)
        self.last_issue_samples.append(row)
        if len(self.last_issue_samples) > 16:
            del self.last_issue_samples[0]


def _new_node_state(model: CycleModel) -> _NodeTimingState:
    queues: dict[str, _Queue] = {}
    for name, params in sorted(model.engine_params.items()):
        queues[name] = _Queue(name, params.queue_depth, params.max_outstanding)
        for index in range(params.queues):
            queues[f"{name}.{index}"] = _Queue(
                f"{name}.{index}", params.queue_depth, params.max_outstanding
            )
    return _NodeTimingState(
        queues=queues,
        engines={
            name: _EngineUnit(name, params)
            for name, params in sorted(model.engine_params.items())
        },
        memory=MemorySystem(model.memory_params),
        counters=CounterSet(),
        totals=_empty_totals(),
        fabric_timings=[],
        tiles_seen={},
    )


class CycleBatchScheduler(BatchScheduler):
    """One functional ABI batch plus one persistent shared-resource schedule."""

    def __init__(
        self,
        model: CycleModel,
        batch_size: int,
        *,
        device: TracingDevice | None = None,
        sessions: Sequence[Session] | None = None,
    ) -> None:
        self.model = model
        requested = int(batch_size)
        if device is None:
            device = TracingDevice(
                model.deployment,
                model.capability,
                root=model.root,
                verify=model.verify,
            )
        if not isinstance(device, TracingDevice):
            raise TimingBindingError(
                "cycle batching requires TracingDevice; an untraced functional "
                "execution cannot supply target-cycle evidence"
            )
        if sessions is None:
            sessions = (
                (device.create_session(),)
                if requested == 1
                else device.create_batch_sessions(requested)
            )
        if len(sessions) != requested:
            raise TimingBindingError(
                f"batch_size={requested} but {len(sessions)} sessions were supplied"
            )
        if (
            device.deployment.deployment_digest
            != model.deployment.deployment_digest
            or device.capability.digest != model.capability.digest
        ):
            raise TimingBindingError(
                "functional device and cycle model do not share deployment and "
                "capability identities"
            )

        super().__init__(device, sessions)
        self.device: TracingDevice
        self._source_identity = self._current_source_identity()
        self.fabric = build_fabric(model.machine, model.topology_class)
        if self.fabric is not None:
            model._validate_fabric_topology(self.fabric)
        self._node_states = [_new_node_state(model) for _ in range(device.node_count)]
        self._trace_cursor = 0
        self._wave_end = int(device._device_cycle)
        self._timing_records: list[BoundTokenTiming] = []
        self._record_sources: dict[
            tuple[int, int], tuple[FunctionalTraceSpan, Completion]
        ] = {}
        self._request_starts: list[list[int]] = [[] for _ in range(self.batch_size)]
        self._timing_problems: list[str] = []

    @property
    def timing_records(self) -> tuple[BoundTokenTiming, ...]:
        """Immutable view of the per-transaction target-cycle bindings."""

        return tuple(self._timing_records)

    def _current_source_identity(self) -> dict[str, Any]:
        return {
            "deployment_id": int(self.model.deployment.deployment_id),
            "deployment_generation": int(self.model.deployment.generation),
            "deployment_digest": self.model.deployment.deployment_digest.hex(),
            "capability_digest": self.model.capability.digest,
            "cost_table_id": self.model.machine.cost_table.cost_table_id,
            "cost_table_digest": self.model.machine.cost_table.digest,
            "technology_view": self.model.machine.cost_table.technology_view,
        }

    def _require_source_identity(self) -> None:
        observed = self._current_source_identity()
        if observed != self._source_identity:
            raise TimingBindingError(
                "deployment, capability or cost-table identity changed during "
                f"cycle batching: started={self._source_identity}, now={observed}"
            )

    def submit_wave(
        self, submissions: Sequence[BatchLaneSubmission]
    ) -> BatchWaveResult:
        """Functionally execute a wave, then time those exact traces together."""

        self._require_source_identity()
        trace_start = len(self.device.transaction_traces)
        wave = super().submit_wave(submissions)
        traces = self.device.transaction_traces[trace_start:]
        try:
            bound = self._bind_wave_traces(wave, traces)
            request_start = max(self._wave_end, *(state.seq_free for state in self._node_states))
            commit_ticks = self._schedule_wave(bound, request_start)
            self._publish_modeled_completions(
                wave, bound, request_start=request_start, commit_ticks=commit_ticks
            )
            self._wave_end = max(commit_ticks.values(), default=request_start)
            # The functional device increments this field by retired work.  In
            # this timing path it is an architectural cycle counter instead;
            # the next wave therefore starts from the modeled completion.
            self.device._device_cycle = self._wave_end
            self._trace_cursor = len(self.device.transaction_traces)
            self._require_source_identity()
        except Exception as exc:
            self.failed = True
            self.active = [False] * self.batch_size
            problem = f"target-cycle binding failed at wave {wave.wave_index}: {exc}"
            self.problems.append(problem)
            self._timing_problems.append(problem)
            raise
        return wave

    def _bind_wave_traces(
        self,
        wave: BatchWaveResult,
        traces: Sequence[FunctionalTraceSpan],
    ) -> dict[int, FunctionalTraceSpan]:
        if len(traces) != len(wave.lanes):
            raise TimingBindingError(
                f"wave has {len(wave.lanes)} completions but {len(traces)} trace spans"
            )
        by_key: dict[tuple[int, int], FunctionalTraceSpan] = {}
        for trace in traces:
            key = (trace.session_id, trace.transaction_id)
            if key in by_key:
                raise TimingBindingError(
                    f"duplicate trace for session/transaction {key}"
                )
            by_key[key] = trace

        bound: dict[int, FunctionalTraceSpan] = {}
        for lane in wave.lanes:
            key = (int(lane.session_id), int(lane.completion.transaction_id))
            trace = by_key.pop(key, None)
            if trace is None:
                raise TimingBindingError(
                    f"lane {lane.lane_index} completion {key} has no exact trace"
                )
            if trace.result is not lane.result:
                raise TimingBindingError(
                    f"lane {lane.lane_index} trace carries a different functional result"
                )
            if trace.completion_record != lane.record:
                raise TimingBindingError(
                    f"lane {lane.lane_index} trace carries a different ABI completion"
                )
            if trace.batch_execution_id != self.batch_execution_id:
                raise TimingBindingError(
                    f"lane {lane.lane_index} trace has batch identity "
                    f"{trace.batch_execution_id!r}, expected {self.batch_execution_id!r}"
                )
            if lane.symbol_batch != self.batch_size:
                raise TimingBindingError(
                    f"lane {lane.lane_index} executed Symbol.BATCH={lane.symbol_batch}, "
                    f"expected physical batch {self.batch_size}"
                )
            if trace.trace_stop - trace.trace_start != len(trace.steps):
                raise TimingBindingError(
                    f"lane {lane.lane_index} trace slice is not contiguous"
                )
            bound[int(lane.lane_index)] = trace
        if by_key:
            raise TimingBindingError(f"unbound transaction traces remain: {sorted(by_key)}")
        return bound

    def _candidate_ready(
        self,
        state: _NodeTimingState,
        cursor: _LaneCursor,
        *,
        node_id: int,
        global_links: Mapping[int, ScheduledLink] | None,
    ) -> int:
        step = cursor.step
        base = max(state.seq_free, cursor.ready_at)
        seq = self.model.sequencer
        if step.kind == "PREDICATE":
            return base + seq.fetch_cycles + seq.predicate_cycles
        if step.kind == "COMMIT":
            return max(base, state.engines["state"].free_at)

        arrival = base + seq.fetch_cycles + seq.decode_cycles
        if step.wait_producers:
            missing = [event for event in step.wait_producers if event not in cursor.events]
            if missing:
                raise TimingBindingError(
                    f"lane {cursor.lane} trace step {step.index} waits on unscheduled "
                    f"events {missing}"
                )
            arrival = max(
                arrival, *(cursor.events[event] for event in step.wait_producers)
            )
            arrival += seq.wait_check_cycles

        if step.kind == "CONTROL" or step.family not in state.queues:
            return arrival
        if (
            step.family == "link"
            and step.node == CLUSTER_WIDE
            and global_links is not None
        ):
            try:
                resolution = global_links[step.index].resolution
            except KeyError as exc:
                raise TimingBindingError(
                    f"cluster LINK trace step {step.index} has no global schedule"
                ) from exc
            if node_id not in resolution.physical_members:
                return arrival

        mapping: TileMapping | None = None
        if step.family in TILED_FAMILIES and not step.trapped:
            mapping = tile_mapping(step, state.engines[step.family].params)
        queue = state.queues[
            self.model._queue_key(step.family, mapping, state.queues)
        ]
        return queue.ready_at(
            arrival, mapping.max_outstanding if mapping is not None else None
        )

    def _time_node_wave(
        self,
        state: _NodeTimingState,
        traces: Mapping[int, FunctionalTraceSpan],
        request_start: int,
        *,
        node_id: int,
        fabric: ClusterFabric | WaferFabric | None,
        global_links: Mapping[int, ScheduledLink] | None = None,
        global_link_readiness: dict[int, int] | None = None,
    ) -> dict[int, int]:
        cursors = {
            lane: _LaneCursor(
                lane=lane,
                trace=trace,
                steps=tuple(
                    step
                    for step in trace.steps
                    if step.node in (CLUSTER_WIDE, node_id)
                ),
                request_start=request_start,
                ready_at=request_start,
                end_at=request_start,
            )
            for lane, trace in traces.items()
        }
        while True:
            candidates: list[tuple[int, int, int]] = []
            for lane, cursor in cursors.items():
                if cursor.done:
                    continue
                ready = self._candidate_ready(
                    state,
                    cursor,
                    node_id=node_id,
                    global_links=global_links,
                )
                distance = (lane - state.rr_cursor) % self.batch_size
                candidates.append((ready, distance, lane))
            if not candidates:
                break
            _ready, _distance, lane = min(candidates)
            cursor = cursors[lane]
            step = cursor.step
            sequencer_start = max(state.seq_free, cursor.ready_at)
            seq_free, step_end = self.model._time_steps(
                (step,),
                sequencer_start,
                queues=state.queues,
                engines=state.engines,
                memory=state.memory,
                events=cursor.events,
                totals=state.totals,
                counters=state.counters,
                fabric=fabric,
                fabric_timings=state.fabric_timings,
                tiles_seen=state.tiles_seen,
                node_id=node_id,
                node_count=self.device.node_count,
                global_links=global_links,
                global_link_readiness=global_link_readiness,
            )
            state.seq_free = seq_free
            cursor.ready_at = seq_free
            cursor.end_at = max(cursor.end_at, step_end)
            state.record_issue(
                lane=lane,
                step=step,
                sequencer_start=sequencer_start,
                sequencer_end=seq_free,
                completion=step_end,
            )
            cursor.position += 1
            state.rr_cursor = (lane + 1) % self.batch_size

        ends: dict[int, int] = {}
        for lane, cursor in cursors.items():
            end = max(cursor.end_at, cursor.ready_at, request_start)
            ends[lane] = end
            state.totals["transaction_cycles"] += end - request_start
        return ends

    def _cluster_link_steps(
        self, traces: Mapping[int, FunctionalTraceSpan]
    ) -> list[TraceStep]:
        return [
            step
            for lane in sorted(traces)
            for step in traces[lane].steps
            if step.kind == "ENGINE"
            and step.family == "link"
            and step.node == CLUSTER_WIDE
            and not step.trapped
        ]

    def _schedule_cluster_links(
        self,
        steps: Sequence[TraceStep],
        readiness: Mapping[int, int],
        request_start: int,
    ) -> dict[int, ScheduledLink]:
        assert isinstance(self.fabric, ClusterFabric)
        ordered: list[tuple[int, int, TraceStep, Any]] = []
        for step in steps:
            resolution = self.model._resolve_link(
                step.descriptor_id,
                Link(step.sub),
                self.fabric,
            )
            ordered.append(
                (
                    max(request_start, int(readiness.get(step.index, request_start))),
                    int(step.index),
                    step,
                    resolution,
                )
            )
        scheduled: dict[int, ScheduledLink] = {}
        for ready, _index, step, resolution in sorted(ordered):
            timing = self.model._time_link(
                step, self.fabric, ready, resolution=resolution
            )
            scheduled[step.index] = ScheduledLink(resolution, timing)
        return scheduled

    def _schedule_cluster_wave(
        self,
        traces: Mapping[int, FunctionalTraceSpan],
        request_start: int,
    ) -> dict[int, int]:
        assert isinstance(self.fabric, ClusterFabric)
        baseline_states = copy.deepcopy(self._node_states)
        fabric_baseline = self.fabric.snapshot()
        link_steps = self._cluster_link_steps(traces)
        readiness: dict[int, int] = {}
        limit = max(2, len(link_steps) + 2)
        for _iteration in range(1, limit + 1):
            self.fabric.restore(fabric_baseline)
            scheduled = self._schedule_cluster_links(
                link_steps, readiness, request_start
            )
            states = copy.deepcopy(baseline_states)
            observed: dict[int, int] = {}
            per_node: list[dict[int, int]] = []
            for node_id, state in enumerate(states):
                per_node.append(
                    self._time_node_wave(
                        state,
                        traces,
                        request_start,
                        node_id=node_id,
                        fabric=self.fabric,
                        global_links=scheduled,
                        global_link_readiness=observed,
                    )
                )
            next_readiness = {
                index: max(
                    request_start,
                    int(readiness.get(index, request_start)),
                    int(observed.get(index, request_start)),
                )
                for index in {step.index for step in link_steps}
            }
            if next_readiness == readiness or not link_steps:
                self._node_states = states
                return {
                    lane: max(node[lane] for node in per_node)
                    for lane in traces
                }
            readiness = next_readiness
        self.fabric.restore(fabric_baseline)
        raise TimingBindingError(
            f"cluster batch LINK schedule did not converge after {limit} iterations"
        )

    def _schedule_wave(
        self,
        traces: Mapping[int, FunctionalTraceSpan],
        request_start: int,
    ) -> dict[int, int]:
        if self.model.topology_class is TopologyClass.CLUSTER_32:
            return self._schedule_cluster_wave(traces, request_start)
        ends = self._time_node_wave(
            self._node_states[0],
            traces,
            request_start,
            node_id=0,
            fabric=self.fabric,
        )
        return ends

    def _make_timing_record(
        self,
        *,
        lane_index: int,
        wave_index: int,
        trace: FunctionalTraceSpan,
        completion: Completion,
        request_start: int,
        commit_tick: int,
        completion_record: bytes,
    ) -> BoundTokenTiming:
        tokens = tuple(int(token) for token in trace.result.produced_tokens)
        token = tokens[0] if len(tokens) == 1 else NO_ID
        return BoundTokenTiming(
            schema=TIMING_RECORD_SCHEMA,
            deployment_id=int(trace.deployment_id),
            deployment_generation=int(trace.deployment_generation),
            deployment_digest=trace.deployment_digest.hex(),
            capability_digest=self.model.capability.digest,
            cost_table_id=self.model.machine.cost_table.cost_table_id,
            cost_table_digest=self.model.machine.cost_table.digest,
            technology_view=self.model.machine.cost_table.technology_view,
            batch_execution_id=self.batch_execution_id,
            physical_batch_size=self.batch_size,
            lane_index=int(lane_index),
            wave_index=int(wave_index),
            session_id=int(trace.session_id),
            session_generation_start=int(trace.session_generation_start),
            session_generation_end=int(trace.session_generation_end),
            transaction_id=int(trace.transaction_id),
            request_descriptor_id=int(trace.request_descriptor_id),
            request_descriptor_digest=trace.request_descriptor_digest.hex(),
            submission_digest=trace.submission_digest.hex(),
            trace_start=int(trace.trace_start),
            trace_stop=int(trace.trace_stop),
            trace_digest=_trace_digest(trace),
            functional_result_digest=_result_digest(trace),
            status=int(trace.result.status),
            produced_token_count=len(tokens),
            produced_token_id=int(token),
            eos_reason=int(trace.result.eos_reason),
            request_start_tick=int(request_start),
            token_commit_tick=int(commit_tick),
            completion_digest=hashlib.sha256(completion_record).hexdigest(),
        )

    def _publish_modeled_completions(
        self,
        wave: BatchWaveResult,
        traces: Mapping[int, FunctionalTraceSpan],
        *,
        request_start: int,
        commit_ticks: Mapping[int, int],
    ) -> None:
        for lane in wave.lanes:
            lane_index = int(lane.lane_index)
            trace = traces[lane_index]
            commit_tick = int(commit_ticks[lane_index])
            modeled = replace(lane.completion, completion_timestamp=commit_tick)
            record = modeled.encode()
            lane.completion = modeled
            lane.record = record
            history = self.history[lane_index]
            if trace.result.produced_tokens:
                if not history.commit_ticks:
                    raise TimingBindingError(
                        f"lane {lane_index} produced a token with no history slot"
                    )
                history.commit_ticks[-1] = commit_tick
            self._request_starts[lane_index].append(request_start)
            timing = self._make_timing_record(
                lane_index=lane_index,
                wave_index=wave.wave_index,
                trace=trace,
                completion=modeled,
                request_start=request_start,
                commit_tick=commit_tick,
                completion_record=record,
            )
            self._validate_live_binding(timing, trace, modeled, record)
            self._timing_records.append(timing)
            self._record_sources[(wave.wave_index, lane_index)] = (trace, modeled)

    def _validate_live_binding(
        self,
        timing: BoundTokenTiming,
        trace: FunctionalTraceSpan,
        completion: Completion,
        completion_record: bytes,
    ) -> None:
        expected = self._make_timing_record(
            lane_index=timing.lane_index,
            wave_index=timing.wave_index,
            trace=trace,
            completion=completion,
            request_start=timing.request_start_tick,
            commit_tick=timing.token_commit_tick,
            completion_record=completion_record,
        )
        if timing != expected:
            raise TimingBindingError(
                f"timing record for wave/lane {(timing.wave_index, timing.lane_index)} "
                "does not match its functional source"
            )
        if completion.completion_timestamp != timing.token_commit_tick:
            raise TimingBindingError("ABI completion does not carry modeled commit tick")
        if completion.transaction_id != timing.transaction_id:
            raise TimingBindingError("transaction identity changed at timing publication")
        if completion.session_id != timing.session_id:
            raise TimingBindingError("session identity changed at timing publication")
        if completion.session_generation != timing.session_generation_end:
            raise TimingBindingError("session generation changed at timing publication")
        if completion.produced_token_count != timing.produced_token_count:
            raise TimingBindingError("completion token count differs from functional result")
        if completion.final_token_id != timing.produced_token_id:
            raise TimingBindingError("completion token differs from functional result")
        if completion.eos_reason != timing.eos_reason:
            raise TimingBindingError("completion EOS differs from functional result")
        if hashlib.sha256(completion_record).hexdigest() != timing.completion_digest:
            raise TimingBindingError("modeled completion digest changed")
        if timing.token_commit_tick < timing.request_start_tick:
            raise TimingBindingError("token commit precedes request admission")
        if (
            timing.status == int(CompletionStatus.SUCCESS)
            and timing.produced_token_count != 1
        ):
            raise TimingBindingError(
                "successful GENERATE timing requires exactly one scalar token"
            )

    def verify_timing_record(self, timing: BoundTokenTiming) -> None:
        """Reject any changed identity, token, EOS or timestamp field."""

        key = (int(timing.wave_index), int(timing.lane_index))
        source = self._record_sources.get(key)
        authoritative = next(
            (
                record
                for record in self._timing_records
                if (record.wave_index, record.lane_index) == key
            ),
            None,
        )
        if source is None or authoritative is None:
            raise TimingBindingError(f"unknown timing wave/lane binding {key}")
        if timing != authoritative:
            raise TimingBindingError(f"timing wave/lane binding {key} was modified")
        trace, completion = source
        self._validate_live_binding(
            timing,
            trace,
            completion,
            # The digest is already bound and the record is deterministic from
            # the completion object, so regenerate rather than retain a second
            # mutable byte buffer.
            completion.encode(),
        )

    @staticmethod
    def _nearest_rank(values: Sequence[float], fraction: float) -> float | None:
        if not values:
            return None
        ordered = sorted(float(value) for value in values)
        index = max(0, math.ceil(fraction * len(ordered)) - 1)
        return ordered[index]

    def _timebase(self) -> dict[str, Any]:
        clock = float(self.model.machine.clock_hz)
        parameter = self.model.machine.used()["clock.frequency_hz"]
        same_process_view = (
            self.model.capability.technology_view
            == self.model.machine.cost_table.technology_view
        )
        characterized = (
            parameter.provenance is Provenance.CHARACTERIZED and same_process_view
        )
        provenance = self.model.machine.provenance_report()
        all_timing_inputs_characterized = provenance["class"] == "characterized"
        return {
            "unit": "target_cycles",
            "clock_frequency_hz": clock,
            "clock_period_seconds": 1.0 / clock,
            "clock_provenance": parameter.provenance.value,
            "clock_source": parameter.source,
            "capability_technology_view": self.model.capability.technology_view,
            "cost_table_technology_view": self.model.machine.cost_table.technology_view,
            "same_process_view": same_process_view,
            "process_timebase_characterized": characterized,
            "modeled_input_provenance": provenance,
            "all_timing_inputs_characterized": all_timing_inputs_characterized,
            "host_wall_time_used": False,
            "retired_instruction_count_used_as_time": False,
            "projection_used_as_qualified_tpot": False,
        }

    def _performance_metrics(self, qualified: bool) -> dict[str, Any]:
        clock = float(self.model.machine.clock_hz)
        sequences: list[dict[str, Any]] = []
        raw_seconds: list[float] = []
        first_start: int | None = None
        last_commit: int | None = None
        for lane, history in enumerate(self.history):
            commits = [int(value) for value in history.commit_ticks]
            starts = self._request_starts[lane]
            intervals = [later - earlier for earlier, later in zip(commits, commits[1:])]
            seconds = [value / clock for value in intervals]
            raw_seconds.extend(seconds)
            if starts:
                first_start = starts[0] if first_start is None else min(first_start, starts[0])
            if commits:
                last_commit = commits[-1] if last_commit is None else max(last_commit, commits[-1])
            sequences.append(
                {
                    "sequence_index": lane,
                    "generated_token_count": len(history.tokens),
                    "request_start_tick": starts[0] if starts else None,
                    "transaction_request_start_ticks": list(starts),
                    "token_commit_ticks": commits,
                    "ttft_cycles": commits[0] - starts[0] if starts and commits else None,
                    "decode_step_cycles": intervals,
                    "decode_step_seconds": seconds,
                }
            )
        total_tokens = sum(len(history.tokens) for history in self.history)
        window_cycles = (
            last_commit - first_start
            if first_start is not None and last_commit is not None
            else 0
        )
        return {
            "qualified_target_tpot": qualified,
            "sequences": sequences,
            "distribution": {
                "sample_count": len(raw_seconds),
                "mean_seconds": (
                    sum(raw_seconds) / len(raw_seconds) if raw_seconds else None
                ),
                "p50_seconds": self._nearest_rank(raw_seconds, 0.50),
                "p95_seconds": self._nearest_rank(raw_seconds, 0.95),
                "p99_seconds": self._nearest_rank(raw_seconds, 0.99),
                "max_seconds": max(raw_seconds) if raw_seconds else None,
            },
            "aggregate": {
                "generated_tokens": total_tokens,
                "window_cycles": window_cycles,
                "window_seconds": window_cycles / clock if window_cycles else None,
                "generated_tokens_per_second": (
                    total_tokens * clock / window_cycles if window_cycles else None
                ),
            },
        }

    def _resource_report(self) -> dict[str, Any]:
        span = max(self._wave_end, 1)
        nodes: list[dict[str, Any]] = []
        for node_id, state in enumerate(self._node_states):
            nodes.append(
                {
                    "node_id": node_id,
                    "sequencer_end_tick": state.seq_free,
                    "totals": dict(state.totals),
                    "scheduler": {
                        "policy": "earliest-ready_round-robin-tie-break",
                        "issue_count": state.issue_count,
                        "cross_lane_transitions": state.cross_lane_transitions,
                        "cross_lane_overlap_events": state.cross_lane_overlap_events,
                        "issue_order_digest": state.issue_order_digest.hex(),
                        "first_issue_samples": list(state.first_issue_samples),
                        "last_issue_samples": list(state.last_issue_samples),
                    },
                    "queues": {
                        name: queue.to_dict()
                        for name, queue in sorted(state.queues.items())
                    },
                    "engines": {
                        name: engine.to_dict(span)
                        for name, engine in sorted(state.engines.items())
                    },
                    "memory": state.memory.report(span),
                }
            )
        fabric = None
        if self.fabric is not None:
            fabric = self.fabric.to_dict()
        return {
            "modeled_makespan_cycles": self._wave_end,
            "node_count": len(nodes),
            "nodes": nodes,
            "fabric": fabric,
        }

    def evidence(
        self,
        expected_tokens: Sequence[Sequence[int]] | None = None,
        *,
        expected_eos_reasons: Sequence[int] | None = None,
        full_model_execution: bool = False,
    ) -> dict[str, Any]:
        """Return ordered correctness and TPOT gates for this same execution."""

        body = super().evidence(expected_tokens)
        problems = list(body["problems"]) + list(self._timing_problems)
        for timing in self._timing_records:
            try:
                self.verify_timing_record(timing)
            except TimingBindingError as exc:
                problems.append(str(exc))

        eos_match: list[bool | None] = [None] * self.batch_size
        if expected_eos_reasons is not None:
            if len(expected_eos_reasons) != self.batch_size:
                problems.append(
                    f"expected EOS count {len(expected_eos_reasons)} does not match "
                    f"batch size {self.batch_size}"
                )
            else:
                for lane, expected in enumerate(expected_eos_reasons):
                    eos_match[lane] = self.history[lane].eos_reason == int(expected)
                    if not eos_match[lane]:
                        problems.append(
                            f"lane {lane} EOS mismatch: actual="
                            f"{self.history[lane].eos_reason}, expected={int(expected)}"
                        )

        tokens_exact = (
            expected_tokens is not None
            and len(expected_tokens) == self.batch_size
            and all(
                sequence["expected_tokens_match"] is True
                for sequence in body["sequences"]
            )
        )
        eos_exact = bool(eos_match) and all(match is True for match in eos_match)
        terminal = not any(self.active)
        records_complete = len(self._timing_records) == sum(
            len(history.transaction_ids) for history in self.history
        )
        if not records_complete:
            problems.append("not every functional transaction has one timing record")
        monotonic = all(
            all(later > earlier for earlier, later in zip(history.commit_ticks, history.commit_ticks[1:]))
            for history in self.history
        )
        if not monotonic:
            problems.append("per-lane token commit ticks are not strictly increasing")

        gate1_pass = bool(
            full_model_execution
            and tokens_exact
            and eos_exact
            and terminal
            and records_complete
            and monotonic
            and not problems
        )
        timebase = self._timebase()
        timing_qualified = bool(
            timebase["process_timebase_characterized"]
            and timebase["all_timing_inputs_characterized"]
        )
        tpot_eligible = gate1_pass and timing_qualified
        if gate1_pass:
            gate1_status = "pass"
        elif expected_tokens is None or expected_eos_reasons is None:
            gate1_status = "not_evaluable"
        elif (
            not full_model_execution
            and tokens_exact
            and eos_exact
            and terminal
            and records_complete
            and monotonic
            and not problems
        ):
            gate1_status = "not_qualified"
        else:
            gate1_status = "fail"

        for lane, sequence in enumerate(body["sequences"]):
            sequence["request_start_ticks"] = list(self._request_starts[lane])
            sequence["token_commit_ticks"] = list(self.history[lane].commit_ticks)
            sequence["expected_eos_reason"] = (
                None
                if expected_eos_reasons is None
                or len(expected_eos_reasons) != self.batch_size
                else int(expected_eos_reasons[lane])
            )
            sequence["eos_reason_match"] = eos_match[lane]

        body.update(
            {
                "schema": CYCLE_BATCH_SCHEMA,
                "status": "rejected" if problems else body["status"],
                "scheduler": "shared_resource_cycle_v1",
                "problems": problems,
                "timing": {
                    "latency_boundary": "request_admission_to_token_commit",
                    "timebase": timebase,
                    "records": [record.to_dict() for record in self._timing_records],
                    "shared_resources": self._resource_report(),
                    "performance": self._performance_metrics(tpot_eligible),
                },
                "acceptance_gates": {
                    "order": [
                        "exact_output_tokens_and_eos",
                        "same_execution_target_tpot",
                    ],
                    "gate1_correctness": {
                        "status": gate1_status,
                        "full_model_execution": bool(full_model_execution),
                        "exact_token_equality": tokens_exact,
                        "exact_eos_equality": eos_exact,
                        "all_lanes_terminal": terminal,
                        "same_execution_timing_records_complete": records_complete,
                    },
                    "gate2_tpot": {
                        "status": "eligible" if tpot_eligible else "blocked",
                        "gate1_precedes_tpot": True,
                        "gate1_passed": gate1_pass,
                        "characterized_process_timebase": timebase[
                            "process_timebase_characterized"
                        ],
                        "all_timing_inputs_characterized": timebase[
                            "all_timing_inputs_characterized"
                        ],
                        "eligible_for_target_tpot": tpot_eligible,
                    },
                },
            }
        )
        body["claim_boundary"].update(
            {
                "engine_coissue_implemented": True,
                "shared_resource_cycle_timing_implemented": True,
                "architectural_request_start_and_token_commit_ticks": True,
                "retired_instruction_timing_used": False,
                "functional_tokens_changed_by_timing_replay": False,
                "eligible_for_full_model_token_correctness_gate": gate1_pass,
                "eligible_for_target_tpot": tpot_eligible,
                "remaining_boundary": (
                    "governed full-model execution and fully characterized "
                    "same-process timing are still required whenever either "
                    "acceptance gate is blocked"
                ),
            }
        )
        return body


__all__ = [
    "BoundTokenTiming",
    "CYCLE_BATCH_SCHEMA",
    "CycleBatchScheduler",
    "TIMING_RECORD_SCHEMA",
    "TimingBindingError",
]
