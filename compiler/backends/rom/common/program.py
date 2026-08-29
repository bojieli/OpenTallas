"""Loop-compressed, IR-driven lowering shared by both ROM products.

The neutral Tensor Kernel IR names one kernel per layer per operation: Qwen3-8B
is roughly 617 kernels, 36 structurally identical layers of about 17 operations.
Emitting one instruction per kernel would reproduce the ABI 2.5 failure this
program exists to remove.  So this module compresses:

* layers whose kernel signatures are identical and whose layer numbers are
  consecutive form one **run**;
* a run is emitted once, between ``CONTROL.LOOP_SETUP`` and
  ``CONTROL.LOOP_NEXT`` (:meth:`~runtime.abi3.builder.DeploymentBuilder.
  open_loop` / :meth:`~runtime.abi3.builder.DeploymentBuilder.close_loop`); and
* every weight the body reads lives in one ROM region striped by layer, so its
  tensor view is a single descriptor carrying
  ``DynamicTerm.loop(run_loop, slot_element_stride)``.

Region identity is derived *structurally* -- run index, body position, operand
slot -- never from tensor names, so the same lowering serves any front end that
emits a conforming graph.

Opcodes come only from :data:`compiler.ir.v3.lowering.KERNEL_TO_ENGINE`.  There
is no ``ROM_MATMUL``: a MATMUL binding a ROM weight view is ``TENSOR.MATMUL``,
and the storage class lives on the memory object, which is exactly why a ROM and
an HBM deployment of the same graph differ in nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Iterable, Mapping, Sequence

from compiler.ir.v3.kernel_ir import (
    IRError,
    Kernel,
    KernelGraph,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE, EngineOp
from runtime.abi3.builder import BuildError, DeploymentBuilder, DynamicTerm
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Attention,
    Reduction,
    Control,
    CounterGroup,
    DTYPE_BITS,
    DType,
    Dma,
    Feature,
    Major,
    NO_ID,
    Permission,
    ReductionOrder,
    Route,
    Selection,
    State,
    StateClass,
    StorageClass,
    Tensor as TensorOp,
    TopologyClass,
    Vector,
    counter_id,
)
from runtime.abi3.deployment import Deployment, ObjectSource
from runtime.abi3.descriptors import MAX_RANK, Phase, SelectionMode, Symbol

from .image import (
    DTYPE_BY_NAME,
    DefectRecord,
    RegionRequest,
    RomCoordinate,
    RomImageError,
    RomImagePlan,
    RomLayoutPolicy,
    RomMember,
    emit_rom_objects,
    plan_rom_image,
)

MAX_OPERATOR_INPUTS = 4
MAX_OPERATOR_OUTPUTS = 2
MAX_WAIT_PRODUCERS = 12

WEIGHT_ROLES = frozenset({"weight", "constant"})

#: ``TA-ABI3-OPCONV-1`` amendment A7: the sequential contract is the scalar
#: oracle used for numeric qualification; execution declares the blocked
#: contract.  The substitution is applied identically for ROM and HBM, so the
#: two deployments stay bit-comparable, and it is recorded in the manifest.
EXECUTION_CONTRACT: Mapping[str, str] = {
    "bf16_bf16_fp32_sequential_rne_v1": "bf16_bf16_fp32_blocked_rne_v1",
}

#: What limits an operator's rate.  The cycle model reads this out of the
#: SCHEDULE descriptor together with the tile mapping.
class ResourceBound:
    ROM_READ = 1
    TENSOR_LANES = 2
    MEMORY_PORT = 3
    STATE_TRANSACTION = 4
    LINK = 5
    SELECTION = 6


#: On-fabric route class of an operator's operands.
class RouteClass:
    LOCAL = 0
    INTRA_RETICLE = 1
    INTER_RETICLE = 2


ENGINE_KEY_BY_FAMILY: Mapping[int, str] = {
    Major.DMA: "dma",
    Major.TENSOR: "tensor",
    Major.VECTOR: "vector",
    Major.ATTENTION: "attention",
    Major.ROUTE: "route",
    Major.REDUCTION: "reduction",
    Major.SELECTION: "selection",
    Major.STATE: "state",
    Major.LINK: "link",
}

#: ``aux0`` sub-case values for the subopcodes several neutral kinds share
#: (``TA-ABI3-OPCONV-1`` sections 3 and 12).
COMPRESS_SUBCASE: Mapping[str, int] = {
    "COMPRESS_PROJECT": 0,
    "COMPRESS_POOL": 1,
    "COMPRESS_STATE_UPDATE": 2,
}
MHC_SUBCASE: Mapping[str, int] = {
    "HYPER_CONNECT_PRE": 0,
    "HYPER_CONNECT_POST": 1,
    "HYPER_CONNECT_HEAD": 2,
}
SCALE_SUBCASE: Mapping[str, int] = {"SCALE": 0, "MUL": 1, "SIGMOID": 2}

STATE_CLASS_BY_NAME: Mapping[str, StateClass] = {
    "kv_cache": StateClass.KV_CACHE,
    "compressed_kv": StateClass.COMPRESSED_KV,
    "token_ring": StateClass.TOKEN_RING,
    "position_cursor": StateClass.POSITION_CURSOR,
    "route_history": StateClass.ROUTE_HISTORY,
    "scratch": StateClass.SCRATCH,
}

COUNTER_GROUP_BY_FAMILY: Mapping[int, CounterGroup] = {
    Major.DMA: CounterGroup.MEMORY,
    Major.TENSOR: CounterGroup.TENSOR,
    Major.VECTOR: CounterGroup.VECTOR_REDUCTION,
    Major.ATTENTION: CounterGroup.ATTENTION,
    Major.ROUTE: CounterGroup.ROUTE_EXPERT,
    Major.REDUCTION: CounterGroup.VECTOR_REDUCTION,
    Major.SELECTION: CounterGroup.SELECTION_EOS,
    Major.STATE: CounterGroup.STATE,
    Major.LINK: CounterGroup.COMMUNICATION,
    Major.CONTROL: CounterGroup.INSTRUCTION,
}


class RomLoweringError(ValueError):
    """Raised when a neutral graph cannot be lowered onto a ROM target."""


# ---------------------------------------------------------------------------
# Structural analysis
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class LayerRun:
    """A span of layers a single loop body covers.

    ``period`` is how many source layers one loop iteration executes.  A stack
    of identical layers has ``period == 1``.  A stack that *alternates* -- as
    DeepSeek-V4-Flash does, whose 43 layers run window, window, then compressed
    sparse and compressed dense attention in alternation -- has ``period == 2``,
    and the body holds both layers' kernels.  Without periodic detection an
    alternating stack would compress to nothing: 41 runs of one layer each.
    """

    index: int
    layers: tuple[int, ...]
    period: int
    groups: int
    body: tuple[tuple[Kernel, ...], ...]  # [body position][group]

    @property
    def length(self) -> int:
        """Loop trip count: how many times the body executes."""
        return self.groups

    @property
    def positions(self) -> int:
        return len(self.body)

    @property
    def layers_covered(self) -> int:
        return len(self.layers)


@dataclass(frozen=True, slots=True)
class GraphAnalysis:
    prologue: tuple[Kernel, ...]
    runs: tuple[LayerRun, ...]
    epilogue: tuple[Kernel, ...]
    producer: Mapping[str, Kernel]
    #: ``tensor_id -> (run index, body position, output slot)`` for tensors a
    #: compressed body produces; every group of the run shares one buffer.
    body_output: Mapping[str, tuple[int, int, int]]
    #: ``tensor_id -> (run index, body position, input slot)`` for every operand
    #: a compressed body reads, first occurrence wins.
    body_input: Mapping[str, tuple[int, int, int]]
    #: ``(run, position, slot) -> the operand of that slot in each group``.
    body_operand: Mapping[tuple[int, int, int], tuple[str, ...]]

    @property
    def compressed_kernel_count(self) -> int:
        return (
            len(self.prologue)
            + sum(run.positions for run in self.runs)
            + len(self.epilogue)
        )


def _kernel_signature(kernel: Kernel, tensors: Mapping[str, Tensor]) -> tuple[Any, ...]:
    """Structural identity of a kernel, including its weights' byte lengths.

    Byte lengths belong in the signature because a loop-addressed ROM region
    needs a constant stride: two layers that differ only in how large one
    projection is cannot share a compressed body.
    """

    def weight_extent(name: str) -> int:
        tensor = tensors[name]
        if tensor.role not in WEIGHT_ROLES or tensor.binding is None:
            return -1
        return tensor.binding.bytes

    return (
        kernel.kind,
        kernel.numeric_contract,
        tuple(tensors[name].role for name in kernel.inputs),
        tuple(tensors[name].role for name in kernel.outputs),
        tuple(tensors[name].dtype for name in kernel.inputs),
        tuple(tensors[name].dtype for name in kernel.outputs),
        tuple(weight_extent(name) for name in kernel.inputs),
        len(kernel.state_reads),
        len(kernel.state_writes),
        kernel.phases,
    )


#: Longest layer pattern the compressor will look for.
MAX_LAYER_PERIOD = 8


def _detect_spans(
    signatures: Sequence[tuple[Any, ...]], max_period: int = MAX_LAYER_PERIOD
) -> list[tuple[int, int, int]]:
    """Split a layer signature sequence into ``(start, period, groups)`` spans.

    Chosen greedily by how many layers a span eliminates from the program
    (``(groups - 1) * period``), then by the smallest period, so a stack with no
    repetition never gets folded into one pointless wide body.
    """
    spans: list[tuple[int, int, int]] = []
    index = 0
    total = len(signatures)
    while index < total:
        best = (0, 1, 1)  # (eliminated, period, groups) with period minimal
        for period in range(1, min(max_period, total - index) + 1):
            groups = 1
            while True:
                nxt = groups + 1
                if index + nxt * period > total:
                    break
                base = index + (nxt - 1) * period
                if any(
                    signatures[base + offset] != signatures[index + offset]
                    for offset in range(period)
                ):
                    break
                groups = nxt
            eliminated = (groups - 1) * period
            if eliminated > best[0] or (eliminated == best[0] and period < best[1]):
                best = (eliminated, period, groups)
        _eliminated, period, groups = best
        spans.append((index, period, groups))
        index += period * groups
    return spans


def analyze(graph: KernelGraph) -> GraphAnalysis:
    """Split ``graph`` into prologue, periodic layer runs and epilogue."""
    tensors = {tensor.tensor_id: tensor for tensor in graph.tensors}
    kernels = list(graph.kernels)
    layered = [i for i, k in enumerate(kernels) if k.layer is not None]
    if not layered:
        raise RomLoweringError(
            "the graph declares no layered kernels; there is nothing to compress "
            "and an unrolled program is not admissible"
        )
    first, last = layered[0], layered[-1]
    if set(layered) != set(range(first, last + 1)):
        raise RomLoweringError(
            "layered kernels are not contiguous in the kernel list; the loop "
            "compressor requires one prologue, one layered span and one epilogue"
        )
    prologue = tuple(kernels[:first])
    epilogue = tuple(kernels[last + 1 :])

    by_layer: dict[int, list[Kernel]] = {}
    for kernel in kernels[first : last + 1]:
        by_layer.setdefault(int(kernel.layer), []).append(kernel)
    layer_numbers = sorted(by_layer)
    if layer_numbers != list(range(layer_numbers[0], layer_numbers[-1] + 1)):
        raise RomLoweringError(
            "layer numbers are not consecutive; the compressor addresses a "
            "layer by a loop induction variable and cannot skip one"
        )

    signatures = [
        tuple(_kernel_signature(k, tensors) for k in by_layer[layer])
        for layer in layer_numbers
    ]
    runs = [
        _make_run(index, layer_numbers[start : start + period * groups], period, by_layer)
        for index, (start, period, groups) in enumerate(
            _detect_spans(signatures)
        )
    ]

    producer: dict[str, Kernel] = {}
    for kernel in kernels:
        for name in kernel.outputs:
            producer[name] = kernel

    body_output: dict[str, tuple[int, int, int]] = {}
    body_input: dict[str, tuple[int, int, int]] = {}
    body_operand: dict[tuple[int, int, int], tuple[str, ...]] = {}
    for run in runs:
        for position, column in enumerate(run.body):
            for slot in range(len(column[0].inputs)):
                names = tuple(k.inputs[slot] for k in column)
                body_operand[(run.index, position, slot)] = names
                for name in names:
                    body_input.setdefault(name, (run.index, position, slot))
            for slot in range(len(column[0].outputs)):
                for kernel in column:
                    body_output[kernel.outputs[slot]] = (run.index, position, slot)
    return GraphAnalysis(
        prologue=prologue,
        runs=tuple(runs),
        epilogue=epilogue,
        producer=producer,
        body_output=body_output,
        body_input=body_input,
        body_operand=body_operand,
    )


def _make_run(
    index: int,
    layers: Sequence[int],
    period: int,
    by_layer: Mapping[int, Sequence[Kernel]],
) -> LayerRun:
    groups = len(layers) // period
    columns: list[list[Kernel]] = []
    for group in range(groups):
        flattened: list[Kernel] = []
        for offset in range(period):
            flattened.extend(by_layer[layers[group * period + offset]])
        columns.append(flattened)
    width = len(columns[0])
    if any(len(column) != width for column in columns):
        raise RomLoweringError(
            f"layer run {index} has groups of different kernel counts"
        )
    body = tuple(
        tuple(columns[group][position] for group in range(groups))
        for position in range(width)
    )
    return LayerRun(
        index=index,
        layers=tuple(layers),
        period=period,
        groups=groups,
        body=body,
    )


# ---------------------------------------------------------------------------
# Placement policy
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class BufferPlacement:
    """Where a non-ROM tensor buffer lives, and which memory port serves it."""

    storage: StorageClass
    size_bytes: int
    permissions: int
    port: int = 0


@dataclass(slots=True)
class LinkStep:
    """One on-fabric operation inserted into a compressed body."""

    position: int
    where: str  # "before" or "after"
    link_sub: int
    collective_op: int
    label: str
    participant_count: int
    byte_extent: int
    route_class: int = 0
    group_id: int = NO_ID
    virtual_channel: int = 0


@dataclass(slots=True)
class RomTargetPolicy:
    """Everything a ROM product must decide that the IR does not say."""

    product: str
    target_id: str
    backend: str
    topology_class: TopologyClass
    layout: RomLayoutPolicy
    #: Bytes of on-chip SRAM the backend may spend on activation buffers before
    #: it spills the remainder to HBM.  Spilling is deterministic: buffers are
    #: considered in emission order.
    sram_budget_bytes: int = 1 << 24
    tile_rows: int = 128
    tile_cols: int = 128
    tile_depth: int = 128
    defects: tuple[DefectRecord, ...] = ()
    features: tuple[Feature, ...] = ()
    #: Maps a region request to the physical resource that should hold it.
    place_region: Callable[[str, str, int, int], RomCoordinate] | None = None
    #: Emits the product's TOPOLOGY descriptor once the plan exists.
    emit_topology: Callable[[DeploymentBuilder, RomImagePlan], int] | None = None
    #: Returns the on-fabric steps for one compressed body.
    link_plan: Callable[[LayerRun, Sequence[str]], Sequence[LinkStep]] | None = None
    notes: dict[str, Any] = dc_field(default_factory=dict)


# ---------------------------------------------------------------------------
# Lowering
# ---------------------------------------------------------------------------
class RomLowering:
    """Lowers one neutral graph onto one immutable-ROM ABI 3.0 deployment."""

    def __init__(
        self,
        graph: KernelGraph,
        capability: Capability,
        policy: RomTargetPolicy,
        *,
        weight_storage_class: StorageClass = StorageClass.ROM,
        deployment_id: int = 1,
        generation: int = 1,
    ) -> None:
        require_neutral(graph)
        self.graph = graph
        self.capability = capability
        self.policy = policy
        self.weight_storage_class = weight_storage_class
        self.tensors = {t.tensor_id: t for t in graph.tensors}
        self.states = {s.state_id: s for s in graph.states}
        self.analysis = analyze(graph)
        self.builder = DeploymentBuilder(
            target_id=policy.target_id,
            model_id=graph.model_id,
            backend=policy.backend,
            capability=capability,
            topology_class=int(policy.topology_class),
            deployment_id=deployment_id,
            generation=generation,
        )
        self.plan: RomImagePlan | None = None
        self._region_of_tensor: dict[str, tuple[str, int]] = {}
        self._scale_of_region: dict[str, tuple[str, int]] = {}
        self._expert_bank: dict[str, tuple[int, tuple[int, ...]]] = {}
        self._buffer_object: dict[str, int] = {}
        self._buffer_place: dict[str, BufferPlacement] = {}
        self._buffer_root: dict[str, str] = {}
        self._sram_used = 0
        self._numeric_cache: dict[tuple[Any, ...], int] = {}
        self._schedule_cache: dict[tuple[int, int], int] = {}
        self._counter_cache: dict[int, int] = {}
        self._view_cache: dict[tuple[Any, ...], int] = {}
        self._wait_cache: dict[tuple[int, ...], int] = {}
        self._loop_of_run: dict[int, int] = {}
        self._state_descriptor: dict[str, int] = {}
        self._state_slot: dict[str, tuple[str, int]] = {}
        self._state_group_shape: dict[str, tuple[int, int, int]] = {}
        self._state_tensor_offset: dict[str, int] = {}
        self._state_owner: dict[str, str] = {}
        self._event_of_tensor: dict[str, tuple[int, int]] = {}
        self._communications: list[tuple[str, int]] = []
        self._link_instruction_count = 0
        self._queue_cursor: dict[int, int] = {}
        self._contract_substitutions: dict[str, str] = {}
        self._port_cursor = 0
        self._unify_buffers()

    # -- sizes ----------------------------------------------------------
    def _extent(self, value: Any) -> int:
        if isinstance(value, Symbolic):
            maximum = value.maximum or self.capability.limits["max_context_positions"]
            return max(int(maximum) * int(value.multiplier or 1), 1)
        return max(int(value), 1)

    def _dims(self, tensor: Tensor) -> tuple[int, ...]:
        dims = tuple(self._extent(d) for d in tensor.shape)
        if not 1 <= len(dims) <= MAX_RANK:
            raise RomLoweringError(
                f"tensor {tensor.tensor_id!r} has rank {len(dims)}, outside 1..{MAX_RANK}"
            )
        return dims

    def _dtype(self, name: str) -> DType:
        try:
            return DTYPE_BY_NAME[name]
        except KeyError:
            raise RomLoweringError(f"dtype {name!r} has no ABI 3.0 storage type") from None

    def _bytes(self, tensor: Tensor) -> int:
        elements = 1
        for dim in self._dims(tensor):
            elements *= dim
        bits = DTYPE_BITS[self._dtype(tensor.dtype)]
        return (elements * bits + 7) // 8

    # -- region planning -------------------------------------------------
    def plan_regions(self) -> RomImagePlan:
        """Derive the ROM region requests structurally and lay them out.

        Region identity is ``(layer run, body position, operand slot)``, never a
        tensor name, so any conforming front end gets the same partition.  Three
        kinds of payload are placed:

        * a direct weight operand of a kernel;
        * its block-scale tensor, named by ``Tensor.scale_tensor_id`` -- a scale
          is immutable model content and belongs in ROM beside the weight it
          scales; and
        * a routed **expert bank**, named by a kernel's
          ``expert_weight_tensors`` attribute.  One slot of that region is one
          layer's whole bank in ascending logical expert order, which is what
          lets one ROUTED_MATMUL descriptor address any runtime-selected expert
          and what lets expert dispatch enable only the tiles that hold them.
        """
        requests: list[RegionRequest] = []
        placed: set[str] = set()

        def coordinate(key: str, role: str, size: int) -> RomCoordinate:
            if self.policy.place_region is None:
                return RomCoordinate()
            return self.policy.place_region(key, role, len(requests), size)

        def entry(tensor: Tensor) -> tuple[str, int, str, int, str]:
            member = self._member(tensor, 0, 0)
            return (
                member.tensor_id,
                member.bytes,
                member.source_path,
                member.source_offset,
                member.source_sha256,
            )

        def emit(
            key: str,
            role: str,
            dtype: str,
            slots: list[list[tuple[str, int, str, int, str]]],
            elements: int,
        ) -> None:
            names = [entry_[0] for slot in slots for entry_ in slot]
            if any(name in placed for name in names):
                if all(name in placed for name in names):
                    return
                raise RomLoweringError(
                    f"ROM region {key!r} mixes already-placed and unplaced weights"
                )
            placed.update(names)
            size = sum(entry_[1] for slot in slots for entry_ in slot)
            requests.append(
                RegionRequest.striped(
                    key,
                    role,
                    dtype,
                    slots,
                    elements,
                    coordinate(key, role, size),
                )
            )
            for slot_index, slot in enumerate(slots):
                for entry_ in slot:
                    self._region_of_tensor[entry_[0]] = (key, slot_index)

        def place_operand(
            key: str, role: str, columns: Sequence[Sequence[Tensor]]
        ) -> None:
            """Place one operand across a run's groups, plus its scale."""
            head = columns[0][0]
            emit(
                key,
                role,
                head.dtype,
                [[entry(t) for t in column] for column in columns],
                sum(self._elements(t) for t in columns[0]),
            )
            scales = [
                [self.tensors[t.scale_tensor_id] for t in column]
                for column in columns
                if all(t.scale_tensor_id for t in column)
            ]
            if len(scales) != len(columns) or not scales:
                return
            emit(
                f"{key}.scale",
                f"{role}_scale",
                scales[0][0].dtype,
                [[entry(t) for t in column] for column in scales],
                sum(self._elements(t) for t in scales[0]),
            )
            self._scale_of_region[key] = (
                f"{key}.scale",
                int(head.scale_block_elements or 0),
            )

        def expert_bank(key: str, columns: Sequence[Sequence[Kernel]]) -> None:
            """Place one routed expert bank per group of a compressed run."""
            names = [
                list(kernel.attributes["expert_weight_tensors"]) for kernel in columns
            ]
            head = self.tensors[names[0][0]]
            place_operand(
                key,
                "expert_bank",
                [[self.tensors[n] for n in group] for group in names],
            )
            self._expert_bank[key] = (len(names[0]), self._dims(head))

        # -- prologue and epilogue weights: one slot each -----------------
        for kernel in (*self.analysis.prologue, *self.analysis.epilogue):
            for slot, name in enumerate(kernel.inputs):
                tensor = self.tensors[name]
                if tensor.role not in WEIGHT_ROLES or name in placed:
                    continue
                place_operand(
                    f"rom.global.k{kernel.index:05d}.s{slot}",
                    "global_weight",
                    [[tensor]],
                )
            if "expert_weight_tensors" in kernel.attributes:
                expert_bank(f"rom.global.k{kernel.index:05d}.experts", [kernel])

        # -- layer-run weights: one region per (run, position, slot) ------
        for run in self.analysis.runs:
            for position, column in enumerate(run.body):
                head = column[0]
                for slot, name in enumerate(head.inputs):
                    if self.tensors[name].role not in WEIGHT_ROLES:
                        continue
                    columns = [[self.tensors[k.inputs[slot]]] for k in column]
                    place_operand(
                        f"rom.r{run.index}.p{position:03d}.s{slot}",
                        "layer_weight",
                        columns,
                    )
                if "expert_weight_tensors" in head.attributes:
                    expert_bank(
                        f"rom.r{run.index}.p{position:03d}.experts", list(column)
                    )

        unplaced = sorted(
            t.tensor_id
            for t in self.graph.tensors
            if t.role in WEIGHT_ROLES and t.tensor_id not in placed
        )
        if unplaced:
            raise RomLoweringError(
                f"{len(unplaced)} weight tensor(s) are never read by a kernel and "
                f"would have no ROM placement: {unplaced[:4]}"
            )
        self.plan = plan_rom_image(
            model_id=self.graph.model_id,
            product=self.policy.product,
            requests=tuple(requests),
            policy=self.policy.layout,
            defects=self.policy.defects,
            notes=self.policy.notes,
        )
        return self.plan

    def _elements(self, tensor: Tensor) -> int:
        elements = 1
        for dim in self._dims(tensor):
            elements *= dim
        return elements

    def _member(self, tensor: Tensor, slot: int, offset: int) -> RomMember:
        binding = tensor.binding
        if binding is None:
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} has no checkpoint binding; a ROM "
                "region must name authenticated checkpoint bytes, never a copy"
            )
        expected = self._bytes(tensor)
        if binding.bytes != expected:
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} binds {binding.bytes} bytes but its "
                f"declared shape and dtype need {expected}"
            )
        if binding.transform != "identity":
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} declares transform "
                f"{binding.transform!r}; a zero-copy ROM region can only place "
                "identity-transformed checkpoint bytes"
            )
        return RomMember(
            tensor_id=tensor.tensor_id,
            slot=slot,
            offset_bytes=offset,
            bytes=binding.bytes,
            source_path=binding.path,
            source_offset=binding.offset,
            source_sha256=binding.sha256,
            dtype=tensor.dtype,
        )

    # -- descriptor helpers ----------------------------------------------
    def _engine_spec(self, family: Major) -> Mapping[str, int]:
        key = ENGINE_KEY_BY_FAMILY[int(family)]
        return self.capability.engines.get(key, {})

    def _lanes(self, family: Major) -> int:
        return max(int(self._engine_spec(family).get("lanes", 0)) or 64, 1)

    def _queues(self, family: Major) -> int:
        return max(int(self._engine_spec(family).get("queues", 1)), 1)

    def _row_elements(self, dtype: DType) -> int:
        """Weight elements one ROM macro row read returns."""
        bits = DTYPE_BITS[dtype]
        return max(self.policy.layout.row_bytes * 8 // bits, 1)

    def _schedule(self, kernel: Kernel, family: Major, sub: int) -> int:
        """Emit the SCHEDULE descriptor for one operator.

        ADR-003 section 6.2 puts tile mapping, bank/port use, NoC path, issue
        window and resource bound in this descriptor -- *not* in program loops.
        A program loop expresses what varies the work (layers, token blocks,
        experts, vocabulary partitions); the schedule expresses how one engine
        instruction is decomposed on the hardware.  Making output-tile and
        K-tile loops into program loops would retire on the order of 258,000
        dispatches per Qwen forward step, which is the failure mode ABI 3.0
        exists to prevent.

        The cycle model reads these fields directly, so every one of them is
        derived from the operator's iteration domain, the engine's lane count
        and the ROM macro read granularity.  None is a placeholder.
        """
        domain = {k: self._extent(v) for k, v in kernel.iteration_domain.items()}
        inputs = [self.tensors[n] for n in kernel.inputs]
        outputs = [self.tensors[n] for n in kernel.outputs]
        weights = [t for t in inputs if t.role in WEIGHT_ROLES]
        lanes = self._lanes(family)
        rows = domain.get("tokens") or (self._dims(outputs[0])[0] if outputs else 1)
        rows = max(int(rows), 1)
        tile_rows = max(min(rows, self.policy.tile_rows), 1)
        tile_cols = max(self.policy.tile_cols, 1)
        tile_depth = 1
        bound = ResourceBound.MEMORY_PORT

        if weights:
            weight_dims = self._dims(weights[0])
            row_elements = self._row_elements(self._dtype(weights[0].dtype))
            width = weight_dims[0]
            reduction = weight_dims[-1]
            if family is Major.TENSOR and sub != int(TensorOp.EMBED_LOOKUP):
                tile_cols = max(min(width, lanes), 1)
                tile_depth = max(min(reduction, row_elements), 1)
                bound = ResourceBound.ROM_READ
            else:
                tile_cols = max(min(reduction, lanes), 1)
                tile_depth = max(min(reduction, row_elements), 1)
                bound = (
                    ResourceBound.ROM_READ
                    if family is Major.TENSOR
                    else ResourceBound.MEMORY_PORT
                )
        elif outputs:
            tile_cols = max(min(self._dims(outputs[0])[-1], lanes), 1)

        if family is Major.ATTENTION:
            head_dim = int(
                domain.get("head_dim", self._dims(outputs[0])[-1] if outputs else lanes)
            )
            tile_cols = max(min(head_dim, lanes), 1)
            tile_depth = max(
                min(
                    int(kernel.attributes.get("block_width", 64)),
                    self.capability.limits["max_context_positions"],
                ),
                1,
            )
            bound = ResourceBound.MEMORY_PORT
        elif family is Major.SELECTION:
            bound = ResourceBound.SELECTION
        elif family is Major.ROUTE:
            bound = ResourceBound.TENSOR_LANES
        elif family is Major.STATE:
            bound = ResourceBound.STATE_TRANSACTION

        tiles = self._tile_count(kernel, tile_rows, tile_cols, tile_depth, rows)
        max_outstanding = max(
            min(tiles, self.capability.limits["max_outstanding_per_queue"]), 1
        )
        issue_window = min(max_outstanding, 0xFFFF)
        bank_mask = self._bank_mask(kernel)
        port_mask = self._port_mask(kernel)
        route_class = self._route_class(kernel)
        queues = self._queues(family)
        queue_index = self._queue_cursor.get(int(family), 0) % queues
        self._queue_cursor[int(family)] = queue_index + 1

        payload = (
            int(family),
            queue_index,
            issue_window,
            tile_rows,
            tile_cols,
            tile_depth,
            bank_mask,
            port_mask,
            route_class,
            bound,
            max_outstanding,
        )
        if payload in self._schedule_cache:
            return self._schedule_cache[payload]
        descriptor = self.builder.schedule(
            engine_family=family,
            queue_index=queue_index,
            issue_window=issue_window,
            tile_rows=tile_rows,
            tile_cols=tile_cols,
            tile_depth=tile_depth,
            bank_mask=bank_mask,
            port_mask=port_mask,
            noc_route_class=route_class,
            resource_bound=bound,
            max_outstanding=max_outstanding,
            key=f"sched.{Major(family).name.lower()}.{len(self._schedule_cache):04d}",
        )
        self._schedule_cache[payload] = descriptor
        return descriptor

    def _tile_count(
        self, kernel: Kernel, tile_rows: int, tile_cols: int, tile_depth: int, rows: int
    ) -> int:
        inputs = [self.tensors[n] for n in kernel.inputs]
        weights = [t for t in inputs if t.role in WEIGHT_ROLES]
        if weights:
            dims = self._dims(weights[0])
            width, reduction = dims[0], dims[-1]
        else:
            outputs = [self.tensors[n] for n in kernel.outputs]
            width = self._dims(outputs[0])[-1] if outputs else 1
            reduction = 1
        return (
            -(-rows // tile_rows)
            * -(-max(width, 1) // tile_cols)
            * -(-max(reduction, 1) // tile_depth)
        )

    def _bank_mask(self, kernel: Kernel) -> int:
        """Which immutable ROM banks or tiles this operator reads."""
        mask = 0
        if self.plan is None:
            return 0
        for name in kernel.inputs:
            if self.tensors[name].role not in WEIGHT_ROLES:
                continue
            placement = self._region_of_tensor.get(name)
            if placement is None:
                continue
            for shard in self.plan.region(placement[0]).shards:
                index = shard.coordinate.tile or shard.coordinate.bank
                mask |= 1 << (index % 32)
        return mask

    def _port_mask(self, kernel: Kernel) -> int:
        """Which mutable memory ports this operator's activations occupy."""
        mask = 0
        for name in (*kernel.inputs, *kernel.outputs):
            if self.tensors[name].role in WEIGHT_ROLES:
                continue
            placement = self._buffer_place.get(self._buffer_key(name))
            if placement is None:
                continue
            mask |= 1 << (placement.port % 32)
        return mask

    def _route_class(self, kernel: Kernel) -> int:
        """Local, intra-reticle or inter-reticle, from the operand placement."""
        if self.plan is None:
            return RouteClass.LOCAL
        reticles: set[int] = set()
        tiles: set[int] = set()
        for name in kernel.inputs:
            if self.tensors[name].role not in WEIGHT_ROLES:
                continue
            placement = self._region_of_tensor.get(name)
            if placement is None:
                continue
            for shard in self.plan.region(placement[0]).shards:
                reticles.add(shard.coordinate.reticle)
                tiles.add(shard.coordinate.tile)
        if len(reticles) > 1:
            return RouteClass.INTER_RETICLE
        if len(tiles) > 1:
            return RouteClass.INTRA_RETICLE
        return RouteClass.LOCAL

    def _numeric(self, kernel: Kernel) -> int:
        attributes = kernel.attributes
        inputs = [self.tensors[n] for n in kernel.inputs]
        outputs = [self.tensors[n] for n in kernel.outputs]
        first = str(attributes.get("input_dtype", inputs[0].dtype if inputs else "bf16"))
        second = str(
            attributes.get(
                "second_input_dtype", inputs[1].dtype if len(inputs) > 1 else first
            )
        )
        result = str(
            attributes.get("output_dtype", outputs[0].dtype if outputs else first)
        )
        accumulator = str(attributes.get("accumulator_dtype", "fp32"))
        contract = EXECUTION_CONTRACT.get(
            kernel.numeric_contract, kernel.numeric_contract
        )
        if contract != kernel.numeric_contract:
            self._contract_substitutions[kernel.numeric_contract] = contract
        order = self._reduction_order(contract, kernel.kind)
        input_dtype = self._dtype(first)
        second_dtype = self._dtype(second)
        output_dtype = self._dtype(result)
        accumulator_dtype = self._dtype(accumulator)
        key = (
            contract,
            int(input_dtype),
            int(second_dtype),
            int(output_dtype),
            int(accumulator_dtype),
            int(order),
        )
        if key in self._numeric_cache:
            return self._numeric_cache[key]
        descriptor = self.builder.numeric(
            contract=contract,
            input_dtype=input_dtype,
            second_input_dtype=second_dtype,
            output_dtype=output_dtype,
            accumulator_dtype=accumulator_dtype,
            reduction_order=order,
            key=f"num.{len(self._numeric_cache):04d}",
        )
        self._numeric_cache[key] = descriptor
        return descriptor

    @staticmethod
    def _reduction_order(contract: str, kind: str) -> ReductionOrder:
        """Amendment A8: RMSNorm sums in a balanced tree, not sequentially."""
        if kind in {"RMS_NORM", "HEAD_RMS_NORM"} or "rmsnorm" in contract:
            return ReductionOrder.PAIRWISE_TREE
        if "blocked" in contract:
            return ReductionOrder.BLOCKED_ASCENDING
        return ReductionOrder.SEQUENTIAL_ASCENDING

    def _counter_class(self, kernel_counter: str, family: Major) -> int:
        group = COUNTER_GROUP_BY_FAMILY[int(family)]
        if kernel_counter:
            candidate = kernel_counter.upper()
            if candidate in CounterGroup.__members__:
                group = CounterGroup[candidate]
        if int(group) in self._counter_cache:
            return self._counter_cache[int(group)]
        descriptor = self.builder.counter_class(
            int(group),
            [counter_id(group, 1), counter_id(group, 2), counter_id(group, 3)],
            key=f"ctr.{group.name.lower()}",
        )
        self._counter_cache[int(group)] = descriptor
        return descriptor

    def _view(
        self,
        *,
        object_id: int,
        dtype: DType,
        dims: Sequence[int],
        element_offset: int = 0,
        dynamic: Sequence[DynamicTerm] = (),
        permissions: int = int(Permission.READ),
        label: str = "view",
    ) -> int:
        key = (
            object_id,
            int(dtype),
            tuple(dims),
            element_offset,
            tuple((t.kind, t.index, t.stride) for t in dynamic),
            permissions,
        )
        if key in self._view_cache:
            return self._view_cache[key]
        descriptor = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            element_offset=element_offset,
            dynamic=list(dynamic),
            permissions=permissions,
            key=f"{label}.{len(self._view_cache):05d}",
        )
        self._view_cache[key] = descriptor
        return descriptor

    def _wait_set(self, producers: Sequence[int]) -> int:
        unique = tuple(sorted(set(producers)))[:MAX_WAIT_PRODUCERS]
        if not unique:
            return NO_ID
        if unique in self._wait_cache:
            return self._wait_cache[unique]
        descriptor = self.builder.wait_set(
            list(unique), key=f"wait.{len(self._wait_cache):05d}"
        )
        self._wait_cache[unique] = descriptor
        return descriptor

    # -- buffers ---------------------------------------------------------
    def _base_buffer_key(self, tensor_id: str) -> str:
        placement = self.analysis.body_output.get(tensor_id)
        if placement is not None:
            run, position, slot = placement
            return f"buf.r{run}.p{position:03d}.o{slot}"
        return f"buf.g.{tensor_id}"

    def _unify_buffers(self) -> None:
        """Alias the buffers a compressed body forces to be one object.

        Layer ``L`` of a run reads the residual its predecessor wrote, and layer
        0 reads what the prologue wrote.  Those are different IR tensors, but a
        single loop body can only name one object, so the operands of one
        (run, position, slot) must resolve to the same buffer.  That aliasing is
        the residual stream; it is a placement decision, not a semantic one, and
        it is rejected outright if the aliased buffers differ in size.
        """
        parent: dict[str, str] = {}

        def find(key: str) -> str:
            parent.setdefault(key, key)
            while parent[key] != key:
                parent[key] = parent[parent[key]]
                key = parent[key]
            return key

        def union(left: str, right: str) -> None:
            a, b = find(left), find(right)
            if a != b:
                parent[min(a, b)] = min(a, b)
                parent[max(a, b)] = min(a, b)

        for (run, position, slot), names in sorted(self.analysis.body_operand.items()):
            keys = []
            for name in names:
                tensor = self.tensors[name]
                if tensor.role in WEIGHT_ROLES or tensor.role == "state":
                    keys = []
                    break
                keys.append(self._base_buffer_key(name))
            for other in keys[1:]:
                union(keys[0], other)
        sizes: dict[str, int] = {}
        for tensor in self.graph.tensors:
            if tensor.role in WEIGHT_ROLES or tensor.role == "state":
                continue
            root = find(self._base_buffer_key(tensor.tensor_id))
            size = self._bytes(tensor)
            if root in sizes and sizes[root] != size:
                raise RomLoweringError(
                    f"loop compression aliases buffers of {sizes[root]} and {size} "
                    f"bytes at {root!r}; the layer body is not uniform"
                )
            sizes[root] = size
        self._buffer_root = {
            self._base_buffer_key(t.tensor_id): find(self._base_buffer_key(t.tensor_id))
            for t in self.graph.tensors
            if t.role not in WEIGHT_ROLES and t.role != "state"
        }

    def _buffer_key(self, tensor_id: str) -> str:
        base = self._base_buffer_key(tensor_id)
        return self._buffer_root.get(base, base)

    def _buffer(self, tensor_id: str) -> int:
        key = self._buffer_key(tensor_id)
        if key in self._buffer_object:
            return self._buffer_object[key]
        tensor = self.tensors[tensor_id]
        size = self._bytes(tensor)
        if tensor.role in {"input", "output"}:
            storage = StorageClass.HOST
            permissions = int(
                Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
            )
        else:
            permissions = int(Permission.READ | Permission.WRITE)
            if self._sram_used + size <= self.policy.sram_budget_bytes:
                storage = StorageClass.SRAM
                self._sram_used += size
            else:
                storage = StorageClass.HBM
        ports = max(int(self.capability.memory.get("sram", {}).get("banks", 8)), 1)
        port = self._port_cursor % min(ports, 32)
        self._port_cursor += 1
        object_id = self.builder.memory_object(
            storage_class=storage,
            size_bytes=size,
            source=ObjectSource.zeros(size),
            permissions=permissions,
            bank_or_tile=port,
            key=key,
        )
        self._buffer_object[key] = object_id
        self._buffer_place[key] = BufferPlacement(storage, size, permissions, port)
        return object_id

    # -- state -----------------------------------------------------------
    def emit_states(self) -> None:
        """Merge congruent per-layer state resources into one physical state.

        The IR names 36 (or 43) per-layer KV resources.  On a ROM target they
        are one physical HBM object with a per-layer slot, so the compressed
        layer body can reach the current layer's rows through the same dynamic
        term the weights use, and so one prepare/commit covers the whole token
        step.  Partial layer advancement therefore cannot become architectural.
        """
        groups: dict[tuple[Any, ...], list[StateResource]] = {}
        for state in self.graph.states:
            key = (
                state.state_class,
                state.dtype,
                state.row_elements,
                self._extent(state.capacity_rows),
                state.initialization,
            )
            groups.setdefault(key, []).append(state)
        for index, key in enumerate(sorted(groups, key=lambda k: str(k))):
            members = groups[key]
            state_class = STATE_CLASS_BY_NAME.get(members[0].state_class)
            if state_class is None:
                raise RomLoweringError(
                    f"state class {members[0].state_class!r} is not in the frozen "
                    "ABI 3.0 registry"
                )
            dtype = self._dtype(members[0].dtype)
            bits = DTYPE_BITS[dtype]
            row_bytes = (members[0].row_elements * bits + 7) // 8
            capacity = self._extent(members[0].capacity_rows)
            slot_bytes = row_bytes * capacity
            total = slot_bytes * len(members)
            group_key = f"state.{index}"
            committed = self.builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=total,
                source=ObjectSource.zeros(total),
                permissions=int(Permission.READ | Permission.STATE_COMMIT),
                key=f"obj.{group_key}.committed",
            )
            prepared = self.builder.memory_object(
                storage_class=StorageClass.STATE,
                size_bytes=total,
                source=ObjectSource.zeros(total),
                permissions=int(Permission.READ | Permission.STATE_PREPARE),
                key=f"obj.{group_key}.prepared",
            )
            view = self._view(
                object_id=prepared,
                dtype=dtype,
                dims=(capacity, members[0].row_elements),
                permissions=int(Permission.READ | Permission.WRITE),
                label="view.state",
            )
            descriptor = self.builder.state(
                state_class=state_class,
                committed_object_id=committed,
                prepared_object_id=prepared,
                row_bytes=row_bytes,
                capacity_rows=capacity,
                element_dtype=dtype,
                view_descriptor_id=view,
                counter_class_id=self._counter_class("state", Major.STATE),
                key=f"desc.{group_key}",
            )
            self._state_group_shape[group_key] = (
                slot_bytes,
                capacity,
                members[0].row_elements,
            )
            for slot, state in enumerate(members):
                self._state_descriptor[state.state_id] = descriptor
                self._state_slot[state.state_id] = (group_key, slot)
            self.builder.name(f"obj.{group_key}", prepared)
        self._plan_state_layout()

    def _plan_state_layout(self) -> None:
        """Assign every role=``state`` tensor a byte offset inside a layer slot.

        The IR names one state tensor per logical view per layer (a key history
        and a value history, say).  Physically they are sub-ranges of one layer
        slot of one merged state object, in first-use order, and the assignment
        must be identical for every layer -- including layers in different loop
        runs -- or the compressed body could not address them with one view.
        """
        order: dict[str, list[str]] = {}
        owner: dict[str, str] = {}
        for kernel in self.graph.kernels:
            state_ids = kernel.state_reads or kernel.state_writes
            if not state_ids:
                continue
            for name in (*kernel.inputs, *kernel.outputs):
                if self.tensors[name].role != "state":
                    continue
                if name in owner:
                    continue
                owner[name] = state_ids[0]
                order.setdefault(state_ids[0], []).append(name)
        # The layout is per *structural* position, so layer 0's key history and
        # layer 7's key history land at the same offset inside their slots.
        offsets: dict[str, int] = {}
        for state_id, names in order.items():
            group_key, _slot = self._state_slot.get(state_id, (None, 0))
            if group_key is None:
                continue
            slot_bytes = self._state_group_shape[group_key][0]
            cursor = 0
            for name in names:
                size = self._bytes(self.tensors[name])
                if cursor + size > slot_bytes:
                    raise RomLoweringError(
                        f"state tensors of {state_id!r} need {cursor + size} bytes "
                        f"but a layer slot of group {group_key} is {slot_bytes}"
                    )
                offsets[name] = cursor
                cursor += size
        self._state_tensor_offset = offsets
        self._state_owner = owner

    def _state_view(self, tensor_id: str) -> int | None:
        """Bind a role=``state`` tensor to a slice of its physical state object."""
        tensor = self.tensors[tensor_id]
        if tensor.role != "state":
            return None
        state_id = self._state_owner.get(tensor_id)
        if state_id is None or state_id not in self._state_slot:
            return None
        group_key, slot = self._state_slot[state_id]
        slot_bytes, _capacity, _row_elements = self._state_group_shape[group_key]
        prepared = self.builder.lookup(f"obj.{group_key}")
        dtype = self._dtype(tensor.dtype)
        bits = DTYPE_BITS[dtype]
        slot_elements = slot_bytes * 8 // bits
        element_offset = (
            slot * slot_elements + self._state_tensor_offset[tensor_id] * 8 // bits
        )
        dynamic: list[DynamicTerm] = []
        loop, period = self._loop_for_state_slot(tensor_id)
        # One loop iteration advances by a whole period of layers, so the state
        # stride is the period's worth of slots, not one slot.
        stride = slot_elements * period
        if loop is not None:
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"state group {group_key} needs a per-layer element stride of "
                    f"{stride}, which does not fit the 32-bit dynamic-term stride "
                    "field of ABI 3.0 tensor views"
                )
            dynamic.append(DynamicTerm.loop(loop, stride))
        return self._view(
            object_id=prepared,
            dtype=dtype,
            dims=self._dims(tensor),
            element_offset=element_offset,
            dynamic=dynamic,
            permissions=int(Permission.READ | Permission.WRITE),
            label="view.state",
        )

    def _loop_for_state_slot(self, tensor_id: str) -> tuple[int | None, int]:
        """The loop that indexes this state operand, and its layer period."""
        placement = self.analysis.body_output.get(
            tensor_id
        ) or self.analysis.body_input.get(tensor_id)
        if placement is not None:
            run = self.analysis.runs[placement[0]]
            return self._loop_of_run.get(run.index), run.period
        return None, 1

    # -- operand views ---------------------------------------------------
    def _operand_view(
        self, tensor_id: str, *, run: LayerRun | None, writable: bool
    ) -> int:
        tensor = self.tensors[tensor_id]
        if tensor.role in WEIGHT_ROLES:
            return self._weight_view(tensor_id, run=run)
        state_view = self._state_view(tensor_id)
        if state_view is not None:
            return state_view
        object_id = self._buffer(tensor_id)
        permissions = int(Permission.READ | Permission.WRITE) if writable else int(
            Permission.READ
        )
        if tensor.role in {"input", "output"}:
            permissions |= int(Permission.HOST_VISIBLE)
        return self._view(
            object_id=object_id,
            dtype=self._dtype(tensor.dtype),
            dims=self._dims(tensor),
            permissions=permissions,
            label="view.buf",
        )

    def _weight_view(self, tensor_id: str, *, run: LayerRun | None) -> int:
        if self.plan is None:  # pragma: no cover - programming error
            raise RomLoweringError("plan_regions() must run before lowering")
        key, slot = self._region_of_tensor[tensor_id]
        region = self.plan.region(key)
        tensor = self.tensors[tensor_id]
        dtype = self._dtype(tensor.dtype)
        dims = self._dims(tensor)
        dynamic: list[DynamicTerm] = []
        element_offset = 0
        if region.slot_count > 1:
            if run is None:
                raise RomLoweringError(
                    f"weight {tensor_id!r} lives in the layer-striped region "
                    f"{key!r} but is read outside a compressed layer body"
                )
            loop = self._loop_of_run[run.index]
            stride = region.slot_element_stride
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"region {key!r} needs a per-layer element stride of {stride}, "
                    "which does not fit the 32-bit dynamic-term stride field of "
                    "ABI 3.0 tensor views; split the region"
                )
            dynamic.append(DynamicTerm.loop(loop, stride))
        else:
            element_offset = slot * region.slot_element_stride
        return self._view(
            object_id=region.object_id,
            dtype=dtype,
            dims=dims,
            element_offset=element_offset,
            dynamic=dynamic,
            permissions=int(Permission.READ),
            label="view.rom",
        )

    # -- operand conventions (TA-ABI3-OPCONV-1) --------------------------
    def _aux(self, kernel: Kernel, family: Major, sub: int) -> list[int]:
        """The auxiliary IDs the frozen operand convention requires.

        ``aux`` is not a spare field: ``TA-ABI3-OPCONV-1`` gives it a meaning per
        subopcode, and an engine rejects an operator whose slots do not match its
        row.  ``EXPERT_DISPATCH`` in particular *requires* ``aux0``, because an
        unbounded expert ID is a memory-safety problem.
        """
        domain = {k: self._extent(v) for k, v in kernel.iteration_domain.items()}
        attributes = kernel.attributes
        inputs = [self.tensors[n] for n in kernel.inputs]
        outputs = [self.tensors[n] for n in kernel.outputs]
        weights = [t for t in inputs if t.role in WEIGHT_ROLES]

        def dim(tensor: Tensor | None, axis: int, default: int) -> int:
            if tensor is None:
                return default
            dims = self._dims(tensor)
            return dims[axis] if -len(dims) <= axis < len(dims) else default

        if family is Major.TENSOR:
            if sub == int(TensorOp.GROUPED_MATMUL):
                return [int(attributes.get("group_count", domain.get("groups", 1)))]
            if sub == int(TensorOp.ROUTED_MATMUL):
                experts = int(
                    attributes.get(
                        "expert_count",
                        domain.get(
                            "experts", dim(weights[0] if weights else None, 0, 1)
                        ),
                    )
                )
                return [experts]
            return []
        if family is Major.VECTOR:
            if sub == int(Vector.HEAD_RMS_NORM):
                return [int(attributes.get("head_count", domain.get("heads", 1)))]
            if sub == int(Vector.ROPE):
                return [
                    int(
                        attributes.get(
                            "rotary_width",
                            domain.get("head_dim", dim(outputs[0] if outputs else None, -1, 1)),
                        )
                    )
                ]
            if sub == int(Vector.SOFTMAX):
                return [int(attributes.get("axis", 0))]
            if sub == int(Vector.HADAMARD):
                return [int(attributes.get("block_width", 32))]
            if sub == int(Vector.COMPRESS):
                return [COMPRESS_SUBCASE[kernel.kind]]
            if sub == int(Vector.MHC):
                return [
                    MHC_SUBCASE[kernel.kind],
                    int(attributes.get("sinkhorn_iterations", 0)),
                    int(attributes.get("hc_mult", 1)),
                ]
            if sub == int(Vector.SCALE):
                return [SCALE_SUBCASE.get(kernel.kind, 0)]
            return []
        if family is Major.ATTENTION:
            group_size = int(
                attributes.get(
                    "group_size",
                    domain.get("heads", 1) // max(domain.get("key_value_heads", 1), 1)
                    or 1,
                )
            )
            mask_mode = 0 if attributes.get("mask_mode", "causal") == "causal" else 1
            if sub == int(Attention.SPARSE):
                second = int(attributes.get("block_width", 64))
            else:
                second = mask_mode
            return [
                max(group_size, 1),
                second,
                int(Symbol.CONTEXT_LENGTH),
                int(Symbol.POSITION_START),
            ]
        if family is Major.ROUTE:
            if sub in (int(Route.TOPK), int(Route.BIASED_TOPK)):
                return [
                    int(
                        attributes.get(
                            "k", dim(outputs[0] if outputs else None, -1, 1)
                        )
                    )
                ]
            if sub == int(Route.EXPERT_DISPATCH):
                experts = int(
                    attributes.get("expert_count", domain.get("experts", 0))
                ) or self.capability.limits["max_expert_ids"]
                if experts <= 0:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r} is an EXPERT_DISPATCH with no "
                        "expert bound; TA-ABI3-OPCONV-1 requires aux0"
                    )
                return [experts]
            if sub == int(Route.INDEX_TOPK):
                return [
                    int(
                        attributes.get(
                            "k", dim(outputs[0] if outputs else None, -1, 1)
                        )
                    ),
                    0 if attributes.get("mask_mode", "causal") == "causal" else 1,
                    int(Symbol.CONTEXT_LENGTH),
                    int(Symbol.POSITION_START),
                ]
            if sub == int(Route.WINDOW_INDEX):
                return [
                    int(attributes.get("window", domain.get("window", 128))),
                    0 if attributes.get("mask_mode", "causal") == "causal" else 1,
                    int(Symbol.CONTEXT_LENGTH),
                ]
            return []
        if family is Major.REDUCTION and sub == int(Reduction.PARTITION_SUM):
            return [int(Symbol.VOCABULARY_PARTITIONS)]
        if family is Major.DMA and sub == int(Dma.FILL):
            return [int(attributes.get("fill_code", 0))]
        return []

    # -- instructions ----------------------------------------------------
    def _emit_kernel(self, kernel: Kernel, *, run: LayerRun | None) -> None:
        if kernel.kind in {"STATE_PREPARE", "STATE_COMMIT"}:
            # Prepare and commit are emitted once, outside every loop, so the
            # whole token step is one transaction.  See emit_program().
            return
        engine = KERNEL_TO_ENGINE.get(kernel.kind)
        if engine is None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} has kind {kernel.kind!r} with no "
                "entry in the frozen lowering table; a backend may not invent an "
                "opcode"
            )
        family = Major(engine.family)
        if kernel.kind == "STATE_READ":
            state = self._state_for(kernel)
            index = self.builder.emit(
                family,
                engine.sub,
                descriptor_id=state,
                source_operation_id=kernel.index,
            )
            return
        inputs = [
            self._operand_view(name, run=run, writable=False)
            for name in kernel.inputs[:MAX_OPERATOR_INPUTS]
        ]
        outputs = [
            self._operand_view(name, run=run, writable=True)
            for name in kernel.outputs[:MAX_OPERATOR_OUTPUTS]
        ]
        if len(kernel.inputs) > MAX_OPERATOR_INPUTS:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} has {len(kernel.inputs)} inputs; an "
                f"ABI 3.0 operator admits {MAX_OPERATOR_INPUTS}"
            )
        if len(kernel.outputs) > MAX_OPERATOR_OUTPUTS:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} has {len(kernel.outputs)} outputs; an "
                f"ABI 3.0 operator admits {MAX_OPERATOR_OUTPUTS}"
            )
        operator = self.builder.operator(
            engine_family=family,
            engine_sub=engine.sub,
            inputs=inputs,
            outputs=outputs,
            aux=self._aux(kernel, family, engine.sub),
            numeric_profile_id=self._numeric(kernel),
            schedule_id=self._schedule(kernel, family, engine.sub),
            counter_class_id=self._counter_class(kernel.counter_class, family),
            source_kernel_id=kernel.index,
            key=f"op.k{kernel.index:05d}",
        )
        producers = [
            self._event_of_tensor[name][0]
            for name in kernel.inputs
            if name in self._event_of_tensor
        ]
        wait = self._wait_set(producers)
        event = self.builder.new_event()
        index = self.builder.emit(
            family,
            engine.sub,
            descriptor_id=operator,
            wait_set_id=wait,
            signal_event_id=event,
            source_operation_id=kernel.index,
        )
        for name in kernel.outputs:
            self._event_of_tensor[name] = (event, index)

    def _state_for(self, kernel: Kernel) -> int:
        for state_id in (*kernel.state_writes, *kernel.state_reads):
            if state_id in self._state_descriptor:
                return self._state_descriptor[state_id]
        raise RomLoweringError(
            f"kernel {kernel.kernel_id!r} is a state operation naming no declared "
            "state resource"
        )

    # -- link fabric -----------------------------------------------------
    def _emit_links(self, run: LayerRun, steps: Iterable[LinkStep]) -> None:
        for step in steps:
            local = self._link_local_object(run)
            communication = self.builder.communication(
                collective_op=step.collective_op,
                local_object_id=local,
                group_id=step.group_id,
                route_class=step.route_class,
                byte_extent=step.byte_extent,
                participant_count=step.participant_count,
                virtual_channel=step.virtual_channel,
                counter_class_id=self._counter_class("communication", Major.LINK),
                key=f"comm.r{run.index}.{step.label}",
            )
            self._communications.append((step.label, communication))
            self.builder.emit(
                Major.LINK,
                step.link_sub,
                descriptor_id=communication,
                signal_event_id=self.builder.new_event(),
            )
            self._link_instruction_count += 1

    def _link_local_object(self, run: LayerRun) -> int:
        """The staging buffer an on-fabric step reads or writes."""
        for position in range(run.positions):
            for slot in range(2):
                key = f"buf.r{run.index}.p{position:03d}.o{slot}"
                root = self._buffer_root.get(key, key)
                if root in self._buffer_object:
                    return self._buffer_object[root]
        if not self._buffer_object:  # pragma: no cover - defensive
            raise RomLoweringError("no buffer exists to anchor an on-fabric step")
        return self._buffer_object[sorted(self._buffer_object)[0]]

    # -- program ---------------------------------------------------------
    def emit_program(self) -> None:
        analysis = self.analysis
        state_descriptors = sorted(set(self._state_descriptor.values()))
        for descriptor in state_descriptors:
            self.builder.emit(Major.STATE, State.PREPARE, descriptor_id=descriptor)
        for kernel in analysis.prologue:
            self._emit_kernel(kernel, run=None)
        for run in analysis.runs:
            steps = list(
                self.policy.link_plan(run, [k[0].kind for k in run.body])
                if self.policy.link_plan is not None
                else ()
            )
            before = {s.position: [] for s in steps}
            after = {s.position: [] for s in steps}
            for step in steps:
                (before if step.where == "before" else after)[step.position].append(step)
            self.builder.open_loop(self._loop_of_run[run.index])
            for position, column in enumerate(run.body):
                self._emit_links(run, before.get(position, ()))
                self._emit_kernel(column[0], run=run)
                self._emit_links(run, after.get(position, ()))
            self.builder.close_loop()
        for kernel in analysis.epilogue:
            self._emit_kernel(kernel, run=None)
        self._emit_selection_tail()
        for descriptor in state_descriptors:
            self.builder.emit(Major.STATE, State.COMMIT, descriptor_id=descriptor)
        self.builder.emit(Major.CONTROL, Control.COMPLETE)

    def _emit_selection_tail(self) -> None:
        """Guarantee on-device selection even if the graph omitted it."""
        kinds = {k.kind for k in self.graph.kernels}
        if "ARGMAX" in kinds and "TOKEN_APPEND" in kinds:
            return
        raise RomLoweringError(
            "the graph declares no ARGMAX/TOKEN_APPEND pair; ABI 3.0 forbids "
            "host-side selection, so the front end must emit both"
        )

    # -- top level -------------------------------------------------------
    def build(self) -> Deployment:
        builder = self.builder
        builder.require(*self.policy.features)
        plan = self.plan or self.plan_regions()
        if self.policy.emit_topology is None:
            builder.topology(
                topology_class=self.policy.topology_class,
                node_count=1,
                key="topology",
            )
        else:
            self.policy.emit_topology(builder, plan)
        emit_rom_objects(builder, plan, storage_class=self.weight_storage_class)
        self.emit_states()
        for run in self.analysis.runs:
            self._loop_of_run[run.index] = builder.loop_control(
                lower_bound=0,
                upper_bound=run.length,
                step=1,
                counter_class_id=self._counter_class("instruction", Major.CONTROL),
                key=f"loop.r{run.index}",
            )
        policy_body = dict(self.graph.generation_policy)
        token_bytes = max(
            int(policy_body.get("maximum_new_tokens", 1024)) * 8, 4096
        )
        token_ring = builder.memory_object(
            storage_class=StorageClass.HOST,
            size_bytes=token_bytes,
            source=ObjectSource.zeros(token_bytes),
            permissions=int(
                Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
            ),
            key="obj.token_ring",
        )
        generation_policy = builder.generation_policy(
            eos_token_ids=[int(i) for i in policy_body.get("eos_token_ids", [0])][:8],
            max_new_tokens=int(policy_body.get("maximum_new_tokens", 1024)),
            vocabulary_size=int(policy_body.get("vocabulary_size", 1)),
            token_ring_object_id=token_ring,
            selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
            key="policy",
        )
        self.emit_program()
        builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=Phase.PREFILL,
            generation_policy_id=generation_policy,
        )
        builder.entrypoint(
            entrypoint_id=1,
            first_instruction=0,
            phase=Phase.DECODE,
            generation_policy_id=generation_policy,
        )
        builder.source_identity = {
            "graph_id": self.graph.graph_id,
            "model_id": self.graph.model_id,
            "numeric_profile": self.graph.numeric_profile,
            "product": self.policy.product,
            "weight_storage_class": StorageClass(self.weight_storage_class).name,
        }
        builder.notes["rom_plan"] = plan.to_dict()
        builder.notes["rom_lowering"] = {
            "compressed_kernel_count": self.analysis.compressed_kernel_count,
            "layer_runs": [
                {
                    "body_positions": run.positions,
                    "first_layer": run.layers[0],
                    "layers_covered": run.layers_covered,
                    "loop_trip": run.groups,
                    "period": run.period,
                    "run": run.index,
                }
                for run in self.analysis.runs
            ],
            "link_instruction_count": self._link_instruction_count,
            "numeric_contract_substitutions": dict(
                sorted(self._contract_substitutions.items())
            ),
            "schedule_descriptor_count": len(self._schedule_cache),
            "source_kernel_count": len(self.graph.kernels),
            "state_groups": len(set(self._state_descriptor.values())),
            "tile_mapping_owner": "schedule_descriptor",
        }
        return builder.finish()


def lower(
    graph: KernelGraph,
    capability: Capability,
    policy: RomTargetPolicy,
    *,
    weight_storage_class: StorageClass = StorageClass.ROM,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto ``policy``'s ROM target and return both artifacts."""
    lowering = RomLowering(
        graph, capability, policy, weight_storage_class=weight_storage_class
    )
    lowering.plan_regions()
    deployment = lowering.build()
    assert lowering.plan is not None
    return deployment, lowering.plan


__all__ = [
    "GraphAnalysis",
    "LayerRun",
    "LinkStep",
    "RomLowering",
    "RomLoweringError",
    "RomTargetPolicy",
    "analyze",
    "lower",
]
