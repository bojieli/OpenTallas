"""Engine interface for the ABI 3.0 functional device.

Every engine family implements the same contract: given a decoded OPERATOR (or
COMMUNICATION / STATE) descriptor and the current loop and symbol bindings, read
its operands through tensor views, compute under a declared numeric contract,
write its results through tensor views, and account its work in the shared
counter registry.

An engine never reads the model graph, never reads the deployment manifest, and
never receives a Python-side value that did not come from device memory or a
request field.  That is what keeps "artifact-only execution" true: the engine is
the datapath, the microsequencer is the control, and the compiled program is the
only thing that connects them.

NumPy -- and, where scale demands it, PyTorch -- is the *arithmetic substrate*
of a simulated engine, exactly as a C++ simulator would call a BLAS kernel.  It
is never a model.  Each engine must reproduce the numeric contract named by its
descriptor, and each contract has a bit-exact scalar oracle.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Mapping, Protocol

import numpy as np

from runtime.abi3.constants import (
    DType,
    Major,
    NO_ID,
    ReductionOrder,
    RoundingMode,
)
from runtime.abi3.deployment import DescriptorTable
from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType
from runtime.sim.counters import CounterSet
from runtime.sim.memory import DeviceMemory, ResolvedView, ViewResolver


class EngineError(Exception):
    """Raised by an engine on a data-dependent or descriptor fault."""

    def __init__(self, message: str, trap_class: int = 8) -> None:
        super().__init__(message)
        self.trap_class = trap_class


@dataclass(slots=True)
class NumericProfile:
    """A decoded numeric descriptor."""

    descriptor_id: int
    input_dtype: int
    second_input_dtype: int
    accumulator_dtype: int
    output_dtype: int
    rounding_mode: int
    reduction_order: int
    saturate: bool
    nan_policy: int
    epsilon_bits: int
    scale_bits: int
    flags: int
    contract: str = ""

    @property
    def epsilon(self) -> float:
        return float(
            np.frombuffer(
                np.uint32(self.epsilon_bits).tobytes(), dtype=np.float32
            )[0]
        )

    @property
    def scale(self) -> float:
        return float(
            np.frombuffer(np.uint32(self.scale_bits).tobytes(), dtype=np.float32)[0]
        )


@dataclass
class EngineContext:
    """Everything an engine may legally see."""

    table: DescriptorTable
    memory: DeviceMemory
    views: ViewResolver
    counters: CounterSet
    loops: dict[int, int]
    symbols: dict[int, int]
    session: Any = None
    device: Any = None
    notes: dict[str, Any] = dc_field(default_factory=dict)
    node_memories: tuple[DeviceMemory, ...] = ()
    """Every logical node's arena, in ascending node order.

    A single-node deployment leaves this empty and :attr:`memory` is the whole
    device.  A cluster deployment fills it, and :attr:`memory` is whichever
    node the microsequencer is currently issuing for.  Only the LINK engine
    reads it: every other engine sees exactly one node's memory, which is what
    makes an inter-node transfer expressible only as a LINK instruction.
    """

    # -- node access ------------------------------------------------------
    @property
    def node_count(self) -> int:
        return len(self.node_memories) or 1

    def node_memory(self, node: int) -> DeviceMemory:
        """The arena of logical node ``node``.

        With one node -- or with participants that are not nodes, which is what
        a wafer's reticles and tiles are -- there is one arena and every
        participant lives in it.
        """
        if not self.node_memories:
            return self.memory
        if not 0 <= node < len(self.node_memories):
            raise EngineError(
                f"node {node} is outside the {len(self.node_memories)} admitted "
                "nodes",
                trap_class=11,
            )
        return self.node_memories[node]

    # -- descriptor access ----------------------------------------------
    def operator(self, descriptor_id: int) -> Descriptor:
        return self.table.get(descriptor_id, ExtendedDescriptorType.OPERATOR)

    def numeric(self, descriptor_id: int) -> NumericProfile:
        if descriptor_id == NO_ID:
            raise EngineError("operator has no numeric profile", trap_class=3)
        descriptor = self.table.get(descriptor_id, ExtendedDescriptorType.NUMERIC)
        payload = descriptor.payload
        return NumericProfile(
            descriptor_id=descriptor_id,
            input_dtype=payload["input_dtype"],
            second_input_dtype=payload["second_input_dtype"],
            accumulator_dtype=payload["accumulator_dtype"],
            output_dtype=payload["output_dtype"],
            rounding_mode=payload["rounding_mode"],
            reduction_order=payload["reduction_order"],
            saturate=bool(payload["saturate"]),
            nan_policy=payload["nan_policy"],
            epsilon_bits=payload["epsilon_bits"],
            scale_bits=payload["scale_bits"],
            flags=payload["flags"],
        )

    def schedule(self, descriptor_id: int) -> Mapping[str, int] | None:
        if descriptor_id == NO_ID:
            return None
        return self.table.get(
            descriptor_id, ExtendedDescriptorType.SCHEDULE
        ).payload

    # -- view access ------------------------------------------------------
    def view(self, view_id: int) -> ResolvedView:
        if view_id == NO_ID:
            raise EngineError("operator references NO_ID as a view", trap_class=3)
        return self.views.resolve(view_id, self.loops, self.symbols)

    def input_view(self, operator: Descriptor, slot: int) -> ResolvedView:
        return self.view(operator.payload[f"input_view_{slot}"])

    def output_view(self, operator: Descriptor, slot: int = 0) -> ResolvedView:
        return self.view(operator.payload[f"output_view_{slot}"])

    def optional_input(self, operator: Descriptor, slot: int) -> ResolvedView | None:
        vid = operator.payload[f"input_view_{slot}"]
        return None if vid == NO_ID else self.view(vid)

    def read(self, view: ResolvedView) -> np.ndarray:
        array = self.views.read_array(view)
        self._account_read(view, array)
        return array

    def write(self, view: ResolvedView, values: np.ndarray) -> None:
        self.views.write_array(view, values)
        self._account_write(view, values)

    def _account_read(self, view: ResolvedView, array: np.ndarray) -> None:
        obj = self.memory[view.object_id]
        nbytes = int(array.size) * int(array.dtype.itemsize)
        key = {
            "HBM": "hbm.bytes_read",
            "SRAM": "sram.bytes_read",
            "ROM": "rom.bytes_read",
            "HOST": "host.bytes_read",
            "STATE": "state.bytes_read",
        }[obj.storage_class.name]
        self.counters.add(key, nbytes)

    def _account_write(self, view: ResolvedView, array: np.ndarray) -> None:
        obj = self.memory[view.object_id]
        nbytes = int(array.size) * int(array.dtype.itemsize)
        key = {
            "HBM": "hbm.bytes_written",
            "SRAM": "sram.bytes_written",
            "ROM": "rom.bytes_read",  # unreachable: ROM has no write permission
            "HOST": "host.bytes_written",
            "STATE": "state.bytes_written",
        }[obj.storage_class.name]
        self.counters.add(key, nbytes)

    # -- symbols ----------------------------------------------------------
    def symbol(self, symbol_id: int) -> int:
        try:
            return self.symbols[int(symbol_id)]
        except KeyError:
            raise EngineError(
                f"runtime symbol {symbol_id} is unbound", trap_class=3
            ) from None


class Engine(Protocol):
    """One engine family."""

    family: Major

    def execute(
        self, ctx: EngineContext, sub: int, descriptor: Descriptor
    ) -> None: ...


_REGISTRY: dict[tuple[int, int], Callable[[EngineContext, int, Descriptor], None]] = {}


def register(family: Major, sub: int):
    """Decorator registering one ``(family, subopcode)`` implementation."""

    def _wrap(function):
        key = (int(family), int(sub))
        if key in _REGISTRY:
            raise RuntimeError(f"engine {family.name}.{sub} is already registered")
        _REGISTRY[key] = function
        return function

    return _wrap


def dispatch(
    ctx: EngineContext, family: int, sub: int, descriptor: Descriptor
) -> None:
    """Execute one engine operation, failing closed on an unimplemented one."""
    handler = _REGISTRY.get((int(family), int(sub)))
    if handler is None:
        raise EngineError(
            f"engine operation {Major(family).name}.{sub:#04x} is not implemented; "
            "no simulator, firmware or framework fallback may substitute for it",
            trap_class=4,
        )
    handler(ctx, sub, descriptor)


def implemented() -> frozenset[tuple[int, int]]:
    return frozenset(_REGISTRY)


def snapshot_registry() -> dict[tuple[int, int], object]:
    """A copy of the dispatch table, for a caller that is about to replace it.

    The RTL vector generators bind every dispatchable operation to a recording
    no-op, because RTL 3.0 implements the control plane and a golden model that
    *did* compute would trap on data the RTL never sees.  That is correct for
    those generators and wrong for everyone else: the table is process-global,
    ``register`` refuses to overwrite so the bindings are written directly, and
    ``importlib`` caches the engine modules so re-importing them does not put
    the real handlers back.  An in-process caller that ran afterwards therefore
    executed no-ops and got empty results with no error -- legal values, no
    trap, nothing refused.  Pair this with :func:`restore_registry`.
    """
    return dict(_REGISTRY)


def restore_registry(snapshot: dict[tuple[int, int], object]) -> None:
    """Put back a table captured by :func:`snapshot_registry`."""
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


#: Families the microsequencer executes itself rather than dispatching to an
#: engine.  Control flow, transactional state, observation and recovery are
#: sequencer responsibilities under ADR-003 section 5, so they are not engine
#: registrations and must not be reported as missing engines.
SEQUENCER_FAMILIES: frozenset[int] = frozenset(
    {
        int(Major.CONTROL),
        int(Major.STATE),
        int(Major.OBSERVATION),
        int(Major.RECOVERY),
    }
)


def coverage_report() -> dict[str, list[str]]:
    """Which frozen subopcodes have an implementation and which do not.

    Sequencer-executed families are reported separately: they are implemented
    in ``runtime/sim/device.py``, not registered here, so counting them as
    missing engines would misreport a complete device as incomplete.
    """
    from runtime.abi3.constants import SUBOPCODES

    present: list[str] = []
    missing: list[str] = []
    sequencer: list[str] = []
    for family, enum_type in SUBOPCODES.items():
        for member in enum_type:
            name = f"{Major(family).name}.{member.name}"
            if int(family) in SEQUENCER_FAMILIES:
                sequencer.append(name)
            elif (int(family), int(member)) in _REGISTRY:
                present.append(name)
            else:
                missing.append(name)
    return {
        "implemented": sorted(present),
        "missing": sorted(missing),
        "sequencer_executed": sorted(sequencer),
    }
