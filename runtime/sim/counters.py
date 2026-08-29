"""Architectural counter registry and snapshot store.

ADR-003 section 13 requires that counter event definitions be versioned and
*identical* in the functional simulator, the cycle simulator and RTL.  This
module is therefore the single definition site: the cycle model and the RTL
scoreboard import these names rather than inventing parallel ones.

All counters are unsigned 64-bit saturating with a sticky overflow flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Iterator, Mapping

from runtime.abi3.constants import CounterGroup, counter_id

UINT64_MAX = (1 << 64) - 1


def _reg(group: CounterGroup, event: int, name: str) -> tuple[int, str]:
    return counter_id(group, event), name


#: Frozen counter registry.  Adding an event is additive; changing one is not.
COUNTERS: dict[int, str] = dict(
    [
        # 0x01 instruction
        _reg(CounterGroup.INSTRUCTION, 1, "instructions.fetched"),
        _reg(CounterGroup.INSTRUCTION, 2, "instructions.issued"),
        _reg(CounterGroup.INSTRUCTION, 3, "instructions.retired"),
        _reg(CounterGroup.INSTRUCTION, 4, "instructions.predicated_off"),
        _reg(CounterGroup.INSTRUCTION, 5, "instructions.trapped"),
        _reg(CounterGroup.INSTRUCTION, 6, "instructions.replayed"),
        _reg(CounterGroup.INSTRUCTION, 7, "control.loop_iterations"),
        _reg(CounterGroup.INSTRUCTION, 8, "control.branches_taken"),
        # 0x02 engine and queue
        _reg(CounterGroup.ENGINE_QUEUE, 1, "engine.dma.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 2, "engine.tensor.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 3, "engine.vector.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 4, "engine.attention.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 5, "engine.route.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 6, "engine.reduction.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 7, "engine.selection.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 8, "engine.state.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 9, "engine.link.descriptors"),
        _reg(CounterGroup.ENGINE_QUEUE, 10, "queue.max_occupancy"),
        _reg(CounterGroup.ENGINE_QUEUE, 11, "queue.wait_events"),
        # 0x03 memory
        _reg(CounterGroup.MEMORY, 1, "hbm.bytes_read"),
        _reg(CounterGroup.MEMORY, 2, "hbm.bytes_written"),
        _reg(CounterGroup.MEMORY, 3, "sram.bytes_read"),
        _reg(CounterGroup.MEMORY, 4, "sram.bytes_written"),
        _reg(CounterGroup.MEMORY, 5, "rom.bytes_read"),
        _reg(CounterGroup.MEMORY, 6, "host.bytes_read"),
        _reg(CounterGroup.MEMORY, 7, "host.bytes_written"),
        _reg(CounterGroup.MEMORY, 8, "state.bytes_read"),
        _reg(CounterGroup.MEMORY, 9, "state.bytes_written"),
        _reg(CounterGroup.MEMORY, 10, "dma.transfers"),
        _reg(CounterGroup.MEMORY, 11, "dma.gather_elements"),
        _reg(CounterGroup.MEMORY, 12, "dma.scatter_elements"),
        # 0x04 tensor
        _reg(CounterGroup.TENSOR, 1, "tensor.multiplications"),
        _reg(CounterGroup.TENSOR, 2, "tensor.additions"),
        _reg(CounterGroup.TENSOR, 3, "tensor.conversions"),
        _reg(CounterGroup.TENSOR, 4, "tensor.saturations"),
        _reg(CounterGroup.TENSOR, 5, "tensor.exceptional_values"),
        _reg(CounterGroup.TENSOR, 6, "tensor.output_elements"),
        _reg(CounterGroup.TENSOR, 7, "tensor.grouped_launches"),
        _reg(CounterGroup.TENSOR, 8, "tensor.routed_launches"),
        _reg(CounterGroup.TENSOR, 9, "tensor.embedding_rows"),
        # 0x05 vector and reduction
        _reg(CounterGroup.VECTOR_REDUCTION, 1, "vector.elements"),
        _reg(CounterGroup.VECTOR_REDUCTION, 2, "vector.norm_rows"),
        _reg(CounterGroup.VECTOR_REDUCTION, 3, "vector.rope_pairs"),
        _reg(CounterGroup.VECTOR_REDUCTION, 4, "vector.activation_elements"),
        _reg(CounterGroup.VECTOR_REDUCTION, 5, "vector.conversions"),
        _reg(CounterGroup.VECTOR_REDUCTION, 6, "reduction.elements"),
        _reg(CounterGroup.VECTOR_REDUCTION, 7, "reduction.ordered_sums"),
        _reg(CounterGroup.VECTOR_REDUCTION, 8, "vector.softmax_rows"),
        _reg(CounterGroup.VECTOR_REDUCTION, 9, "vector.compress_rows"),
        _reg(CounterGroup.VECTOR_REDUCTION, 10, "vector.mhc_sites"),
        # 0x06 attention
        _reg(CounterGroup.ATTENTION, 1, "attention.score_multiplications"),
        _reg(CounterGroup.ATTENTION, 2, "attention.value_multiplications"),
        _reg(CounterGroup.ATTENTION, 3, "attention.context_positions"),
        _reg(CounterGroup.ATTENTION, 4, "attention.sparse_indices"),
        _reg(CounterGroup.ATTENTION, 5, "attention.heads"),
        _reg(CounterGroup.ATTENTION, 6, "attention.kv_bytes_read"),
        # 0x07 route and expert
        _reg(CounterGroup.ROUTE_EXPERT, 1, "route.selected_experts"),
        _reg(CounterGroup.ROUTE_EXPERT, 2, "route.dispatched_bytes"),
        _reg(CounterGroup.ROUTE_EXPERT, 3, "route.rejected_ids"),
        _reg(CounterGroup.ROUTE_EXPERT, 4, "route.topk_candidates"),
        _reg(CounterGroup.ROUTE_EXPERT, 5, "route.expert_reductions"),
        _reg(CounterGroup.ROUTE_EXPERT, 6, "route.hash_lookups"),
        # 0x08 state
        _reg(CounterGroup.STATE, 1, "state.reads"),
        _reg(CounterGroup.STATE, 2, "state.prepares"),
        _reg(CounterGroup.STATE, 3, "state.commits"),
        _reg(CounterGroup.STATE, 4, "state.discards"),
        _reg(CounterGroup.STATE, 5, "state.rows_committed"),
        _reg(CounterGroup.STATE, 6, "state.generation_advances"),
        # 0x09 selection and EOS
        _reg(CounterGroup.SELECTION_EOS, 1, "selection.tokens_selected"),
        _reg(CounterGroup.SELECTION_EOS, 2, "selection.tokens_appended"),
        _reg(CounterGroup.SELECTION_EOS, 3, "selection.eos_stops"),
        _reg(CounterGroup.SELECTION_EOS, 4, "selection.length_stops"),
        _reg(CounterGroup.SELECTION_EOS, 5, "selection.invalid_tokens"),
        _reg(CounterGroup.SELECTION_EOS, 6, "selection.vocabulary_elements"),
        _reg(CounterGroup.SELECTION_EOS, 7, "selection.tie_multiplicity"),
        # 0x0a communication
        _reg(CounterGroup.COMMUNICATION, 1, "link.messages_sent"),
        _reg(CounterGroup.COMMUNICATION, 2, "link.messages_received"),
        _reg(CounterGroup.COMMUNICATION, 3, "link.bytes_sent"),
        _reg(CounterGroup.COMMUNICATION, 4, "link.bytes_received"),
        _reg(CounterGroup.COMMUNICATION, 5, "link.collectives"),
        _reg(CounterGroup.COMMUNICATION, 6, "link.barriers"),
        _reg(CounterGroup.COMMUNICATION, 7, "link.retries"),
        _reg(CounterGroup.COMMUNICATION, 8, "link.credit_stalls"),
        _reg(CounterGroup.COMMUNICATION, 9, "link.remote_dma_bytes"),
        # 0x0b fault and recovery
        _reg(CounterGroup.FAULT_RECOVERY, 1, "fault.traps"),
        _reg(CounterGroup.FAULT_RECOVERY, 2, "fault.poisoned_transactions"),
        _reg(CounterGroup.FAULT_RECOVERY, 3, "fault.cancellations"),
        _reg(CounterGroup.FAULT_RECOVERY, 4, "fault.drains"),
        _reg(CounterGroup.FAULT_RECOVERY, 5, "fault.watchdog_events"),
        _reg(CounterGroup.FAULT_RECOVERY, 6, "fault.resets"),
        _reg(CounterGroup.FAULT_RECOVERY, 7, "fault.integrity_events"),
        # 0x0c latency
        _reg(CounterGroup.LATENCY, 1, "latency.transaction_cycles"),
        _reg(CounterGroup.LATENCY, 2, "latency.issue_cycles"),
        _reg(CounterGroup.LATENCY, 3, "latency.stall_cycles"),
    ]
)

NAME_TO_ID: dict[str, int] = {name: cid for cid, name in COUNTERS.items()}


class CounterSet:
    """Saturating unsigned 64-bit counters with sticky overflow."""

    __slots__ = ("_values", "_overflow")

    def __init__(self) -> None:
        self._values: dict[str, int] = {}
        self._overflow: set[str] = set()

    def add(self, name: str, amount: int = 1) -> None:
        if amount == 0:
            return
        if name not in NAME_TO_ID:
            raise KeyError(f"counter {name!r} is not in the frozen registry")
        value = self._values.get(name, 0) + amount
        if value > UINT64_MAX:
            value = UINT64_MAX
            self._overflow.add(name)
        self._values[name] = value

    def max(self, name: str, value: int) -> None:
        if name not in NAME_TO_ID:
            raise KeyError(f"counter {name!r} is not in the frozen registry")
        if value > self._values.get(name, 0):
            self._values[name] = min(value, UINT64_MAX)

    def get(self, name: str) -> int:
        return self._values.get(name, 0)

    def __getitem__(self, name: str) -> int:
        return self.get(name)

    def merge(self, other: "CounterSet") -> None:
        for name, value in other._values.items():
            self.add(name, value)
        self._overflow |= other._overflow

    def snapshot(self) -> dict[str, int]:
        return dict(sorted(self._values.items()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "counters": self.snapshot(),
            "sticky_overflow": sorted(self._overflow),
            "registry_size": len(COUNTERS),
        }

    def reset(self) -> None:
        self._values.clear()
        self._overflow.clear()
