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
    Kernel,
    KernelGraph,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
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
from runtime.abi3.constants import IntegrityMode
from runtime.abi3.deployment import Deployment, ObjectSource
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.descriptors import (
    LayoutClass,
    MAX_RANK,
    Phase,
    SelectionMode,
    Symbol,
)

from .image import (
    DTYPE_BY_NAME,
    DefectRecord,
    RegionRequest,
    RomCoordinate,
    RomImagePlan,
    RomLayoutPolicy,
    RomMember,
    ROM_PERMISSIONS,
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

#: Spellings a kernel *attribute* may use for a numeric format.  Tensor dtypes
#: are checked against the neutral registry, but attributes are free text, and
#: front ends legitimately write the IEEE names.
DTYPE_ALIASES: Mapping[str, str] = {
    "bfloat16": "bf16",
    "binary16": "fp16",
    "binary32": "fp32",
    "binary64": "fp32",
    "e8m0_scale": "e8m0",
    "float16": "fp16",
    "float32": "fp32",
    "float8_e4m3fn": "fp8_e4m3fn",
    "float8_e5m2": "fp8_e5m2",
    "fp4_e2m1": "mxfp4_e2m1",
    "int32": "i32",
    "int64": "i64",
    "int8": "i8",
    "mxfp4": "mxfp4_e2m1",
    "uint32": "u32",
    "uint64": "u64",
    "uint8": "u8",
}

#: Neutral state-class name -> frozen ABI 3.0 :class:`StateClass`.
#:
#: ``compressor_window`` has no exact value in the frozen registry.  It is
#: session-durable, transactional, row-appended recurrent compressor state, so
#: ``SCRATCH`` would misdescribe it and ``COMPRESSED_KV`` is the closest frozen
#: class that preserves durability and commit semantics.  The alias is recorded
#: in the deployment manifest rather than hidden, and the gap is reported: the
#: registry needs its own value through a versioned minor bump, which a backend
#: may not make privately.
STATE_CLASS_BY_NAME: Mapping[str, StateClass] = {
    "kv_cache": StateClass.KV_CACHE,
    "kv_window": StateClass.KV_CACHE,
    "compressed_kv": StateClass.COMPRESSED_KV,
    "compressor_window": StateClass.COMPRESSED_KV,
    "token_ring": StateClass.TOKEN_RING,
    "position_cursor": StateClass.POSITION_CURSOR,
    "route_history": StateClass.ROUTE_HISTORY,
    "scratch": StateClass.SCRATCH,
}

#: Neutral names that have no exact frozen class, and the value they borrow.
STATE_CLASS_ALIASES: Mapping[str, str] = {
    "compressor_window": "COMPRESSED_KV",
    "kv_window": "KV_CACHE",
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


def _binary32_bits(attributes: Mapping[str, Any], keys: Sequence[str]) -> int:
    """Read a numeric-descriptor constant as a binary32 bit pattern.

    A graph may state such a constant three ways: already as a bit pattern, as
    a BF16 code (the model's own storage form, which widens exactly by a
    sixteen-bit shift), or as a real number. The descriptor field is a binary32
    pattern, so all three are converted here rather than at three call sites.
    """
    import struct

    for key in keys:
        if key not in attributes:
            continue
        value = attributes[key]
        if key.endswith("_bits"):
            return int(value) & 0xFFFFFFFF
        if key.endswith("_bf16_code"):
            return (int(value) & 0xFFFF) << 16
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int.from_bytes(struct.pack("<f", float(value)), "little")
    return 0


# ---------------------------------------------------------------------------
# Operand geometry (TA-ABI3-OPCONV-1) and token blocking (amendment A13)
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class KernelShape:
    """Everything an operator's views need that the kernel alone does not say."""

    contraction: bool
    #: Static leading extent of the principal operand: the token block when the
    #: leading axis is a runtime symbol, otherwise the declared extent.
    rows: int
    cols: int
    depth: int
    transposed: bool
    row_symbolic: bool
    block: int
    trip: int
    symbol: int
    principal: tuple[int, ...]


#: Neutral symbol name -> the frozen runtime-symbol registry.
SYMBOL_BY_NAME: Mapping[str, Symbol] = {
    "span_tokens": Symbol.SPAN_TOKENS,
    "context_tokens": Symbol.CONTEXT_LENGTH,
    "position_start": Symbol.POSITION_START,
    "position_end": Symbol.POSITION_END,
    "generation_index": Symbol.GENERATION_INDEX,
    "batch": Symbol.BATCH,
}

#: Contraction subopcodes: the operations whose operands are stated as matrices.
CONTRACTION_SUBOPS = frozenset(
    {
        int(TensorOp.MATMUL),
        int(TensorOp.GROUPED_MATMUL),
        int(TensorOp.ROUTED_MATMUL),
    }
)


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
    #: Rows one iteration of a token-block loop covers.  Zero means one block
    #: spanning the whole declared context, which is the fewest dispatches a
    #: request can be served in; a smaller block trades dispatches for a smaller
    #: live activation window.  Either way amendment A13 resolves the final
    #: iteration to the rows the request actually has.
    token_block_rows: int = 0
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
        self._generated_objects: dict[str, int] = {}
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
        self._state_column: dict[str, int] = {}
        self._substituted_inputs: dict[str, str] = {}
        self._position_input_cache: frozenset[str] | None = None
        self._state_owner: dict[str, str] = {}
        self._event_of_tensor: dict[str, int] = {}
        self._communications: list[tuple[str, int]] = []
        self._link_instruction_count = 0
        self._queue_cursor: dict[int, int] = {}
        self._contract_substitutions: dict[str, str] = {}
        self._state_class_aliases: dict[str, str] = {}
        self._port_cursor = 0
        self._unify_buffers()

    # -- sizes ----------------------------------------------------------
    def _extent(self, value: Any) -> int:
        """Resolve a possibly symbolic extent to the largest value it can take.

        ``Symbolic.maximum`` is the maximum of the *extent*, already including
        ``multiplier`` -- the DeepSeek front end writes ``multiplier=6,
        maximum=1572864`` for six routed copies of a 262,144-token span.  The
        multiplier is only used when no maximum is declared, where the
        capability's context bound stands in.
        """
        if isinstance(value, Symbolic):
            if value.maximum:
                return max(int(value.maximum), 1)
            bound = self.capability.limits["max_context_positions"]
            return max(bound * int(value.multiplier or 1), 1)
        return max(int(value), 1)

    def _dims(self, tensor: Tensor) -> tuple[int, ...]:
        dims = tuple(self._extent(d) for d in tensor.shape)
        if not 1 <= len(dims) <= MAX_RANK:
            raise RomLoweringError(
                f"tensor {tensor.tensor_id!r} has rank {len(dims)}, outside 1..{MAX_RANK}"
            )
        return dims

    def _dtype(self, name: str) -> DType:
        resolved = DTYPE_ALIASES.get(name, name)
        try:
            return DTYPE_BY_NAME[resolved]
        except KeyError:
            raise RomLoweringError(
                f"dtype {name!r} has no ABI 3.0 storage type"
            ) from None

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
            # A derived constant is mask-programmed as its own object rather
            # than as a member of a checkpoint-backed region: it has no
            # checkpoint byte range to name, and its authentication is the
            # digest of its declared generator's output. `_region_object`
            # materialises it on first reference.
            if any(t.generator for column in columns for t in column):
                if not all(t.generator for column in columns for t in column):
                    raise RomLoweringError(
                        f"operand {key!r} mixes derived constants with "
                        "checkpoint-backed weights; a region is one or the other"
                    )
                return
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
                if all(
                    t.scale_tensor_id and t.scale_tensor_id in self.tensors
                    for t in column
                )
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
            place_operand(
                key,
                "expert_bank",
                [[self.tensors[n] for n in group] for group in names],
            )

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

        # A derived constant is placed as its own mask-programmed object on
        # first reference, so it is legitimately absent from the region plan.
        # Everything else backed by checkpoint bytes must be placed, or it
        # would silently have no home.
        unplaced = sorted(
            t.tensor_id
            for t in self.graph.tensors
            if t.role in WEIGHT_ROLES
            and t.tensor_id not in placed
            and not t.generator
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
            if tensor.generator:
                raise RomLoweringError(
                    f"constant {tensor.tensor_id!r} is derived, so it is placed "
                    "as its own mask-programmed object rather than as a member "
                    "of a checkpoint-backed region; this is a caller error"
                )
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} has neither a checkpoint binding "
                "nor a generator.  A ROM region names authenticated checkpoint "
                "bytes or a declared deterministic generator, never a private "
                "copy of unspecified contents"
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
        # An engine reads its epsilon and its scale from the numeric
        # descriptor, so a kernel that declares either must have it carried
        # through. Omitting them produced a deployment the verifier admitted
        # and the RMSNorm engine then refused at execution, which is the worst
        # place for a missing field to surface.
        epsilon_bits = _binary32_bits(attributes, ("epsilon_bits", "epsilon"))
        scale_bits = _binary32_bits(
            attributes, ("scale_bits", "scale_bf16_code", "scale")
        )
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
            epsilon_bits,
            scale_bits,
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
            epsilon_bits=epsilon_bits,
            scale_bits=scale_bits,
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
        strides: Sequence[int] | None = None,
        element_offset: int = 0,
        dynamic: Sequence[DynamicTerm] = (),
        permissions: int = int(Permission.READ),
        scale_object_id: int = NO_ID,
        scale_block_elements: int = 0,
        label: str = "view",
    ) -> int:
        # Amendment A8 freezes block-scale addressing: one scale byte per
        # ``scale_block_elements`` in the view's logical row-major order.
        layout = (
            LayoutClass.BLOCK_SCALED
            if scale_object_id != NO_ID and scale_block_elements
            else LayoutClass.DENSE
        )
        key = (
            object_id,
            int(dtype),
            tuple(dims),
            tuple(strides) if strides is not None else None,
            element_offset,
            tuple((t.kind, t.index, t.stride) for t in dynamic),
            permissions,
            scale_object_id,
            scale_block_elements,
            int(layout),
        )
        if key in self._view_cache:
            return self._view_cache[key]
        if layout is LayoutClass.BLOCK_SCALED and dims[-1] % scale_block_elements:
            raise RomLoweringError(
                f"block-scaled view of {dims} needs the last axis to be a multiple "
                f"of {scale_block_elements}"
            )
        descriptor = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            strides=list(strides) if strides is not None else None,
            element_offset=element_offset,
            dynamic=list(dynamic),
            layout_class=layout,
            scale_object_id=scale_object_id,
            scale_block_elements=scale_block_elements,
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
    def _state_tensors(self) -> dict[str, list[tuple[str, str]]]:
        """Role=``state`` planes of each resource, with the direction they use.

        A kernel that writes a resource defines the row layout; a kernel that
        reads one addresses the planes those writes produced.  Both are recorded
        so the column assignment can pair them.
        """
        order: dict[str, list[tuple[str, str]]] = {}
        owner: dict[str, str] = {}
        for kernel in self.graph.kernels:
            state_ids = kernel.state_reads or kernel.state_writes
            if not state_ids:
                continue
            for direction, names in (("in", kernel.inputs), ("out", kernel.outputs)):
                for name in names:
                    tensor = self.tensors[name]
                    declared = tensor.role == "state"
                    writes = direction == "out" and bool(kernel.state_writes)
                    if not (declared or writes) or name in owner:
                        continue
                    state_id = (
                        kernel.state_writes[0]
                        if writes and kernel.state_writes
                        else state_ids[0]
                    )
                    owner[name] = state_id
                    order.setdefault(state_id, []).append((name, direction))
        self._state_owner = owner
        return order

    def emit_states(self) -> None:
        """Merge congruent per-layer state resources into one physical state.

        The IR names 36 (or 43) per-layer KV resources.  On a ROM target they
        are one physical HBM object with a per-layer slot, so the compressed
        layer body can reach the current layer's rows through the same dynamic
        term the weights use, and so one prepare/commit covers the whole token
        step.  Partial layer advancement therefore cannot become architectural.
        """
        views = self._state_tensors()
        footprint = {
            state_id: sum(
                self._bytes(self.tensors[name])
                for name, direction in names
                if direction == "in"
            )
            or sum(self._bytes(self.tensors[name]) for name, _ in names)
            for state_id, names in views.items()
        }
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
                    "ABI 3.0 registry and has no documented alias; extend the "
                    "registry through a versioned change, never privately"
                )
            if members[0].state_class in STATE_CLASS_ALIASES:
                self._state_class_aliases[members[0].state_class] = (
                    STATE_CLASS_ALIASES[members[0].state_class]
                )
            dtype = self._dtype(members[0].dtype)
            bits = DTYPE_BITS[dtype]
            row_bytes = (members[0].row_elements * bits + 7) // 8
            capacity = self._extent(members[0].capacity_rows)
            # The IR's row contract describes the append transaction.  The
            # physical slot must additionally hold every declared view of the
            # resource -- a windowed KV resource exposes a key history and a
            # value history, each of the full capacity -- so the object is sized
            # to the larger of the two.
            slot_bytes = max(
                row_bytes * capacity,
                max((footprint.get(m.state_id, 0) for m in members), default=0),
            )
            if slot_bytes <= 0:
                raise RomLoweringError(
                    f"state group {index} has no capacity"
                )
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
        """Give every state operand a *column* inside its resource's row.

        A KV resource holds one fused row per position -- ``key`` then ``value``
        -- and the graph names each plane as its own tensor.  So a plane is a
        view with the resource's row width as its leading stride and its column
        as the element offset: a description of half a row, never a copy of one.

        Columns are assigned in first-use order within each direction, and the
        k-th plane a resource *reads* is the k-th plane it *writes*.  That is
        what pairs ``key_history`` with the append that produced it without the
        backend knowing what a key is.
        """
        order = self._state_tensors()
        columns: dict[str, int] = {}
        for state_id, names in order.items():
            group_key, _slot = self._state_slot.get(state_id, (None, 0))
            if group_key is None:
                continue
            row_elements = self._state_group_shape[group_key][2]
            cursor = {"in": 0, "out": 0}
            for name, direction in names:
                width = self._plane_width(name)
                if cursor[direction] + width > row_elements:
                    raise RomLoweringError(
                        f"state planes of {state_id!r} need "
                        f"{cursor[direction] + width} elements but its row is "
                        f"{row_elements}"
                    )
                columns.setdefault(self._state_struct_key(name), cursor[direction])
                cursor[direction] += width
        self._state_column = columns

    def _plane_width(self, tensor_id: str) -> int:
        """Elements one position contributes: the non-leading extents' product."""
        dims = self._dims(self.tensors[tensor_id])
        width = 1
        for extent in dims[1:]:
            width *= extent
        return width

    def _state_struct_key(self, tensor_id: str) -> str:
        """Structural identity of a state operand, shared by every layer."""
        placement = self.analysis.body_input.get(
            tensor_id
        ) or self.analysis.body_output.get(tensor_id)
        if placement is not None:
            run, position, slot = placement
            return f"st.r{run}.p{position:03d}.s{slot}"
        return f"st.g.{tensor_id}"

    def _state_plane_view(
        self, kernel: Kernel, tensor_id: str, direction: str, run: LayerRun | None
    ) -> int | None:
        """One plane of a merged state resource, moved by the layer loop.

        The window is the resource's whole capacity rather than a token block:
        attention reads the entire context, and an append addresses absolute
        positions.  Both directions name the *prepared* image, because a
        transaction attends the rows it has just appended; the committed image
        is the durability record the commit publishes, not the buffer execution
        runs against.
        """
        state_id = self._state_owner.get(tensor_id)
        if state_id is None and direction == "out" and kernel.state_writes:
            state_id = kernel.state_writes[0]
        if state_id is None or state_id not in self._state_slot:
            return None
        group_key, slot = self._state_slot[state_id]
        slot_bytes, capacity, row_elements = self._state_group_shape[group_key]
        prepared = self.builder.lookup(f"obj.{group_key}")
        tensor = self.tensors[tensor_id]
        dtype = self._dtype(tensor.dtype)
        bits = DTYPE_BITS[dtype]
        window = slot_bytes * 8 // bits
        column = self._state_column.get(self._state_struct_key(tensor_id), 0)
        extents = list(self._dims(tensor))
        if len(extents) < 2:
            extents = [capacity, max(row_elements - column, 1)]
        else:
            extents[0] = capacity
        strides = [1] * len(extents)
        running = 1
        for axis in range(len(extents) - 1, 0, -1):
            strides[axis] = running
            running *= extents[axis]
        strides[0] = row_elements
        dynamic: list[DynamicTerm] = []
        loop, advance = self._loop_for_state_slot(tensor_id, run)
        offset = slot * window + column
        if loop is not None:
            stride = window * advance
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"state group {group_key} needs a per-layer element stride of "
                    f"{stride}, which does not fit the 32-bit dynamic-term stride "
                    "field of ABI 3.0 tensor views"
                )
            dynamic.append(DynamicTerm.loop(loop, stride))
            offset = column
        return self._view(
            object_id=prepared,
            dtype=dtype,
            dims=extents,
            strides=strides,
            element_offset=offset,
            dynamic=dynamic,
            permissions=int(Permission.READ | Permission.WRITE),
            label="view.state",
        )

    def _loop_for_state_slot(
        self, tensor_id: str, run: LayerRun | None
    ) -> tuple[int | None, int]:
        """The loop that indexes this state operand, and its slot advance.

        The advance is measured, not assumed: it is the difference between the
        state slots the successive groups of the run actually name.  In a
        period-2 stack only one layer of the period may own a given resource,
        so the advance is one slot per iteration even though the period is two.
        """
        placement = self.analysis.body_input.get(
            tensor_id
        ) or self.analysis.body_output.get(tensor_id)
        if placement is None:
            return None, 1
        loop = self._loop_of_run.get(placement[0])
        names = self.analysis.body_operand.get(placement)
        if names is None or len(names) < 2:
            if run is None or run.groups < 2:
                return loop, 1
            names = None
        if names is None:
            return loop, 1
        slots: list[int] = []
        for name in names:
            state_id = self._state_owner.get(name)
            if state_id is None or state_id not in self._state_slot:
                return loop, 1
            slots.append(self._state_slot[state_id][1])
        steps = {second - first for first, second in zip(slots, slots[1:])}
        if len(steps) != 1:
            raise RomLoweringError(
                f"state operand {tensor_id!r} moves by {sorted(steps)} slots "
                "between loop iterations; a single dynamic term needs one stride"
            )
        return loop, steps.pop()

    # -- token blocking and operand geometry ------------------------------
    def _leading_symbol(self, tensor: Tensor) -> tuple[int | None, int]:
        """The runtime symbol of a tensor's leading axis, and its multiplier."""
        if not tensor.shape or not isinstance(tensor.shape[0], Symbolic):
            return None, 1
        axis = tensor.shape[0]
        symbol = SYMBOL_BY_NAME.get(axis.symbol)
        return (int(symbol) if symbol is not None else None), int(axis.multiplier or 1)

    def _principal(self, kernel: Kernel) -> Tensor | None:
        if kernel.outputs:
            return self.tensors[kernel.outputs[0]]
        if kernel.inputs:
            return self.tensors[kernel.inputs[0]]
        return None

    def _shape_of(self, kernel: Kernel, engine) -> KernelShape:
        """Derive one operator's matrix geometry and its token block."""
        family = Major(engine.family)
        contraction = family is Major.TENSOR and engine.sub in CONTRACTION_SUBOPS
        principal = self._principal(kernel)
        principal_dims = tuple(self._dims(principal)) if principal is not None else (1,)
        symbol, multiplier = (
            self._leading_symbol(principal) if principal is not None else (None, 1)
        )
        # A13 states the resolved leading extent as ``symbol - iteration *
        # bound_divisor``.  A multiplied symbolic extent -- six routed copies of
        # a span -- is not expressible that way, so such an operand keeps its
        # full declared extent rather than silently presenting the wrong rows.
        row_symbolic = symbol is not None and multiplier == 1
        span_max = int(self.capability.limits["max_context_positions"])
        configured = int(self.policy.token_block_rows or 0)
        block = max(min(configured or span_max, span_max), 1)
        declared_rows = principal_dims[0] if principal_dims else 1
        trip = max(-(-declared_rows // block), 1) if row_symbolic else 1
        rows = block if row_symbolic else max(declared_rows, 1)

        cols = principal_dims[-1] if len(principal_dims) > 1 else 1
        depth = 0
        transposed = False
        if contraction:
            weight = self._contraction_weight(kernel)
            activation = self.tensors[kernel.inputs[0]] if kernel.inputs else None
            weight_dims = tuple(self._dims(weight)) if weight is not None else (1, 1)
            act_dims = tuple(self._dims(activation)) if activation is not None else (1,)
            depth = int(
                self._extent(kernel.iteration_domain.get("reduction_width", 0)) or 0
            )
            if depth <= 1:
                depth = act_dims[-1]
            # TA-ABI3-OPCONV-1 section 2: in1 is n-major ``[N, K]``.  A
            # checkpoint that stores ``[K, N]`` is presented n-major by swapping
            # the view's strides, never by a relayout pass.
            if len(weight_dims) >= 2 and weight_dims[-1] == depth:
                cols, transposed = weight_dims[-2], False
            elif len(weight_dims) >= 2 and weight_dims[-2] == depth:
                cols, transposed = weight_dims[-1], True
            else:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: weight {weight_dims} shares no "
                    f"reduction axis with the activation {act_dims}"
                )
            # The output is the matrix ``[rows, N]`` whatever rank the graph
            # gave it: a head-shaped result is the same bytes described three
            # ways, and folding it costs nothing and moves nothing.
            out_elements = 1
            for extent in principal_dims:
                out_elements *= extent
            if row_symbolic:
                out_elements = out_elements // max(declared_rows, 1) * rows
            if cols and out_elements % cols:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: result of {out_elements} "
                    f"elements is not a whole number of {cols}-wide rows"
                )
        return KernelShape(
            contraction=contraction,
            rows=rows,
            cols=cols,
            depth=depth,
            transposed=transposed,
            row_symbolic=row_symbolic,
            block=block,
            trip=trip,
            symbol=symbol if symbol is not None else int(Symbol.SPAN_TOKENS),
            principal=principal_dims,
        )

    def _contraction_weight(self, kernel: Kernel) -> Tensor | None:
        if "expert_weight_tensors" in kernel.attributes:
            names = list(kernel.attributes["expert_weight_tensors"])
            return self.tensors[names[0]] if names else None
        for name in kernel.inputs[1:]:
            tensor = self.tensors[name]
            if tensor.role in WEIGHT_ROLES:
                return tensor
        return self.tensors[kernel.inputs[1]] if len(kernel.inputs) > 1 else None

    def _open_row_loop(self, kernel: Kernel, shape: KernelShape) -> int | None:
        """Open this kernel's token-block loop, if its rows are a symbol.

        The loop counts blocks -- step one, ``bound_divisor`` the block -- so a
        view's row term advances by a whole block and amendment A13 reads the
        induction value as the block index it is.  With one block over the whole
        declared context the loop runs once and exists only to carry that
        resolution; with a smaller block it also bounds the live window.
        """
        if not shape.row_symbolic:
            return None
        loop = self.builder.loop_control(
            lower_bound=0,
            upper_bound=shape.trip,
            step=1,
            max_iterations=shape.trip,
            bound_symbol=Symbol(shape.symbol),
            bound_divisor=shape.block,
            counter_class_id=self._counter_class("instruction", Major.CONTROL),
            key=f"loop.block.k{kernel.index:05d}",
        )
        self.builder.open_loop(loop)
        return loop

    @property
    def _position_inputs(self) -> frozenset[str]:
        """Declared inputs whose content is the request's position range.

        A rank-one index vector over the token axis that no embedding reads
        holds ``POSITION_START + i`` and nothing else.  ADR-003 binds that range
        as a request symbol, so it is materialised from the frozen
        ``arange_u32_v1`` generator and the view is offset by the symbol --
        identical values, and no host window that nothing could fill.
        """
        cached = getattr(self, "_position_input_cache", None)
        if cached is not None:
            return cached
        consumers: dict[str, list[str]] = {}
        for kernel in self.graph.kernels:
            for name in kernel.inputs:
                consumers.setdefault(name, []).append(kernel.kind)
        names = set()
        for tensor in self.graph.tensors:
            if tensor.role != "input" or tensor.dtype not in {"u32", "i32"}:
                continue
            if len(tensor.shape) != 1 or not isinstance(tensor.shape[0], Symbolic):
                continue
            kinds = consumers.get(tensor.tensor_id, [])
            if not kinds or any(k == "EMBEDDING_LOOKUP" for k in kinds):
                continue
            names.add(tensor.tensor_id)
        self._position_input_cache = frozenset(names)
        return self._position_input_cache

    def _position_object(self, tensor_id: str) -> int:
        """The mask-programmed position range, materialised once."""
        cached = self._generated_objects.get(tensor_id)
        if cached is not None:
            return cached
        from runtime.sim.generators import GeneratorError, digest_of, generate

        span_max = int(self.capability.limits["max_context_positions"])
        parameters = {"count": max(2 * span_max, 1)}
        try:
            payload = generate("arange_u32_v1", parameters)
            digest = digest_of("arange_u32_v1", parameters)
        except GeneratorError as exc:  # pragma: no cover - frozen generator
            raise RomLoweringError(f"position range {tensor_id!r}: {exc}") from None
        object_id = self.builder.memory_object(
            storage_class=self.weight_storage_class,
            size_bytes=int(payload.nbytes),
            source=ObjectSource.generated(
                "arange_u32_v1", parameters, int(payload.nbytes), digest
            ),
            permissions=ROM_PERMISSIONS,
            alignment_log2=12,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=bytes.fromhex(digest),
            key=f"obj.rom.positions.{tensor_id}",
        )
        self._generated_objects[tensor_id] = object_id
        self._substituted_inputs[tensor_id] = "arange_u32_v1"
        return object_id

    # -- operand views ---------------------------------------------------
    def _row_term(self, tensor: Tensor, shape: KernelShape, loop: int | None):
        """The block term that moves a view's leading axis, if it has one."""
        if loop is None or not shape.row_symbolic:
            return None
        symbol, multiplier = self._leading_symbol(tensor)
        if symbol is None or multiplier != 1:
            return None
        width = 1
        for extent in self._dims(tensor)[1:]:
            width *= extent
        stride = shape.block * width
        if stride > 0xFFFFFFFF:
            raise RomLoweringError(
                f"tensor {tensor.tensor_id!r} needs a token-block element stride "
                f"of {stride}, which does not fit the 32-bit dynamic-term stride "
                "field of ABI 3.0 tensor views; declare a smaller block"
            )
        return DynamicTerm.loop(loop, stride)

    def _buffer_view(
        self,
        tensor: Tensor,
        *,
        dims: Sequence[int],
        strides: Sequence[int] | None,
        shape: KernelShape,
        loop: int | None,
        writable: bool,
        blocked: bool = True,
    ) -> int:
        object_id = self._buffer(tensor.tensor_id)
        permissions = (
            int(Permission.READ | Permission.WRITE) if writable else int(Permission.READ)
        )
        if tensor.role in {"input", "output"}:
            permissions |= int(Permission.HOST_VISIBLE)
        scale_object = NO_ID
        block = 0
        if tensor.scale_tensor_id and tensor.scale_tensor_id in self.tensors:
            scale = self.tensors[tensor.scale_tensor_id]
            block = int(tensor.scale_block_elements or 0)
            if block:
                scale_object = (
                    self._region_object(scale.tensor_id)
                    if scale.role in WEIGHT_ROLES
                    else self._buffer(scale.tensor_id)
                )
        term = self._row_term(tensor, shape, loop) if blocked else None
        return self._view(
            object_id=object_id,
            dtype=self._dtype(tensor.dtype),
            dims=dims,
            strides=strides,
            dynamic=[term] if term is not None else (),
            permissions=permissions,
            scale_object_id=scale_object,
            scale_block_elements=block if scale_object != NO_ID else 0,
            label="view.buf",
        )

    def _blocked_dims(self, tensor: Tensor, shape: KernelShape) -> list[int]:
        """The tensor's declared extents with its leading axis token-blocked."""
        dims = list(self._dims(tensor))
        symbol, multiplier = self._leading_symbol(tensor)
        if dims and symbol is not None and multiplier == 1 and shape.row_symbolic:
            dims[0] = min(shape.block, dims[0])
        return dims

    def _broadcast(
        self, dims: list[int], shape: KernelShape
    ) -> tuple[list[int], list[int] | None]:
        """Insert the principal operand's missing middle axes at stride zero.

        A rotary coefficient table holds one row per *token* while the tensor it
        rotates holds one per ``(token, head)``: every head of a token shares the
        row.  A zero stride says so, and nothing is copied to make it true.  The
        rule is positional and model-blind -- one axis fewer, agreeing on the
        leading extent -- so it never has to know what a head is.
        """
        principal = list(shape.principal)
        if shape.row_symbolic and principal:
            principal[0] = min(shape.block, principal[0])
        if len(dims) < 2 or len(principal) != len(dims) + 1:
            return dims, None
        if principal[0] != dims[0]:
            return dims, None
        strides = [1] * len(dims)
        running = 1
        for axis in range(len(dims) - 1, -1, -1):
            strides[axis] = running
            running *= dims[axis]
        inserted = list(principal[1:-1])
        return (
            [dims[0], *inserted, dims[-1]],
            [strides[0], *([0] * len(inserted)), strides[-1]],
        )

    def _index_view(
        self,
        kernel: Kernel,
        shape: KernelShape,
        name: str,
        loop: int | None,
        *,
        count: int,
        absolute: bool,
    ) -> int:
        """A movement's index vector: one index per row the movement touches.

        Absolute when what it addresses is indexed by position -- a rotary table
        spans every admissible position, a KV window every row of the context --
        and span-relative when it addresses the request's own rows.  Selecting
        the final row of a span is ``SPAN_LAST_INDEX``; a view offsets by
        ``selector * stride`` and cannot compute ``span - 1`` for itself.
        """
        tensor = self.tensors[name]
        terms: list[DynamicTerm] = []
        if absolute:
            terms.append(DynamicTerm.symbol(Symbol.POSITION_START, 1))
            if loop is not None and shape.row_symbolic:
                terms.append(DynamicTerm.loop(loop, shape.block))
        elif count == 1:
            terms.append(DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX, 1))
        elif loop is not None and shape.row_symbolic:
            terms.append(DynamicTerm.loop(loop, shape.block))
        if name in self._position_inputs:
            object_id = self._position_object(name)
            permissions = int(Permission.READ)
        else:
            object_id = self._buffer(name)
            permissions = int(Permission.READ)
            if tensor.role in {"input", "output"}:
                permissions |= int(Permission.HOST_VISIBLE)
        return self._view(
            object_id=object_id,
            dtype=self._dtype(tensor.dtype),
            dims=[max(count, 1)],
            strides=[1],
            dynamic=terms,
            permissions=permissions,
            label="view.index",
        )

    def _operand_view(
        self,
        kernel: Kernel,
        shape: KernelShape,
        *,
        slot: int,
        direction: str,
        name: str,
        run: LayerRun | None,
        loop: int | None,
        family: Major,
        sub: int,
    ) -> int:
        tensor = self.tensors[name]
        writable = direction == "out"
        # A declared state effect is the authority: a kernel that writes a state
        # resource writes into that resource's prepared image, even when the
        # graph names the result as an ordinary activation.
        if tensor.role == "state" or (writable and kernel.state_writes):
            view = self._state_plane_view(kernel, name, direction, run)
            if view is not None:
                return view
        if tensor.role in WEIGHT_ROLES:
            return self._weight_view(name, run=run, shape=shape, slot=slot)
        if family is Major.SELECTION:
            # TA-ABI3-OPCONV-1 section 8: selection operands are one-dimensional
            # and an ID is exactly one element.
            elements = 1
            if direction == "in" and sub == int(Selection.ARGMAX):
                for extent in self._dims(tensor):
                    elements *= extent
            return self._buffer_view(
                tensor,
                dims=[max(elements, 1)],
                strides=[1],
                shape=shape,
                loop=loop,
                writable=writable,
                blocked=False,
            )
        if shape.contraction and direction == "in" and slot == 0:
            return self._buffer_view(
                tensor,
                dims=[shape.rows, shape.depth],
                strides=[shape.depth, 1],
                shape=shape,
                loop=loop,
                writable=False,
            )
        if shape.contraction and direction == "out" and slot == 0:
            return self._buffer_view(
                tensor,
                dims=[shape.rows, shape.cols],
                strides=[shape.cols, 1],
                shape=shape,
                loop=loop,
                writable=True,
            )
        dims = self._blocked_dims(tensor, shape)
        broadcast_dims, broadcast_strides = (
            self._broadcast(dims, shape) if direction == "in" and slot > 0 else (dims, None)
        )
        return self._buffer_view(
            tensor,
            dims=broadcast_dims,
            strides=broadcast_strides,
            shape=shape,
            loop=loop,
            writable=writable,
        )

    def _region_object(self, tensor_id: str) -> int:
        if self.plan is None:  # pragma: no cover - programming error
            raise RomLoweringError("plan_regions() must run before lowering")
        generated = self._generated_object(tensor_id)
        if generated is not None:
            return generated
        key, _slot = self._region_of_tensor[tensor_id]
        return self.plan.region(key).object_id

    def _generated_object(self, tensor_id: str) -> int | None:
        """Place a derived constant as its own mask-programmed ROM object.

        A rotary coefficient table is exactly the kind of thing a mask ROM is
        for: a constant array, fixed at manufacture, that no checkpoint
        contains. Its authentication is the digest of its declared generator's
        output rather than a checkpoint byte range, and the device re-derives
        and re-checks it at load, so nothing is taken on trust.
        """
        tensor = self.tensors.get(tensor_id)
        if tensor is None or not tensor.generator:
            return None
        cached = self._generated_objects.get(tensor_id)
        if cached is not None:
            return cached
        from runtime.sim.generators import GeneratorError, digest_of, generate

        try:
            payload = generate(tensor.generator, tensor.generator_parameters)
            digest = digest_of(tensor.generator, tensor.generator_parameters)
        except GeneratorError as exc:
            raise RomLoweringError(f"constant {tensor_id!r}: {exc}") from None
        object_id = self.builder.memory_object(
            storage_class=self.weight_storage_class,
            size_bytes=int(payload.nbytes),
            source=ObjectSource.generated(
                tensor.generator,
                tensor.generator_parameters,
                int(payload.nbytes),
                digest,
            ),
            permissions=ROM_PERMISSIONS,
            alignment_log2=12,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=bytes.fromhex(digest),
            key=f"obj.rom.generated.{tensor_id}",
        )
        self._generated_objects[tensor_id] = object_id
        return object_id

    def _weight_view(
        self,
        tensor_id: str,
        *,
        run: LayerRun | None,
        shape: KernelShape | None = None,
        slot: int = 1,
    ) -> int:
        if self.plan is None:  # pragma: no cover - programming error
            raise RomLoweringError("plan_regions() must run before lowering")
        tensor = self.tensors[tensor_id]
        dims: Sequence[int] = self._dims(tensor)
        strides: Sequence[int] | None = None
        if shape is not None and shape.contraction and slot == 1 and len(dims) >= 2:
            # TA-ABI3-OPCONV-1 section 2: in1 is ``[N, K]``.  A checkpoint that
            # stores ``[K, N]`` is presented n-major by swapping the view's
            # strides -- a description, never a relayout pass.
            dims = [shape.cols, shape.depth]
            strides = [1, shape.cols] if shape.transposed else [shape.depth, 1]
        generated = self._generated_object(tensor_id)
        if generated is not None:
            # A derived constant has one mask-programmed object of its own and
            # no per-layer striping, so the view is the whole table.
            return self._view(
                object_id=generated,
                dtype=self._dtype(tensor.dtype),
                dims=dims,
                strides=strides,
                permissions=int(Permission.READ),
                label="view.rom.generated",
            )
        key, region_slot = self._region_of_tensor[tensor_id]
        region = self.plan.region(key)
        dtype = self._dtype(tensor.dtype)
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
            element_offset = region_slot * region.slot_element_stride
        scale_object, block = self._scale_binding(key)
        return self._view(
            object_id=region.object_id,
            dtype=dtype,
            dims=dims,
            strides=strides,
            element_offset=element_offset,
            dynamic=dynamic,
            permissions=int(Permission.READ),
            scale_object_id=scale_object,
            scale_block_elements=block,
            label="view.rom",
        )

    def _scale_binding(self, region_key: str) -> tuple[int, int]:
        """The immutable block-scale object that scales ``region_key``."""
        if self.plan is None or region_key not in self._scale_of_region:
            return NO_ID, 0
        scale_key, block = self._scale_of_region[region_key]
        if not block:
            return NO_ID, 0
        return self.plan.region(scale_key).object_id, block

    def _expert_bank_view(self, kernel: Kernel, run: LayerRun | None) -> int:
        """One view over a layer's whole routed expert bank.

        The engine resolves the runtime expert ID inside this view
        (TA-ABI3-OPCONV-1 section 2), so a routed matmul needs exactly one
        weight descriptor no matter how many experts the layer has -- and the
        expert dimension is an addressing dimension, never a program loop.
        """
        names = list(kernel.attributes["expert_weight_tensors"])
        key, _slot = self._region_of_tensor[names[0]]
        region = self.plan.region(key)  # type: ignore[union-attr]
        head = self.tensors[names[0]]
        dims = (len(names), *self._dims(head))
        dynamic: list[DynamicTerm] = []
        element_offset = 0
        if region.slot_count > 1:
            if run is None:
                raise RomLoweringError(
                    f"expert bank {key!r} is read outside a compressed layer body"
                )
            stride = region.slot_element_stride
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"expert bank {key!r} needs a per-layer element stride of "
                    f"{stride}, which does not fit the 32-bit dynamic-term stride "
                    "field of ABI 3.0 tensor views; split the bank"
                )
            dynamic.append(DynamicTerm.loop(self._loop_of_run[run.index], stride))
        scale_object, block = self._scale_binding(key)
        return self._view(
            object_id=region.object_id,
            dtype=self._dtype(region.dtype),
            dims=dims,
            element_offset=element_offset,
            dynamic=dynamic,
            permissions=int(Permission.READ),
            scale_object_id=scale_object,
            scale_block_elements=block,
            label="view.experts",
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
            # The head map is a property of the operands, not of a name: the
            # query carries the query heads and the KV history the KV heads, so
            # the group size is read off the shapes and only overridden when the
            # graph states it.
            query_heads = int(
                domain.get("query_heads", 0) or domain.get("heads", 0) or 0
            ) or dim(inputs[0] if inputs else None, 1, 1)
            kv_heads = int(
                domain.get("key_value_heads", 0) or domain.get("kv_heads", 0) or 0
            ) or dim(inputs[1] if len(inputs) > 1 else None, 1, 1)
            group_size = int(attributes.get("group_size", 0)) or (
                max(query_heads, 1) // max(kv_heads, 1)
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
    def _operand_order(self, kernel: Kernel, family: Major, sub: int) -> list[int]:
        """The IR input order permuted into the frozen operand convention.

        Two movements need it.  ``DMA.GATHER`` and ``DMA.SCATTER`` read
        ``(index, source)`` while both exporters emit ``(source, index)``,
        because the neutral IR states what is moved before it states where.
        Permuting here keeps a backend concern out of the IR: the index is the
        32-bit integer operand, which is model-blind and needs no name.
        """
        order = list(range(len(kernel.inputs)))
        if family is not Major.DMA or sub not in (int(Dma.GATHER), int(Dma.SCATTER)):
            return order
        index = next(
            (
                slot
                for slot in order
                if self.tensors[kernel.inputs[slot]].dtype in {"u32", "i32"}
            ),
            None,
        )
        if index is None or index == 0:
            return order
        return [index] + [slot for slot in order if slot != index]

    def _movement_views(
        self,
        kernel: Kernel,
        shape: KernelShape,
        order: Sequence[int],
        run: LayerRun | None,
        loop: int | None,
        sub: int,
    ) -> tuple[list[int], list[int]]:
        """Views for a gather or a scatter: an index, a plane, a destination."""
        index_name = kernel.inputs[order[0]]
        source_name = kernel.inputs[order[1]] if len(order) > 1 else None
        out_name = kernel.outputs[0] if kernel.outputs else None
        gather = sub == int(Dma.GATHER)
        addressed = source_name if not gather else out_name
        subject = self.tensors[source_name] if source_name is not None else None
        # An index is absolute when what it addresses spans every admissible
        # position -- a rotary table, a KV window -- and span-relative when it
        # addresses the rows of the request itself.
        absolute = True
        if gather and subject is not None:
            symbol, _ = self._leading_symbol(subject)
            absolute = symbol is None
        count = 1
        if addressed is not None:
            dims = self._blocked_dims(self.tensors[addressed], shape)
            if gather:
                count = max(dims[0], 1)
            else:
                count = max(self._blocked_dims(self.tensors[source_name], shape)[0], 1)
        views = [
            self._index_view(
                kernel, shape, index_name, loop, count=count, absolute=absolute
            )
        ]
        if source_name is not None:
            if gather:
                # A gather addresses arbitrary rows of its source, so the source
                # presents its whole declared extent rather than one block.
                tensor = self.tensors[source_name]
                views.append(
                    self._buffer_view(
                        tensor,
                        dims=self._dims(tensor),
                        strides=None,
                        shape=shape,
                        loop=loop,
                        writable=False,
                        blocked=False,
                    )
                )
            else:
                views.append(
                    self._operand_view(
                        kernel,
                        shape,
                        slot=1,
                        direction="in",
                        name=source_name,
                        run=run,
                        loop=loop,
                        family=Major.DMA,
                        sub=sub,
                    )
                )
        outputs = []
        if out_name is not None:
            outputs.append(
                self._operand_view(
                    kernel,
                    shape,
                    slot=0,
                    direction="out",
                    name=out_name,
                    run=run,
                    loop=loop,
                    family=Major.DMA,
                    sub=sub,
                )
            )
        return views, outputs

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
            self.builder.emit(
                family,
                engine.sub,
                descriptor_id=self._state_for(kernel),
                source_operation_id=kernel.index,
            )
            return
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
        shape = self._shape_of(kernel, engine)
        loop = self._open_row_loop(kernel, shape)
        order = self._operand_order(kernel, family, engine.sub)
        if family is Major.DMA and engine.sub in (int(Dma.GATHER), int(Dma.SCATTER)):
            inputs, outputs = self._movement_views(
                kernel, shape, order, run, loop, engine.sub
            )
        else:
            inputs = [
                self._operand_view(
                    kernel,
                    shape,
                    slot=abi_slot,
                    direction="in",
                    name=kernel.inputs[ir_slot],
                    run=run,
                    loop=loop,
                    family=family,
                    sub=engine.sub,
                )
                for abi_slot, ir_slot in enumerate(order[:MAX_OPERATOR_INPUTS])
            ]
            if "expert_weight_tensors" in kernel.attributes:
                # TA-ABI3-OPCONV-1 section 2: ROUTED_MATMUL reads
                # (activations, routed weights, expert IDs, route weights).  The
                # neutral IR names the bank in an attribute rather than an
                # operand, so the backend places it and binds it to slot 1.
                inputs.insert(1, self._expert_bank_view(kernel, run))
                inputs = inputs[:MAX_OPERATOR_INPUTS]
            outputs = [
                self._operand_view(
                    kernel,
                    shape,
                    slot=abi_slot,
                    direction="out",
                    name=name,
                    run=run,
                    loop=loop,
                    family=family,
                    sub=engine.sub,
                )
                for abi_slot, name in enumerate(kernel.outputs[:MAX_OPERATOR_OUTPUTS])
            ]
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
            self._event_of_tensor[name]
            for name in kernel.inputs
            if name in self._event_of_tensor
        ]
        wait = self._wait_set(producers)
        event = self.builder.new_event()
        self.builder.emit(
            family,
            engine.sub,
            descriptor_id=operator,
            wait_set_id=wait,
            signal_event_id=event,
            source_operation_id=kernel.index,
        )
        if loop is not None:
            self.builder.close_loop()
        # Only already-emitted producers enter a wait set, so a loop-carried
        # value is ordered by the loop body itself rather than by a wait on an
        # event the first iteration cannot yet have signalled.
        for name in kernel.outputs:
            self._event_of_tensor[name] = event

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
        self._require_on_device_selection()
        for descriptor in state_descriptors:
            self.builder.emit(Major.STATE, State.COMMIT, descriptor_id=descriptor)
        self.builder.emit(Major.CONTROL, Control.COMPLETE)

    def _require_on_device_selection(self) -> None:
        """ABI 3.0 mandates on-device selection; refuse a graph without it."""
        kinds = {k.kind for k in self.graph.kernels}
        if "ARGMAX" in kinds and "TOKEN_APPEND" in kinds:
            return
        raise RomLoweringError(
            "the graph declares no ARGMAX/TOKEN_APPEND pair; ABI 3.0 forbids "
            "host-side selection, so the front end must emit both"
        )

    # -- top level -------------------------------------------------------
    def _prove_memory_capacity(self) -> dict[str, Any]:
        """Prove the emitted objects fit the memory the capability declares.

        ROM removes weight traffic; it does not remove mutable state.  This is
        where the compiler discharges the capacity obligation for the KV, the
        compressor state, the token ring and the activation working set, against
        the exact SRAM and HBM the capability advertises.  STATE objects are
        priced against HBM because that is where session state physically lives.
        """
        footprint: dict[int, int] = {}
        for descriptor in self.builder.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
                continue
            storage = descriptor.payload["storage_class"]
            footprint[storage] = (
                footprint.get(storage, 0) + descriptor.payload["size_bytes"]
            )
        used = {
            StorageClass(storage).name.lower(): total
            for storage, total in sorted(footprint.items())
        }
        memory = self.capability.memory
        declared = {
            "hbm": int(memory.get("hbm", {}).get("bytes", 0)),
            "rom": int(memory.get("rom", {}).get("bytes", 0)),
            "sram": int(memory.get("sram", {}).get("bytes", 0)),
        }
        session = used.get("hbm", 0) + used.get("state", 0)
        checks = {
            "hbm_and_state": (session, declared["hbm"]),
            "rom": (used.get("rom", 0), declared["rom"]),
            "sram": (used.get("sram", 0), declared["sram"]),
        }
        for name, (needed, limit) in sorted(checks.items()):
            if needed > limit:
                raise RomLoweringError(
                    f"{name} objects need {needed} bytes but the capability "
                    f"declares {limit}; the placement does not fit the target"
                )
        return {
            "declared": declared,
            "session_bytes_in_hbm": session,
            "used": used,
        }

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
        builder.notes["memory_footprint"] = self._prove_memory_capacity()
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
            "state_class_aliases": dict(sorted(self._state_class_aliases.items())),
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
