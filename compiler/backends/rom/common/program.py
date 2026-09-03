"""Loop-compressed, IR-driven lowering shared by both ROM products.

The neutral Tensor Kernel IR names one kernel per layer per operation: Qwen3-8B
is roughly 730 kernels, 36 structurally identical layers of about 20 operations.
Emitting one instruction per kernel would reproduce the ABI 2.5 failure this
program exists to remove.  So this module compresses along two axes, and only
two -- a third would be the engine's own decomposition leaking into the
instruction stream.

**Layers.** Layers whose kernel signatures agree form one **run**, emitted once
between ``CONTROL.LOOP_SETUP`` and ``CONTROL.LOOP_NEXT``.  A run may be periodic:
DeepSeek's stack alternates two attention classes, so its body holds two layers
and the loop runs twenty times.  Every weight the body reads lives in one ROM
region striped by layer, so its tensor view is a single descriptor carrying
``DynamicTerm.loop(run_loop, slot_element_stride)``.

**Token blocks.** A span is a runtime symbol and a view states static extents, so
an operand over the token axis is read through a loop bound by
``Symbol.SPAN_TOKENS`` with the block as its ``bound_divisor``.  Amendment A13
(wire format section 12.4) then resolves the final iteration's leading extent to
``symbol - iteration * bound_divisor``: the rows the request actually has.  With
one block spanning the declared context that loop runs once and exists only to
carry the resolution, and a 93-token prefill issues one dispatch per kernel per
layer rather than one per token.

Everything else is a *schedule* field.  Output tiles, reduction tiles, bank and
port masks and the NoC route class describe how one engine instruction is
decomposed on the hardware, and the cycle model reads them from the SCHEDULE
descriptor.  Making them program loops would retire on the order of 258,000
dispatches per Qwen forward step.

Operand shapes follow ``TA-ABI3-OPCONV-1``: a contraction states its operands as
matrices (``[rows, K]``, ``[N, K]``, ``[rows, N]``) whatever rank the graph gave
them, everything else keeps the declared rank so an engine that reads heads
finds an axis for them, and a lower-rank input is broadcast onto the principal
operand with a zero stride.  All of it is description; nothing is relaid out and
nothing is copied.

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

from compiler.backends.numeric_contracts import (
    EXECUTION_CONTRACT,
    reduction_order_for,
)
from compiler.ir.v3.kernel_ir import (
    Kernel,
    KernelGraph,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import (
    ABSENT_OPERANDS,
    EngineOp,
    KERNEL_TO_ENGINE,
    abi_input_slots as _shared_input_slots,
)
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
    InstructionFlag,
    Major,
    NO_ID,
    ParticipantScope,
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
    Comparison,
    iteration_extent,
    LayoutClass,
    MAX_RANK,
    Phase,
    PredicateKind,
    SelectionMode,
    SelectorKind,
    Symbol,
)
# The frozen compression ratios, from the module that defines them rather than
# restated here: ``VECTOR.COMPRESS``'s ``aux_id_1`` must name one of them and
# the engine refuses anything else.
from runtime.reference.compression_pool import PINNED_COMPRESSION_RATIOS

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

#: Neutral state classes whose ABI 3.0 representation is one live, ordinary
#: writable HBM buffer.  The model caches and compressor histories update in
#: place during one uninterrupted, fail-stop execution; they have no
#: rollback/retry or durable-publication contract.
DIRECT_BUFFER_STATE_CLASSES = frozenset(
    {"compressed_kv", "compressor_window", "kv_cache", "kv_window"}
)


def _is_direct_buffer_state(state_class: str) -> bool:
    """Whether ``state_class`` lowers as an ordinary mutable HBM object."""

    return str(state_class) in DIRECT_BUFFER_STATE_CLASSES

#: Integer operand types.  These carry indices and identifiers, never values a
#: broadcast could share between heads.
INDEX_DTYPES = frozenset({"u32", "i32", "u64", "i64"})

#: Index types a checkpoint stores at 64 bits and every ABI 3.0 operator reads
#: at 32.  The values are small enough that the low word *is* the value, so the
#: reconciliation is a view's element type and stride, not a conversion.
WIDE_INDEX_DTYPES = frozenset({"u64", "i64"})

#: The readings a kernel may declare for a table whose stored element is wider
#: than the element every reader of it uses, and the ABI type each names.  A
#: reading is a property of the *data* -- it says what the bytes mean and how
#: wide the meaning is -- so a graph declares it on the kernel that reads the
#: table.  Deriving it from the operator's name instead is how it was lost when
#: an exporter renamed the operation to the one it had always performed.
TABLE_ELEMENT_READINGS: Mapping[str, DType] = {
    "low_u32_of_i64": DType.U32,
    "low_u32_of_u64": DType.U32,
}

#: What limits an operator's rate.  The cycle model reads this out of the
#: SCHEDULE descriptor together with the tile mapping.

def _declared_new_token_budget(policy_body: dict, span_max: int) -> int:
    """The decode budget the neutral IR declares, refused rather than defaulted.

    Both backends used to supply a default when the key was absent -- 1024 here,
    512 in the HBM lowering, which additionally spelled the key wrong and so took
    its default every time. Two backends inventing two different budgets for one
    IR is precisely the divergence a shared IR exists to prevent, and neither
    invention is visible in a token stream until a generation runs long enough to
    hit the smaller cap and looks like an early stop.

    A graph that appends tokens without declaring a budget is a graph whose
    decode length nobody chose.
    """

    declared = policy_body.get("maximum_new_tokens")
    if declared is None:
        raise ValueError(
            "the generation policy declares no 'maximum_new_tokens'; a decode "
            "budget must be stated by the IR rather than defaulted by a backend"
        )
    budget = int(declared)
    if budget > span_max:
        raise ValueError(
            f"generation policy admits {budget} new tokens but the capability "
            f"holds {span_max} context positions"
        )
    return budget


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
#: Neutral kinds whose entry in the frozen lowering table names an ABI 3.0
#: operator that does not perform the operation the released model performs.
#:
#: ``HASH_ROUTE`` is the one this backend has met.  DeepSeek-V4-Flash selects a
#: token's six experts by *reading a table with the token ID*:
#: ``routes = tid2eid[token_id]`` over a ``[129280, 6]`` int64 table shipped in
#: the checkpoint, which is what ``src/opentallas/routing.py`` executes and what
#: the graph's own ``table_rows`` attribute states.  ``ROUTE.HASH_ROUTE``
#: computes something else entirely -- ``table[mix32(key) % slots]``, the
#: frozen consistent-hash destination lookup a fabric uses to decide which node
#: owns a key -- and would return one destination per key rather than six.  The
#: name collided; the operation did not.
#:
#: ABI 3.0 already has this operator and needs no amendment for it:
#: ``TENSOR.EMBED_LOOKUP`` is "exact row gather from a table indexed by a 32-bit
#: ID, no arithmetic and therefore no conversion", which is the operation
#: exactly, down to the bound check on the ID.  The substitution belongs in the
#: exporter -- the kernel kind should be ``EMBEDDING_LOOKUP`` -- and the
#: DeepSeek exporter has since made exactly that substitution, keeping
#: ``source_operation_kind: HASH_ROUTE`` as the record of what the released
#: module calls it.  This row therefore no longer fires for the published
#: graph; it remains so that a graph that still names the old kind lowers to
#: the operator that performs the operation rather than to one that does not.
ENGINE_OVERRIDE: Mapping[str, EngineOp] = {
    "HASH_ROUTE": EngineOp(Major.TENSOR, TensorOp.EMBED_LOOKUP, 2, 1),
}

#: ABI input slots this backend supplies ``absent_operands`` for, by neutral
#: kind, because the operand convention requires them empty and no exporter can
#: yet say so.  ``VECTOR.COMPRESS`` sub-case 2 is the only case: its ``in1`` is
#: the projection matrix, which a state update has none of, while its ``in2``
#: is the position embedding, which is exactly what the APE table is.
#:
#: This is *not* a second hole table.  Amendment A20 makes ``absent_operands``
#: the one statement of a hole and
#: ``compiler/ir/v3/lowering.py::abi_input_slots`` the one placement of it, and
#: both are adopted below; what survives here is a seed for that call, because
#: ``COMPRESS_STATE_UPDATE`` is not in the frozen ``OPTIONAL_INPUT_SLOTS`` and
#: a kernel that declared the attribute would be refused at neutral admission.
#: Adding it there, and emitting it from the exporters, deletes this table
#: outright and changes nothing else -- the placement is already shared.
#: ``compiler/backends/hbm_sram/plan.py`` seeds the same row for the same
#: reason: one convention, two backends.
ABI_EMPTY_INPUT_SLOTS: Mapping[str, tuple[int, ...]] = {
    "COMPRESS_STATE_UPDATE": (1,),
}


def index_topk_capacity(kernel: Kernel, slots: int, window: int) -> int:
    """``ROUTE.INDEX_TOPK``'s ``aux_id_0`` from the graph, or A20's derivation.

    ``slots`` is ``out0``'s last extent and ``window`` is ``in1``'s; the answer
    is the *compressed segment's* width, which is neither of them.  Both lanes
    call this arithmetic with the same two numbers, and a test compares them --
    they read two different attribute names before, ``k`` here and ``top_k``
    there, which agreed on every ranked kernel because those declare both and
    disagreed on every dense one because those declare only ``k``.
    ``compiler/backends/hbm_sram/plan.py::index_topk_capacity`` is the twin.
    """
    declared = kernel.attributes.get("top_k", kernel.attributes.get("k"))
    if declared is not None:
        return int(declared)
    return int(slots) - int(window)


def abi_input_slots_of(kernel: Kernel, order: Sequence[int]) -> list[int | None]:
    """The IR input each ABI input slot carries; ``None`` for a declared hole.

    A slot left ``NO_ID`` is not a missing operand, it is a stated one, and the
    remaining operands go *either side* of it.  ``VECTOR.COMPRESS`` sub-case 2
    reads the projected candidates in ``in0`` and the absolute position
    embedding in ``in2``, because ``in1`` is the projection matrix that a state
    update does not have; amendment A20's dense ``ROUTE.INDEX_TOPK`` leaves
    ``in0`` empty and keeps the window block in ``in1`` and the compression
    ratio in ``in2``.  Packing them down put the APE where the projection
    belongs in the first case and the one-element ratio constant where the
    window block belongs in the second, and the engine said so exactly:
    ``ROUTE.INDEX_TOPK window view 2084 covers 1 query rows, expected 104``.

    The placement is ``compiler/ir/v3/lowering.py::abi_input_slots`` and nothing
    else, so a hole is placed identically on both lanes rather than by two
    private copies of one while-loop.  It is module-level, not a method, so that
    the two lanes' placements can be compared against each other directly --
    ``compiler/backends/hbm_sram/plan.py::_abi_input_slots`` is the same call on
    the same inputs, and a test says so.
    """
    return _shared_input_slots(kernel.kind, list(order), hole_attributes(kernel))


def hole_attributes(kernel: Kernel) -> Mapping[str, object]:
    """``kernel.attributes``, with the convention's own holes seeded in.

    A kernel that declares ``absent_operands`` has already been checked against
    the frozen ``OPTIONAL_INPUT_SLOTS`` at neutral admission and is
    authoritative -- the backend adds nothing to it.
    """
    if ABSENT_OPERANDS in kernel.attributes:
        return kernel.attributes
    convention = ABI_EMPTY_INPUT_SLOTS.get(kernel.kind)
    if convention is None:
        return kernel.attributes
    return {**kernel.attributes, ABSENT_OPERANDS: list(convention)}


#: Neutral kinds whose TA-ABI3-OPCONV-1 row states an explicit batch axis that
#: the neutral IR does not declare.  ADR-003 section 15 gives the neutral IR
#: model semantics and no batch concept -- a batch is a deployment property --
#: so a token-major ``[tokens, ...]`` operand is exactly one rank short of its
#: row and the backend has to insert the missing axis.
#:
#: ``VECTOR.MHC``'s post sub-case reads ``[B, S, ...]`` off every operand;
#: ``VECTOR.COMPRESS``'s project sub-case reads ``[B, S, K]`` in and
#: ``[B, S, 2, N]`` out; its pool sub-case reads ``[B, G, P, D]`` in and
#: ``[B, G, D]`` out; its state-update sub-case reads ``[B, S, 2, W]`` in and
#: writes two ``[B, G, P, D]``.
#:
#: The inserted axis goes *after* the leading one.  Amendment A13 clamps a
#: view's **leading** extent on a block loop's partial final iteration, so a
#: leading axis of one is never clamped and the operand would present a whole
#: declared block -- 262,144 rows -- for a 4-token request.  ``[rows, 1, ...]``
#: keeps A13 exact.  For every row here but one that is also all the placement
#: has to be: the arithmetic is independent per leading position, so
#: ``batch * span`` is the count either way.
#:
#: See :meth:`_token_as_batch`.  This mirrors ``_batched_operand`` in
#: ``compiler/backends/hbm_sram/lower.py``: one convention, two backends.
TOKEN_AS_BATCH_KINDS = frozenset({"HYPER_CONNECT_POST", "COMPRESS_PROJECT"})

#: The rows that need the *other* placement: batch leading at extent one, and
#: the request-dependent extent behind it at axis 1.
#:
#: ``VECTOR.COMPRESS``'s state update forms its groups *along* ``S`` --
#: ``groups = span // ratio`` -- and its overlap transform reaches across ``G``
#: (``pool[:, 1:, :ratio] = groups[:, :-1, :, :head_dim]``), so neither extent
#: can be the batch and both sit at axis 1.  Its pool reads the operands the
#: state update writes, in the same shape.
#:
#: Until amendment A18 this was not a placement at all, because A13 clamped
#: ``dim0`` only: ``[T, 1, 2, W]`` put the tokens in the batch and the engine
#: refused it with ``span 1 contains no complete group of 4``, and
#: ``[1, T_max, 2, W]`` was never clamped and read 262,144 rows of zeros.  A18
#: lets the view name the axis, and name the unit its elements are counted in,
#: so the group axis is ``SPAN_TOKENS`` in units of the compression ratio.
#: See :meth:`_batch_leads`.
BATCH_LEADS_KINDS = frozenset({"COMPRESS_POOL", "COMPRESS_STATE_UPDATE"})

#: The released routed pipeline carries ``top_k * span_tokens`` as one leading
#: symbolic extent.  A13 could clamp only ``span_tokens`` itself, so the first
#: ROM lowering represented these rows one token at a time.  That changes a
#: blocked contraction's matrix shape: the HBM lane groups every request row
#: selecting the same expert while ROM groups only one token's selections, and
#: NumPy/OpenBLAS is allowed to choose a different binary32 association for the
#: two shapes.  A18 now states the multiplied extent directly, so this complete
#: producer chain can retain the neutral graph's whole-span batch.
#:
#: The set is deliberately closed over the chain.  Batching only
#: ``ROUTED_MATMUL`` would make it consume rows its per-token producer had not
#: written yet; batching an unrelated multiplied-symbol operator would change
#: its schedule without an operand-convention proof.
MULTIPLIED_SPAN_BATCH_KINDS = frozenset(
    {"EXPERT_DISPATCH", "QUANTIZE", "ROUTED_MATMUL", "SWIGLU", "MUL"}
)

MHC_SUBCASE: Mapping[str, int] = {
    "HYPER_CONNECT_PRE": 0,
    "HYPER_CONNECT_POST": 1,
    "HYPER_CONNECT_HEAD": 2,
}
SCALE_SUBCASE: Mapping[str, int] = {"SCALE": 0, "MUL": 1, "SIGMOID": 2}

#: Neutral operand orders that differ from TA-ABI3-OPCONV-1's slot order, and
#: the permutation that reconciles them.  The ``MHC`` row is
#: ``(hidden, fn, base, scale)`` and both exporters emit
#: ``(hidden, fn, scale, base)``.  This mirrors ``_SLOT_PERMUTATION`` in
#: ``compiler/backends/hbm_sram/plan.py``: one convention, two backends.
_SLOT_PERMUTATION: Mapping[str, tuple[int, ...]] = {
    "HYPER_CONNECT_PRE": (0, 1, 3, 2),
    "HYPER_CONNECT_HEAD": (0, 1, 3, 2),
    # ``ROUTE.EXPERT_DISPATCH`` reads (expert IDs, activations).  Both exporters
    # emit (activations, expert IDs), following TA-ABI3-OPCONV-1 section 5,
    # whose row reads "in0 activations | in1 selected IDs" -- and the executing
    # engine reads the opposite: ``runtime/sim/engines/route.py`` takes
    # ``input_view_0`` as the U32 expert-ID array and ``input_view_1`` as the
    # tokens, and refuses the documented order outright because the ID slot must
    # be U32.  The two cannot both be right; the doc and the engine have to be
    # reconciled by whoever owns them.  Until they are, this backend emits what
    # executes, because the alternative is a lane that cannot run at all.
    "EXPERT_DISPATCH": (1, 0),
}

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


def _narrow_bf16_rne(bits: int) -> int:
    """Round a binary32 bit pattern to its BF16 code, ties to even."""
    code = (int(bits) >> 16) & 0xFFFF
    remainder = int(bits) & 0xFFFF
    if remainder > 0x8000 or (remainder == 0x8000 and code & 1):
        code = (code + 1) & 0xFFFF
    return code


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
        if key.endswith("_bits") or key.endswith("_binary32"):
            # A binary32 pattern, written as an integer or as the hexadecimal
            # string a frozen reference states it in.  Both name the same 32
            # bits; parsing the string here is what keeps the graph from having
            # to restate the constant a second way for a backend's benefit.
            if isinstance(value, str):
                return int(value, 0) & 0xFFFFFFFF
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
@dataclass(frozen=True)
class RequestAxis:
    """A neutral axis name resolved to an A5 symbol and an A18 unit.

    Amendment A18 states an axis's extent as an affine function of one bound
    symbol, ``numerator * value / unit + bias``: ``unit`` is how many of the
    symbol's units one element of the axis holds, and ``bias`` is elements the
    operand carries whatever the request is.  A compressed group of four tokens
    is ``SPAN_TOKENS`` in units of four; a KV join carrying a 128-row sliding
    window beside the span is ``SPAN_TOKENS`` with a bias of 128.

    A18 put this on the view rather than in the registry, and section 4 is why
    -- ``span_groups_ratio4`` names one model's compression ratio, and the
    frozen registries do not name a model.  An affine image of a symbol already
    in the registry is not a new symbol.
    """

    symbol: Symbol
    unit: int = 1
    numerator: int = 1
    bias: int = 0

    @property
    def is_identity(self) -> bool:
        """Is the extent the symbol's own value, unscaled and unbiased?

        This asks about the *function*, not about which symbol it reads.  A KV
        cache counting one row per context token is the identity in
        ``CONTEXT_LENGTH`` and needs nothing A13 did not already do; comparing
        the whole description instead would call it non-identity because the
        symbol differs from the span, and hand it a resolving loop it does not
        need.  Qwen's every state plane is that case.
        """
        return self.numerator == 1 and self.unit == 1 and self.bias == 0


#: A13's own affine function: the axis counts the symbol's own units.
IDENTITY_AXIS = RequestAxis(Symbol.SPAN_TOKENS)


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
    #: True when the block is *one token* and each operand presents whatever
    #: multiple of a token it holds -- six routed copies for a dispatched
    #: activation, one for the token that produced them.  See ``_shape_of``.
    per_token: bool = False
    #: Multiplier of a whole-span leading axis retained through A18.  One is
    #: the ordinary token-block case; values above one mean ``rows`` and the
    #: clamped view extent are this many axis elements per bound-symbol unit.
    batch_multiplier: int = 1
    #: Amendment A18's affine description of the *principal's* leading axis.
    #: ``rows``, ``block`` and every view extent are in an axis's own elements;
    #: ``divisor`` is the loop's block in the bound symbol's units, and each
    #: operand derives its own step from it through its own affine function.
    axis: RequestAxis = IDENTITY_AXIS
    #: The loop's ``bound_divisor``: how many of ``symbol``'s units one
    #: iteration advances.  Deriving every operand's block from this, rather
    #: than from the principal's declared maximum, is what lets two operands of
    #: a *join* disagree about their maxima and still be blocked consistently.
    divisor: int = 1


#: Neutral symbol name -> the frozen runtime-symbol registry.

SYMBOL_BY_NAME: Mapping[str, RequestAxis] = {
    "span_tokens": RequestAxis(Symbol.SPAN_TOKENS),
    # The two exporters spell the context extent differently -- Qwen's graph
    # declares ``context_tokens`` and DeepSeek's declares ``context_length`` --
    # and an unrecognised name is not an error here, it is silence: the operand
    # keeps its declared maximum and no block loop is opened, so a 4-token
    # request would address the whole 262,144-row context.  Both names are
    # listed rather than one being assumed.
    "context_tokens": RequestAxis(Symbol.CONTEXT_LENGTH),
    "context_length": RequestAxis(Symbol.CONTEXT_LENGTH),
    "position_start": RequestAxis(Symbol.POSITION_START),
    "position_end": RequestAxis(Symbol.POSITION_END),
    "generation_index": RequestAxis(Symbol.GENERATION_INDEX),
    "batch": RequestAxis(Symbol.BATCH),
    # The compressor's group counts: a registered symbol divided by a pinned
    # compression ratio, which is what an A18 unit states.
    "span_groups_ratio4": RequestAxis(Symbol.SPAN_TOKENS, 4),
    "span_groups_ratio128": RequestAxis(Symbol.SPAN_TOKENS, 128),
    "context_groups_ratio4": RequestAxis(Symbol.CONTEXT_LENGTH, 4),
    "context_groups_ratio128": RequestAxis(Symbol.CONTEXT_LENGTH, 128),
    # The attention KV join's output rows.  These were left undeclared on the
    # reading that A17 already makes a join's output the sum of its inputs.
    # That reading is wrong, and section 18 of the operand conventions says so
    # in terms: A17 names the axis a join consumes and is a *check* evaluated
    # against what the operands resolve to, not a derivation -- a view's extent
    # is the view's own statement and no operator rewrites one.  Undeclared,
    # every operand of the join presented its maximum, the sums agreed, A17
    # passed, and layer 2's attention read 327,808 rows of mostly zeros for a
    # 4-token request with nothing refusing it.  Measured, not reasoned: the
    # resolved operands were (262144, 128, 65536) summing to the output's
    # 327,808 when the request had 133 rows.
    #
    # These are the *prefill* forms, and they are now derived rather than
    # trusted: ``_check_join_extent`` sums the operands of every axis-0 join
    # and refuses an output whose declared function is not that sum.  The
    # decode form is not in this table because it is not one entry -- the sum
    # is over two symbols and A18 states one -- so it is derived per phase from
    # the graph's ``phase_symbol_binding`` and emitted as its own path.  The
    # paragraph below records what this table said before that existed; the
    # last sentence of it was wrong, and a decode step is where it was wrong.
    #
    # ``window`` is the span joined to a 128-row sliding window, which is the
    # bias: those rows are there for a span of one.  The compressed layers add
    # ``context / ratio`` more, and in *prefill* the context is the span, so
    # ratio-4 is ``5 * span / 4 + 128`` and ratio-128 is ``129 * span / 128 +
    # 128``.  Decode binds the two symbols apart and A18 is exact for an affine
    # function of one, so a decode of a compressed layer needs a phase split
    # that prefill does not; it is not solved here because it is not needed
    # here, and stating it speculatively would state it wrong.
    "attention_rows_window": RequestAxis(Symbol.SPAN_TOKENS, 1, 1, 128),
    "attention_rows_ratio4": RequestAxis(Symbol.SPAN_TOKENS, 4, 5, 128),
    "attention_rows_ratio128": RequestAxis(Symbol.SPAN_TOKENS, 128, 129, 128),
    "selected_rows_ratio128": RequestAxis(Symbol.SPAN_TOKENS, 128, 1, 128),
}

#: Amendment A3's frozen ``comparisons`` registry, as the exporter's
#: symbol-comparison grammar spells it.  ``"<symbol> <op> <integer>"`` is the
#: whole grammar; an operator outside this table is refused rather than guessed
#: at, because a predicate that is read wrongly is a predicate that silently
#: enables or disables an operator.
PREDICATE_COMPARISONS: Mapping[str, Comparison] = {
    "==": Comparison.EQ,
    "!=": Comparison.NE,
    "<": Comparison.LT,
    "<=": Comparison.LE,
    ">": Comparison.GT,
    ">=": Comparison.GE,
}


def _evaluate_comparison(comparison: Comparison, value: int, immediate: int) -> bool:
    """A frozen A3 comparison against a symbol whose value is known.

    Used to *prove* that two alternative paths of one kernel cannot both issue:
    each path's condition is evaluated under the other phase's pinned symbols,
    and a path that could still fire there is refused rather than emitted.
    """
    if comparison is Comparison.EQ:
        return value == immediate
    if comparison is Comparison.NE:
        return value != immediate
    if comparison is Comparison.LT:
        return value < immediate
    if comparison is Comparison.LE:
        return value <= immediate
    if comparison is Comparison.GT:
        return value > immediate
    return value >= immediate


def _rewrite_comparison(
    axis: RequestAxis, operator: str, immediate: int
) -> tuple[Comparison, int]:
    """State ``f(S) <op> K`` as a comparison on the bound symbol itself.

    A18 makes a declared axis an affine image of a registered symbol,
    ``numerator * S / unit + bias`` with the division flooring, and A3's
    ``COMPARE_SYMBOL`` compares the *symbol* against an immediate.  So a
    condition written over the derived name has to be moved onto the symbol,
    and moved **exactly**: ``span_groups_ratio128 > 0`` is ``S // 128 > 0`` is
    ``S >= 128``, not ``S > 0``.  Getting that wrong by one unit is the whole
    defect class this lowering exists to close -- a predicate that reads true
    where the source reads false issues the operator the source skips.

    Only ``numerator == 1`` is rewritten.  A numerator above one makes the
    image non-surjective and an equality over it names a set of symbol values
    no single comparison states; rather than approximate it, this refuses.
    """
    unit = max(int(axis.unit), 1)
    numerator = int(axis.numerator)
    bias = int(axis.bias)
    if numerator != 1:
        raise RomLoweringError(
            f"predicate over an axis whose A18 numerator is {numerator}: a "
            "comparison on the derived value is not a comparison on the "
            "symbol, and this backend will not approximate one"
        )
    # ``S // unit <op> target`` with ``target = immediate - bias``.  ``S`` is a
    # count and is never negative, which is what makes each rewrite exact.
    target = int(immediate) - bias
    if operator == ">":
        return Comparison.GE, max(unit * (target + 1), 0)
    if operator == ">=":
        return Comparison.GE, max(unit * target, 0)
    if operator == "<":
        return Comparison.LT, max(unit * target, 0)
    if operator == "<=":
        return Comparison.LT, max(unit * (target + 1), 0)
    if unit == 1:
        return PREDICATE_COMPARISONS[operator], target
    raise RomLoweringError(
        f"predicate {operator!r} against an axis in units of {unit}: an "
        "equality on a floored quotient names a range of symbol values and "
        "``COMPARE_SYMBOL`` states one comparison; this backend will not "
        "approximate it"
    )


#: The index families ``ROUTE.WINDOW_INDEX`` actually produces.  A gate, not a
#: label: a family outside this set is refused at compile time.
#:
#: The engine writes ``arange(first, last + 1)`` over *absolute positions* of a
#: causal window, tail-padded -- that and nothing else.  A graph may name a
#: different family, and the DeepSeek export does: the ratio-128 layers declare
#: ``causal_compressed_dense``, whose released form is
#: ``arange(0, context // ratio) + offset`` -- an enumeration of completed
#: *compression groups*, counted in groups rather than positions, and rebased
#: onto the joined KV rows.  No frozen operator produces that, and
#: ``index_family`` is read by no engine, no verifier and no other backend, so
#: lowering it to ``WINDOW_INDEX`` emits a second copy of the sliding-window
#: position list under a name that says otherwise.
#:
#: Nothing can catch that downstream.  Every index it names is a legal KV row,
#: so the operand checks pass, the bound checks pass and the numeric checks
#: pass; twenty layers would attend their sliding window twice and never reach
#: a compressed group, and the tokens would come out fluent and wrong.  A lane
#: that does not build is a visible failure and a lane that attends the wrong
#: rows is an invisible one, so this refuses -- exactly as ``CACHE_ROW_MAPS``
#: refuses a destination-row map this backend does not implement, "rather than
#: silently taken as the identity".
#:
#: Adding the operator, or restating the plan, is a change to the frozen
#: lowering table and to the exporter, and neither is a backend's to make.
IMPLEMENTED_INDEX_FAMILIES = frozenset({"causal_circular_window"})


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
    """One on-fabric operation inserted into a compressed body.

    ``participant_scope`` (amendment A14) says what the step's participants
    *are*: nodes, reticles or tiles of the admitted topology.  The count is
    then a *derivation*, not a declaration: ``_participant_count`` reads it out
    of the TOPOLOGY descriptor this backend itself emitted, exactly as the LINK
    engine will, so ``participant_count=None`` is the normal value.  A
    point-to-point step, which has no participant set at all, states its two
    endpoints explicitly.
    """

    position: int
    where: str  # "before" or "after"
    link_sub: int
    collective_op: int
    label: str
    byte_extent: int
    participant_scope: ParticipantScope = ParticipantScope.NODE
    participant_count: int | None = None
    route_class: int = 0
    group_id: int = NO_ID
    virtual_channel: int = 0
    #: Numeric contract of an arithmetic collective.  An all-reduce reduces
    #: real bytes under a real contract or it is not a reduction, so the step
    #: names one; a movement collective needs none.
    reduction_contract: str = ""
    reduction_dtype: str = "bf16"


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
        self._scale_of_region: dict[str, tuple[str, int, int]] = {}
        self._buffer_object: dict[str, int] = {}
        self._buffer_place: dict[str, BufferPlacement] = {}
        self._buffer_root: dict[str, str] = {}
        self._buffer_size: dict[str, int] = {}
        self._sram_used = 0
        self._numeric_cache: dict[tuple[Any, ...], int] = {}
        self._schedule_cache: dict[tuple[int, int], int] = {}
        self._counter_cache: dict[int, int] = {}
        self._view_cache: dict[tuple[Any, ...], int] = {}
        self._wait_cache: dict[tuple[int, ...], int] = {}
        self._loop_of_run: dict[int, int] = {}
        self._state_descriptor: dict[str, int] = {}
        self._state_object: dict[str, int] = {}
        self._state_slot: dict[str, tuple[str, int]] = {}
        self._state_group_shape: dict[str, tuple[int, int, int]] = {}
        self._state_group_count = 0
        self._direct_state_groups: dict[str, str] = {}
        self._state_column: dict[str, int] = {}
        self._substituted_inputs: dict[str, str] = {}
        self._position_input_cache: frozenset[str] | None = None
        self._state_owner: dict[str, str] = {}
        self._event_of_tensor: dict[str, int] = {}
        # Qwen's append results and attention-history operands have different
        # tensor IDs even though they address the same physical KV group.  This
        # frontier makes the DMA-to-attention dependency explicit by resource.
        self._kv_cache_write_events: dict[str, list[int]] = {}
        self._communications: list[tuple[str, int]] = []
        self._link_endpoint_objects: dict[int, tuple[int, int]] = {}
        self._link_numeric: dict[tuple[str, str], int] = {}
        self._link_instruction_count = 0
        self._queue_cursor: dict[int, int] = {}
        self._contract_substitutions: dict[str, str] = {}
        self._state_class_aliases: dict[str, str] = {}
        self._state_row_widenings: dict[str, dict[str, int]] = {}
        self._port_cursor = 0
        self._predicate_cache: dict[tuple[Any, ...], int] = {}
        self._predicate_values: dict[str, str] | None = None
        self._predicated_operators: dict[str, str] = {}
        self._operand_alternatives: dict[str, str] = {}
        # The released DeepSeek compressor exposes one logical predicate with
        # two implementations: a symbol comparison for prefill and a
        # data-backed ring-boundary test for decode.  Both are ordinary ABI
        # 3.0 predicates.  The maps below carry only compiler bookkeeping;
        # every architectural bit lives in emitted HBM objects, views,
        # operators, predicates, and events.
        self._compressor_predicates = self._discover_compressor_predicates()
        self._compressor_boundary_objects: dict[int, int] = {}
        self._compressor_boundary_predicates: dict[int, int] = {}
        self._compressor_transition_ratios: set[int] = set()
        self._compressor_path_events: dict[str, dict[str, int]] = {}
        self._deferred_token_appends: list[Kernel] = []
        self._token_step_fence_event = NO_ID
        #: Tensor -> phase -> the A18 extent that phase's path writes.  A join
        #: whose operands sum over two runtime symbols has no single extent,
        #: and every view of its result -- the producer's and the consumer's --
        #: has to state the phase's own.
        self._phase_extent: dict[str, dict[str, RequestAxis]] = {}
        self._unrepresentable_predicates: dict[str, dict[str, str]] = {}
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

    def _padded_symbol_bound(self) -> int:
        """Rows covered by all token blocks, including a partial final block."""

        bound = int(self.capability.limits["max_context_positions"])
        configured = int(self.policy.token_block_rows or 0)
        block = max(min(configured or bound, bound), 1)
        return -(-bound // block) * block

    def _padded_bytes(self, tensor: Tensor) -> int:
        """Allocate a symbolic-leading buffer through its final padded block.

        A13 clamps the final iteration to the request's real rows at execution,
        but the frozen verifier proves every tensor view over the loop's static
        block.  When the architectural bound is not a multiple of that block,
        the backing zero buffer therefore carries an unreachable padded tail.
        Token-blocking disabled (zero) leaves every existing allocation exact.
        """

        dims = list(self._dims(tensor))
        symbol, multiplier, axis = self._leading_symbol(tensor)
        if symbol not in {int(Symbol.SPAN_TOKENS), int(Symbol.CONTEXT_LENGTH)}:
            return self._bytes(tensor)
        bound = int(self.capability.limits["max_context_positions"])
        padded = self._padded_symbol_bound()
        if padded == bound:
            return self._bytes(tensor)
        logical_axis = (
            bound * int(axis.numerator) // max(int(axis.unit), 1)
            + int(axis.bias)
        ) * max(int(multiplier), 1)
        padded_axis = (
            padded * int(axis.numerator) // max(int(axis.unit), 1)
            + int(axis.bias)
        ) * max(int(multiplier), 1)
        dims[0] += max(padded_axis - logical_axis, 0)
        elements = 1
        for dim in dims:
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
        * a routed **expert bank**: an ordinary weight operand whose declared
          rank-3 ``[E, N, K]`` shape and segmented binding make it one.  One
          slot of that region is one layer's whole bank, one member per expert
          in ascending logical expert order, which is what lets one
          ROUTED_MATMUL descriptor address any runtime-selected expert and what
          lets expert dispatch enable only the tiles that hold them.
        """
        requests: list[RegionRequest] = []
        placed: set[str] = set()

        def coordinate(key: str, role: str, size: int) -> RomCoordinate:
            if self.policy.place_region is None:
                return RomCoordinate()
            return self.policy.place_region(key, role, len(requests), size)

        def entries(tensor: Tensor) -> list[tuple[str, int, str, int, str]]:
            """One placement entry per authenticated range this tensor holds.

            A stacked expert bank contributes one entry per expert, because its
            binding is segmented and each segment is its own checkpoint tensor.
            """
            return [
                (
                    member.tensor_id,
                    member.bytes,
                    member.source_path,
                    member.source_offset,
                    member.source_sha256,
                )
                for member in self._members(tensor, 0, 0)
            ]

        def emit(
            key: str,
            role: str,
            dtype: str,
            columns: Sequence[Sequence[Tensor]],
            elements: int,
        ) -> None:
            # ``placed`` and the region index are keyed by *tensor*: a tensor is
            # what a kernel names as an operand.  The region's members are the
            # ranges those tensors are made of, which for a segmented binding is
            # finer than one per tensor.
            names = [tensor.tensor_id for column in columns for tensor in column]
            if any(name in placed for name in names):
                if all(name in placed for name in names):
                    return
                raise RomLoweringError(
                    f"ROM region {key!r} mixes already-placed and unplaced weights"
                )
            placed.update(names)
            slots = [
                [entry for tensor in column for entry in entries(tensor)]
                for column in columns
            ]
            size = sum(entry[1] for slot in slots for entry in slot)
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
            for slot_index, column in enumerate(columns):
                for tensor in column:
                    self._region_of_tensor[tensor.tensor_id] = (key, slot_index)

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
                columns,
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
                scales,
                sum(self._elements(t) for t in scales[0]),
            )
            self._scale_of_region[key] = (
                f"{key}.scale",
                int(head.scale_block_elements or 0),
                self._scale_block_rows(head),
            )

        # -- prologue and epilogue weights: one slot each -----------------
        for kernel in (*self.analysis.prologue, *self.analysis.epilogue):
            for slot, name in enumerate(kernel.inputs):
                tensor = self.tensors[name]
                if tensor.role not in WEIGHT_ROLES or name in placed:
                    continue
                place_operand(
                    f"rom.global.k{kernel.index:05d}.s{slot}",
                    self._weight_role(kernel, tensor, "global_weight"),
                    [[tensor]],
                )

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
                        self._weight_role(head, columns[0][0], "layer_weight"),
                        columns,
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

    def _scale_block_rows(self, tensor: Tensor) -> int:
        """How many leading rows one of this tensor's scale codes covers.

        Amendment A15 states a block scale as two extents.  The neutral IR
        names only the block along the reduction axis, because the scale
        tensor's own declared shape carries the rest -- a ``[1024, 4096]`` FP8
        weight with a 128-element block whose scale is ``[8, 32]`` is scaled in
        128 x 128 tiles, and ``1024 / 8`` says so.  Reading it off the two
        declared shapes is the whole derivation; nothing here is assumed, and a
        shape that does not divide is refused rather than rounded.
        """
        block = int(tensor.scale_block_elements or 0)
        scale_id = tensor.scale_tensor_id
        if not block or not scale_id or scale_id not in self.tensors:
            return 1
        scale = self.tensors[scale_id]
        dims = self._dims(tensor)
        scale_dims = self._dims(scale)
        width = dims[-1] if dims else 1
        scale_width = scale_dims[-1] if scale_dims else 1
        if width % block or scale_width != width // block:
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} is {list(dims)} with a {block}-element "
                f"scale block, so its scale's last axis must be {width // block}; "
                f"{scale_id!r} declares {list(scale_dims)}"
            )
        rows = 1
        for extent in dims[:-1]:
            rows *= extent
        scale_rows = 1
        for extent in scale_dims[:-1]:
            scale_rows *= extent
        if scale_rows <= 0 or rows % scale_rows:
            raise RomLoweringError(
                f"weight {tensor.tensor_id!r} has {rows} rows and its scale "
                f"{scale_id!r} has {scale_rows}; a block scale covers a whole "
                "number of rows per code"
            )
        return max(rows // scale_rows, 1)

    def _expert_bank_extent(self, kernel: Kernel, tensor: Tensor) -> int:
        """The leading expert extent of a routed weight bank, or ``0``.

        A routed contraction reads one weight operand holding every expert's
        matrix, and the engine resolves the runtime expert ID *inside* that
        view (TA-ABI3-OPCONV-1 section 2).  The expert axis is therefore an
        addressing dimension and never a program loop, and the operand is
        ``[E, N, K]`` rather than the ``[N, K]`` every other contraction weight
        is.

        The bank is recognised from the data -- the kernel declares how many
        experts it selects among, and the operand's own leading extent is that
        many -- rather than from the operator's name.  A name is not a shape:
        keying this on ``kind == "ROUTED_MATMUL"`` would drop the expert axis
        the moment an exporter renamed the operation, which is exactly how the
        route table's narrowing was lost.
        """
        declared = int(kernel.attributes.get("expert_count", 0) or 0)
        if declared <= 1:
            return 0
        dims = self._dims(tensor)
        if len(dims) != 3 or dims[0] != declared:
            return 0
        return declared

    def _narrowed_read(self, kernel: Kernel, tensor: Tensor) -> DType | None:
        """The element type a declared table reading asks this weight be read at.

        A checkpoint may store a table at 64 bits that every reader of it uses
        at 32 -- DeepSeek's ``tid2eid`` holds expert IDs below 256 in int64.
        The kernel that reads the table declares the reading, so the backend
        presents the same bytes through a narrower element type and a doubled
        stride: a description, never a conversion pass.
        """
        declared = str(kernel.attributes.get("table_element_reading", ""))
        if not declared:
            return None
        narrow = TABLE_ELEMENT_READINGS.get(declared)
        if narrow is None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares table_element_reading "
                f"{declared!r}, which names no ABI 3.0 element type"
            )
        if tensor.dtype not in WIDE_INDEX_DTYPES:
            return None
        # The reading is the *table's*.  When the kernel states the table's row
        # count, only the operand with that many rows is read through it, so a
        # second wide operand of the same kernel keeps its own element type.
        rows = int(kernel.attributes.get("table_rows", 0) or 0)
        if rows and self._dims(tensor)[0] != rows:
            return None
        return narrow

    def _weight_role(self, kernel: Kernel, tensor: Tensor, default: str) -> str:
        """The ROM region role this weight operand is placed under."""
        if self._expert_bank_extent(kernel, tensor):
            return "expert_bank"
        return default

    def _members(self, tensor: Tensor, slot: int, offset: int) -> list[RomMember]:
        """The ROM members one weight tensor contributes, in payload order.

        A binding is usually one authenticated checkpoint range and yields one
        member.  A *segmented* binding is a bank the model addresses as one
        operand and the checkpoint stores apart -- DeepSeek's 256 routed
        experts per layer, interleaved and lexicographically ordered in the
        shards -- and yields one member per segment, each naming its own source
        tensor, shard file, file offset and digest.

        Collapsing a segmented binding to ``(binding.path, binding.offset,
        binding.bytes)`` reconciles byte for byte and is nevertheless wrong in
        every particular: the segments are not contiguous and not even
        ascending in the file, so a single 1 GiB range starting at expert 0
        reads 255 other experts' bytes.  Nothing downstream would complain --
        the totals balance and the digest is the binding's own -- which is
        exactly why the expansion happens here, where the segments are still
        named.  It is also what keeps the placement granularity the ROM layout
        policy works in: an expert, not a whole bank.
        """
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
        members: list[RomMember] = []
        cursor = offset
        # An unsegmented binding keeps the tensor's own identity; a segment
        # names the checkpoint tensor it is, which is what makes an expert
        # addressable by name in the plan, the manifest and the inverse proof.
        for source in binding.segments or (binding,):
            members.append(
                RomMember(
                    tensor_id=(
                        source.source_name if binding.segments else tensor.tensor_id
                    ),
                    slot=slot,
                    offset_bytes=cursor,
                    bytes=source.bytes,
                    source_path=source.path,
                    source_offset=source.offset,
                    source_sha256=source.sha256,
                    dtype=tensor.dtype,
                )
            )
            cursor += source.bytes
        return members

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

    def _schedule(
        self,
        kernel: Kernel,
        family: Major,
        sub: int,
        *,
        rows_override: int | None = None,
        placement_views: tuple[Sequence[int], Sequence[int]] | None = None,
    ) -> int:
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
        # The rows *one dispatch* covers.  Normally that is the operator's
        # token extent, but an operator issued once per token covers one row
        # however many the iteration domain names, and a schedule that claimed
        # otherwise would price a per-token dispatch as a whole block.
        rows = (
            rows_override
            if rows_override is not None
            else domain.get("tokens") or (self._dims(outputs[0])[0] if outputs else 1)
        )
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
        if placement_views is None:
            bank_mask = self._bank_mask(kernel)
            port_mask = self._port_mask(kernel)
            route_class = self._route_class(kernel)
        else:
            bank_mask, port_mask, route_class = self._view_placement(
                *placement_views
            )
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

    def _view_placement(
        self, inputs: Sequence[int], outputs: Sequence[int]
    ) -> tuple[int, int, int]:
        """Reconstruct schedule placement from an auxiliary operator's views.

        Most operators bind exactly the graph operands, so their placement is
        cheaply derived from tensor IDs.  The rolling compressor also emits
        ABI-3.0 DMA/reduction primitives whose views are compiler-created
        slices of the packed projection and direct HBM history.  Those slices
        have no neutral tensor ID of their own; their descriptors are therefore
        the only honest source for bank, port, and route placement.
        """

        planned: dict[int, Any] = {}
        if self.plan is not None:
            planned = {int(region.object_id): region for region in self.plan.regions}
        bank_mask = 0
        port_mask = 0
        reticles: set[int] = set()
        tiles: set[int] = set()
        for view_id in (*inputs, *outputs):
            if int(view_id) == NO_ID:
                continue
            view = self.builder.table[int(view_id)]
            object_id = int(view.primary_object_id)
            obj = self.builder.table[object_id]
            storage = StorageClass(int(obj.payload["storage_class"]))
            if storage is StorageClass.ROM:
                # Generated constants are mask-programmed too, but unlike a
                # checkpoint region they occupy no published plan shard and
                # therefore assert no planned-bank bit.
                region = planned.get(object_id)
                if region is None or view_id not in inputs:
                    continue
                for shard in region.shards:
                    index = shard.coordinate.tile or shard.coordinate.bank
                    bank_mask |= 1 << (index % 32)
                    reticles.add(int(shard.coordinate.reticle))
                    tiles.add(int(shard.coordinate.tile))
                continue
            port_mask |= 1 << (int(obj.payload["bank_or_tile"]) % 32)
        if len(reticles) > 1:
            route = RouteClass.INTER_RETICLE
        elif len(tiles) > 1:
            route = RouteClass.INTRA_RETICLE
        else:
            route = RouteClass.LOCAL
        return bank_mask, port_mask, route

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
        # ``in1`` is the *weight*.  A routed contraction names its weight bank in
        # an attribute rather than as an operand -- the backend places the bank
        # and binds it to slot 1 -- so the IR's second input is the expert ID
        # array, and reading the profile's second dtype off it declared a U32
        # weight for an MXFP4 bank.  The bank states its own format.
        second = str(
            attributes.get(
                "second_input_dtype",
                attributes.get("expert_weight_dtype")
                or (inputs[1].dtype if len(inputs) > 1 else first),
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
        order = reduction_order_for(contract, kernel.kind, attributes)
        # An engine reads its epsilon and its scale from the numeric
        # descriptor, so a kernel that declares either must have it carried
        # through. Omitting them produced a deployment the verifier admitted
        # and the RMSNorm engine then refused at execution, which is the worst
        # place for a missing field to surface.
        epsilon_bits = self._epsilon_bits(kernel)
        scale_bits = _binary32_bits(
            attributes,
            (
                "scale_bits",
                "score_scale_binary32",
                # ``VECTOR.INDEX_SCORE``'s learned-index scale, as the released
                # DeepSeek exporter spells it.  The engine reads it off the
                # numeric descriptor and refuses a scale that is not a positive
                # finite binary32, so an unrecognised spelling is not a missing
                # optimisation -- it is an operator that cannot be issued.
                "head_weight_scale_binary32",
                "scale_bf16_code",
                "scale",
            ),
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

    def _epsilon_bits(self, kernel: Kernel) -> int:
        """The numeric descriptor's epsilon, in the encoding its opcode reads.

        A NUMERIC descriptor's epsilon field is a binary32 pattern for every
        contract that adds the epsilon in binary32.  The released *unweighted*
        head RMSNorm is not one of them: its square, mean, epsilon and
        reciprocal square root are all BF16-domain, so the engine requires a
        BF16 epsilon code and refuses any other encoding rather than guess
        which one a pattern is in.  The narrowing therefore belongs here, where
        the operand arity that distinguishes the two head-norm contracts is
        known; the weighted head norm -- Qwen's, which passes a gain vector --
        keeps binary32.  This mirrors ``_epsilon_bits`` in
        ``compiler/backends/hbm_sram/lower.py``: one convention, two backends.
        """
        bits = _binary32_bits(kernel.attributes, ("epsilon_bits", "epsilon"))
        if kernel.kind != "HEAD_RMS_NORM" or not bits or len(kernel.inputs) != 1:
            return bits
        return _narrow_bf16_rne(bits)

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
        scale_block_rows: int = 0,
        extent_axis: int = 0,
        extent_unit: int = 0,
        extent_numerator: int = 0,
        extent_bias: int = 0,
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
            scale_block_rows,
            int(layout),
            extent_axis,
            extent_unit,
            extent_numerator,
            extent_bias,
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
            scale_block_rows=scale_block_rows,
            extent_axis=extent_axis,
            extent_unit=extent_unit,
            extent_numerator=extent_numerator,
            extent_bias=extent_bias,
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
        padded_sizes: dict[str, int] = {}
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
            padded_sizes[root] = max(
                padded_sizes.get(root, 0), self._padded_bytes(tensor)
            )
        self._buffer_root = {
            self._base_buffer_key(t.tensor_id): find(self._base_buffer_key(t.tensor_id))
            for t in self.graph.tensors
            if t.role not in WEIGHT_ROLES and t.role != "state"
        }
        self._buffer_size = padded_sizes

    def _buffer_key(self, tensor_id: str) -> str:
        base = self._base_buffer_key(tensor_id)
        return self._buffer_root.get(base, base)

    def _buffer(self, tensor_id: str) -> int:
        key = self._buffer_key(tensor_id)
        if key in self._buffer_object:
            return self._buffer_object[key]
        tensor = self.tensors[tensor_id]
        size = self._buffer_size.get(key, self._padded_bytes(tensor))
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

        The direction is the kernel's *effect*, not the operand's position.  A
        ``STATE_READ`` re-presentation -- DeepSeek's ``compress_kv_valid_view``,
        which narrows the compressed cache to the rows a request has actually
        filled -- declares ``state_reads`` and no ``state_writes``, and yet
        names its result in ``outputs`` with ``role: state``.  Counting that
        result as a *written* plane reserves it a second column beside the
        append's, so the resource's row is widened to hold two copies of a
        record there is only one of, the append fills the low half and every
        reader addresses the high half, which nothing writes.  That is 21
        all-zero ``INDEX_SCORE`` kernels and a sparse index that selects by
        tie-break, with no trap anywhere: the rows read are inside the object
        and legally zero.  A kernel that does not write the resource does not
        consume a column of it.
        """
        order: dict[str, list[tuple[str, str]]] = {}
        owner: dict[str, str] = {}
        for kernel in self.graph.kernels:
            state_ids = kernel.state_reads or kernel.state_writes
            if not state_ids:
                continue
            for position, names in (("in", kernel.inputs), ("out", kernel.outputs)):
                for name in names:
                    tensor = self.tensors[name]
                    declared = tensor.role == "state"
                    writes = position == "out" and self._writes_resource(kernel, name)
                    if not (declared or writes) or name in owner:
                        continue
                    direction = "out" if writes else "in"
                    state_id = (
                        kernel.state_writes[0]
                        if writes and kernel.state_writes
                        else state_ids[0]
                    )
                    owner[name] = state_id
                    order.setdefault(state_id, []).append((name, direction))
        self._state_owner = owner
        return order

    @staticmethod
    def _direct_state_source(state: StateResource, size_bytes: int) -> ObjectSource:
        """Materialise a direct buffer's declared fresh-session sentinel."""

        if state.initialization == "zero":
            return ObjectSource.zeros(size_bytes)
        if state.initialization != "negative_infinity":
            raise RomLoweringError(
                f"state {state.state_id!r}: direct-buffer initialization "
                f"{state.initialization!r} is unsupported"
            )
        if state.dtype != "fp32" or size_bytes % 4:
            raise RomLoweringError(
                f"state {state.state_id!r}: negative_infinity initialization "
                f"requires whole FP32 elements, got {state.dtype!r} and "
                f"{size_bytes} bytes"
            )
        # Object sources materialise bytes, independently of the dtype through
        # which an operator later views them.  Repeating the U32 bit pattern is
        # therefore the exact spelling of FP32 -infinity, and uses an existing
        # frozen generator rather than adding a state-specific ABI concept.
        from runtime.sim.generators import digest_of

        parameters = {"value": 0xFF800000, "count": size_bytes // 4}
        generator = "constant_u32_v1"
        return ObjectSource.generated(
            generator,
            parameters,
            size_bytes,
            digest_of(generator, parameters),
        )

    def emit_states(self) -> None:
        """Merge congruent per-layer state resources into one physical state.

        The IR names 36 (or 43) per-layer KV resources.  On a ROM target they
        are one physical HBM object with a per-layer slot, so the compressed
        layer body can reach the current layer's rows through the same dynamic
        term the weights use, and so one prepare/commit covers the whole token
        step.  Partial layer advancement therefore cannot become architectural.
        """
        views = self._state_tensors()
        # A resource's *physical* row must hold every plane the graph places on
        # it in one direction at once.  The declared row states the append
        # contract; where a graph declares planes wider than that -- DeepSeek's
        # compressor window declares a 1,024-element row and then writes two
        # 4,096-element planes -- the row is widened to what the views need and
        # the widening is recorded, because silently truncating a plane would
        # corrupt the model and silently overlapping two would be worse.
        plane_rows: dict[str, int] = {}
        for state_id, names in views.items():
            per_direction = {"in": 0, "out": 0}
            for name, direction in names:
                per_direction[direction] += self._plane_width(name)
            plane_rows[state_id] = max(per_direction.values(), default=0)
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
            dtype = self._dtype(members[0].dtype)
            bits = DTYPE_BITS[dtype]
            declared_row = members[0].row_elements
            row_elements = max(
                declared_row,
                max((plane_rows.get(m.state_id, 0) for m in members), default=0),
            )
            if row_elements != declared_row:
                # Keyed by class *and* declared row: DeepSeek's index cache and
                # its attention cache are both ``compressed_kv`` and differ only
                # in their row, so a key of the class alone lets one group's
                # record silently replace the other's.
                self._state_row_widenings[
                    f"{members[0].state_class}.row{declared_row}"
                ] = {
                    "declared_row_elements": declared_row,
                    "physical_row_elements": row_elements,
                    "state_class": members[0].state_class,
                }
            row_bytes = (row_elements * bits + 7) // 8
            capacity = self._extent(members[0].capacity_rows)
            slot_bytes = row_bytes * capacity
            if slot_bytes <= 0:
                raise RomLoweringError(f"state group {index} has no capacity")
            total = slot_bytes * len(members)
            group_key = f"state.{index}"
            self._state_group_count += 1
            self._state_group_shape[group_key] = (slot_bytes, capacity, row_elements)
            for slot, state in enumerate(members):
                self._state_slot[state.state_id] = (group_key, slot)

            if _is_direct_buffer_state(members[0].state_class):
                source = self._direct_state_source(members[0], total)
                direct = self.builder.memory_object(
                    storage_class=StorageClass.HBM,
                    size_bytes=total,
                    source=source,
                    permissions=int(Permission.READ | Permission.WRITE),
                    alignment_log2=12,
                    integrity_mode=IntegrityMode.CRC_AND_ECC,
                    content_digest=source.authenticated_content_digest(),
                    key=f"obj.{group_key}",
                )
                self._state_object[group_key] = direct
                self._direct_state_groups[group_key] = members[0].state_class
                continue

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
                dims=(capacity, row_elements),
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
            for slot, state in enumerate(members):
                self._state_descriptor[state.state_id] = descriptor
            self._state_object[group_key] = prepared
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
            spans: dict[str, list[tuple[int, int, str]]] = {"in": [], "out": []}
            for name, direction in names:
                width = self._plane_width(name)
                if cursor[direction] + width > row_elements:
                    raise RomLoweringError(
                        f"state planes of {state_id!r} need "
                        f"{cursor[direction] + width} elements but its row is "
                        f"{row_elements}"
                    )
                columns.setdefault(self._state_struct_key(name), cursor[direction])
                spans[direction].append((cursor[direction], width, name))
                cursor[direction] += width
            self._check_read_planes_are_written(state_id, spans)
        self._state_column = columns

    @staticmethod
    def _check_read_planes_are_written(
        state_id: str, spans: Mapping[str, Sequence[tuple[int, int, str]]]
    ) -> None:
        """Refuse a resource whose readers address columns no writer fills.

        The columns are the whole of what pairs a read with the append that
        produced it, and a mismatch is silent in every direction that matters:
        the rows are inside the object, they are legally zero because the image
        is zero-initialised, and no engine can tell a plane that was never
        written from one written with zeros.  DeepSeek's compressed caches
        spent this program's whole history in that state -- the index cache
        read 128 elements past its own append, which is 21 all-zero
        ``INDEX_SCORE`` kernels and a learned sparse index that selected by
        tie-break.  A resource that has writers at all must cover every column
        its readers name.
        """
        written = sorted((start, start + width) for start, width, _ in spans["out"])
        if not written:
            return
        merged: list[list[int]] = []
        for start, stop in written:
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(merged[-1][1], stop)
            else:
                merged.append([start, stop])
        for start, width, name in spans["in"]:
            stop = start + width
            if any(low <= start and stop <= high for low, high in merged):
                continue
            raise RomLoweringError(
                f"state resource {state_id!r} is read at columns "
                f"[{start}, {stop}) by {name!r}, which no write of the resource "
                f"covers (writes cover {[tuple(m) for m in merged]}); a reader "
                "and a writer that disagree about the row layout exchange "
                "zeros in silence"
            )

    def _request_sized_planes(self, kernel: Kernel) -> list[str]:
        """Operands that are state planes whose leading extent the request sets.

        A state plane presents the resource's whole capacity, which is right for
        a KV window addressed by absolute position and wrong for a *compressed*
        cache: its capacity counts one row per group of ``ratio`` context
        tokens, so a request that has filled one of 65,536 groups must present
        one.  Nothing shortened them, so the attention join summed 65,668 rows
        for a request with 133 -- A17's check passed, because it is a check on
        what the operands say and they all said their maximum.
        """
        named: list[str] = []
        for name in (*kernel.inputs, *kernel.outputs):
            tensor = self.tensors.get(name)
            if tensor is None or tensor.role != "state":
                continue
            symbol, _multiplier, axis = self._leading_symbol(tensor)
            if symbol is None or axis.is_identity:
                continue
            if self._state_owner.get(name) is not None:
                named.append(name)
        return named

    def _writes_resource(self, kernel: Kernel, name: str) -> bool:
        """Is this output of a state-writing kernel *the resource*, or a value?

        A kernel that declares a state effect does not thereby make every result
        it produces a plane of that resource.  ``DMA.CACHE_APPEND``'s
        destination is the cache, and Qwen declares it ``role: activation``, so
        the role alone cannot decide it.  ``VECTOR.COMPRESS``'s state-update
        sub-case is the counter-example: it rolls the compressor's raw slots --
        which is a real state effect, and which the operand convention binds to
        no operand at all -- while its two results are the pool operands
        ``COMPRESS_POOL`` reads next.

        The graph already separates them.  A resource plane is written and not
        read again as an operand; a value is produced to be consumed.  Routing a
        consumed value into the state image writes it to a different object from
        the one its reader addresses, which loses it silently -- 62 compressor
        pools per token step, read back as zeros.
        """
        if not kernel.state_writes:
            return False
        if self.tensors[name].role == "state":
            return True
        return name not in self._value_reads

    @property
    def _value_reads(self) -> frozenset[str]:
        """Tensors some kernel reads as an ordinary operand."""
        cached = getattr(self, "_value_reads_cache", None)
        if cached is None:
            cached = frozenset(
                name for kernel in self.graph.kernels for name in kernel.inputs
            )
            self._value_reads_cache = cached
        return cached

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
        self,
        kernel: Kernel,
        tensor_id: str,
        direction: str,
        run: LayerRun | None,
        *,
        batch_lead: bool = False,
        extent_axis: int = 0,
        extent_unit: int = 0,
        extent_numerator: int = 0,
        extent_bias: int = 0,
        extra_terms: Sequence[DynamicTerm] = (),
    ) -> int | None:
        """One plane of a merged state resource, moved by the layer loop.

        The window is the resource's whole capacity rather than a token block:
        attention reads the entire context, and an append addresses absolute
        positions.  Both directions name the *prepared* image, because a
        transaction attends the rows it has just appended; the committed image
        is the durability record the commit publishes, not the buffer execution
        runs against.

        A *compressed* cache is the exception, and amendment A18 is what lets it
        be said.  Its capacity counts one row per group of ``ratio`` context
        tokens, so a request that has filled 1 of 65,536 groups must present 1
        -- and before A18 there was no way to state that, because the extent is
        a division of ``CONTEXT_LENGTH`` and A13 clamped only in the symbol's
        own units.  ``extent_unit`` says the division and ``extra_terms``
        carries the loop that resolves it; ``batch_lead`` fronts the plane with
        a batch of one where the operand row asks for ``[B, C, D]``.
        """
        state_id = self._state_owner.get(tensor_id)
        if (
            state_id is None
            and direction == "out"
            and self._writes_resource(kernel, tensor_id)
        ):
            state_id = kernel.state_writes[0]
        if state_id is None or state_id not in self._state_slot:
            return None
        group_key, slot = self._state_slot[state_id]
        slot_bytes, capacity, row_elements = self._state_group_shape[group_key]
        prepared = self._state_object[group_key]
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
            # The induction value is relative to this compressed run, while a
            # state slot is deployment-global.  Keep the representative
            # layer's starting slot as the static base and let the loop term
            # advance from there.  Dropping the base aliases every later run
            # onto slot zero (and aliases both halves of a period-2 run onto
            # the same slots): prefill can survive because each layer writes
            # immediately before reading, but decode then consumes another
            # layer's retained history.
            offset = slot * window + column
        if batch_lead:
            # The inserted axis holds one element, so its stride never moves an
            # address; it takes the whole plane so the view stays row-major and
            # ``stride[1]`` remains one row of the axis A18's walk test reads.
            extents = [1, *extents]
            strides = [extents[1] * strides[0], *strides]
        dynamic.extend(extra_terms)
        return self._view(
            object_id=prepared,
            dtype=dtype,
            dims=extents,
            strides=strides,
            element_offset=offset,
            dynamic=dynamic,
            permissions=int(Permission.READ | Permission.WRITE),
            extent_axis=extent_axis,
            extent_unit=extent_unit,
            extent_numerator=extent_numerator,
            extent_bias=extent_bias,
            label="view.state",
        )

    def _compressor_history_view(
        self,
        kernel: Kernel,
        state_id: str,
        run: LayerRun | None,
        *,
        dims: Sequence[int],
        strides: Sequence[int],
        column: int = 0,
    ) -> int:
        """A direct-HBM slice of one compressor history resource.

        Raw compressor history is a state *effect* in the neutral graph, not
        an operator operand, so it has no tensor ID for ``_state_plane_view``
        to follow.  This is the missing binding: one ordinary writable view of
        the resource's own rows, with the same outer layer-loop term used by
        every other merged per-layer state object.
        """

        state = self.states.get(state_id)
        if state is None or state_id not in self._state_slot:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: compressor history {state_id!r} "
                "is not a declared emitted state resource"
            )
        if not _is_direct_buffer_state(state.state_class):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: compressor history {state_id!r} "
                "is not an ordinary direct HBM buffer"
            )
        group_key, slot = self._state_slot[state_id]
        slot_bytes, capacity, row_elements = self._state_group_shape[group_key]
        if int(dims[0]) != capacity:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: compressor history view has "
                f"{dims[0]} rows; resource {state_id!r} has {capacity}"
            )
        highest = int(column)
        for extent, stride in zip(dims, strides):
            highest += max(int(extent) - 1, 0) * int(stride)
        if highest >= capacity * row_elements:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: compressor history slice exceeds "
                f"resource {state_id!r}'s {capacity}x{row_elements} elements"
            )

        bits = DTYPE_BITS[self._dtype(state.dtype)]
        window = slot_bytes * 8 // bits
        dynamic: list[DynamicTerm] = []
        if run is not None and run.groups > 1:
            column_peers = next(
                (
                    peers
                    for peers in run.body
                    if any(peer.index == kernel.index for peer in peers)
                ),
                None,
            )
            if column_peers is None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} is not in run {run.index}"
                )
            try:
                state_position = list(kernel.state_reads).index(state_id)
            except ValueError:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} does not read compressor "
                    f"history {state_id!r}"
                ) from None
            slots: list[int] = []
            for peer in column_peers:
                if state_position >= len(peer.state_reads):
                    raise RomLoweringError(
                        f"kernel {peer.kernel_id!r} omits compressor history "
                        f"slot {state_position} folded by run {run.index}"
                    )
                peer_id = peer.state_reads[state_position]
                peer_group, peer_slot = self._state_slot[peer_id]
                if peer_group != group_key:
                    raise RomLoweringError(
                        f"run {run.index} folds compressor histories from "
                        "different physical groups"
                    )
                slots.append(peer_slot)
            advances = {
                right - left for left, right in zip(slots, slots[1:])
            }
            if len(advances) != 1:
                raise RomLoweringError(
                    f"compressor history {state_id!r} advances by "
                    f"{sorted(advances)} slots in run {run.index}"
                )
            stride = window * advances.pop()
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"compressor history {state_id!r} needs layer stride "
                    f"{stride}, outside ABI 3.0's dynamic-term field"
                )
            dynamic.append(DynamicTerm.loop(self._loop_of_run[run.index], stride))

        return self._view(
            object_id=self._state_object[group_key],
            dtype=self._dtype(state.dtype),
            dims=dims,
            strides=strides,
            element_offset=slot * window + int(column),
            dynamic=dynamic,
            permissions=int(Permission.READ | Permission.WRITE),
            label="view.compressor_history",
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
    def _leading_symbol(
        self, tensor: Tensor
    ) -> tuple[int | None, int, RequestAxis]:
        """The runtime symbol of a tensor's leading axis, multiplier and affine."""
        if not tensor.shape or not isinstance(tensor.shape[0], Symbolic):
            return None, 1, IDENTITY_AXIS
        axis = tensor.shape[0]
        request = SYMBOL_BY_NAME.get(axis.symbol)
        if request is None:
            return None, int(axis.multiplier or 1), IDENTITY_AXIS
        return int(request.symbol), int(axis.multiplier or 1), request

    def _principal(self, kernel: Kernel) -> Tensor | None:
        """The operand whose leading extent sets this operator's row geometry.

        Normally the result: how many rows an operation produces is what a
        token block has to cover.  A movement into a *cache* is the exception.
        Its destination extent is the cache's capacity -- 128 rows of sliding
        window, or every compressed group the context admits -- and has nothing
        to do with how many rows the request moves into it.  Taking the
        capacity as the row count made an append declare an index vector as
        long as the whole cache, which is how a 104-token prefill came to name
        row 262,143 of a 128-row window.  A kernel that says how its
        destination row is addressed is saying its destination is a cache, so
        the rows moved are the source's.
        """
        if kernel.attributes.get("cache_row") and kernel.inputs:
            return self.tensors[kernel.inputs[0]]
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
        symbol, multiplier, axis = (
            self._leading_symbol(principal)
            if principal is not None
            else (None, 1, IDENTITY_AXIS)
        )
        # A18 can state a multiplied request extent directly.  Keep the whole
        # routed producer chain at ``top_k * span`` so every blocked routed
        # contraction sees the neutral graph's request-wide row grouping.
        # Other multiplied-symbol operations retain the older exact fallback:
        # iteration ``t`` presents precisely that token's multiplied rows.
        batch_multiplier = (
            multiplier
            if symbol is not None
            and multiplier > 1
            and kernel.kind in MULTIPLIED_SPAN_BATCH_KINDS
            else 1
        )
        per_token = (
            symbol is not None and multiplier > 1 and batch_multiplier == 1
        )
        row_symbolic = symbol is not None
        # The rows a block loop may walk are bounded by the *smallest* extent
        # any of the kernel's symbolic-leading operands declares.  A graph may
        # give one operand a shorter maximum than the capability's context
        # bound, and a view that presented the capability's rows would run off
        # that operand's object.
        # The loop's block is stated in the *bound symbol's* units and the trip
        # follows from the symbol's own maximum.  Taking either from the
        # principal's declared extent is what gave a group axis a quarter of the
        # iterations it needs and an attention join one block too many -- the
        # extra block being exactly its 128-row window, which is a bias and not
        # a step.
        symbol_max = int(self.capability.limits["max_context_positions"])
        configured = int(self.policy.token_block_rows or 0)
        divisor = max(min(configured or symbol_max, symbol_max), 1)
        # A view's row term advances by ``step * row width`` elements and that
        # stride is a 32-bit field, so the block is halved until every operand's
        # stride fits.  Halving costs iterations, never correctness; refusing
        # would cost the whole compression.
        widest = self._widest_row(kernel)
        while (
            divisor > 1
            and divisor * widest * max(batch_multiplier, 1) > 0xFFFFFFFF
        ):
            divisor //= 2
        declared_rows = principal_dims[0] if principal_dims else 1
        trip = max(-(-symbol_max // divisor), 1) if row_symbolic else 1
        if per_token:
            # One token per iteration, and the loop counts tokens rather than
            # blocks.  The trip is the capability's loop bound because that is
            # the most tokens one instruction may walk; a longer span needs a
            # second dispatch, not a longer loop.
            divisor = 1
            trip = max(
                min(symbol_max, int(self.capability.limits["max_loop_trip"])), 1
            )
        probe = KernelShape(
            contraction=False, rows=1, cols=1, depth=0, transposed=False,
            row_symbolic=row_symbolic, block=1, trip=trip, symbol=0,
            principal=(), per_token=per_token,
            batch_multiplier=batch_multiplier, axis=axis, divisor=divisor,
        )
        block = self._axis_block(probe, axis) if row_symbolic else 1
        rows = min(block, declared_rows) if row_symbolic else max(declared_rows, 1)
        if per_token:
            rows = multiplier
        elif batch_multiplier > 1:
            rows = min(block * batch_multiplier, declared_rows)

        cols = principal_dims[-1] if len(principal_dims) > 1 else 1
        depth = 0
        transposed = False
        if contraction:
            weight = self._contraction_weight(kernel)
            activation = self.tensors[kernel.inputs[0]] if kernel.inputs else None
            weight_dims = tuple(self._dims(weight)) if weight is not None else (1, 1)
            act_dims = tuple(self._dims(activation)) if activation is not None else (1,)
            # The iteration domain is the authority on the reduction width
            # when the graph states it.  Otherwise it is read off the operands:
            # the activation's last axis, or -- when the graph gave the result a
            # head-shaped rank -- the product of its non-leading axes, which is
            # the same contraction described differently.
            folded = 1
            for extent in act_dims[1:]:
                folded *= extent
            candidates = [
                int(self._extent(kernel.iteration_domain.get("reduction_width", 0)) or 0),
                act_dims[-1],
                folded,
            ]
            # TA-ABI3-OPCONV-1 section 2: in1 is n-major ``[N, K]``.  A
            # checkpoint that stores ``[K, N]`` is presented n-major by swapping
            # the view's strides, never by a relayout pass.
            for candidate in candidates:
                if candidate <= 0 or len(weight_dims) < 2:
                    continue
                if weight_dims[-1] == candidate:
                    depth, cols, transposed = candidate, weight_dims[-2], False
                    break
                if weight_dims[-2] == candidate:
                    depth, cols, transposed = candidate, weight_dims[-1], True
                    break
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
            per_token=per_token,
            batch_multiplier=batch_multiplier,
            axis=axis,
            divisor=divisor,
        )

    def _symbolic_row_bound(self, kernel: Kernel, symbol: int, unit: int) -> int:
        """The smallest leading extent any operand on *this* axis declares.

        An extent is only comparable with another stated in the same symbol and
        the same A18 unit.  A kernel may hold both -- ``INDEX_SCORE`` reads a
        token-major query and a group-major key -- and taking the smaller of
        65,536 groups and 262,144 tokens would bound a token axis by a count of
        groups, which is the shape of arithmetic A18 exists to stop the backend
        doing implicitly.
        """
        span_max = int(self.capability.limits["max_context_positions"])
        bound = span_max // max(unit, 1)
        for name in (*kernel.inputs, *kernel.outputs):
            tensor = self.tensors.get(name)
            if tensor is None or tensor.role in WEIGHT_ROLES:
                continue
            leading, multiplier, operand_axis = self._leading_symbol(tensor)
            if leading != symbol or operand_axis.unit != unit or multiplier != 1:
                continue
            bound = min(bound, self._dims(tensor)[0])
        return max(bound, 1)

    def _widest_row(self, kernel: Kernel) -> int:
        """The widest per-row element count any of this kernel's operands has."""
        widest = 1
        for name in (*kernel.inputs, *kernel.outputs):
            tensor = self.tensors.get(name)
            if tensor is None or tensor.role in WEIGHT_ROLES:
                continue
            width = 1
            for extent in self._dims(tensor)[1:]:
                width *= extent
            widest = max(widest, width)
        return widest

    def _contraction_weight(self, kernel: Kernel) -> Tensor | None:
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
            # The loop counts the *symbol's* units and the blocked axis counts
            # its own, ``unit`` symbol units each, so one iteration of a block
            # of ``block`` axis elements advances the symbol by ``block *
            # unit``.  Amendment A18's walk test and its clamp both read the
            # divisor in the symbol's units; with unit one this is what A13
            # always wrote.
            bound_divisor=shape.divisor,
            counter_class_id=self._counter_class("instruction", Major.CONTROL),
            key=f"loop.block.k{kernel.index:05d}",
        )
        self.builder.open_loop(loop)
        return loop

    def _open_context_loop(
        self, kernel: Kernel, capacity: int, axis: RequestAxis
    ) -> int:
        """A loop whose only job is to resolve a *context*-sized axis.

        Amendment A18 shortens an axis only through a loop term that walks it,
        so an operand whose extent the request decides needs a loop even when
        nothing about it iterates.  One block over the whole declared capacity
        is that loop: it runs once, and the resolution it carries is the point
        of it.  ``_open_row_loop`` says the same thing about the token axis.

        The divisor is in ``CONTEXT_LENGTH``'s own units, so it is the capacity
        times the compression ratio: 65,536 groups of four is the whole
        262,144-position context, and one iteration covers all of it.
        """
        trip = 1
        loop = self.builder.loop_control(
            lower_bound=0,
            upper_bound=trip,
            step=1,
            max_iterations=trip,
            bound_symbol=Symbol(axis.symbol),
            bound_divisor=capacity * axis.unit // max(axis.numerator, 1),
            counter_class_id=self._counter_class("instruction", Major.CONTROL),
            key=f"loop.context.k{kernel.index:05d}",
        )
        self.builder.open_loop(loop)
        return loop

    @property
    def _position_inputs(self) -> frozenset[str]:
        """Declared inputs whose content is the request's position range.

        A rank-one integer input over the token axis that no embedding reads
        holds ``POSITION_START + i`` and nothing else.  ADR-003 binds that range
        as a request symbol, so it is materialised from the frozen
        ``arange_u32_v1`` generator and the view is offset by the symbol --
        identical values, and no host window that nothing could fill.

        A graph may declare the range as a span-length vector or as a single
        base offset; both name the same range, and both resolve to a view of
        the materialised one.  Reading a scalar offset as if it were the whole
        vector is how the second form would otherwise fail.
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
            if len(tensor.shape) != 1:
                continue
            axis = tensor.shape[0]
            if not isinstance(axis, Symbolic) and int(axis) != 1:
                continue
            kinds = consumers.get(tensor.tensor_id, [])
            if not kinds or any(k == "EMBEDDING_LOOKUP" for k in kinds):
                continue
            names.add(tensor.tensor_id)
        self._position_input_cache = frozenset(names)
        return self._position_input_cache

    def _token_stream_input(self) -> str | None:
        """The declared input the host stages a request's tokens into.

        A rank-one index vector over the token axis that an embedding reads is
        the token stream, and the host queue's input window is where it arrives.
        Binding it to the same object the generation policy names as the token
        ring is what makes a decode step read the token the previous step
        appended.
        """
        for kernel in self.graph.kernels:
            if kernel.kind != "EMBEDDING_LOOKUP" or not kernel.inputs:
                continue
            tensor = self.tensors[kernel.inputs[0]]
            if (
                tensor.role == "input"
                and tensor.dtype in {"u32", "i32"}
                and len(tensor.shape) == 1
            ):
                return tensor.tensor_id
        return None

    #: Frozen vocabulary for a movement's destination-row map.  A backend that
    #: met an addressing it does not implement would otherwise write a request's
    #: rows to whatever the identity map named.
    CACHE_ROW_MAPS = frozenset(
        {
            "absolute_position",
            "absolute_position_mod_window",
            "completed_absolute_position_floor_div_ratio",
        }
    )

    def _cache_row_modulus(self, kernel: Kernel) -> int | None:
        """The ring modulus a movement's destination-row map declares, if any.

        ``absolute_position_mod_window`` is a ring of ``window_size`` rows and
        resolves to a ring index table.  ``absolute_position`` and
        ``completed_absolute_position_floor_div_ratio`` both read the position
        range unchanged: the first because that is what it says, the second
        because a compressed group's row *is* its group ordinal and the graph
        indexes it from the start of the request.  Anything else is refused
        rather than silently taken as the identity.
        """
        declared = kernel.attributes.get("cache_row")
        if declared is None:
            return None
        name = str(declared)
        if name not in self.CACHE_ROW_MAPS:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares destination-row map "
                f"{name!r}, which this backend does not implement; the frozen "
                f"maps are {', '.join(sorted(self.CACHE_ROW_MAPS))}"
            )
        if name != "absolute_position_mod_window":
            return None
        window = int(kernel.attributes.get("window_size", 0))
        if window <= 0:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} addresses a ring but declares "
                f"window_size {window}"
            )
        return window

    def _cache_row_divisor(self, kernel: Kernel) -> int | None:
        """The divisor of a compressed-cache destination-row map, if any."""

        declared = kernel.attributes.get("cache_row")
        if declared is None:
            return None
        name = str(declared)
        if name not in self.CACHE_ROW_MAPS:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares destination-row map "
                f"{name!r}, which this backend does not implement; the frozen "
                f"maps are {', '.join(sorted(self.CACHE_ROW_MAPS))}"
            )
        if name != "completed_absolute_position_floor_div_ratio":
            return None
        divisor = int(kernel.attributes.get("ratio", 0) or 0)
        if divisor <= 0:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} addresses compressed state but "
                f"declares ratio {divisor}"
            )
        return divisor

    def _ring_object(self, modulus: int) -> int:
        """The ``position mod modulus`` range, materialised once per modulus."""
        key = f"ring.{modulus}"
        cached = self._generated_objects.get(key)
        if cached is not None:
            return cached
        from runtime.sim.generators import GeneratorError, digest_of, generate

        span_max = int(self.capability.limits["max_context_positions"])
        parameters = {
            "count": max(span_max + self._padded_symbol_bound(), 1),
            "modulus": int(modulus),
        }
        try:
            payload = generate("ring_indices_v1", parameters)
            digest = digest_of("ring_indices_v1", parameters)
        except GeneratorError as exc:  # pragma: no cover - frozen generator
            raise RomLoweringError(f"ring index range: {exc}") from None
        object_id = self.builder.memory_object(
            storage_class=self.weight_storage_class,
            size_bytes=int(payload.nbytes),
            source=ObjectSource.generated(
                "ring_indices_v1", parameters, int(payload.nbytes), digest
            ),
            permissions=ROM_PERMISSIONS,
            alignment_log2=12,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=bytes.fromhex(digest),
            key=f"obj.rom.ring.{modulus}",
        )
        self._generated_objects[key] = object_id
        return object_id

    def _floor_div_object(self, divisor: int) -> int:
        """The ``position // divisor`` range, or a fail-closed refusal."""

        from runtime.sim.generators import (
            GeneratorError,
            digest_of,
            generate,
            registered,
        )

        generator = "floor_div_indices_v1"
        if generator not in registered():
            raise RomLoweringError(
                f"compressed cache rows require registered generator "
                f"{generator!r}; falling back to absolute positions would "
                "silently address the wrong HBM rows"
            )
        key = f"floor_div.{divisor}"
        cached = self._generated_objects.get(key)
        if cached is not None:
            return cached
        span_max = int(self.capability.limits["max_context_positions"])
        parameters = {
            "count": max(span_max + self._padded_symbol_bound(), 1),
            "divisor": int(divisor),
        }
        try:
            payload = generate(generator, parameters)
            digest = digest_of(generator, parameters)
        except GeneratorError as exc:
            raise RomLoweringError(
                f"floor-div index range for divisor {divisor}: {exc}"
            ) from None
        object_id = self.builder.memory_object(
            storage_class=self.weight_storage_class,
            size_bytes=int(payload.nbytes),
            source=ObjectSource.generated(
                generator, parameters, int(payload.nbytes), digest
            ),
            permissions=ROM_PERMISSIONS,
            alignment_log2=12,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=bytes.fromhex(digest),
            key=f"obj.rom.floor_div.{divisor}",
        )
        self._generated_objects[key] = object_id
        return object_id

    def _position_object(self, tensor_id: str) -> int:
        """The mask-programmed position range, materialised once."""
        cached = self._generated_objects.get(tensor_id)
        if cached is not None:
            return cached
        from runtime.sim.generators import GeneratorError, digest_of, generate

        span_max = int(self.capability.limits["max_context_positions"])
        parameters = {"count": max(span_max + self._padded_symbol_bound(), 1)}
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
        symbol, multiplier, axis = self._leading_symbol(tensor)
        if symbol is None or (
            multiplier != 1
            and not shape.per_token
            and shape.batch_multiplier == 1
        ):
            return None
        width = 1
        for extent in self._dims(tensor)[1:]:
            width *= extent
        # The *step*, not the block: A18's walk test reads what one iteration
        # advances, and a bias advances nothing.
        step = self._axis_step(shape, axis)
        stride = step * width * (
            multiplier
            if shape.per_token or shape.batch_multiplier > 1
            else 1
        )
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
        element_offset: int = 0,
        term: DynamicTerm | None = None,
        extra_terms: Sequence[DynamicTerm] = (),
        extent_axis: int = 0,
        extent_unit: int | None = None,
        extent_numerator: int = 0,
        extent_bias: int = 0,
    ) -> int:
        object_id = self._buffer(tensor.tensor_id)
        permissions = (
            int(Permission.READ | Permission.WRITE) if writable else int(Permission.READ)
        )
        if tensor.role in {"input", "output"}:
            permissions |= int(Permission.HOST_VISIBLE)
        scale_object = NO_ID
        block = 0
        row_block = 0
        if tensor.scale_tensor_id and tensor.scale_tensor_id in self.tensors:
            scale = self.tensors[tensor.scale_tensor_id]
            block = int(tensor.scale_block_elements or 0)
            if block:
                scale_object = (
                    self._region_object(scale.tensor_id)
                    if scale.role in WEIGHT_ROLES
                    else self._buffer(scale.tensor_id)
                )
                row_block = self._scale_block_rows(tensor)
        if term is None:
            term = self._row_term(tensor, shape, loop) if blocked else None
        # Amendment A18: the view says which axis the request determines and in
        # what unit, and the verifier refuses a declaration nothing resolves --
        # rightly, because an unresolvable one silently presents the declared
        # maximum.  So the fields are written only alongside the term that
        # walks that axis, and the unit is the tensor's own.
        terms = [*([term] if term is not None else ()), *extra_terms]
        if extent_unit is None:
            # By default the declared extent is the tensor's *leading* axis, in
            # that axis's own unit, resolved by the row term.  A view with no
            # term declares nothing: A18 refuses a declaration nothing resolves.
            _symbol, tensor_multiplier, declared = self._leading_symbol(tensor)
            extent_unit = declared.unit if terms else 0
            extent_numerator = (
                declared.numerator
                * (
                    tensor_multiplier
                    if shape.batch_multiplier > 1 and tensor_multiplier > 1
                    else 1
                )
                if terms
                else 0
            )
            extent_bias = declared.bias if terms else 0
            if not terms:
                extent_axis = 0
        return self._view(
            object_id=object_id,
            dtype=self._dtype(tensor.dtype),
            dims=dims,
            strides=strides,
            element_offset=element_offset,
            dynamic=terms,
            permissions=permissions,
            scale_object_id=scale_object,
            scale_block_elements=block if scale_object != NO_ID else 0,
            scale_block_rows=row_block if scale_object != NO_ID else 0,
            extent_axis=extent_axis,
            extent_unit=extent_unit,
            extent_numerator=extent_numerator,
            extent_bias=extent_bias,
            label="view.buf",
        )

    def _token_as_batch(
        self, tensor: Tensor, shape: KernelShape
    ) -> tuple[list[int], list[int]]:
        """A token-blocked operand presented as ``[tokens, 1, ...]``.

        Several TA-ABI3-OPCONV-1 rows carry an explicit batch axis.
        ``VECTOR.MHC``'s post sub-case is one -- ``in0`` is ``[B, S, H]``,
        ``in1`` ``[B, S, M, H]``, and the engine reads ``B`` and ``S`` off
        ``in0`` -- and ``VECTOR.COMPRESS``'s project sub-case is another, with
        ``in0`` ``[B, S, K]`` and ``out0`` ``[B, S, 2, N]``.  The graph declares
        one sequence per request and no batch axis at all, so the backend has to
        say which axis is which.  ``TOKEN_AS_BATCH_KINDS`` lists the rows that
        need it, and records which of them this placement is also *sufficient*
        for.

        Naming the token axis ``B`` and giving ``S`` extent one is the only
        placement that stays correct under token blocking.  The alternative --
        a leading batch of one with the tokens second -- would put the blocked
        axis in position 1, and amendment A13's partial final extent clamps
        ``dim0`` only, so a 104-token request would present the whole declared
        block instead.  The operation is independent per ``(b, s)`` site, so
        which of the two axes carries the sequence changes nothing, and
        ``vector.mhc_sites`` counts ``batch * span`` either way.
        """
        dims = self._blocked_dims(tensor, shape)
        strides = self._row_major_strides(dims)
        # The inserted axis has one element, so its stride never moves an
        # address; it takes the leading stride so the view still reads
        # row-major from the axis it splits.
        return [dims[0], 1, *dims[1:]], [strides[0], strides[0], *strides[1:]]

    def _axis_step(self, shape: KernelShape, axis: RequestAxis) -> int:
        """Elements of *this* operand's axis one loop iteration advances.

        Amendment A18's ``iteration_extent``: ``numerator * bound_divisor /
        unit``.  Every operand derives its own step from the one divisor the
        loop carries, which is why two operands of a join may declare different
        maxima and still be blocked consistently -- the old rule compared their
        maxima to the kernel's and blocked only the one that agreed, which is
        how a join's output came to clamp while its inputs did not.

        The bias is deliberately not here.  It is elements the operand carries
        whatever the request is -- a KV join's 128-row sliding window is present
        for a span of one -- so it belongs to the extent, not to the step.
        """
        step = iteration_extent(shape.divisor, axis.numerator, axis.unit)
        if step is None:
            raise RomLoweringError(
                f"a loop block of {shape.divisor} symbol units is not a whole "
                f"number of elements of an axis counted as {axis.numerator}/"
                f"{axis.unit}; amendment A18 needs one iteration to be a whole "
                "number of the axis it walks"
            )
        return max(step, 1)

    def _axis_block(self, shape: KernelShape, axis: RequestAxis) -> int:
        """The operand's declared extent for one iteration: step plus bias."""
        return self._axis_step(shape, axis) + int(axis.bias)

    def _batch_leads(
        self, tensor: Tensor, shape: KernelShape
    ) -> tuple[list[int], list[int]]:
        """An operand presented as ``[1, rows, ...]``: the A18 placement.

        The mirror of :meth:`_token_as_batch`.  Where that one keeps the token
        axis leading so A13 can clamp it, this one puts a batch of one in front
        because the operator's own arithmetic needs the request-dependent extent
        at axis 1 -- and amendment A18 is what makes that extent resolvable, by
        letting the view name the axis instead of assuming the leading one.

        The inserted axis has one element, so its stride never moves an address.
        It takes the whole span of the axis it fronts, which keeps the view
        row-major and leaves ``stride[1]`` equal to one element of the blocked
        axis -- the stride A18's walk test reads.
        """
        dims = self._blocked_dims(tensor, shape)
        strides = self._row_major_strides(dims)
        return [1, *dims], [dims[0] * strides[0], *strides]

    def _blocked_dims(self, tensor: Tensor, shape: KernelShape) -> list[int]:
        """The tensor's declared extents with its leading axis token-blocked."""
        dims = list(self._dims(tensor))
        symbol, multiplier, axis = self._leading_symbol(tensor)
        if not dims or symbol is None or not shape.row_symbolic:
            return dims
        block = self._axis_block(shape, axis)
        if shape.per_token:
            # One token's worth of *this* operand: six routed rows, or the one
            # token they came from.
            dims[0] = min(block * multiplier, dims[0])
        elif shape.batch_multiplier > 1:
            # The complete routed batch: each bound-symbol unit contributes
            # ``multiplier`` physical rows to this operand.  A18 carries the
            # same multiplier as the view's extent numerator.
            dims[0] = min(block * multiplier, dims[0])
        elif multiplier == 1:
            dims[0] = min(block, dims[0])
        return dims

    @staticmethod
    def _row_major_strides(dims: Sequence[int]) -> list[int]:
        strides = [1] * len(dims)
        running = 1
        for axis in range(len(dims) - 1, -1, -1):
            strides[axis] = running
            running *= max(int(dims[axis]), 1)
        return strides

    def _quantized_prefix(
        self, kernel: Kernel, dims: list[int], *, slot: int, direction: str
    ) -> tuple[list[int], list[int]] | None:
        """A block quantiser that converts only the leading part of each row.

        A quantiser whose code output is narrower than its source is quantising
        a *prefix* of the row and leaving the rest alone -- DeepSeek quantises
        the 448 non-rotary channels of a 512-wide KV vector and keeps the 64
        rotary ones in BF16, because the rotary channels carry position and
        cannot afford E4M3FN.  The engine reads the source and the codes as one
        shape, so the narrowing has to be in the *view*: the same row stride,
        fewer elements of it.

        The output shape is the authority rather than an attribute, so a graph
        that says the same thing twice cannot say it two different ways; the
        declared ``quantized_width`` is checked against it instead of trusted.
        Returns ``None`` for every operand this does not apply to, which is all
        of them but a partial quantiser's source.
        """
        if kernel.kind != "QUANTIZE" or direction != "in" or slot != 0:
            return None
        if not kernel.outputs or not dims:
            return None
        codes = self._dims(self.tensors[kernel.outputs[0]])
        if not codes:
            return None
        width = int(codes[-1])
        if width == int(dims[-1]):
            return None
        if not 0 < width < int(dims[-1]):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} quantises {width} of a "
                f"{dims[-1]}-wide row, which is not a prefix of it"
            )
        declared = kernel.attributes.get("quantized_width")
        if declared is not None and int(declared) != width:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares quantized_width "
                f"{int(declared)} but its code output is {width} wide"
            )
        strides = self._row_major_strides(dims)
        return [*dims[:-1], width], strides

    def _inserted_broadcast_axis(
        self, kernel: Kernel, dims: list[int]
    ) -> tuple[list[int], list[int]]:
        """Read a ``BROADCAST`` source through one axis of stride zero.

        The neutral kernel states that its result is its source with ``extent``
        inserted at ``axis``, every element of the new axis being the same
        element.  A stride of zero *is* that statement: the view reaches no
        further than the source does, costs no bytes, and the engine reads one
        row ``extent`` times instead of holding ``extent`` copies of it.

        Only the source is widened.  A zero stride on a writable view would
        make every element of the axis the same *location*, which is an
        aliasing write whose result is whichever copy landed last.
        """
        attributes = kernel.attributes
        axis = int(attributes["axis"])
        extent = int(attributes["extent"])
        if not 0 <= axis <= len(dims):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: BROADCAST axis {axis} is outside "
                f"the rank-{len(dims)} source"
            )
        if extent <= 0:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: BROADCAST extent {extent} is not "
                "positive"
            )
        strides = self._row_major_strides(dims)
        return (
            [*dims[:axis], extent, *dims[axis:]],
            [*strides[:axis], 0, *strides[axis:]],
        )

    def _selected_plane(
        self, kernel: Kernel, dims: list[int]
    ) -> tuple[list[int], list[int], int]:
        """Read one plane of a ``SELECT`` source: drop an axis, offset into it.

        The mirror of :meth:`_inserted_broadcast_axis`.  A broadcast reads one
        source through an axis of stride zero; a select reads one plane by
        dropping the named axis and offsetting the view's element origin by
        ``index`` of that axis's stride.  The destination keeps the rank the
        graph declared, which is the source's rank minus one.
        """
        attributes = kernel.attributes
        axis = int(attributes["axis"])
        index = int(attributes["index"])
        if not 0 <= axis < len(dims):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: SELECT axis {axis} is outside the "
                f"rank-{len(dims)} source"
            )
        if not 0 <= index < int(dims[axis]):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: SELECT index {index} is outside "
                f"the {dims[axis]} planes of axis {axis}"
            )
        strides = self._row_major_strides(dims)
        return (
            [*dims[:axis], *dims[axis + 1 :]],
            [*strides[:axis], *strides[axis + 1 :]],
            index * strides[axis],
        )

    def _broadcast(
        self,
        dims: list[int],
        shape: KernelShape,
        *,
        scale_factor: bool = False,
    ) -> tuple[list[int], list[int] | None]:
        """Insert the principal operand's missing middle axes at stride zero.

        A rotary coefficient table holds one row per *token* while the tensor it
        rotates holds one per ``(token, head)``: every head of a token shares the
        row.  A zero stride says so, and nothing is copied to make it true.  The
        rule is positional and model-blind -- one axis fewer, agreeing on the
        leading extent -- so it never has to know what a head is.

        Under a per-token routed block there is a second shape of the same
        statement: one value per *routed row* against a tensor held per
        ``(routed row, channel)``.  The routing weight is that -- six binary32
        numbers, one for each expert this token selected, multiplying six
        2,048-wide rows -- and the engines that take a second operand require it
        to cover the trailing axes rather than a prefix of them, so the value is
        broadcast along the channels with a zero stride and again nothing is
        copied.

        ``scale_factor`` says the operand is ``VECTOR.SCALE``'s ``input_view_1``,
        which is the *same* statement without the routed block: the elementwise
        sub-case requires the factor's extents to equal the value's trailing
        extents and there is no column-vector rule, so a factor the graph states
        as one number per row is presented at the value's own shape with a
        stride of zero on every axis but the first.  DeepSeek's sampling
        temperature is one number against ``[1, 129280]`` logits and reaches
        this by that route rather than through a routed block.
        ``compiler/backends/hbm_sram/lower.py::_row_broadcast`` is the same
        rule, gated the same way -- on the operator's own row, not on a
        per-token block.
        """
        principal = list(shape.principal)
        if shape.row_symbolic and principal:
            block = (
                shape.rows
                if shape.per_token or shape.batch_multiplier > 1
                else shape.block
            )
            principal[0] = min(block, principal[0])
        if (
            shape.per_token or shape.batch_multiplier > 1 or scale_factor
        ) and len(principal) > 1:
            elements = 1
            for extent in dims:
                elements *= extent
            if elements == principal[0] and list(dims) != principal:
                return (
                    list(principal),
                    [1, *([0] * (len(principal) - 1))],
                )
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
        stride: int = 1,
        modulus: int | None = None,
        divisor: int | None = None,
    ) -> int:
        """A movement's index vector: one index per row the movement touches.

        Absolute when what it addresses is indexed by position -- a rotary table
        spans every admissible position, a KV window every row of the context --
        and span-relative when it addresses the request's own rows.  Selecting
        the final row of a span is ``SPAN_LAST_INDEX``; a view offsets by
        ``selector * stride`` and cannot compute ``span - 1`` for itself.

        ``stride`` is how many positions one row of the movement advances.  It
        is one wherever a movement touches consecutive rows, and a pooled row
        that stands for several positions declares the number it stands for; a
        view whose element stride says so reaches the same range without an
        index vector anyone has to materialise.  The stride multiplies the loop
        induction too, because a block of rows spans ``block * stride``
        positions rather than ``block`` of them.
        """
        tensor = self.tensors[name]
        if stride < 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: index stride {stride} is not "
                "positive"
            )
        if modulus is not None and divisor is not None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: an index map cannot be both "
                "modular and floor-divided"
            )
        floor_object = self._floor_div_object(divisor) if divisor is not None else None
        # A compressed output contributes one row per ``divisor`` positions.
        # Exporters may leave the default stride of one or state that ratio
        # explicitly; both describe the same quotient-table sampling and must
        # not be multiplied into ratio squared.
        if floor_object is not None and stride not in {1, divisor}:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: floor-div row map with divisor "
                f"{divisor} declares incompatible position_stride {stride}"
            )
        table_stride = divisor if floor_object is not None else stride
        terms: list[DynamicTerm] = []
        if absolute:
            terms.append(DynamicTerm.symbol(Symbol.POSITION_START, 1))
            if loop is not None and shape.row_symbolic:
                terms.append(DynamicTerm.loop(loop, shape.block * table_stride))
        elif count == 1:
            terms.append(DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX, 1))
        elif loop is not None and shape.row_symbolic:
            terms.append(DynamicTerm.loop(loop, shape.block * stride))
        dtype = self._dtype(tensor.dtype)
        if name in self._position_inputs:
            if floor_object is not None:
                object_id = floor_object
            elif modulus is not None:
                object_id = self._ring_object(modulus)
            else:
                object_id = self._position_object(name)
            permissions = int(Permission.READ)
            # The materialised range is ``arange_u32_v1``, so the view over it
            # is U32 whatever word the graph used for "an integer position".  A
            # graph that declares the offset as I32 is not declaring a second
            # object with a second element type; ABI 3.0 indices are unsigned
            # because a negative position is meaningless, and reading the same
            # bytes through a signed view is how a movement's index came out
            # refused for a difference that does not exist.
            dtype = DType.U32
        else:
            object_id = self._buffer(name)
            permissions = int(Permission.READ)
            if tensor.role in {"input", "output"}:
                permissions |= int(Permission.HOST_VISIBLE)
        # Amendment A18: ``count`` is in the principal's axis units, so the
        # index vector is shortened in those units too -- one index per row the
        # movement touches, and a compressor's row is a group of four tokens.
        # Declared only alongside the loop term that resolves it, which is what
        # the amendment's third admission rule requires.
        walked = any(t.kind == int(SelectorKind.LOOP_INDUCTION) for t in terms)
        return self._view(
            object_id=object_id,
            dtype=dtype,
            dims=[max(count, 1)],
            strides=[table_stride],
            dynamic=terms,
            permissions=permissions,
            extent_unit=shape.axis.unit if walked else 0,
            extent_numerator=shape.axis.numerator if walked else 0,
            extent_bias=shape.axis.bias if walked else 0,
            label="view.index",
        )

    # -- REDUCTION.EXPERT_SUM --------------------------------------------
    def _expert_sum_slots(self, kernel: Kernel) -> tuple[str, str | None, str | None]:
        """Which neutral operand fills which slot of the frozen EXPERT_SUM row.

        ``TA-ABI3-OPCONV-1`` section 6 reads (contributions, weights, optional
        base), and amendment A10 makes the weights optional: an operator that
        omits ``input_view_1`` declares the weight was applied earlier, which is
        exactly what the released DeepSeek expert does -- it multiplies by the
        routing weight before its down projection, so re-applying it at the
        reduction would square it.

        The neutral IR says which convention is in force rather than the
        backend guessing.  A ``base_operand_index`` attribute names the base
        operand, and a graph that names one has already applied its weights.
        Everything else this kernel reads -- the routed rows' expert identity,
        for one -- is a dataflow fact the ABI row has no slot for, so it is
        dropped here rather than bound to the base slot it would otherwise
        silently occupy with 32-bit integers.
        """
        attributes = kernel.attributes
        contributions = kernel.inputs[0]
        declared = attributes.get("base_operand_index")
        if declared is not None:
            index = int(declared)
            if not 1 <= index < len(kernel.inputs):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} names base operand {index}, "
                    f"which is not one of its {len(kernel.inputs)} inputs"
                )
            return contributions, None, kernel.inputs[index]
        if len(kernel.inputs) > 1:
            weights = self.tensors[kernel.inputs[1]]
            if weights.dtype not in {"u32", "i32", "i64"}:
                return contributions, kernel.inputs[1], None
        return contributions, None, None

    def _expert_sum_geometry(self, kernel: Kernel) -> tuple[int, int, int]:
        """One token's contribution count, its width, and the output width.

        The contribution axis is never the token axis, and the neutral IR
        states it two ways.  The mHC branch reduction declares
        ``[tokens, streams, width]``, so the count is the second axis; the MoE
        reduction declares ``[top_k * tokens, width]`` -- a multiplied symbolic
        extent -- so the count is the multiplier.  Both are read off the
        operand rather than from a name.
        """
        contributions = self.tensors[kernel.inputs[0]]
        dims = self._dims(contributions)
        _symbol, multiplier, _axis = self._leading_symbol(contributions)
        trailing = 1
        for extent in dims[1:]:
            trailing *= extent
        if multiplier > 1:
            count, width = multiplier, trailing
        elif len(dims) > 2:
            count = dims[1]
            width = trailing // max(dims[1], 1)
        else:
            count, width = 1, trailing
        out = self.tensors[kernel.outputs[0]] if kernel.outputs else contributions
        out_width = 1
        for extent in self._dims(out)[1:]:
            out_width *= extent
        return max(count, 1), max(width, 1), max(out_width, 1)

    def _open_token_loop(self, kernel: Kernel) -> int:
        """One iteration per token, for a reduction across a non-token axis.

        ``REDUCTION.EXPERT_SUM`` reduces the *leading* axis of ``in0`` and takes
        one weight per leading index.  Every reduction in either graph reduces
        an axis that is not the token axis and weights it per token, so the
        descriptor that says what the operator means presents one token: ``[c,
        width]`` contributions against ``[c]`` weights.  The loop that walks the
        tokens therefore has ``bound_divisor = 1``, and amendment A13's clamp
        correctly does not reach it -- the loop steps by one token's row, not by
        one whole block of the leading axis, which is the condition the resolver
        and the verifier both derive.

        The cost is one dispatch per token for this one operator.  It is bounded
        by the capability's own loop maximum: a span longer than
        ``max_loop_trip`` fails closed at the device with a trip-count trap
        rather than reducing the wrong number of tokens.
        """
        symbol = Symbol.SPAN_TOKENS
        unit = 1
        if kernel.outputs:
            named, multiplier, named_axis = self._leading_symbol(
                self.tensors[kernel.outputs[0]]
            )
            if named is not None and multiplier == 1:
                symbol, unit = Symbol(named), named_axis.unit
        trip = max(
            min(
                self._symbolic_row_bound(kernel, int(symbol), unit),
                int(self.capability.limits["max_loop_trip"]),
            ),
            1,
        )
        loop = self.builder.loop_control(
            lower_bound=0,
            upper_bound=trip,
            step=1,
            max_iterations=trip,
            bound_symbol=symbol,
            # One iteration is one element of the blocked axis, which is
            # ``unit`` of the symbol's own units -- one token, or one compressed
            # group of four.  A18's walk test needs the divisor to be a whole
            # number of axis elements, and A13's ``bound_divisor = 1`` is this
            # with a unit of one.
            bound_divisor=unit,
            counter_class_id=self._counter_class("instruction", Major.CONTROL),
            key=f"loop.token.k{kernel.index:05d}",
        )
        self.builder.open_loop(loop)
        return loop

    def _emit_routed_row_identity(
        self, kernel: Kernel, shape: KernelShape, loop: int | None
    ) -> None:
        """Materialise the routed-row expert identity a dispatch declares.

        The neutral ``EXPERT_DISPATCH`` kernel declares two results: the
        dispatched activations and, per its ``routed_row_expert_output``
        attribute, which expert each routed row belongs to.  The frozen
        ``ROUTE.EXPERT_DISPATCH`` writes only the first -- section 5's row has
        one output -- so the second has to be stated separately or the routed
        matmul downstream reads an unwritten buffer and contracts every row
        against expert zero, which no check would catch.

        It is a movement, not a computation: routed row ``6t + k`` belongs to
        expert ``ids[t, k]``, which is the dispatch's own ID operand read in
        routed-row order, the same bytes in the same order.  Flattening the
        request's whole ID matrix says exactly that and preserves the same
        whole-span routed batch as the dispatch output it describes.
        """
        ids = self.tensors[kernel.inputs[1]]
        routed = self.tensors[kernel.outputs[1]]
        slots = 1
        for extent in self._dims(ids)[1:]:
            slots *= extent
        rows = shape.rows
        step = self._axis_step(shape, shape.axis) * slots
        multiplied = shape.batch_multiplier > 1 and loop is not None

        def flattened(tensor: Tensor, *, writable: bool) -> int:
            return self._buffer_view(
                tensor,
                dims=[rows],
                strides=[1],
                shape=shape,
                loop=loop,
                writable=writable,
                blocked=False,
                term=(
                    DynamicTerm.loop(loop, step) if loop is not None else None
                ),
                extent_unit=shape.axis.unit if multiplied else 0,
                extent_numerator=(
                    shape.axis.numerator * shape.batch_multiplier
                    if multiplied
                    else 0
                ),
                extent_bias=shape.axis.bias if multiplied else 0,
            )

        self._emit_operator(
            kernel,
            Major.DMA,
            int(Dma.TRANSFER),
            [flattened(ids, writable=False)],
            [flattened(routed, writable=True)],
            loop=None,
            schedule_rows=rows,
            suffix=".ids",
        )

    def _is_row_local_gather(self, kernel: Kernel, sub: int) -> bool:
        """Does this gather address *inside* a row rather than across rows?

        ``DMA.GATHER`` moves whole rows of its source: ``out[i] = src[idx[i]]``.
        Two different movements in this graph spell themselves ``GATHER``.  The
        rotary coefficient gather is the row form -- its source is a constant
        table with no token axis, and each index names a table row.  The routing
        weight gather is not: ``gathered[t, k] = scores[t, ids[t, k]]`` picks one
        element *within* token ``t``'s own score row, and the index values run
        over the 256 experts rather than over the tokens.

        The operands say which it is.  A source whose leading axis is the same
        span symbol the index carries is addressed within a row, because its
        rows are the request's tokens and the index is not a token number.  That
        form is emitted one token at a time -- the source view is that token's
        row, the index view that token's slots -- which is the frozen row form
        applied to one row, not a second kind of movement.
        """
        if sub != int(Dma.GATHER) or len(kernel.inputs) < 2 or not kernel.outputs:
            return False
        source = self.tensors[kernel.inputs[0]]
        index = self.tensors[kernel.inputs[1]]
        if index.dtype not in INDEX_DTYPES:
            return False
        source_symbol, source_multiplier, _ = self._leading_symbol(source)
        index_symbol, index_multiplier, _ = self._leading_symbol(index)
        return (
            source_symbol is not None
            and source_symbol == index_symbol
            and source_multiplier == index_multiplier == 1
            and len(self._dims(source)) == 2
            and len(self._dims(index)) == 2
        )

    def _row_local_gather_views(
        self, kernel: Kernel, shape: KernelShape, loop: int
    ) -> tuple[list[int], list[int]]:
        """One token's operands for a within-row gather."""
        source = self.tensors[kernel.inputs[0]]
        index = self.tensors[kernel.inputs[1]]
        result = self.tensors[kernel.outputs[0]]

        def per_token(tensor: Tensor, *, writable: bool) -> int:
            width = 1
            for extent in self._dims(tensor)[1:]:
                width *= extent
            return self._buffer_view(
                tensor,
                dims=[width],
                strides=[1],
                shape=shape,
                loop=loop,
                writable=writable,
                blocked=False,
                term=DynamicTerm.loop(loop, width),
            )

        # TA-ABI3-OPCONV-1 section 7: the index is in0 and the source in1.
        return (
            [per_token(index, writable=False), per_token(source, writable=False)],
            [per_token(result, writable=True)],
        )

    def _expert_sum_views(
        self,
        kernel: Kernel,
        shape: KernelShape,
        run: LayerRun | None,
        loop: int,
    ) -> tuple[list[int], list[int]]:
        """One token's operands for ``REDUCTION.EXPERT_SUM``."""
        count, width, out_width = self._expert_sum_geometry(kernel)
        contributions, weights, base = self._expert_sum_slots(kernel)

        def per_token(name: str, dims: Sequence[int], *, writable: bool) -> int:
            tensor = self.tensors[name]
            stride = 1
            for extent in dims:
                stride *= extent
            return self._buffer_view(
                tensor,
                dims=list(dims),
                strides=self._row_major_strides(dims),
                shape=shape,
                loop=loop,
                writable=writable,
                blocked=False,
                term=DynamicTerm.loop(loop, stride),
            )

        inputs = [per_token(contributions, [count, width], writable=False)]
        if weights is not None:
            span = 1
            for extent in self._dims(self.tensors[weights])[1:]:
                span *= extent
            inputs.append(per_token(weights, [max(span, 1)], writable=False))
        elif base is not None:
            inputs.append(NO_ID)
        if base is not None:
            inputs.append(per_token(base, [out_width], writable=False))
        outputs = [per_token(kernel.outputs[0], [out_width], writable=True)]
        return inputs, outputs

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
        context: int | None = None,
        leading_extent: int | None = None,
    ) -> int:
        tensor = self.tensors[name]
        writable = direction == "out"
        # A declared state effect is the authority: a kernel that writes a state
        # resource writes into that resource's prepared image, even when the
        # graph names the result as an ordinary activation.
        if tensor.role == "state" or (writable and kernel.state_writes):
            plane_axis = IDENTITY_AXIS
            terms: tuple[DynamicTerm, ...] = ()
            if context is not None:
                symbol, _multiplier, declared = self._leading_symbol(tensor)
                if symbol is not None and not declared.is_identity:
                    plane_axis = declared
                    terms = (
                        DynamicTerm.loop(
                            context,
                            self._plane_row(tensor) * self._dims(tensor)[0],
                        ),
                    )
            view = self._state_plane_view(
                kernel,
                name,
                direction,
                run,
                extent_unit=plane_axis.unit if terms else 0,
                extent_numerator=plane_axis.numerator if terms else 0,
                extent_bias=plane_axis.bias if terms else 0,
                extra_terms=terms,
            )
            if view is not None:
                return view
        if tensor.role in WEIGHT_ROLES:
            # The route table ships as int64 and every reader of it -- the
            # engine, the result tensor, the released model's own use of it --
            # is 32-bit, so the table is *read* through a U32 view over the
            # same bytes.  The graph says which tables those are, by name of
            # the reading, in ``table_element_reading``.
            #
            # This was keyed on ``kind == "HASH_ROUTE"`` and the exporter then
            # correctly renamed that kind to the exact row gather it always
            # was.  The narrowing silently stopped applying, and the lane
            # stopped 5,247 instructions short of its retained baseline on an
            # I64 table written into a U32 result.  A numeric narrowing is a
            # property of the data, never of the operator's name; keying it on
            # a different name would only move the same defect.
            return self._weight_view(
                name,
                run=run,
                shape=shape,
                slot=slot,
                bank=self._expert_bank_extent(kernel, tensor),
                narrow_dtype=self._narrowed_read(kernel, tensor),
            )
        if kernel.kind == "ROUTED_MATMUL" and tensor.dtype in INDEX_DTYPES:
            # TA-ABI3-OPCONV-1 section 2: the expert-ID operand is
            # ``[rows, topk]``.  DeepSeek resolves the routing *before* the
            # contraction -- ``ROUTE.EXPERT_DISPATCH`` has already made six
            # rows of one token, each belonging to exactly one expert -- so the
            # graph carries one ID per row and ``topk`` is one.  That is the
            # frozen matrix with a single column, not a different operand: the
            # engine's slot loop runs once and there is nothing to combine,
            # which is precisely what a pre-dispatched row means.
            rows = self._blocked_dims(tensor, shape)
            if len(rows) == 1:
                return self._buffer_view(
                    tensor,
                    dims=[rows[0], 1],
                    strides=[1, 1],
                    shape=shape,
                    loop=loop,
                    writable=writable,
                )
        if kernel.kind in BATCH_LEADS_KINDS:
            # The batch leads at extent one and the request moves axis 1.  The
            # weights of a state update -- its position embedding -- are
            # ``[ratio, W]`` with no batch axis and have already returned
            # through the weight branch above.
            dims, strides = self._batch_leads(tensor, shape)
            if leading_extent is not None and len(dims) > 1:
                dims[1] = min(int(leading_extent), dims[1])
            return self._buffer_view(
                tensor,
                dims=dims,
                strides=strides,
                shape=shape,
                loop=loop,
                writable=writable,
                extent_axis=1,
            )
        if kernel.kind in TOKEN_AS_BATCH_KINDS:
            # The operand row states a batch axis the graph does not declare.
            # See TOKEN_AS_BATCH_KINDS: the weights of a compressor projection
            # are ``[N, K]`` with no batch axis at all, and they have already
            # returned through the weight branch above, so only the activation
            # operands reach here.
            dims, strides = self._token_as_batch(tensor, shape)
            if leading_extent is not None and dims:
                dims[0] = min(int(leading_extent), dims[0])
            return self._buffer_view(
                tensor,
                dims=dims,
                strides=strides,
                shape=shape,
                loop=loop,
                writable=writable,
            )
        if name in self._position_inputs:
            # The request's position range is a bound symbol, not host data:
            # every operand that reads it reads the same materialised range
            # offset by POSITION_START, whether it indexes a movement or places
            # attention's causal horizon.
            return self._index_view(
                kernel,
                shape,
                name,
                loop,
                count=(int(leading_extent) if leading_extent is not None else shape.rows),
                absolute=True,
            )
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
        if leading_extent is not None and dims:
            symbol, _multiplier, _axis = self._leading_symbol(tensor)
            if symbol is not None:
                dims[0] = min(int(leading_extent), dims[0])
        element_offset = 0
        narrowed = self._quantized_prefix(kernel, dims, slot=slot, direction=direction)
        if narrowed is not None:
            return self._buffer_view(
                tensor,
                dims=narrowed[0],
                strides=narrowed[1],
                shape=shape,
                loop=loop,
                writable=writable,
            )
        if direction == "in" and kernel.kind == "BROADCAST":
            broadcast_dims, broadcast_strides = self._inserted_broadcast_axis(
                kernel, dims
            )
        elif direction == "in" and kernel.kind == "SELECT":
            broadcast_dims, broadcast_strides, element_offset = self._selected_plane(
                kernel, dims
            )
        elif (
            direction == "in"
            and slot > 0
            and tensor.dtype not in INDEX_DTYPES
        ):
            # An index is not broadcast.  ``_broadcast`` inserts the principal's
            # missing middle axes at stride zero so that a coefficient row held
            # per *token* reaches a tensor held per ``(token, head)``; that is a
            # statement about values every head shares.  An index array names
            # rows, and the operand rows that read it say how many -- amendment
            # A6's sparse index is ``[span, slots]`` and stays rank two however
            # many heads the query has.  Widening it produced a rank-three index
            # the attention engine correctly refused.
            broadcast_dims, broadcast_strides = self._broadcast(
                dims,
                shape,
                scale_factor=(
                    family is Major.VECTOR
                    and sub == int(Vector.SCALE)
                    and slot == 1
                ),
            )
        else:
            broadcast_dims, broadcast_strides = dims, None
        multiplied_broadcast = (
            shape.batch_multiplier > 1
            and broadcast_strides is not None
            and bool(dims)
            and bool(broadcast_dims)
            and broadcast_dims[0] != dims[0]
        )
        return self._buffer_view(
            tensor,
            dims=broadcast_dims,
            strides=broadcast_strides,
            element_offset=element_offset,
            shape=shape,
            loop=loop,
            writable=writable,
            # A routed weight is stored as ``[span, top_k]`` but presented as
            # one value per row of ``[top_k * span, width]``.  The clamped axis
            # belongs to that presented view, so its affine numerator is
            # ``top_k`` even though the underlying tensor leads with plain
            # ``span``.  Its row term already advances by ``top_k`` values.
            extent_unit=shape.axis.unit if multiplied_broadcast else None,
            extent_numerator=(
                shape.axis.numerator * shape.batch_multiplier
                if multiplied_broadcast
                else 0
            ),
            extent_bias=shape.axis.bias if multiplied_broadcast else 0,
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
        group_rows: int = 0,
        group: int = 0,
        bank: int = 0,
        narrow_dtype: DType | None = None,
        row_step: int = 1,
    ) -> int:
        """One weight operand's view.

        ``group_rows`` narrows the view to one block-diagonal group of a
        feature-grouped contraction: the same reduction width, ``group_rows``
        of the ``N`` axis, starting ``group * group_rows`` rows in.  The offset
        is stated in the view rather than performed by a movement, and it lands
        on a whole scale block because the group boundary is a multiple of the
        block-scale row tiling -- amendment A15's addressing reads the block
        index straight off ``element_offset``.

        ``bank`` is a routed contraction's expert extent.  Its weight is one
        operand holding every expert's matrix, so the operand is ``[E, N, K]``
        and the expert is chosen by the engine inside the view.  Folding it to
        ``[N, K]`` like every other contraction weight does not lose a
        description, it loses 255 of the 256 experts.
        """
        if self.plan is None:  # pragma: no cover - programming error
            raise RomLoweringError("plan_regions() must run before lowering")
        tensor = self.tensors[tensor_id]
        dims: Sequence[int] = self._dims(tensor)
        strides: Sequence[int] | None = None
        group_offset = 0
        if int(row_step) < 1:
            raise RomLoweringError(
                f"weight {tensor_id!r} row step {row_step} is not positive"
            )
        if shape is not None and shape.contraction and slot == 1 and len(dims) >= 2:
            # TA-ABI3-OPCONV-1 section 2: in1 is ``[N, K]``.  A checkpoint that
            # stores ``[K, N]`` is presented n-major by swapping the view's
            # strides -- a description, never a relayout pass.
            dims = [shape.cols, shape.depth]
            strides = [1, shape.cols] if shape.transposed else [shape.depth, 1]
            if group_rows:
                if shape.transposed:
                    raise RomLoweringError(
                        f"weight {tensor_id!r} is stored K-major, so a grouped "
                        "row range is not a contiguous element offset; the "
                        "group would have to be a stride, which a view's "
                        "leading axis already is"
                    )
                dims = [group_rows, shape.depth]
                group_offset = group * group_rows * shape.depth
            if bank:
                if group_rows:
                    raise RomLoweringError(
                        f"weight {tensor_id!r} is a routed expert bank and a "
                        "feature-grouped operand at once; the leading axis "
                        "cannot be both the expert and the group"
                    )
                # The expert is the outermost axis of the stack, so its stride
                # is the whole matrix each expert holds -- whichever way that
                # matrix itself is stored.
                dims = [bank, *dims]
                strides = [shape.cols * shape.depth, *strides]
        if int(row_step) != 1:
            if len(dims) < 2:
                raise RomLoweringError(
                    f"weight {tensor_id!r} needs a rank-two row space for "
                    f"row step {row_step}"
                )
            if strides is None:
                strides = self._row_major_strides(dims)
            strides = list(strides)
            strides[0] *= int(row_step)
            dims = [
                (int(dims[0]) + int(row_step) - 1) // int(row_step),
                *dims[1:],
            ]
        # A narrowed view reads the *same bytes* through a smaller element
        # type.  The int64 route table holds expert IDs below 256, so each of
        # its little-endian words is a U32 followed by a zero U32, and a view
        # with twice the stride reads exactly the value the engine wants -- a
        # description, never a conversion pass, the same reasoning that
        # presents a K-major weight n-major by swapping strides.
        ratio = 1
        if narrow_dtype is not None:
            wide = DTYPE_BITS[self._dtype(tensor.dtype)]
            narrow = DTYPE_BITS[narrow_dtype]
            if narrow > wide or wide % narrow:
                raise RomLoweringError(
                    f"weight {tensor_id!r} is {wide}-bit and cannot be read "
                    f"through a {narrow}-bit view"
                )
            ratio = wide // narrow
            if strides is None:
                strides = self._row_major_strides(dims)
            strides = [extent * ratio for extent in strides]
            group_offset *= ratio
        generated = self._generated_object(tensor_id)
        if generated is not None:
            # A derived constant has one mask-programmed object of its own and
            # no per-layer striping, so the view is the whole table.
            return self._view(
                object_id=generated,
                dtype=narrow_dtype or self._dtype(tensor.dtype),
                dims=dims,
                strides=strides,
                element_offset=group_offset,
                permissions=int(Permission.READ),
                label="view.rom.generated",
            )
        key, region_slot = self._region_of_tensor[tensor_id]
        region = self.plan.region(key)
        dtype = narrow_dtype or self._dtype(tensor.dtype)
        dynamic: list[DynamicTerm] = []
        element_offset = 0
        if region.slot_count > 1:
            if run is None:
                raise RomLoweringError(
                    f"weight {tensor_id!r} lives in the layer-striped region "
                    f"{key!r} but is read outside a compressed layer body"
                )
            loop = self._loop_of_run[run.index]
            stride = region.slot_element_stride * ratio
            if stride > 0xFFFFFFFF:
                raise RomLoweringError(
                    f"region {key!r} needs a per-layer element stride of {stride}, "
                    "which does not fit the 32-bit dynamic-term stride field of "
                    "ABI 3.0 tensor views; split the region"
                )
            dynamic.append(DynamicTerm.loop(loop, stride))
        else:
            element_offset = region_slot * region.slot_element_stride * ratio
        element_offset += group_offset
        scale_object, block, row_block = self._scale_binding(key)
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
            scale_block_rows=row_block,
            label="view.rom",
        )

    def _scale_binding(self, region_key: str) -> tuple[int, int, int]:
        """The immutable block-scale object that scales ``region_key``."""
        if self.plan is None or region_key not in self._scale_of_region:
            return NO_ID, 0, 0
        scale_key, block, row_block = self._scale_of_region[region_key]
        if not block:
            return NO_ID, 0, 0
        return self.plan.region(scale_key).object_id, block, row_block

    # -- operand conventions (TA-ABI3-OPCONV-1) --------------------------
    def _index_topk_capacity(self, kernel: Kernel) -> int:
        """``ROUTE.INDEX_TOPK``'s ``aux_id_0``: the compressed segment's width.

        A19's caution, restated by A20 for both operand rows and the one that
        bites: ``aux0`` is the segment, never the whole joined operand.  A
        backend that copies the output's last extent into it declares ``W + k``
        where ``k`` belongs, and the engine refuses -- ``ROUTE.INDEX_TOPK
        selects 2176 positions and joins a 128-slot window into 2176 slots``.
        The graph states the number (``top_k`` ranked, ``k`` dense), and the
        derivation A20 gives for a ``NO_ID`` ``aux0`` -- the output's slots
        minus the joined window's width -- is what stands in when it does not.

        ``compiler/backends/hbm_sram/plan.py::_index_topk_capacity`` is the same
        rule.  It was not: this lane read ``k`` and that one read ``top_k``,
        which agreed on the ranked kernels because they declare both and
        disagreed on the dense ones, which declare only ``k``.
        """
        slots = (
            self._dims(self.tensors[kernel.outputs[0]])[-1] if kernel.outputs else 0
        )
        order = self._operand_order(kernel, Major.ROUTE, int(Route.INDEX_TOPK))
        slot_map = self._abi_input_slots(kernel, order)
        window = 0
        if len(slot_map) > 1 and slot_map[1] is not None:
            window = self._dims(self.tensors[kernel.inputs[slot_map[1]]])[-1]
        return index_topk_capacity(kernel, slots, window)

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
                # TA-ABI3-OPCONV-1 section 3: ``aux0`` is the sub-case,
                # ``aux1`` the compression ratio and ``aux2`` the runtime symbol
                # holding the start position.  ``aux1`` is not decoration -- the
                # pool and the state update read the ratio to know how many
                # candidates a group pools and whether the groups overlap, and
                # the engine refuses any value that is not a pinned ratio.
                # ``aux2`` is what makes the operator's prefill-only guard real:
                # the compressor's raw slots roll on the decode path and this
                # operator's arity does not bind them, so an unbound ``aux2``
                # would let a decode step read the guard as position zero and
                # execute anyway.
                ratio = int(attributes.get("ratio", 0))
                if ratio not in PINNED_COMPRESSION_RATIOS:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r} declares compression ratio "
                        f"{attributes.get('ratio')!r}; VECTOR.COMPRESS pins the "
                        f"ratio to one of {sorted(PINNED_COMPRESSION_RATIOS)}"
                    )
                return [
                    COMPRESS_SUBCASE[kernel.kind],
                    ratio,
                    int(Symbol.POSITION_START),
                ]
            if sub == int(Vector.MHC):
                return [
                    MHC_SUBCASE[kernel.kind],
                    int(attributes.get("sinkhorn_iterations", 0)),
                    int(attributes.get("hc_mult", 1)),
                ]
            if sub == int(Vector.SCALE):
                # ``VECTOR.SCALE`` has three sub-cases and the kind name
                # settles only two of them.  A kernel named ``SCALE`` that
                # binds a second operand is the elementwise product, not a
                # constant scale: the engine refuses sub-case 0 with
                # ``input_view_1`` bound, and it is right to -- the constant is
                # in the numeric profile and the operand would be ignored.  The
                # operand map is the authority.  DeepSeek's sampling
                # temperature is the case: ``main.sample.temperature`` is a
                # ``SCALE`` reading the logits and the request's temperature,
                # and the kind-only table sent it to sub-case 0 --
                # ``VECTOR.SCALE sub-case 0 (multiply by the profile's
                # scale_bits) does not read input_view_1, but one is bound``.
                # ``compiler/backends/hbm_sram/plan.py`` states the same rule;
                # this lane did not, which is why only this lane stopped.
                if len(kernel.inputs) >= 2:
                    return [1]
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
            if sub == int(Attention.SPARSE):
                # SPARSE takes a *fused* rank-2 KV, [kv_rows, head_dim], so its
                # axis 1 is a head width and not a head count -- reading it gave
                # 512 and a group size of 64 // 512, which the engine then
                # refused ("the group size is 64; the operator declares 1").
                # The fused form has one KV head by construction.
                kv_heads = int(
                    domain.get("key_value_heads", 0) or domain.get("kv_heads", 0) or 1
                )
            else:
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
                    self._index_topk_capacity(kernel),
                    0 if attributes.get("mask_mode", "causal") == "causal" else 1,
                    int(Symbol.CONTEXT_LENGTH),
                    int(Symbol.POSITION_START),
                ]
            if sub == int(Route.WINDOW_INDEX):
                family = str(attributes.get("index_family", ""))
                if family and family not in IMPLEMENTED_INDEX_FAMILIES:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r} declares index family "
                        f"{family!r}, which this backend does not implement.  "
                        "It lowers to ROUTE.WINDOW_INDEX, and that operator "
                        "emits arange(first, last + 1) over the absolute "
                        "positions of a causal window, tail-padded -- a "
                        "position list, not the enumeration this family names. "
                        " No engine reads index_family, so the substitution "
                        "would produce legal KV rows and nothing downstream "
                        "could refuse them.  The frozen families are "
                        f"{', '.join(sorted(IMPLEMENTED_INDEX_FAMILIES))}"
                    )
                # ``window_size`` is the name both exporters use; ``window``
                # was read here and is declared by neither, so every window
                # index fell through to the 128 default and was right only
                # because 128 is what the released model uses.  A model with a
                # different window would have got 128 with nothing to say so.
                return [
                    int(
                        attributes.get(
                            "window",
                            attributes.get(
                                "window_size", domain.get("window", 128)
                            ),
                        )
                    ),
                    0 if attributes.get("mask_mode", "causal") == "causal" else 1,
                    int(Symbol.CONTEXT_LENGTH),
                ]
            return []
        if family is Major.REDUCTION and sub == int(Reduction.PARTITION_SUM):
            return [int(Symbol.VOCABULARY_PARTITIONS)]
        if family is Major.REDUCTION and sub == int(Reduction.GROUPED_CONCAT):
            # Amendment A17: a concatenation states the axis it joins.  The
            # graph says which axis, and it is not always zero -- an index
            # window joined to a compressed-index block joins on the feature
            # axis, and axis 0 could not express it at all because the two
            # operands have different widths.
            return [int(attributes.get("axis", 0))]
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

        The hyper-connection rows need it by name.  ``VECTOR.MHC`` reads
        ``(hidden, fn, base, scale)``; both exporters emit
        ``(hidden, fn, scale, base)``, following the released module's own
        argument order.  The neutral IR fixes *which* tensors an operation
        reads and the convention fixes *which slot* each occupies, so the
        reconciliation is a backend's job -- the same reasoning as amendment
        A11's ``KV_APPEND`` permutation.
        """
        order = list(range(len(kernel.inputs)))
        permutation = _SLOT_PERMUTATION.get(kernel.kind)
        if permutation is not None and len(order) == len(permutation):
            return [order[slot] for slot in permutation]
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

    def _abi_input_slots(
        self, kernel: Kernel, order: Sequence[int]
    ) -> list[int | None]:
        """The IR input each ABI input slot carries; ``None`` for a declared hole."""
        return abi_input_slots_of(kernel, order)

    def _movement_views(
        self,
        kernel: Kernel,
        shape: KernelShape,
        order: Sequence[int],
        run: LayerRun | None,
        loop: int | None,
        sub: int,
        leading_extent: int | None = None,
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
            symbol, _, _ = self._leading_symbol(subject)
            absolute = symbol is None
        # One index per row the movement touches: the rows it writes for a
        # gather, the rows it reads for a scatter.
        counted = addressed if gather else source_name
        count = 1
        if counted is not None:
            count = max(
                int(leading_extent)
                if leading_extent is not None
                else self._blocked_dims(self.tensors[counted], shape)[0],
                1,
            )
        views = [
            self._index_view(
                kernel,
                shape,
                index_name,
                loop,
                count=count,
                absolute=absolute,
                stride=int(kernel.attributes.get("position_stride", 1)),
                modulus=self._cache_row_modulus(kernel),
                divisor=self._cache_row_divisor(kernel),
            )
        ]
        if source_name is not None:
            if gather:
                # A gather addresses arbitrary rows of its source, so the source
                # presents its whole declared extent rather than one block.  It
                # may well be immutable -- a rotary coefficient table is a mask
                # ROM constant -- so it resolves the same way any weight does.
                tensor = self.tensors[source_name]
                if tensor.role in WEIGHT_ROLES:
                    views.append(self._weight_view(source_name, run=run))
                else:
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
                        leading_extent=leading_extent,
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
                    leading_extent=leading_extent,
                )
            )
        return views, outputs

    def _feature_group_count(
        self, kernel: Kernel, family: Major, sub: int, shape: KernelShape
    ) -> int:
        """How many *feature* groups a grouped contraction splits into.

        There are two grouped contractions and they are different operators.
        ABI 3.0's ``TENSOR.GROUPED_MATMUL`` is the ragged-row one: ``input 2``
        is a per-group row count, the groups partition the activation *rows* in
        ascending order, and every group shares one reduction width and one
        output width (``runtime/sim/engines/tensor.py``, and
        TA-ABI3-OPCONV-1 section 2's "group index").  DeepSeek's grouped output
        projection is the block-diagonal one --
        ``einsum("bsgd,grd->bsgr")`` in the released ``Attention.forward`` --
        where group ``g`` reads its own 4,096 columns of a 32,768-wide
        activation and writes its own 1,024 columns of an 8,192-wide result,
        and *every* token passes through *every* group.

        No row partition of a token-major buffer presents the second as the
        first.  Group ``g`` would own the rows ``{t * G + g}``, which are
        strided by the group count, and a rank-2 view has one row stride; the
        group-major order that would make them contiguous needs a group stride
        of ``span * width``, and ``span`` is a runtime symbol, not a static
        stride.

        ABI 3.0 expresses the block-diagonal form exactly, and with no
        amendment: it is one ``TENSOR.MATMUL`` per group over views that offset
        into the shared operands.  That is what
        :meth:`_emit_feature_grouped_contraction` emits.  This returns the
        group count when the kernel is that form, and ``1`` otherwise -- a
        ragged-row grouped matmul still lowers to ``TENSOR.GROUPED_MATMUL``.
        """
        if family is not Major.TENSOR or sub != int(TensorOp.GROUPED_MATMUL):
            return 1
        if not shape.contraction or len(kernel.inputs) < 2 or not kernel.outputs:
            return 1
        declared = (
            kernel.attributes.get("groups")
            or kernel.attributes.get("group_count")
            or kernel.iteration_domain.get("groups")
            or 0
        )
        groups = self._extent(declared) if declared else 0
        if groups <= 1:
            return 1
        activation = self.tensors[kernel.inputs[0]]
        width = 1
        for extent in self._dims(activation)[1:]:
            width *= extent
        if width != groups * shape.depth:
            # The activation carries one reduction width, so the groups are a
            # row partition after all and the frozen operator says it.
            return 1
        if shape.cols % groups:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares {groups} feature groups "
                f"but a result width of {shape.cols}, which is not a whole "
                "number of groups"
            )
        out_width = 1
        for extent in self._dims(self.tensors[kernel.outputs[0]])[1:]:
            out_width *= extent
        if out_width != shape.cols:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} is a {groups}-group block-diagonal "
                f"contraction writing {shape.cols} columns, but its result is "
                f"{out_width} wide"
            )
        return groups

    def _emit_feature_grouped_contraction(
        self, kernel: Kernel, shape: KernelShape, run: LayerRun | None, groups: int
    ) -> None:
        """One ``TENSOR.MATMUL`` per block-diagonal group.

        Group ``g`` contracts the activation columns
        ``[g * depth, (g + 1) * depth)`` against the weight rows
        ``[g * rank, (g + 1) * rank)`` into the result columns
        ``[g * rank, (g + 1) * rank)``.  Every operand keeps its buffer's own
        row stride, so each view still walks whole rows of the tensor it names
        and A13's partial final extent still clamps the last token block --
        which the folded ``[rows, depth]`` view the generic contraction path
        builds would not have done, because its row stride is the reduction
        width rather than the row.

        The groups write disjoint column ranges of one result and are ordered
        only by the sequencer, which issues them in program order; the
        consumer waits on the last of them.
        """
        activation = self.tensors[kernel.inputs[0]]
        result = self.tensors[kernel.outputs[0]]
        act_width = 1
        for extent in self._dims(activation)[1:]:
            act_width *= extent
        out_width = shape.cols
        rank = shape.cols // groups
        # One token-block loop covers all the groups: they read the same block
        # of rows, so opening a loop per group would retire eight loop headers
        # to walk one axis once.
        loop = self._open_row_loop(kernel, shape)
        for group in range(groups):
            source = self._buffer_view(
                activation,
                dims=[shape.rows, shape.depth],
                strides=[act_width, 1],
                element_offset=group * shape.depth,
                shape=shape,
                loop=loop,
                writable=False,
            )
            weight = self._weight_view(
                kernel.inputs[1],
                run=run,
                shape=shape,
                slot=1,
                group_rows=rank,
                group=group,
            )
            destination = self._buffer_view(
                result,
                dims=[shape.rows, rank],
                strides=[out_width, 1],
                element_offset=group * rank,
                shape=shape,
                loop=loop,
                writable=True,
            )
            self._emit_operator(
                kernel,
                Major.TENSOR,
                int(TensorOp.MATMUL),
                [source, weight],
                [destination],
                loop=loop if group == groups - 1 else None,
                suffix=f".g{group:02d}",
            )

    def _emit_index_score(self, kernel: Kernel, run: LayerRun | None) -> None:
        """``VECTOR.INDEX_SCORE``: the row with two request-dependent extents.

        TA-ABI3-OPCONV-1 gives it ``in0 [B,S,Hd,D]``, ``in1 [B,C,D]``,
        ``in2 [B,S,Hd]`` and ``out0 [B,S,C]``, and the engine requires
        ``kv_batch == batch``.  ``S`` is the request's span and ``C`` its
        compressed context, so under *every* assignment of ``B`` at least one of
        them lands on a non-leading axis -- which is the second case the wire
        format's section 12.8 cites for amendment A18.

        A18 lets a view name one such axis, deliberately, and ``out0`` has two.
        The one that becomes a loop is the span: a per-token dispatch makes
        ``S`` a static one, leaving ``C`` as the only extent the request moves,
        which is exactly the shape the amendment says is expressible.  The cost
        is one dispatch per token for this operator, the same trade the routed
        contraction already makes, and it is bounded by the capability's loop
        trip rather than by the context.

        The candidate axis is then resolved by a context loop that runs once.
        Both the key and the score row count *groups*, so both declare the
        compression ratio as their unit; the key's leading batch is the plane
        fronting that the operand row asks for.
        """
        query, key, weights = (self.tensors[name] for name in kernel.inputs[:3])
        result = self.tensors[kernel.outputs[0]]
        heads, head_dim = self._dims(query)[1], self._dims(query)[2]
        candidates = self._dims(result)[1]
        _symbol, _multiplier, key_axis = self._leading_symbol(key)
        unit = key_axis.unit
        if unit <= 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: the index key leads with "
                f"{key.shape[0]!r}, which states no compression ratio; "
                "VECTOR.INDEX_SCORE scores compressed groups"
            )
        shape = self._shape_of(kernel, EngineOp(Major.VECTOR, Vector.INDEX_SCORE, 3, 1))
        token = self._open_token_loop(kernel)
        context = self._open_context_loop(kernel, candidates, key_axis)

        def token_term(width: int) -> DynamicTerm:
            return DynamicTerm.loop(token, width)

        query_view = self._buffer_view(
            query,
            dims=[1, 1, heads, head_dim],
            strides=[heads * head_dim, heads * head_dim, head_dim, 1],
            shape=shape,
            loop=token,
            writable=False,
            term=token_term(heads * head_dim),
        )
        # The key is ``[B, C, D]`` wherever it lives.  In the released graph it
        # is a plane of the compressed cache, which is a STATE resource; a graph
        # that keeps it as an ordinary activation states the same operand.
        key_term = DynamicTerm.loop(context, self._plane_row(key) * candidates)
        key_view = self._state_plane_view(
            kernel,
            kernel.inputs[1],
            "in",
            run,
            batch_lead=True,
            extent_axis=1,
            extent_unit=unit,
            extra_terms=(key_term,),
        )
        if key_view is None:
            key_width = self._plane_width(key.tensor_id)
            key_view = self._buffer_view(
                key,
                dims=[1, candidates, key_width],
                strides=[candidates * key_width, key_width, 1],
                shape=shape,
                loop=context,
                writable=False,
                term=DynamicTerm.loop(context, key_width * candidates),
                extent_axis=1,
                extent_unit=unit,
            )
        weight_view = self._buffer_view(
            weights,
            dims=[1, 1, heads],
            strides=[heads, heads, 1],
            shape=shape,
            loop=token,
            writable=False,
            term=token_term(heads),
        )
        score_view = self._buffer_view(
            result,
            dims=[1, 1, candidates],
            strides=[candidates, candidates, 1],
            shape=shape,
            loop=token,
            writable=True,
            term=token_term(candidates),
            extra_terms=(DynamicTerm.loop(context, candidates),),
            extent_axis=2,
            extent_unit=unit,
        )
        self._emit_operator(
            kernel,
            Major.VECTOR,
            int(Vector.INDEX_SCORE),
            [query_view, key_view, weight_view],
            [score_view],
            loop=context,
            schedule_rows=1,
            extra_close=1,
        )

    def _plane_row(self, tensor: Tensor) -> int:
        """Elements between successive rows of a state plane's merged struct."""
        state_id = self._state_owner.get(tensor.tensor_id)
        if state_id is None or state_id not in self._state_slot:
            return self._plane_width(tensor.tensor_id)
        group_key, _slot = self._state_slot[state_id]
        return self._state_group_shape[group_key][2]

    # -- predicates (amendment A3) ---------------------------------------
    #
    # The neutral graph states three different conditional shapes and ABI 3.0
    # states exactly one thing about an instruction: ``predicate_id`` plus the
    # ``PREDICATED``/``PREDICATE_INVERT`` flags, resolved against a
    # ``PREDICATE`` descriptor (type ``0x000f``, amendment A3).  So each shape
    # has to be *mapped* onto that, and the mapping is written out here rather
    # than inferred at each site:
    #
    # ``execution_predicate``
    #     the whole operator vanishes -- one predicated instruction.
    # ``conditional_outputs``
    #     the operator issues and some outputs vanish.  ABI 3.0 has no
    #     per-output predicate, so this is only expressible when *every*
    #     output is conditional on one value, which is then the operator's own
    #     predicate; anything else is refused rather than half-lowered.
    # ``operand_present_predicate``
    #     the operator issues and one operand vanishes.  ABI 3.0 has no
    #     per-operand predicate either, so this becomes a *pair* of
    #     instructions on complementary predicates -- the full operand row
    #     under the condition, the reduced row under its inverse -- which is
    #     what the ``OPTIONAL_FEATURE`` flag's "authenticated alternative path"
    #     already assumes exists.  Events are single-assignment, so the pair
    #     cannot share one and an unpredicated ``CONTROL.NOP`` behind them
    #     publishes the event the result is ordered by.
    #
    # A predicate that is declared and not lowered is invisible: the operator
    # issues where the source skips it, and either an engine refuses it or it
    # computes against an operand the request does not have.  ``instructions
    # .predicated_off`` is the measurement that says the mapping is live.
    def _discover_compressor_predicates(self) -> dict[str, dict[str, Any]]:
        """Index the released compressor's two-phase predicate declarations.

        The prefill form is a frozen ``COMPARE_SYMBOL`` predicate.  The decode
        form is exactly ``POSITION_END mod ratio == 0`` (the graph spells
        ``POSITION_END`` as ``context_length``), implemented below by reading
        the existing ``ring_indices_v1`` table into an ordinary four-byte HBM
        flag and using ``BOOLEAN_OBJECT``.  No new predicate kind or private
        host decision is involved.
        """

        found: dict[str, dict[str, Any]] = {}
        for kernel in self.graph.kernels:
            if kernel.kind != "COMPRESS_STATE_UPDATE":
                continue
            name = str(kernel.attributes.get("predicate_output", ""))
            if not name:
                continue
            ratio = int(kernel.attributes.get("ratio", 0) or 0)
            if ratio not in PINNED_COMPRESSION_RATIOS:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: compressor predicate names "
                    f"unpinned ratio {ratio}"
                )
            conditions = kernel.attributes.get("predicate_condition")
            if not isinstance(conditions, Mapping):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: rolling compression needs "
                    "separate prefill and decode predicate conditions"
                )
            prefill = str(conditions.get("prefill", ""))
            decode = str(conditions.get("decode", ""))
            # CONTEXT_LENGTH and POSITION_END are the same request scalar in
            # ABI 3.0.  Freeze the exact graph spelling accepted here rather
            # than treating an arbitrary modulus string as equivalent.
            if decode.split() != ["context_length", "%", str(ratio), "==", "0"]:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: decode predicate {decode!r} "
                    f"is not the exact POSITION_END modulo {ratio} boundary"
                )
            self._symbol_condition(prefill)
            spec = {
                "name": name,
                "ratio": ratio,
                "prefill": prefill,
                "decode": decode,
            }
            previous = found.get(name)
            if previous is not None and previous != spec:
                raise RomLoweringError(
                    f"compressor predicate {name!r} has conflicting declarations"
                )
            found[name] = spec
        return found

    def _compressor_predicate_of(
        self, kernel: Kernel
    ) -> dict[str, Any] | None:
        """Return the rolling predicate used by ``kernel``, if any."""

        names: set[str] = set()
        output = kernel.attributes.get("predicate_output")
        if output:
            names.add(str(output))
        execution = kernel.attributes.get("execution_predicate")
        if execution:
            names.add(str(execution))
        conditional = kernel.attributes.get("conditional_outputs")
        if conditional:
            names.update(str(value) for value in dict(conditional).values())
        matched = [
            self._compressor_predicates[name]
            for name in names
            if name in self._compressor_predicates
        ]
        if not matched:
            return None
        if len({entry["name"] for entry in matched}) != 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} names multiple rolling-compressor "
                "predicates"
            )
        return matched[0]

    def _symbol_condition(self, condition: str) -> tuple[Symbol, Comparison, int]:
        """Parse one declared condition into an A3 ``COMPARE_SYMBOL`` triple."""
        parts = str(condition).split()
        if len(parts) != 3 or parts[1] not in PREDICATE_COMPARISONS:
            raise RomLoweringError(
                f"predicate condition {condition!r} is not the declared "
                "'<symbol> <comparison> <integer>' statement over a runtime "
                "symbol.  ABI 3.0's frozen predicate kinds state a comparison "
                "and nothing else: there is no arithmetic in a PREDICATE "
                "payload and in particular no modulus"
            )
        name, operator, literal = parts
        axis = SYMBOL_BY_NAME.get(name)
        if axis is None:
            raise RomLoweringError(
                f"predicate condition {condition!r} names {name!r}, which is "
                "not a runtime symbol this backend resolves; an unrecognised "
                "name would silently predicate nothing"
            )
        try:
            immediate = int(literal)
        except ValueError:
            raise RomLoweringError(
                f"predicate condition {condition!r} compares against "
                f"{literal!r}, which is not an integer immediate"
            ) from None
        comparison, value = _rewrite_comparison(axis, operator, immediate)
        return Symbol(int(axis.symbol)), comparison, value

    def _predicate_conditions(self) -> Mapping[str, str]:
        """``predicate_output`` value name -> the condition this target states.

        A kernel that computes a boolean names it in ``predicate_output`` and
        says what it means in ``predicate_condition``, one entry per phase.  No
        neutral kind produces a ``bool`` and ABI 3.0 has no operator that could
        write one, so the value itself cannot exist on the device: what a
        backend can do is state the *condition* the value stands for, and only
        where a frozen predicate kind states it.

        The released compressor's condition has two phases and only one of them
        is expressible.  Prefill is ``span_groups_ratioN > 0`` -- a comparison
        over a declared symbol, which ``COMPARE_SYMBOL`` states exactly.
        Decode is ``(start_pos + 1) % ratio == 0``, and the frozen
        ``comparisons`` registry has no modulus, no masking and no arithmetic;
        ``BOOLEAN_OBJECT`` reads a *statically* indexed word, so it cannot read
        ``ring[start_pos]`` either.  Inventing a predicate kind for it would be
        an ABI change and is not a backend's to make, so the decode form is
        recorded as unrepresentable and reported in the deployment notes rather
        than approximated.
        """
        if self._predicate_values is not None:
            return self._predicate_values
        values: dict[str, str] = {}
        for kernel in self.graph.kernels:
            name = kernel.attributes.get("predicate_output")
            if not name:
                continue
            declared = kernel.attributes.get("predicate_condition")
            if declared is None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} declares predicate output "
                    f"{name!r} and no ``predicate_condition``; a value no "
                    "instruction can compute and no condition can state is a "
                    "predicate a backend would have to guess"
                )
            forms = (
                {"": str(declared)}
                if isinstance(declared, str)
                else {str(k): str(v) for k, v in dict(declared).items()}
            )
            usable: dict[str, str] = {}
            refused: dict[str, str] = {}
            for phase, condition in forms.items():
                try:
                    self._symbol_condition(condition)
                except RomLoweringError as exc:
                    refused[phase] = f"{condition} -- {exc}"
                else:
                    usable[phase] = condition
            if not usable:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} declares predicate output "
                    f"{name!r} whose every phase is outside ABI 3.0's frozen "
                    f"predicate kinds: {refused}"
                )
            order = [p for p in ("prefill", "", "decode") if p in usable]
            chosen = usable[order[0] if order else sorted(usable)[0]]
            # A rolling compressor's modulus form is not discarded: it is
            # lowered by the explicit ring-backed BOOLEAN_OBJECT path.  Other
            # unrepresentable forms remain reportable walls.
            if refused and str(name) not in self._compressor_predicates:
                self._unrepresentable_predicates[str(name)] = {
                    "lowered": chosen,
                    **{f"refused.{phase}": text for phase, text in refused.items()},
                }
            values[str(name)] = chosen
        self._predicate_values = values
        return values

    def _condition_of(self, declared: str, where: str) -> str:
        """One declared predicate, as a condition over a runtime symbol."""
        conditions = self._predicate_conditions()
        if declared in conditions:
            return conditions[declared]
        if len(str(declared).split()) != 3:
            raise RomLoweringError(
                f"{where}: predicate {declared!r} is neither a symbol "
                "comparison nor the ``predicate_output`` of a kernel in this "
                "graph; a predicate a backend cannot resolve is a predicate it "
                "would silently drop"
            )
        return str(declared)

    def _predicate_descriptor(self, condition: str, where: str) -> int:
        symbol, comparison, immediate = self._symbol_condition(condition)
        key = (int(symbol), int(comparison), int(immediate))
        cached = self._predicate_cache.get(key)
        if cached is not None:
            return cached
        descriptor = self.builder.predicate(
            kind=PredicateKind.COMPARE_SYMBOL,
            comparison=comparison,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(symbol),
            immediate=int(immediate),
            key=(
                f"pred.{symbol.name.lower()}."
                f"{comparison.name.lower()}.{immediate}"
            ),
        )
        self._predicate_cache[key] = descriptor
        return descriptor

    def _kernel_condition(self, kernel: Kernel) -> str | None:
        """The one condition under which this kernel's operator is issued."""
        declared: list[str] = []
        attribute = kernel.attributes.get("execution_predicate")
        if attribute:
            declared.append(str(attribute))
        if getattr(kernel, "predicate", ""):
            declared.append(str(kernel.predicate))
        conditional = kernel.attributes.get("conditional_outputs")
        if conditional:
            names = {str(v) for v in dict(conditional).values()}
            # ``COMPRESS_STATE_UPDATE`` is the one kernel that declares this,
            # and the exporter's reason is that the released
            # ``Compressor.forward`` writes its raw window on every step, so
            # only the two pooled results are conditional.  On this ABI the
            # raw window is not part of the operator at all: ``VECTOR.COMPRESS``
            # binds no STATE resource in this sub-case and the engine says so
            # ("the decode path rolls the compressor's raw slots, which is a
            # STATE resource this operator's arity does not bind").  Both of
            # the operator's declared outputs are the pooled ones, so once they
            # are conditional there is nothing unconditional left for it to do
            # and the whole instruction carries the predicate.  That equality
            # is checked rather than assumed: a kernel with an unconditional
            # output beside a conditional one is refused, because ABI 3.0 has
            # no per-output predicate and half-lowering one would write a
            # result the source did not produce.
            if len(names) != 1 or len(conditional) != len(kernel.outputs):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} declares "
                    f"{len(conditional)} conditional outputs of "
                    f"{len(kernel.outputs)} on {len(names)} distinct "
                    "predicates; ABI 3.0 predicates an instruction, not an "
                    "output, so only an operator whose every output is "
                    "conditional on one value is expressible"
                )
            declared.append(next(iter(names)))
        resolved = {self._condition_of(d, kernel.kernel_id) for d in declared}
        if not resolved:
            return None
        if len(resolved) > 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} names {len(resolved)} distinct "
                f"predicates {sorted(resolved)}; an ABI 3.0 instruction "
                "carries one ``predicate_id`` and there is no conjunction"
            )
        return next(iter(resolved))

    def _prove_run_predicates_agree(self) -> None:
        """Every layer a loop body stands for must state the same predicate.

        A run is emitted once and executed once per group, so the body carries
        the *first* group's kernel at each position.  The fold identity is
        structural -- kind, contract, operand roles, dtypes, weight extents --
        and says nothing about attributes, so two layers with different
        conditions could share a body and one layer's predicate would silently
        govern the other's execution.  Nothing downstream could see it: the
        program is admitted, every operand is in bounds, and the wrong layer is
        simply skipped or issued.  So it is checked here, where the fold is
        known, rather than assumed from the fact that the released stack
        alternates in step with its compression ratios.
        """
        for run in self.analysis.runs:
            for position, column in enumerate(run.body):
                conditions = {self._kernel_condition(k) for k in column}
                if len(conditions) > 1:
                    raise RomLoweringError(
                        f"run {run.index} position {position} folds layers "
                        f"{[k.kernel_id for k in column]} whose execution "
                        f"predicates differ ({sorted(map(str, conditions))}); a "
                        "loop body states one predicate and would govern every "
                        "layer it stands for with it"
                    )
                # Compared after resolution, not as declared: each layer names
                # its own predicate value, and two layers stating the same
                # condition through different names are the same predicate.
                operands = {self._operand_present(k) for k in column}
                if len(operands) > 1:
                    raise RomLoweringError(
                        f"run {run.index} position {position} folds layers "
                        f"{[k.kernel_id for k in column]} whose conditionally "
                        "present operands differ; one loop body cannot state "
                        "two alternative paths"
                    )

    def _prove_predicates_lowered(self, emitted: Sequence[Kernel]) -> None:
        """Nothing the graph declared conditional was issued unconditionally.

        This is the check the whole section exists for.  A predicate that is
        declared and not lowered leaves no trace at runtime: the instruction
        issues where the source skips it, and either an engine refuses it or it
        computes against an operand the request does not have and nothing
        complains.  So the lowering proves, against the kernels it actually
        emitted, that every declared condition reached an instruction.
        """
        missing: list[str] = []
        for kernel in emitted:
            attributes = kernel.attributes
            declares = bool(
                attributes.get("execution_predicate")
                or attributes.get("conditional_outputs")
                or getattr(kernel, "predicate", "")
            )
            if declares and kernel.kernel_id not in self._predicated_operators:
                missing.append(f"{kernel.kernel_id} ({kernel.kind}): execution")
            if (
                attributes.get("operand_present_predicate")
                and kernel.kernel_id not in self._operand_alternatives
            ):
                missing.append(f"{kernel.kernel_id} ({kernel.kind}): operand")
        if missing:
            raise RomLoweringError(
                "these kernels declare a condition that reached no "
                f"instruction: {missing}.  A declared predicate that is not "
                "lowered is invisible -- the operator issues where the source "
                "skips it -- so the lowering refuses rather than emitting it"
            )

    def _predicate_report(self) -> dict[str, Any]:
        """What this lowering predicated, and what it could not state."""
        report: dict[str, Any] = {}
        if self._predicated_operators:
            report["predicated_operators"] = len(self._predicated_operators)
            report["predicated_conditions"] = {
                condition: sum(
                    1
                    for value in self._predicated_operators.values()
                    if value == condition
                )
                for condition in sorted(set(self._predicated_operators.values()))
            }
        if self._operand_alternatives:
            report["operand_alternative_paths"] = len(self._operand_alternatives)
            report["operand_alternative_conditions"] = {
                condition: sum(
                    1
                    for value in self._operand_alternatives.values()
                    if value == condition
                )
                for condition in sorted(set(self._operand_alternatives.values()))
            }
        if self._phase_extent:
            # Published beside the program for the same reason the predicate
            # report is: a join whose row space the *phase* decides is not
            # visible in any one descriptor, and a reader comparing the two
            # lanes needs to see that both split the same resource the same
            # way.  Each entry is the tensor and, per phase, the affine
            # function that phase's path declares.
            report["phase_split_extents"] = {
                name: {
                    phase: (
                        f"{extent.numerator}*"
                        f"{Symbol(int(extent.symbol)).name}/"
                        f"{extent.unit}+{extent.bias}"
                    )
                    for phase, extent in sorted(table.items())
                }
                for name, table in sorted(self._phase_extent.items())
            }
        if self._unrepresentable_predicates:
            report["unrepresentable_predicates"] = dict(
                sorted(self._unrepresentable_predicates.items())
            )
        if self._compressor_transition_ratios:
            report["rolling_compressor"] = {
                "abi": "3.0",
                "boundary": "ring_indices_v1(POSITION_END) == 0",
                "history": "ordinary_hbm_circular_absolute_position",
                "ratios": sorted(self._compressor_transition_ratios),
                "roll_copy": False,
            }
        return report

    # -- amendment A18 across a phase boundary ---------------------------
    #
    # ABI 3.0 section 12.2 fixes one relation between the three request
    # scalars: ``CONTEXT_LENGTH == POSITION_START + SPAN_TOKENS``.  A graph
    # that pins one of them in a phase therefore pins a second, and that is
    # what lets a sum over two symbols collapse onto one *per phase* without
    # any backend inventing an identity of its own.
    PHASE_SYMBOL_BY_NAME: Mapping[str, Symbol] = {
        "span_tokens": Symbol.SPAN_TOKENS,
        "position_start": Symbol.POSITION_START,
        "context_length": Symbol.CONTEXT_LENGTH,
    }

    def _phase_substitution(
        self, pinned: Mapping[str, Any], where: str
    ) -> tuple[dict[int, int], dict[int, tuple[int, int]]]:
        """``(constants, aliases)`` implied by one phase's pinned symbols.

        ``constants`` maps a symbol to the value the phase pins it to.
        ``aliases`` maps a symbol to ``(base symbol, offset)`` -- the symbol is
        that base plus a constant.  Everything here follows from the pinned
        values and section 12.2's relation; nothing is assumed about how a host
        drives the device.
        """
        constants: dict[int, int] = {}
        for name, value in dict(pinned).items():
            symbol = self.PHASE_SYMBOL_BY_NAME.get(str(name))
            if symbol is None:
                raise RomLoweringError(
                    f"{where}: phase binding names {name!r}, which is not one "
                    "of the three request scalars section 12.2 relates; a "
                    "binding this backend cannot read is one it would drop"
                )
            constants[int(symbol)] = int(value)
        aliases: dict[int, tuple[int, int]] = {}
        if int(Symbol.CONTEXT_LENGTH) not in constants:
            start = constants.get(int(Symbol.POSITION_START))
            span = constants.get(int(Symbol.SPAN_TOKENS))
            if start is not None:
                aliases[int(Symbol.CONTEXT_LENGTH)] = (int(Symbol.SPAN_TOKENS), start)
            elif span is not None:
                aliases[int(Symbol.CONTEXT_LENGTH)] = (
                    int(Symbol.POSITION_START),
                    span,
                )
        return constants, aliases

    def _join_extent_under(
        self,
        names: Sequence[str],
        axis: int,
        constants: Mapping[int, int],
        aliases: Mapping[int, tuple[int, int]],
    ) -> tuple[RequestAxis | None, int]:
        """:meth:`_join_extent`, evaluated under one phase's substitutions.

        A17 makes a join's output the sum of its inputs, and A18 states an
        extent as an affine image of *one* symbol.  The compressed attention
        join is a sum over two -- ``span_tokens + 128 + context_length /
        ratio`` -- so the sum has no A18 image at all and the exporter's own
        ``attention_rows_ratioN`` was taken on trust.  It was wrong: it names
        the *span's* group count, which equals the context's only while the
        span is the context, so it is exact in prefill and short by every
        committed group at every decode step.

        Under a phase's substitutions the sum does collapse.  A symbol the
        phase pins to a constant folds into the bias; a symbol the phase makes
        an offset image of another is rewritten onto that other when the
        rewrite is exact -- an offset survives a floor only when the divisor is
        one, so a nonzero offset against a group axis is left alone rather than
        approximated.

        What remains is a sum of affine images of one symbol, and it is
        combined only where the combination is exact: ``floor(a*S) +
        floor(b*S/u) == floor((a*u + b)*S/u)`` because the first term is a
        whole number of the symbol's units.  Two *floored* terms have no such
        identity, so this refuses rather than rounding one.
        """
        symbol: int | None = None
        exact = 0
        floored: RequestAxis | None = None
        bias = 0
        for name in names:
            tensor = self.tensors[name]
            entry = tensor.shape[axis] if axis < len(tensor.shape) else None
            if not isinstance(entry, Symbolic):
                bias += int(self._dims(tensor)[axis])
                continue
            request = SYMBOL_BY_NAME.get(entry.symbol)
            if request is None or int(entry.multiplier or 1) != 1:
                raise RomLoweringError(
                    f"join operand {name!r} leads on axis {axis} with "
                    f"{entry.symbol!r}, which this backend cannot state as an "
                    "A18 affine image"
                )
            unit = max(int(request.unit), 1)
            numerator = int(request.numerator)
            bias += int(request.bias)
            named = int(request.symbol)
            value = constants.get(named)
            if value is not None:
                bias += numerator * int(value) // unit
                continue
            alias = aliases.get(named)
            if alias is not None and (alias[1] == 0 or unit == 1):
                bias += numerator * int(alias[1]) // unit
                named = alias[0]
            if symbol is None:
                symbol = named
            elif symbol != named:
                raise RomLoweringError(
                    f"a join of operands over {Symbol(symbol).name} and "
                    f"{Symbol(named).name} has no single A18 extent in this "
                    "phase; this backend refuses to invent one"
                )
            if unit == 1:
                exact += numerator
            elif floored is None:
                floored = RequestAxis(Symbol(named), unit, numerator, 0)
            else:
                raise RomLoweringError(
                    f"a join with two floored operand extents "
                    f"({floored.numerator}/{floored.unit} and "
                    f"{numerator}/{unit}) has no exact A18 sum; this backend "
                    "refuses to round one"
                )
        if symbol is None:
            return None, bias
        if floored is None:
            return RequestAxis(Symbol(symbol), 1, exact, bias), 0
        unit = int(floored.unit)
        return (
            RequestAxis(Symbol(symbol), unit, exact * unit + floored.numerator, bias),
            0,
        )

    @staticmethod
    def _substitute_condition(
        triple: tuple[Symbol, Comparison, int],
        constants: Mapping[int, int],
        aliases: Mapping[int, tuple[int, int]],
    ) -> tuple[Symbol, Comparison, int] | bool:
        """One ``COMPARE_SYMBOL`` triple under a phase's substitutions.

        Returns the rewritten triple, or ``True``/``False`` when the phase
        decides the comparison outright.  ``S + offset <op> K`` is
        ``S <op> K - offset`` for every frozen comparison, which is why moving
        a condition across the section 12.2 relation is exact where moving an
        extent across it is not.
        """
        symbol, comparison, immediate = triple
        value = constants.get(int(symbol))
        if value is not None:
            return _evaluate_comparison(comparison, int(value), int(immediate))
        alias = aliases.get(int(symbol))
        if alias is not None:
            return Symbol(alias[0]), comparison, int(immediate) - int(alias[1])
        return symbol, comparison, immediate

    def _join_extent(
        self, names: Sequence[str], axis: int
    ) -> tuple[RequestAxis | None, int]:
        """The join-axis extent of a set of operands, as one affine statement.

        Amendment A17 makes a join's output extent the sum of its inputs', so
        the reduced path's output is the sum over the operands that remain.
        Static extents add into the bias -- a 128-row sliding window is there
        for a span of one -- and symbolic ones add their numerators.  Two
        symbolic operands counted in *different* units, or over different
        symbols, have no single affine image and are refused rather than
        approximated: the full attention join is exactly that case, which is
        why the exporter states its fused form itself and only the reduced one
        is derived here.
        """
        symbol: Symbol | None = None
        unit = 1
        numerator = 0
        bias = 0
        for name in names:
            tensor = self.tensors[name]
            entry = tensor.shape[axis] if axis < len(tensor.shape) else None
            if not isinstance(entry, Symbolic):
                bias += int(self._dims(tensor)[axis])
                continue
            request = SYMBOL_BY_NAME.get(entry.symbol)
            if request is None or int(entry.multiplier or 1) != 1:
                raise RomLoweringError(
                    f"join operand {name!r} leads on axis {axis} with "
                    f"{entry.symbol!r}, which this backend cannot state as an "
                    "A18 affine image; the reduced path's extent would be a "
                    "guess"
                )
            if symbol is None:
                symbol, unit = Symbol(int(request.symbol)), int(request.unit)
            elif (int(symbol), unit) != (int(request.symbol), int(request.unit)):
                raise RomLoweringError(
                    f"a join of operands counted in different units "
                    f"({symbol.name}/{unit} and "
                    f"{Symbol(int(request.symbol)).name}/{request.unit}) has no "
                    "single A18 extent; this backend refuses to invent one"
                )
            numerator += int(request.numerator)
            bias += int(request.bias)
        if symbol is None:
            return None, bias
        return RequestAxis(symbol, unit, numerator, bias), 0

    def _phase_present_paths(
        self,
        kernel: Kernel,
        shape: KernelShape,
        *,
        condition: str,
        context_loop: int | None,
        context_divisor: int,
        declared_output: int,
    ) -> list[tuple[str, int, int]] | None:
        """One path per phase for a join whose sum spans two symbols.

        ``None`` when the kernel declares no phase binding, which is every
        join but DeepSeek's compressed attention view: the full operand row
        then keeps the single instruction and the single declared extent it
        has always had.

        Otherwise the full row is emitted once per phase.  Each path carries
        that phase's *derived* extent -- ``5 * span / 4 + 128`` in prefill,
        ``context / 4 + 129`` in decode -- and that phase's rewriting of the
        operand's own presence condition, which is what keeps exactly one of
        them issuing per request.  The two are refused unless they are provably
        disjoint: each is evaluated under the other phase's pinned symbols and
        must read false there, so "one path per request" is a check rather than
        a hope.  ABI 3.0 gives an instruction one predicate and has no
        conjunction, so a pair that overlapped would run twice and write the
        same rows twice.
        """
        declared = kernel.attributes.get("phase_symbol_binding")
        if not declared:
            return None
        if int(kernel.attributes.get("axis", 0)) != 0:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares a phase binding on a "
                "feature join; A18's extent axis is the token axis and a "
                "feature join does not move it"
            )
        base = self._symbol_condition(condition)
        names = list(kernel.inputs)
        output_axis = self._declared_join_axis(kernel.outputs[0], 0)
        paths: list[tuple[str, int, int]] = []
        triples: dict[str, tuple[Symbol, Comparison, int]] = {}
        pinned_by_phase: dict[str, dict[int, int]] = {}
        for phase, pinned in sorted(dict(declared).items()):
            constants, aliases = self._phase_substitution(
                pinned, f"kernel {kernel.kernel_id!r} phase {phase!r}"
            )
            pinned_by_phase[phase] = constants
            moved = self._substitute_condition(base, constants, aliases)
            if moved is False:
                continue
            if moved is True:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: phase {phase!r} decides the "
                    f"operand condition {condition!r} outright, so the reduced "
                    "path is unreachable there and the pair is not a pair"
                )
            extent, _static = self._join_extent_under(names, 0, constants, aliases)
            if extent is None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: in phase {phase!r} the "
                    "join's operands sum to a static extent, which no A18 "
                    "term resolves"
                )
            triples[phase] = moved
            if output_axis is not None and (
                int(extent.symbol),
                int(extent.unit),
                int(extent.numerator),
                int(extent.bias),
            ) == (
                int(output_axis.symbol),
                int(output_axis.unit),
                int(output_axis.numerator),
                int(output_axis.bias),
            ):
                # The declared symbol *is* this phase's sum, so the path keeps
                # the view the kernel already built: the prefill instruction is
                # byte-identical to the one this program emitted before the
                # phase split existed.
                view = declared_output
            elif int(extent.symbol) == int(Symbol.SPAN_TOKENS):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: phase {phase!r} sums to a "
                    "span-bound extent the output does not declare"
                )
            else:
                if context_loop is None or context_divisor <= 0:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r}: phase {phase!r} sums to "
                        f"a {Symbol(int(extent.symbol)).name}-bound extent and "
                        "no context loop resolves it"
                    )
                view = self._phase_join_output(
                    kernel,
                    shape,
                    extent=extent,
                    loop=context_loop,
                    divisor=context_divisor,
                )
            paths.append(
                (
                    str(phase),
                    self._predicate_from_triple(moved),
                    view,
                )
            )
            self._phase_extent.setdefault(kernel.outputs[0], {})[str(phase)] = extent
        for phase, triple in triples.items():
            for other, constants in pinned_by_phase.items():
                if other == phase:
                    continue
                value = constants.get(int(triple[0]))
                if value is None:
                    continue
                if _evaluate_comparison(triple[1], int(value), int(triple[2])):
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r}: the {phase!r} path's "
                        f"condition still reads true under {other!r}'s pinned "
                        "symbols, so two paths would issue for one request"
                    )
        if len(paths) < 2:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} declares a phase binding that "
                f"leaves {len(paths)} present paths; a split that does not "
                "split is a declaration nothing checks"
            )
        return paths

    def _phase_consumer_paths(
        self, kernel: Kernel
    ) -> dict[int, dict[str, RequestAxis]] | None:
        """Operands of this kernel whose extent the phase decides.

        A tensor produced by a phase-split join has no single A18 extent, and a
        view of it is a statement of that extent wherever it is read.  So the
        split does not stop at the producer: every consumer states the same two
        functions, or it presents rows the producer did not write.  Left
        unpropagated, DeepSeek's sparse attention read the prefill function at
        decode -- 129 rows of a 137-row join -- and refused the eight rebased
        compressed indices its own selector had just produced.

        One hop is the whole propagation for both released graphs: the join's
        output is read by ``ATTENTION.SPARSE`` and by nothing else, and that
        operator's own output is span-sized.  A second hop would be refused
        below rather than followed silently.
        """
        if not self._phase_extent or not kernel.inputs:
            return None
        found: dict[int, dict[str, RequestAxis]] = {}
        for index, name in enumerate(kernel.inputs):
            phases = self._phase_extent.get(name)
            if phases is not None:
                found[index] = phases
        if not found:
            return None
        if self._kernel_condition(kernel) is not None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} reads a phase-split extent and "
                "declares a condition of its own; an ABI 3.0 instruction "
                "carries one predicate_id and there is no conjunction"
            )
        for name in kernel.outputs:
            if name in self._phase_extent:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} would propagate a phase-split "
                    "extent to its own output; this backend follows one hop and "
                    "refuses to guess the rest"
                )
        return found

    def _emit_phase_consumer(
        self,
        kernel: Kernel,
        shape: KernelShape,
        family: Major,
        sub: int,
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        order: Sequence[int],
        paths: Mapping[int, Mapping[str, RequestAxis]],
        loop: int | None,
        schedule_rows: int | None,
        extra_close: int,
        context_loop: int | None,
        context_divisor: int,
    ) -> None:
        """One instruction per phase, each stating that phase's row space."""
        slots = self._abi_input_slots(kernel, order)
        phases = sorted({phase for table in paths.values() for phase in table})
        events: list[tuple[int, int, bool]] = []
        for table in paths.values():
            if sorted(table) != phases:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} reads two phase-split "
                    "operands that name different phases"
                )
        for phase in phases:
            row = list(inputs)
            for ir_slot, table in paths.items():
                abi_slot = next(
                    (i for i, ir in enumerate(slots) if ir == ir_slot), None
                )
                if abi_slot is None or abi_slot >= len(row):
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r}: no ABI slot carries the "
                        f"phase-split operand {ir_slot}"
                    )
                extent = table[phase]
                if int(extent.symbol) == int(Symbol.SPAN_TOKENS):
                    continue  # the declared view already states this phase
                if context_loop is None or context_divisor <= 0:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r}: phase {phase!r} names a "
                        f"{Symbol(int(extent.symbol)).name}-bound row space and "
                        "no loop resolves it"
                    )
                row[abi_slot] = self._phase_extent_view(
                    self.tensors[kernel.inputs[ir_slot]],
                    shape,
                    extent=extent,
                    loop=context_loop,
                    divisor=context_divisor,
                    writable=False,
                )
            predicate = self._phase_predicate(phase)
            event = self._emit_operator(
                kernel,
                family,
                sub,
                row,
                outputs,
                loop=None,
                schedule_rows=schedule_rows,
                suffix=f".{phase}",
                predicate_id=predicate,
            )
            events.append((event, predicate, False))
        join = self._emit_guarded_join(events, source_operation_id=kernel.index)
        for name in kernel.outputs:
            self._event_of_tensor[name] = join
        if loop is not None:
            self.builder.close_loop()
        for _ in range(extra_close):
            self.builder.close_loop()

    def _emit_guarded_join(
        self,
        paths: Sequence[tuple[int, int, bool]],
        *,
        source_operation_id: int = NO_ID,
    ) -> int:
        """Converge mutually exclusive event paths without waiting on a skip.

        A predicated-off instruction never signals.  Each CONTROL.WAIT carries
        the exact same guard as its producer, so precisely the live path is
        acquired; the following unconditional NOP can then publish one event
        to ordinary consumers.
        """

        if not paths:
            raise RomLoweringError("cannot join an empty set of guarded paths")
        for event, predicate, inverted in paths:
            self.builder.emit(
                Major.CONTROL,
                Control.WAIT,
                wait_set_id=self._wait_set([event]),
                predicate_id=predicate,
                invert_predicate=inverted,
                source_operation_id=source_operation_id,
            )
        joined = self.builder.new_event()
        self.builder.emit(
            Major.CONTROL,
            Control.NOP,
            signal_event_id=joined,
            source_operation_id=source_operation_id,
        )
        return joined

    def _phase_predicate(self, phase: str) -> int:
        value = Phase.PREFILL if str(phase) == "prefill" else Phase.DECODE
        if str(phase) not in {"prefill", "decode"}:
            raise RomLoweringError(
                f"phase {phase!r} is neither prefill nor decode; ABI 3.0's "
                "PHASE_IS predicate names one of the two"
            )
        key = ("phase", int(value))
        cached = self._predicate_cache.get(key)
        if cached is not None:
            return cached
        descriptor = self.builder.predicate(
            kind=PredicateKind.PHASE_IS,
            comparison=Comparison.EQ,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(Symbol.PHASE),
            immediate=int(value),
            key=f"pred.phase.{value.name.lower()}",
        )
        self._predicate_cache[key] = descriptor
        return descriptor

    def _predicate_from_triple(
        self, triple: tuple[Symbol, Comparison, int]
    ) -> int:
        symbol, comparison, immediate = triple
        key = (int(symbol), int(comparison), int(immediate))
        cached = self._predicate_cache.get(key)
        if cached is not None:
            return cached
        descriptor = self.builder.predicate(
            kind=PredicateKind.COMPARE_SYMBOL,
            comparison=comparison,
            selector_kind=SelectorKind.RUNTIME_SYMBOL,
            selector_index=int(symbol),
            immediate=int(immediate),
            key=(
                f"pred.{symbol.name.lower()}."
                f"{comparison.name.lower()}.{immediate}"
            ),
        )
        self._predicate_cache[key] = descriptor
        return descriptor

    def _declared_join_axis(self, name: str, axis: int) -> RequestAxis | None:
        """The A18 function the graph declares for one tensor's join axis."""
        tensor = self.tensors[name]
        entry = tensor.shape[axis] if axis < len(tensor.shape) else None
        if not isinstance(entry, Symbolic):
            return None
        request = SYMBOL_BY_NAME.get(entry.symbol)
        if request is None or int(entry.multiplier or 1) != 1:
            return None
        return request

    def _check_join_extent(self, kernel: Kernel, join_axis: int) -> None:
        """Refuse a join whose declared output extent is not its operands' sum.

        A17 makes the output of a join the sum of its inputs and the engine
        checks exactly that, one dispatch after admission.  Until now the
        *reduced* path of a conditionally present operand was the only extent a
        backend derived; the full path took whatever symbol the exporter had
        put on the output tensor, and for DeepSeek's compressed attention join
        that symbol was ``attention_rows_ratioN`` -- the span's group count
        where the join carries the context's.  It agreed with the operands in
        prefill, where the span *is* the context, so every gate this program
        had ever run passed and the first decode step failed at the engine with
        ``output view ... differ from the axis-0 concatenation``.

        Deriving it here says the same thing at lowering, in both lanes, for
        every join and every phase -- and a phase whose sum has no A18 image at
        all is refused rather than declared, which is what the exporter's
        untested word amounted to.
        """
        if join_axis != 0 or not kernel.outputs or not kernel.inputs:
            return
        declared = self._declared_join_axis(kernel.outputs[0], 0)
        phases = kernel.attributes.get("phase_symbol_binding")
        names = list(kernel.inputs)
        if phases:
            for phase, pinned in sorted(dict(phases).items()):
                constants, aliases = self._phase_substitution(
                    pinned, f"kernel {kernel.kernel_id!r} phase {phase!r}"
                )
                self._join_extent_under(names, 0, constants, aliases)
            return
        derived, static = self._join_extent_under(names, 0, {}, {})
        if declared is None:
            if derived is not None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: the join's operands sum to a "
                    "request-determined extent and its output declares a "
                    "static one"
                )
            return
        if derived is None or (
            int(derived.symbol),
            int(derived.unit),
            int(derived.numerator),
            int(derived.bias),
        ) != (
            int(declared.symbol),
            int(declared.unit),
            int(declared.numerator),
            int(declared.bias),
        ):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: the output declares extent "
                f"{declared.numerator}*{Symbol(int(declared.symbol)).name}/"
                f"{declared.unit}+{declared.bias} and its operands sum to "
                + (
                    "a static extent"
                    if derived is None
                    else f"{derived.numerator}*{Symbol(int(derived.symbol)).name}/"
                    f"{derived.unit}+{derived.bias}"
                )
                + "; A17 makes the two the same number and the engine checks it"
            )

    def _phase_join_output(
        self,
        kernel: Kernel,
        shape: KernelShape,
        *,
        extent: RequestAxis,
        loop: int,
        divisor: int,
    ) -> int:
        """``out0`` of one phase's path, with that phase's derived extent."""
        return self._phase_extent_view(
            self.tensors[kernel.outputs[0]],
            shape,
            extent=extent,
            loop=loop,
            divisor=divisor,
            writable=True,
        )

    def _phase_extent_view(
        self,
        tensor: Tensor,
        shape: KernelShape,
        *,
        extent: RequestAxis,
        loop: int,
        divisor: int,
        writable: bool,
    ) -> int:
        """A view of ``tensor`` whose leading axis states ``extent``."""
        declared = list(self._dims(tensor))
        dims = self._blocked_dims(tensor, shape)
        width = 1
        for element in declared[1:]:
            width *= int(element)
        step = iteration_extent(divisor, extent.numerator, extent.unit)
        if step is None:
            raise RomLoweringError(
                f"tensor {tensor.tensor_id!r}: a loop block of {divisor} symbol "
                f"units is not a whole number of an axis counted as "
                f"{extent.numerator}/{extent.unit}"
            )
        dims[0] = min(step + int(extent.bias), declared[0])
        return self._buffer_view(
            tensor,
            dims=dims,
            strides=None,
            shape=shape,
            loop=loop,
            writable=writable,
            term=DynamicTerm.loop(loop, step * width),
            extent_axis=0,
            extent_unit=extent.unit,
            extent_numerator=extent.numerator,
            extent_bias=extent.bias,
        )

    def _reduced_join_output(
        self,
        kernel: Kernel,
        shape: KernelShape,
        *,
        loop: int | None,
        join_axis: int,
        present: Sequence[str],
    ) -> int:
        """``out0`` of the path where one join operand is absent."""
        tensor = self.tensors[kernel.outputs[0]]
        declared = list(self._dims(tensor))
        dims = self._blocked_dims(tensor, shape)
        axis, static = self._join_extent(present, join_axis)
        if join_axis == 0:
            if axis is None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: with operand "
                    "absent the join has no request-determined extent, so its "
                    "output would present its declared maximum"
                )
            width = 1
            for extent in declared[1:]:
                width *= extent
            term = (
                DynamicTerm.loop(loop, self._axis_step(shape, axis) * width)
                if loop is not None and shape.row_symbolic
                else None
            )
            dims[0] = min(self._axis_block(shape, axis), declared[0])
            return self._buffer_view(
                tensor,
                dims=dims,
                strides=None,
                shape=shape,
                loop=loop,
                writable=True,
                term=term,
                extent_axis=0,
                extent_unit=axis.unit if term is not None else 0,
                extent_numerator=axis.numerator if term is not None else 0,
                extent_bias=axis.bias if term is not None else 0,
            )
        # A17's feature join.  The segments the join keeps are a prefix of the
        # destination's columns, so the reduced path is the same buffer read
        # with a shorter extent on that axis and the buffer's own row stride.
        if axis is not None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: the reduced feature join still "
                "has a request-determined width, and amendment A18 gives a "
                "view one extent axis, which the token axis already holds"
            )
        dims[join_axis] = min(static, declared[join_axis])
        return self._buffer_view(
            tensor,
            dims=dims,
            strides=self._row_major_strides(declared),
            shape=shape,
            loop=loop,
            writable=True,
        )

    def _kernel_predicate(self, kernel: Kernel) -> int:
        condition = self._kernel_condition(kernel)
        if condition is None:
            return NO_ID
        descriptor = self._predicate_descriptor(condition, kernel.kernel_id)
        self._predicated_operators[kernel.kernel_id] = condition
        return descriptor

    def _operand_present(self, kernel: Kernel) -> tuple[int, str] | None:
        """The operand slot that vanishes, and the condition that keeps it."""
        declared = kernel.attributes.get("operand_present_predicate")
        if not declared:
            return None
        entries = dict(declared)
        if len(entries) != 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} names {len(entries)} operands "
                "whose presence the request decides; two independent operands "
                "need four alternative paths and ABI 3.0 gives an instruction "
                "one predicate, so this backend refuses rather than picking "
                "one"
            )
        slot, condition = next(iter(entries.items()))
        index = int(slot)
        if not 0 <= index < len(kernel.inputs):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} names operand {index} as "
                f"conditionally present; it has {len(kernel.inputs)} inputs"
            )
        if self._kernel_condition(kernel) is not None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} is both predicated and names a "
                "conditionally present operand; that is four paths on one "
                "``predicate_id``"
            )
        return index, self._condition_of(str(condition), kernel.kernel_id)

    # -- DeepSeek rolling compressor: explicit ABI-3.0 dataflow ---------
    def _emit_aux_operator(
        self,
        kernel: Kernel,
        family: Major,
        sub: int,
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        suffix: str,
        aux: Sequence[int] = (),
        wait_events: Sequence[int] = (),
        predicate_id: int = NO_ID,
        invert_predicate: bool = False,
        schedule_rows: int = 1,
    ) -> int:
        """Emit one compiler-expanded primitive for a neutral kernel.

        These are not private instructions.  Each descriptor names an existing
        frozen ABI 3.0 DMA or reduction operation, retains the neutral source
        kernel ID, and derives placement from its actual views.
        """

        dependencies = [int(event) for event in wait_events if event != NO_ID]
        # The independent checker reconstructs dependencies at neutral-kernel
        # granularity.  Every primitive expanded from a state update therefore
        # acquires the packed projection's completion, even the flag/reset
        # primitives that do not read its bytes; this is conservative ordering
        # and gives the expansion one clear entry frontier.
        if kernel.kind == "COMPRESS_STATE_UPDATE" and kernel.inputs:
            producer = self._event_of_tensor.get(kernel.inputs[0], NO_ID)
            if producer != NO_ID and producer not in dependencies:
                dependencies.append(producer)
        operator = self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=inputs,
            outputs=outputs,
            aux=aux,
            numeric_profile_id=self._numeric(kernel),
            schedule_id=self._schedule(
                kernel,
                family,
                sub,
                rows_override=max(int(schedule_rows), 1),
                placement_views=(inputs, outputs),
            ),
            counter_class_id=self._counter_class(kernel.counter_class, family),
            source_kernel_id=kernel.index,
            key=f"op.k{kernel.index:05d}.compressor.{suffix}",
        )
        event = self.builder.new_event()
        self.builder.emit(
            family,
            sub,
            descriptor_id=operator,
            wait_set_id=self._wait_set(dependencies),
            signal_event_id=event,
            predicate_id=predicate_id,
            invert_predicate=invert_predicate,
            source_operation_id=kernel.index,
        )
        return event

    def _compressor_flag_object(self, ratio: int) -> int:
        cached = self._compressor_boundary_objects.get(int(ratio))
        if cached is not None:
            return cached
        ports = max(int(self.capability.memory.get("sram", {}).get("banks", 8)), 1)
        port = self._port_cursor % min(ports, 32)
        self._port_cursor += 1
        object_id = self.builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=4,
            source=ObjectSource.zeros(4),
            permissions=int(Permission.READ | Permission.WRITE),
            bank_or_tile=port,
            key=f"obj.compressor.boundary_ratio{ratio}",
        )
        self._compressor_boundary_objects[int(ratio)] = object_id
        return object_id

    def _compressor_ring_view(
        self,
        modulus: int,
        count: int,
        *,
        symbol: Symbol,
        element_offset: int = 0,
        loop: int | None = None,
        loop_stride: int = 0,
        extent_unit: int = 0,
    ) -> int:
        """A slice of ``ring_indices_v1`` at an ABI runtime position."""

        dynamic = [DynamicTerm.symbol(symbol, 1)]
        if loop is not None:
            dynamic.append(DynamicTerm.loop(loop, int(loop_stride)))
        return self._view(
            object_id=self._ring_object(int(modulus)),
            dtype=DType.U32,
            dims=[max(int(count), 1)],
            strides=[1],
            element_offset=int(element_offset),
            dynamic=dynamic,
            permissions=int(Permission.READ),
            extent_unit=int(extent_unit) if loop is not None else 0,
            extent_numerator=1 if loop is not None else 0,
            label="view.compressor_ring",
        )

    def _emit_compressor_boundary_flag(self, kernel: Kernel, ratio: int) -> int:
        """Publish ``POSITION_END mod ratio == 0`` as BOOLEAN_OBJECT false/zero.

        Decode copies the existing ring-table word into the flag.  Prefill
        writes one, making the inverted boolean false even when the prompt ends
        on a group boundary.  Complementary PHASE_IS paths are joined before
        any instruction evaluates the object predicate, so predicate
        evaluation never races the DMA write it observes.
        """

        cached = self._compressor_boundary_predicates.get(ratio)
        if cached is not None:
            return cached

        flag_object = self._compressor_flag_object(ratio)
        flag_view = self._view(
            object_id=flag_object,
            dtype=DType.U32,
            dims=[1],
            strides=[1],
            permissions=int(Permission.READ | Permission.WRITE),
            label="view.compressor_boundary",
        )
        ring_word = self._compressor_ring_view(
            ratio, 1, symbol=Symbol.POSITION_END
        )
        decode_phase = self._phase_predicate("decode")
        prefill_phase = self._phase_predicate("prefill")
        decoded = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.TRANSFER),
            [ring_word],
            [flag_view],
            suffix=f"boundary_ratio{ratio}.decode",
            predicate_id=decode_phase,
        )
        prefilled = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.FILL),
            [],
            [flag_view],
            suffix=f"boundary_ratio{ratio}.prefill",
            aux=[1],
            predicate_id=prefill_phase,
        )
        # Acquire whichever write the request phase issued before any later
        # instruction evaluates BOOLEAN_OBJECT.  A synthetic join event is not
        # needed: these waits retire on the scalar control queue in program
        # order, and their only purpose is to make the later predicate read
        # happen after the flag write.  Putting the wait on the predicated
        # engine instruction itself would be too late because the predicate is
        # evaluated before its wait set.
        for event, predicate in (
            (decoded, decode_phase),
            (prefilled, prefill_phase),
        ):
            self.builder.emit(
                Major.CONTROL,
                Control.WAIT,
                wait_set_id=self._wait_set([event]),
                predicate_id=predicate,
                source_operation_id=kernel.index,
            )
        predicate = self.builder.predicate(
            kind=PredicateKind.BOOLEAN_OBJECT,
            comparison=Comparison.EQ,
            object_id=flag_object,
            element_index=0,
            key=f"pred.compressor.boundary_ratio{ratio}",
        )
        self._compressor_boundary_predicates[ratio] = predicate
        return predicate

    def _compressor_states(
        self, kernel: Kernel, ratio: int, width: int
    ) -> tuple[str, str, int]:
        """Return ``(kv, score, slots)`` for one exact raw-history pair."""

        coefficient = 2 if ratio == 4 else 1
        slots = coefficient * ratio
        if len(kernel.state_reads) != 2 or set(kernel.state_reads) != set(
            kernel.state_writes
        ):
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: rolling compression requires "
                "the same KV and score histories in state_reads/state_writes"
            )
        candidates = [self.states[name] for name in kernel.state_reads]
        kv = [state for state in candidates if state.initialization == "zero"]
        scores = [
            state
            for state in candidates
            if state.initialization == "negative_infinity"
        ]
        if len(kv) != 1 or len(scores) != 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: raw histories need one zero KV "
                "resource and one negative-infinity score resource"
            )
        for state in candidates:
            if (
                state.state_class != "compressor_window"
                or state.dtype != "fp32"
                or self._extent(state.capacity_rows) != slots
                or int(state.row_elements) != width
            ):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: history {state.state_id!r} "
                    f"is not the required FP32 {slots}x{width} direct buffer"
                )
        return kv[0].state_id, scores[0].state_id, slots

    def _compressor_pool_slice(
        self,
        kernel: Kernel,
        shape: KernelShape,
        tensor_id: str,
        *,
        rows: int,
        width: int,
        element_offset: int = 0,
    ) -> int:
        tensor = self.tensors[tensor_id]
        return self._buffer_view(
            tensor,
            dims=[int(rows), int(width)],
            strides=[int(width), 1],
            shape=shape,
            loop=None,
            writable=True,
            blocked=False,
            element_offset=int(element_offset),
        )

    def _emit_compressor_state_transition(
        self,
        kernel: Kernel,
        shape: KernelShape,
        run: LayerRun | None,
        spec: Mapping[str, Any],
    ) -> None:
        """Lower raw-history maintenance and both pool-operand paths.

        Physical history is a no-copy circular buffer.  Absolute position
        ``p`` writes slot ``p mod slots``.  At a decode boundary, reading the
        ring table beginning at ``POSITION_END`` orders the retained rows from
        oldest to newest, which is exactly the released previous/current group
        order and needs no post-pool roll.
        """

        ratio = int(spec["ratio"])
        packed = self.tensors[kernel.inputs[0]]
        packed_dims = self._dims(packed)
        if len(packed_dims) != 3 or packed_dims[1] != 2:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: packed projection must be "
                "[S,2,W]"
            )
        width = int(packed_dims[2])
        coefficient = 2 if ratio == 4 else 1
        if width % coefficient:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: width {width} is not divisible "
                f"by overlap coefficient {coefficient}"
            )
        head_dim = width // coefficient
        kv_state, score_state, slots = self._compressor_states(
            kernel, ratio, width
        )
        boundary = self._emit_compressor_boundary_flag(kernel, ratio)
        prefill_phase = self._phase_predicate("prefill")

        kv_history = self._compressor_history_view(
            kernel,
            kv_state,
            run,
            dims=[slots, width],
            strides=[width, 1],
        )
        score_history = self._compressor_history_view(
            kernel,
            score_state,
            run,
            dims=[slots, width],
            strides=[width, 1],
        )
        reset_kv = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.FILL),
            [],
            [kv_history],
            suffix="history_reset.kv",
            aux=[0],
            predicate_id=prefill_phase,
            schedule_rows=slots,
        )
        reset_scores = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.FILL),
            [],
            [score_history],
            suffix="history_reset.scores",
            aux=[0xFF800000],
            predicate_id=prefill_phase,
            schedule_rows=slots,
        )
        reset_ready = self._emit_guarded_join(
            [
                (reset_kv, prefill_phase, False),
                (reset_scores, prefill_phase, False),
            ],
            source_operation_id=kernel.index,
        )

        # The normal state-update view geometry is still used for its exact
        # prefill pool assembly.  The loop also resolves all explicit token
        # views below; the production ROM policy uses one full-context block.
        loop = self._open_row_loop(kernel, shape)
        if loop is None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: rolling compressor has no "
                "SPAN_TOKENS loop"
            )
        token_rows = int(shape.divisor)
        if token_rows % ratio:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: token block {token_rows} is not "
                f"a whole number of ratio-{ratio} groups"
            )

        order = self._operand_order(kernel, Major.VECTOR, int(Vector.COMPRESS))
        inputs = [
            (
                NO_ID
                if ir_slot is None
                else self._operand_view(
                    kernel,
                    shape,
                    slot=abi_slot,
                    direction="in",
                    name=kernel.inputs[ir_slot],
                    run=run,
                    loop=loop,
                    family=Major.VECTOR,
                    sub=int(Vector.COMPRESS),
                )
            )
            for abi_slot, ir_slot in enumerate(
                self._abi_input_slots(kernel, order)[:MAX_OPERATOR_INPUTS]
            )
        ]
        outputs = [
            self._operand_view(
                kernel,
                shape,
                slot=slot,
                direction="out",
                name=name,
                run=run,
                loop=loop,
                family=Major.VECTOR,
                sub=int(Vector.COMPRESS),
            )
            for slot, name in enumerate(kernel.outputs)
        ]

        packed_term = DynamicTerm.loop(loop, token_rows * 2 * width)
        kv_values = self._buffer_view(
            packed,
            dims=[token_rows, width],
            strides=[2 * width, 1],
            shape=shape,
            loop=loop,
            writable=False,
            term=packed_term,
            extent_unit=1,
            extent_numerator=1,
        )
        score_terms = self._buffer_view(
            packed,
            dims=[1, token_rows, width],
            strides=[token_rows * 2 * width, 2 * width, 1],
            shape=shape,
            loop=loop,
            writable=False,
            element_offset=width,
            term=packed_term,
            extent_axis=1,
            extent_unit=1,
            extent_numerator=1,
        )
        score_tensor = self.tensors[kernel.outputs[1]]
        score_scratch = self._buffer_view(
            score_tensor,
            dims=[token_rows, width],
            strides=[width, 1],
            shape=shape,
            loop=loop,
            writable=True,
            term=DynamicTerm.loop(loop, token_rows * width),
            extent_unit=1,
            extent_numerator=1,
        )
        ape_indices = self._compressor_ring_view(
            ratio,
            token_rows,
            symbol=Symbol.POSITION_START,
            loop=loop,
            loop_stride=token_rows,
            extent_unit=1,
        )
        ape = self._weight_view(kernel.inputs[1], run=run)
        ape_ready = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.GATHER),
            [ape_indices, ape],
            [score_scratch],
            suffix="ape_gather",
            schedule_rows=token_rows,
        )
        packed_event = self._event_of_tensor.get(kernel.inputs[0], NO_ID)
        biased_ready = self._emit_aux_operator(
            kernel,
            Major.REDUCTION,
            int(Reduction.ORDERED_SUM),
            [score_terms, score_scratch],
            [score_scratch],
            suffix="score_plus_ape",
            wait_events=[ape_ready, packed_event],
            schedule_rows=token_rows,
        )

        history_indices = self._compressor_ring_view(
            slots,
            token_rows,
            symbol=Symbol.POSITION_START,
            loop=loop,
            loop_stride=token_rows,
            extent_unit=1,
        )
        kv_written = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.SCATTER),
            [history_indices, kv_values],
            [kv_history],
            suffix="history_append.kv",
            wait_events=[reset_ready, packed_event],
            schedule_rows=token_rows,
        )
        scores_written = self._emit_aux_operator(
            kernel,
            Major.DMA,
            int(Dma.SCATTER),
            [history_indices, score_scratch],
            [score_history],
            suffix="history_append.scores",
            wait_events=[reset_ready, biased_ready, kv_written],
            schedule_rows=token_rows,
        )
        history_ready = scores_written

        prefill_predicate = self._predicate_descriptor(
            str(spec["prefill"]), kernel.kernel_id
        )
        prefill_pool = self._emit_operator(
            kernel,
            Major.VECTOR,
            int(Vector.COMPRESS),
            inputs,
            outputs,
            loop=None,
            predicate_id=prefill_predicate,
            extra_wait_events=[history_ready],
            suffix=".prefill",
        )

        decode_tail = history_ready
        for plane, state_id, output_name in (
            ("kv", kv_state, kernel.outputs[0]),
            ("scores", score_state, kernel.outputs[1]),
        ):
            if ratio == 4:
                halves = (
                    ("previous", 0, 0),
                    ("current", head_dim, ratio * head_dim),
                )
                for label, source_column, destination_offset in halves:
                    source = self._compressor_history_view(
                        kernel,
                        state_id,
                        run,
                        dims=[slots, head_dim],
                        strides=[width, 1],
                        column=source_column,
                    )
                    indices = self._compressor_ring_view(
                        slots,
                        ratio,
                        symbol=Symbol.POSITION_END,
                        element_offset=0 if label == "previous" else ratio,
                    )
                    destination = self._compressor_pool_slice(
                        kernel,
                        shape,
                        output_name,
                        rows=ratio,
                        width=head_dim,
                        element_offset=destination_offset,
                    )
                    decode_tail = self._emit_aux_operator(
                        kernel,
                        Major.DMA,
                        int(Dma.GATHER),
                        [indices, source],
                        [destination],
                        suffix=f"boundary_gather.{plane}.{label}",
                        wait_events=[decode_tail],
                        predicate_id=boundary,
                        invert_predicate=True,
                        schedule_rows=ratio,
                    )
            else:
                source = self._compressor_history_view(
                    kernel,
                    state_id,
                    run,
                    dims=[slots, width],
                    strides=[width, 1],
                )
                indices = self._compressor_ring_view(
                    slots, slots, symbol=Symbol.POSITION_END
                )
                destination = self._compressor_pool_slice(
                    kernel,
                    shape,
                    output_name,
                    rows=slots,
                    width=width,
                )
                decode_tail = self._emit_aux_operator(
                    kernel,
                    Major.DMA,
                    int(Dma.GATHER),
                    [indices, source],
                    [destination],
                    suffix=f"boundary_gather.{plane}",
                    wait_events=[decode_tail],
                    predicate_id=boundary,
                    invert_predicate=True,
                    schedule_rows=slots,
                )

        for name in kernel.outputs:
            self._event_of_tensor.pop(name, None)
            self._compressor_path_events[name] = {
                "prefill": prefill_pool,
                "decode": decode_tail,
            }
        self._predicated_operators[kernel.kernel_id] = (
            f"{spec['prefill']} | ring(POSITION_END,{ratio}) == 0 on decode"
        )
        self._compressor_transition_ratios.add(ratio)
        self.builder.close_loop()

    def _emit_compressor_paths(
        self,
        kernel: Kernel,
        shape: KernelShape,
        family: Major,
        sub: int,
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        order: Sequence[int],
        run: LayerRun | None,
        loop: int | None,
        schedule_rows: int | None,
        extra_close: int,
        spec: Mapping[str, Any],
    ) -> None:
        """Emit prefill-many and decode-one views of a conditional chain."""

        ratio = int(spec["ratio"])
        boundary = self._compressor_boundary_predicates.get(ratio)
        if boundary is None:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: ratio-{ratio} boundary flag was "
                "not emitted before its compressor consumer"
            )
        prefill = self._predicate_descriptor(str(spec["prefill"]), kernel.kernel_id)
        path_inputs = {
            phase: [
                self._compressor_path_events[name][phase]
                for name in kernel.inputs
                if name in self._compressor_path_events
            ]
            for phase in ("prefill", "decode")
        }
        prefill_event = self._emit_operator(
            kernel,
            family,
            sub,
            inputs,
            outputs,
            loop=None,
            schedule_rows=schedule_rows,
            suffix=".prefill",
            predicate_id=prefill,
            extra_wait_events=path_inputs["prefill"],
        )

        compressed_rope_gather = (
            family is Major.DMA
            and sub == int(Dma.GATHER)
            and bool(kernel.attributes.get("compressed", False))
        )
        if compressed_rope_gather:
            stride = int(kernel.attributes.get("position_stride", 0) or 0)
            if stride != ratio or len(order) != 2:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: compressed coefficient "
                    f"gather must bind one index and one ratio-{ratio} source"
                )
            index_name = kernel.inputs[order[0]]
            coefficient_name = kernel.inputs[order[1]]
            coefficient = self.tensors[coefficient_name]
            if coefficient.role not in WEIGHT_ROLES:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: compressed coefficient "
                    f"source {coefficient_name!r} is not immutable"
                )
            # At a boundary the just-completed token has absolute zero-based
            # position p, while the pooled group represents p + 1 - ratio.
            # The quotient table produces floor(p / ratio); presenting the
            # immutable coefficient table with a ratio-row stride turns that
            # ordinal back into ratio * floor(p / ratio), exactly the first
            # position of the completed group.  This uses two ordinary ABI-3.0
            # views and the existing floor_div_indices_v1 object.
            decode_inputs = [
                self._index_view(
                    kernel,
                    shape,
                    index_name,
                    None,
                    count=1,
                    absolute=True,
                    stride=ratio,
                    divisor=ratio,
                ),
                self._weight_view(
                    coefficient_name,
                    run=run,
                    row_step=ratio,
                ),
            ]
            decode_outputs = [
                self._operand_view(
                    kernel,
                    shape,
                    slot=slot,
                    direction="out",
                    name=name,
                    run=run,
                    loop=None,
                    family=family,
                    sub=sub,
                    leading_extent=1,
                )
                for slot, name in enumerate(kernel.outputs)
            ]
        elif family is Major.DMA and sub in (
            int(Dma.GATHER),
            int(Dma.SCATTER),
        ):
            decode_inputs, decode_outputs = self._movement_views(
                kernel,
                shape,
                order,
                run,
                None,
                sub,
                leading_extent=1,
            )
        else:
            decode_inputs = [
                (
                    NO_ID
                    if ir_slot is None
                    else self._operand_view(
                        kernel,
                        shape,
                        slot=abi_slot,
                        direction="in",
                        name=kernel.inputs[ir_slot],
                        run=run,
                        loop=None,
                        family=family,
                        sub=sub,
                        leading_extent=1,
                    )
                )
                for abi_slot, ir_slot in enumerate(
                    self._abi_input_slots(kernel, order)[:MAX_OPERATOR_INPUTS]
                )
            ]
            decode_outputs = [
                self._operand_view(
                    kernel,
                    shape,
                    slot=slot,
                    direction="out",
                    name=name,
                    run=run,
                    loop=None,
                    family=family,
                    sub=sub,
                    leading_extent=1,
                )
                for slot, name in enumerate(kernel.outputs)
            ]
        decode_event = self._emit_operator(
            kernel,
            family,
            sub,
            decode_inputs,
            decode_outputs,
            loop=None,
            schedule_rows=1,
            suffix=".decode",
            predicate_id=boundary,
            invert_predicate=True,
            extra_wait_events=path_inputs["decode"],
        )
        if kernel.kind == "KV_APPEND":
            # The state-read alias and subsequent attention are unconditional:
            # on a non-boundary decode they consume the retained cache rather
            # than a newly appended row.  Publish one unconditional ready event
            # only at this architectural convergence point.
            joined = self._emit_guarded_join(
                [(prefill_event, prefill, False), (decode_event, boundary, True)],
                source_operation_id=kernel.index,
            )
            for name in kernel.outputs:
                self._compressor_path_events.pop(name, None)
                self._event_of_tensor[name] = joined
        else:
            for name in kernel.outputs:
                self._event_of_tensor.pop(name, None)
                self._compressor_path_events[name] = {
                    "prefill": prefill_event,
                    "decode": decode_event,
                }
        self._predicated_operators[kernel.kernel_id] = (
            f"{spec['prefill']} | ring(POSITION_END,{ratio}) == 0 on decode"
        )
        if loop is not None:
            self.builder.close_loop()
        for _ in range(extra_close):
            self.builder.close_loop()

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
        engine = ENGINE_OVERRIDE.get(kernel.kind, engine)
        if kernel.kind == "COMPRESS_PROJECT" and len(kernel.inputs) == 2:
            # The frozen ``VECTOR.COMPRESS`` project sub-case is one operator
            # over *both* compressor matrices: in0 hidden, in1 the KV
            # projection, in2 the gate projection, out0 the packed
            # ``[B, S, 2, N]``.  This export splits it into two kernels of two
            # operands each -- ``compress_project.key_value`` and
            # ``compress_project.score`` -- and each of those is a plain
            # contraction: ``[span, 4096] x [1024, 4096]^T`` accumulated in
            # increasing reduction index, which is what its own attributes say
            # and what ``TENSOR.MATMUL`` executes under the sequential
            # contract.  For BF16 operands the two spellings are bit-identical:
            # the product is exact in binary32 either way, so a materialised
            # product and a fused product-add round at the same place.
            engine = EngineOp(Major.TENSOR, TensorOp.MATMUL, 2, 1)
        family = Major(engine.family)
        if kernel.kind == "STATE_READ":
            if self._kernel_uses_direct_state(kernel):
                # Direct state is already the execution image.  STATE_READ is
                # therefore a view/alias declaration, not an engine action,
                # but its dataflow edge must survive so the first real
                # consumer still waits for the append that produced the rows.
                producers = {
                    self._event_of_tensor[name]
                    for name in kernel.inputs
                    if name in self._event_of_tensor
                }
                producers.update(self._kv_cache_read_events(kernel))
                if len(producers) > 1:
                    raise RomLoweringError(
                        f"kernel {kernel.kernel_id!r}: an alias-only STATE_READ "
                        f"has {len(producers)} distinct producer events"
                    )
                event = next(iter(producers), None)
                for name in kernel.outputs:
                    if event is None:
                        self._event_of_tensor.pop(name, None)
                    else:
                        self._event_of_tensor[name] = event
                condition = self._kernel_condition(kernel)
                if condition is not None:
                    # The alias emits no instruction to predicate.  Recording
                    # the resolved condition proves it was intentionally
                    # absorbed; the consuming operator carries the condition.
                    self._predicated_operators[kernel.kernel_id] = condition
                return
            # A state read is one instruction and no operator descriptor, so it
            # takes the kernel's predicate directly.  This is the shape A18
            # names: the compressed-KV valid view leads with
            # ``context_groups_ratioN``, which is zero until the context holds
            # one whole group, and a zero-extent view is refused -- so the read
            # must not be issued rather than issued against nothing.
            self.builder.emit(
                family,
                engine.sub,
                descriptor_id=self._state_for(kernel),
                predicate_id=self._kernel_predicate(kernel),
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
        schedule_rows: int | None = None
        groups = self._feature_group_count(kernel, family, engine.sub, shape)
        if groups > 1:
            self._emit_feature_grouped_contraction(kernel, shape, run, groups)
            return
        if family is Major.REDUCTION and engine.sub == int(Reduction.EXPERT_SUM):
            # A weighted reduction across a non-token axis is stated one token
            # at a time; see _open_token_loop.  One dispatch covers one row, so
            # the schedule is priced for one row rather than for the block the
            # iteration domain names.
            loop = self._open_token_loop(kernel)
            inputs, outputs = self._expert_sum_views(kernel, shape, run, loop)
            schedule_rows = 1
            self._emit_operator(
                kernel,
                family,
                engine.sub,
                inputs,
                outputs,
                loop=loop,
                schedule_rows=schedule_rows,
            )
            return
        if kernel.kind == "INDEX_SCORE":
            self._emit_index_score(kernel, run)
            return
        if family is Major.DMA and self._is_row_local_gather(kernel, engine.sub):
            loop = self._open_token_loop(kernel)
            inputs, outputs = self._row_local_gather_views(kernel, shape, loop)
            self._emit_operator(
                kernel,
                family,
                engine.sub,
                inputs,
                outputs,
                loop=loop,
                schedule_rows=1,
            )
            return
        compressor_spec = self._compressor_predicate_of(kernel)
        if kernel.kind == "COMPRESS_STATE_UPDATE":
            if compressor_spec is None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: COMPRESS_STATE_UPDATE has no "
                    "two-phase rolling predicate declaration"
                )
            self._emit_compressor_state_transition(
                kernel, shape, run, compressor_spec
            )
            return
        loop = self._open_row_loop(kernel, shape)
        # A state plane whose leading extent the request sets needs a loop that
        # resolves it -- one block over the whole capacity, running once.  A18
        # refuses a declaration nothing walks, and leaving it undeclared is what
        # let the attention join read its maximum.
        planes = self._request_sized_planes(kernel)
        consumer_paths = self._phase_consumer_paths(kernel)
        context = None
        context_divisor = 0
        if planes:
            plane = self.tensors[planes[0]]
            _s, _m, plane_axis = self._leading_symbol(plane)
            context_divisor = (
                self._dims(plane)[0]
                * int(plane_axis.unit)
                // max(int(plane_axis.numerator), 1)
            )
            context = self._open_context_loop(
                kernel, self._dims(plane)[0], plane_axis
            )
        elif consumer_paths is not None and any(
            int(extent.symbol) != int(Symbol.SPAN_TOKENS)
            for _slot, phases in consumer_paths.items()
            for extent in phases.values()
        ):
            # A consumer of a phase-split join reads a *context*-sized row
            # space in one phase and a span-sized one in the other, and A18
            # resolves an extent only through a loop that walks it.  This
            # kernel binds no request-sized state plane of its own, so the loop
            # that resolves the context form has to be opened for the operand
            # rather than for a plane: one block over the whole context, run
            # once, exactly as ``_open_context_loop`` does for a plane.
            context_divisor = int(self.capability.limits["max_context_positions"])
            context = self._open_context_loop(
                kernel, context_divisor, RequestAxis(Symbol.CONTEXT_LENGTH)
            )
        if kernel.kind == "EXPERT_DISPATCH" and len(kernel.outputs) > 1:
            self._emit_routed_row_identity(kernel, shape, loop)
        order = self._operand_order(kernel, family, engine.sub)
        if family is Major.DMA and engine.sub in (int(Dma.GATHER), int(Dma.SCATTER)):
            inputs, outputs = self._movement_views(
                kernel, shape, order, run, loop, engine.sub
            )
        else:
            inputs = [
                (
                    NO_ID
                    if ir_slot is None
                    else self._operand_view(
                        kernel,
                        shape,
                        slot=abi_slot,
                        direction="in",
                        name=kernel.inputs[ir_slot],
                        run=run,
                        loop=loop,
                        family=family,
                        sub=engine.sub,
                        context=context,
                    )
                )
                for abi_slot, ir_slot in enumerate(
                    self._abi_input_slots(kernel, order)[:MAX_OPERATOR_INPUTS]
                )
            ]
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
                    context=context,
                )
                for abi_slot, name in enumerate(kernel.outputs[:MAX_OPERATOR_OUTPUTS])
            ]
        innermost = context if context is not None else loop
        closes = 1 if context is not None and loop is not None else 0
        if family is Major.REDUCTION and engine.sub == int(Reduction.GROUPED_CONCAT):
            self._check_join_extent(kernel, int(kernel.attributes.get("axis", 0)))
        present = self._operand_present(kernel)
        if compressor_spec is not None:
            if present is not None or consumer_paths is not None:
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r}: a rolling-compressor path "
                    "cannot also carry an independent optional/phase split"
                )
            self._emit_compressor_paths(
                kernel,
                shape,
                family,
                engine.sub,
                inputs,
                outputs,
                order=order,
                run=run,
                loop=innermost,
                schedule_rows=schedule_rows,
                extra_close=closes,
                spec=compressor_spec,
            )
            return
        if present is None and consumer_paths is not None:
            self._emit_phase_consumer(
                kernel,
                shape,
                family,
                engine.sub,
                inputs,
                outputs,
                order=order,
                paths=consumer_paths,
                loop=innermost,
                schedule_rows=schedule_rows,
                extra_close=closes,
                context_loop=context,
                context_divisor=context_divisor,
            )
            return
        if present is None:
            self._emit_operator(
                kernel,
                family,
                engine.sub,
                inputs,
                outputs,
                loop=innermost,
                schedule_rows=schedule_rows,
                extra_close=closes,
            )
            return
        self._emit_alternative_paths(
            kernel,
            shape,
            family,
            engine.sub,
            inputs,
            outputs,
            order=order,
            absent=present[0],
            condition=present[1],
            loop=innermost,
            row_loop=loop,
            schedule_rows=schedule_rows,
            extra_close=closes,
            context_loop=context,
            context_divisor=context_divisor,
        )

    def _emit_alternative_paths(
        self,
        kernel: Kernel,
        shape: KernelShape,
        family: Major,
        sub: int,
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        order: Sequence[int],
        absent: int,
        condition: str,
        loop: int | None,
        row_loop: int | None,
        schedule_rows: int | None,
        extra_close: int,
        context_loop: int | None = None,
        context_divisor: int = 0,
    ) -> None:
        """One operator, two complementary paths, one event.

        ``operand_present_predicate`` says the operator issues either way and
        one *operand* is there only under a condition.  ABI 3.0 predicates an
        instruction, not an operand, so the pair is the lowering: the full
        operand row under the condition, the reduced row under its inverse.
        The two paths cannot share an event -- ABI 3.0 events are
        single-assignment and the verifier says so -- and a consumer cannot
        wait on the path that did not run, because a wait on an unsignalled
        event is a device fault.  So the pair is followed by an unpredicated
        ``CONTROL.NOP`` that publishes the event the *result* is ordered by: it
        is the join of the two paths, it retires whichever path ran, and it is
        what keeps the consumer's dependency real rather than dropped.

        Two things change on the reduced path and both matter.  The wait set
        drops the vanished operand's producer -- that producer is predicated
        off by the same condition and will never signal, and a wait on an
        unsignalled event is a device fault, not a stall.  And, for a join, the
        output's extent drops that operand's contribution: A17 makes the output
        the sum of the inputs, so a path that keeps the full extent would
        declare rows no operand supplies.

        Which slots may actually be emptied is not a guess, and it is no longer
        this function's to decide.  A slot the *graph* declares empty is an
        ``absent_operands`` statement checked at neutral admission against the
        frozen ``OPTIONAL_INPUT_SLOTS``, and ``_abi_input_slots`` has already
        placed it -- there is nothing conditional about it, which is the whole
        point of the static form.  What is left here is the conditional form,
        and it empties a slot only where the row reads it through
        ``optional_input`` and can join what remains:
        ``REDUCTION.GROUPED_CONCAT``.

        ``ROUTE.INDEX_TOPK``'s ``in0`` is the case that changed and the reduced
        path keeps binding it anyway.  Amendment A20 makes the slot optional, so
        A19's "every other frozen operand row is mandatory" no longer covers it
        and emptying it would now execute; it is still not what this path should
        do.  A19 defines the zero-candidate case *with* a score view -- the
        operator reads the view's shape, reads no value from it, and emits the
        joined window -- and the reduced path is exactly that case, so binding
        the view is the operand row the amendment describes rather than a second
        spelling of it. Emptying it would additionally move the span off the
        score view and onto ``out0``, which is a different derivation for a path
        whose only difference is meant to be a dropped ordering dependency.
        """
        predicate = self._predicate_descriptor(condition, kernel.kernel_id)
        slots = self._abi_input_slots(kernel, order)
        abi_slot = next(
            (index for index, ir in enumerate(slots) if ir == absent), None
        )
        optional = family is Major.REDUCTION and sub == int(Reduction.GROUPED_CONCAT)
        reduced_inputs = list(inputs)
        reduced_outputs = list(outputs)
        if optional:
            if abi_slot is None or abi_slot >= len(reduced_inputs):
                raise RomLoweringError(
                    f"kernel {kernel.kernel_id!r} names input {absent} as "
                    "conditionally present, and no ABI slot carries it"
                )
            reduced_inputs[abi_slot] = NO_ID
            reduced_outputs[0] = self._reduced_join_output(
                kernel,
                shape,
                loop=row_loop,
                join_axis=int(kernel.attributes.get("axis", 0)),
                present=[
                    name
                    for index, name in enumerate(kernel.inputs)
                    if index != absent
                ],
            )
        self._operand_alternatives[kernel.kernel_id] = condition
        present_paths = self._phase_present_paths(
            kernel,
            shape,
            condition=condition,
            context_loop=context_loop,
            context_divisor=context_divisor,
            declared_output=outputs[0] if outputs else NO_ID,
        )
        path_events: list[tuple[int, int, bool]] = []
        if present_paths is None:
            event = self._emit_operator(
                kernel,
                family,
                sub,
                inputs,
                outputs,
                loop=None,
                schedule_rows=schedule_rows,
                predicate_id=predicate,
            )
            path_events.append((event, predicate, False))
        else:
            for phase, path_predicate, path_output in present_paths:
                event = self._emit_operator(
                    kernel,
                    family,
                    sub,
                    inputs,
                    [path_output, *outputs[1:]],
                    loop=None,
                    schedule_rows=schedule_rows,
                    suffix=f".{phase}",
                    predicate_id=path_predicate,
                )
                path_events.append((event, path_predicate, False))
        absent_event = self._emit_operator(
            kernel,
            family,
            sub,
            reduced_inputs,
            reduced_outputs,
            loop=None,
            schedule_rows=schedule_rows,
            suffix=".absent",
            predicate_id=predicate,
            invert_predicate=True,
            wait_inputs=[
                name for index, name in enumerate(kernel.inputs) if index != absent
            ],
        )
        path_events.append((absent_event, predicate, True))
        join = self._emit_guarded_join(
            path_events, source_operation_id=kernel.index
        )
        for name in kernel.outputs:
            self._event_of_tensor[name] = join
        if loop is not None:
            self.builder.close_loop()
        for _ in range(extra_close):
            self.builder.close_loop()

    def _emit_operator(
        self,
        kernel: Kernel,
        family: Major,
        sub: int,
        inputs: Sequence[int],
        outputs: Sequence[int],
        *,
        loop: int | None,
        schedule_rows: int | None = None,
        suffix: str = "",
        extra_close: int = 0,
        predicate_id: int | None = None,
        invert_predicate: bool = False,
        wait_inputs: Sequence[str] | None = None,
        extra_wait_events: Sequence[int] = (),
        event: int | None = None,
    ) -> int:
        """Bind one operator descriptor, issue it, and close its loop.

        ``predicate_id`` defaults to the kernel's own declared predicate;
        passing one states an alternative path explicitly.  ``wait_inputs``
        narrows the producers this instruction waits on -- the reduced path of
        a conditionally present operand must not wait on the producer that
        vanished with it, because that producer is predicated off by the same
        condition and will never signal.  ``event`` lets both paths of such a
        pair publish the *same* event, so a consumer waits on one producer and
        exactly one of the two paths signals it.

        ``extra_close`` closes further enclosing loops, innermost first, for an
        operator that needed more than one -- ``INDEX_SCORE`` needs a token loop
        and a context loop because its output has a request-dependent extent on
        two axes and amendment A18 gives a view one.

        ``suffix`` distinguishes several operators emitted for one kernel --
        the block-diagonal groups of a feature-grouped contraction -- so that
        each gets its own descriptor key while every one of them still names
        the kernel it came from.
        """
        operator = self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=inputs,
            outputs=outputs,
            aux=self._aux(kernel, family, sub),
            numeric_profile_id=self._numeric(kernel),
            schedule_id=self._schedule(
                kernel, family, sub, rows_override=schedule_rows
            ),
            counter_class_id=self._counter_class(kernel.counter_class, family),
            source_kernel_id=kernel.index,
            key=f"op.k{kernel.index:05d}{suffix}",
        )
        producers = [
            self._event_of_tensor[name]
            for name in (kernel.inputs if wait_inputs is None else wait_inputs)
            if name in self._event_of_tensor
        ]
        producers.extend(self._kv_cache_read_events(kernel))
        producers.extend(int(item) for item in extra_wait_events if item != NO_ID)
        if (
            kernel.kind == "TOKEN_APPEND"
            and self._token_step_fence_event != NO_ID
            and self._token_step_fence_event not in producers
        ):
            producers.append(self._token_step_fence_event)
        wait = self._wait_set(producers)
        if event is None:
            event = self.builder.new_event()
        if predicate_id is None:
            predicate_id = self._kernel_predicate(kernel)
        self.builder.emit(
            family,
            sub,
            descriptor_id=operator,
            wait_set_id=wait,
            signal_event_id=event,
            predicate_id=predicate_id,
            invert_predicate=invert_predicate,
            source_operation_id=kernel.index,
        )
        if loop is not None:
            self.builder.close_loop()
        for _ in range(extra_close):
            self.builder.close_loop()
        # Only already-emitted producers enter a wait set, so a loop-carried
        # value is ordered by the loop body itself rather than by a wait on an
        # event the first iteration cannot yet have signalled.
        for name in kernel.outputs:
            self._event_of_tensor[name] = event
        if kernel.kind == "KV_APPEND":
            self._record_kv_cache_write(kernel, event)
        return event

    def _kv_cache_groups(self, resources: Sequence[str]) -> list[str]:
        """Physical ordinary-HBM Qwen KV groups named by state effects."""

        groups: list[str] = []
        for state_id in resources:
            state = self.states.get(state_id)
            placement = self._state_slot.get(state_id)
            if state is None or placement is None or state.state_class != "kv_cache":
                continue
            group = str(placement[0])
            if group not in groups:
                groups.append(group)
        return groups

    def _kv_cache_read_events(self, kernel: Kernel) -> list[int]:
        events: list[int] = []
        for group in self._kv_cache_groups(kernel.state_reads):
            events.extend(self._kv_cache_write_events.get(group, ()))
        return list(dict.fromkeys(events))

    def _record_kv_cache_write(self, kernel: Kernel, event: int) -> None:
        if event == NO_ID:
            return
        for group in self._kv_cache_groups(kernel.state_writes):
            frontier = self._kv_cache_write_events.setdefault(group, [])
            if int(event) not in frontier:
                frontier.append(int(event))

    def _state_for(self, kernel: Kernel) -> int:
        for state_id in (*kernel.state_writes, *kernel.state_reads):
            if state_id in self._state_descriptor:
                return self._state_descriptor[state_id]
        raise RomLoweringError(
            f"kernel {kernel.kernel_id!r} is a state operation naming no declared "
            "state resource"
        )

    def _kernel_uses_direct_state(self, kernel: Kernel) -> bool:
        """Whether every state resource named by ``kernel`` is direct HBM."""

        named = (*kernel.state_reads, *kernel.state_writes)
        if not named:
            return False
        direct = {
            _is_direct_buffer_state(self.states[state_id].state_class)
            for state_id in named
            if state_id in self.states
        }
        if len(direct) > 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r} mixes direct-buffer and "
                "transactional state resources"
            )
        return direct == {True}

    # -- link fabric -----------------------------------------------------
    def _admitted_topology(self) -> Mapping[str, int]:
        """The one TOPOLOGY descriptor this lowering has already emitted."""
        ids = self.builder.table.ids_of_type(int(ExtendedDescriptorType.TOPOLOGY))
        if len(ids) != 1:
            raise RomLoweringError(
                f"the deployment declares {len(ids)} TOPOLOGY descriptors; an "
                "on-fabric step is derived against exactly one admitted topology"
            )
        return self.builder.table[ids[0]].payload

    def _participant_count(self, step: LinkStep) -> int:
        """How many participants ``step`` addresses, derived, not declared.

        Amendment A14 (wire format section 12.5) makes a collective's member
        set a function of ``participant_scope`` and the admitted topology::

            NODE     -> node_count
            RETICLE  -> reticle_count
            TILE     -> reticle_count * tiles_per_reticle

        with ``route_group_count`` partitioning that set and ``group_id``
        selecting one part.  The LINK engine derives exactly this and refuses a
        descriptor whose ``participant_count`` disagrees, so the backend must
        derive it too rather than assert a number of its own.  Before A14 the
        derivation was ``node_count`` alone, and a wafer declares one node, so
        every wafer collective came out degenerate however the backend counted.
        """
        if step.participant_count is not None:
            return int(step.participant_count)
        topology = self._admitted_topology()
        reticles = int(topology["reticle_count"])
        tiles = int(topology["tiles_per_reticle"])
        scope = ParticipantScope(int(step.participant_scope))
        if scope is ParticipantScope.NODE:
            count = int(topology["node_count"])
        elif scope is ParticipantScope.RETICLE:
            count = reticles
        else:
            count = reticles * tiles
        if count < 1:
            raise RomLoweringError(
                f"on-fabric step {step.label!r} is {scope.name}-scoped, and the "
                f"admitted topology declares {reticles} reticles of {tiles} "
                "tiles, so that fabric does not exist"
            )
        groups = int(topology["route_group_count"])
        if step.group_id != NO_ID and groups > 1:
            if count % groups:
                raise RomLoweringError(
                    f"on-fabric step {step.label!r} names route group "
                    f"{step.group_id}, but {count} participants do not divide "
                    f"into {groups} equal contiguous groups"
                )
            count //= groups
        return count

    def _emit_links(self, run: LayerRun, steps: Iterable[LinkStep]) -> None:
        """Issue one compressed body's on-fabric steps.

        ``participant_scope`` states which fabric each step addresses and the
        count follows from the topology (:meth:`_participant_count`), so a
        wafer's tile-scoped collectives now say what they mean instead of
        borrowing the one node a ``WAFER_LOGICAL_DEVICE`` declares.
        """
        for step in steps:
            count = self._participant_count(step)
            local, remote = self._link_endpoints(count, step.byte_extent)
            communication = self.builder.communication(
                collective_op=step.collective_op,
                local_object_id=local,
                remote_object_id=remote,
                # ``local_tile_id`` of the admitted topology is this endpoint,
                # and it is a member of the participant set the step names, so
                # it can be the root of a multicast, gather or scatter.
                source_node=0,
                destination_node=0,
                group_id=step.group_id,
                route_class=step.route_class,
                byte_extent=step.byte_extent,
                participant_count=count,
                participant_scope=ParticipantScope(int(step.participant_scope)),
                reduction_numeric_id=self._link_reduction_numeric(step),
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

    def _collapse_event_frontier(self, events: Sequence[int]) -> list[int]:
        """Reduce an event frontier until one ABI wait set can name it."""

        level = sorted(set(int(event) for event in events if event != NO_ID))
        if not level:
            raise RomLoweringError("a terminal token step has no work events")
        while len(level) > MAX_WAIT_PRODUCERS:
            collapsed: list[int] = []
            for offset in range(0, len(level), MAX_WAIT_PRODUCERS):
                chunk = level[offset : offset + MAX_WAIT_PRODUCERS]
                joined = self.builder.new_event()
                self.builder.emit(
                    Major.CONTROL,
                    Control.NOP,
                    wait_set_id=self._wait_set(chunk),
                    signal_event_id=joined,
                )
                collapsed.append(joined)
            level = collapsed
        return level

    def _emit_terminal_fence(self) -> int:
        """Acquire every issued work event and publish a fenced completion."""

        unconditional: list[int] = []
        conditional: dict[tuple[int, bool], list[int]] = {}
        # Snapshot the work program before adding convergence instructions.
        work = tuple(self.builder.instructions)
        # An unconditional event already acquired by a later unconditional
        # signaller is transitively covered by that signaller.  Keep every
        # event whose only consumers are predicated: on the path where those
        # consumers are skipped, their producer still has to finish before the
        # token is published.
        acquired_by_unconditional_signal: set[int] = set()
        for instruction in work:
            if (
                instruction.predicate_id != NO_ID
                or instruction.signal_event_id == NO_ID
                or instruction.wait_set_id == NO_ID
            ):
                continue
            wait = self.builder.table[int(instruction.wait_set_id)].payload
            acquired_by_unconditional_signal.update(
                int(wait[f"producer_{slot}"])
                for slot in range(int(wait["producer_count"]))
            )

        for instruction in work:
            event = int(instruction.signal_event_id)
            if event == NO_ID:
                continue
            if instruction.predicate_id == NO_ID:
                if event not in acquired_by_unconditional_signal:
                    unconditional.append(event)
                continue
            guard = (
                int(instruction.predicate_id),
                bool(instruction.flags & int(InstructionFlag.PREDICATE_INVERT)),
            )
            conditional.setdefault(guard, []).append(event)

        if conditional:
            # A predicated-off producer never signals.  Guard each wait with
            # exactly its producer's predicate, then publish one unconditional
            # event after all live guarded waits have retired.
            for (predicate, inverted), events in sorted(conditional.items()):
                for offset in range(0, len(events), MAX_WAIT_PRODUCERS):
                    self.builder.emit(
                        Major.CONTROL,
                        Control.WAIT,
                        wait_set_id=self._wait_set(
                            events[offset : offset + MAX_WAIT_PRODUCERS]
                        ),
                        predicate_id=predicate,
                        invert_predicate=inverted,
                    )
        frontier = self._collapse_event_frontier(unconditional)
        fenced = self.builder.new_event()
        self.builder.emit(
            Major.CONTROL,
            Control.FENCE,
            wait_set_id=self._wait_set(frontier),
            signal_event_id=fenced,
        )
        return fenced

    def _link_reduction_numeric(self, step: LinkStep) -> int:
        """The numeric contract of an arithmetic collective, or ``NO_ID``.

        A reduction's result lands in the same participant slot its
        contributions came from, so the contract's input and output storage
        formats are the same one, and the engine widens to binary32 and rounds
        once under the contract's own reduction order.  A movement collective
        reduces nothing and names nothing.
        """
        if not step.reduction_contract:
            return NO_ID
        key = (step.reduction_contract, step.reduction_dtype)
        cached = self._link_numeric.get(key)
        if cached is not None:
            return cached
        dtype = self._dtype(step.reduction_dtype)
        descriptor = self.builder.numeric(
            contract=step.reduction_contract,
            input_dtype=dtype,
            output_dtype=dtype,
            accumulator_dtype=DType.FP32,
            reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
            key=f"numeric.link.{len(self._link_numeric):02d}",
        )
        self._link_numeric[key] = descriptor
        return descriptor

    def _link_endpoints(self, count: int, extent: int) -> tuple[int, int]:
        """The local slot array and the remote participant array of one step.

        A collective's remote endpoint is the **participant array**: one slot of
        ``byte_extent`` per participant, and participant ``k`` owns
        ``[remote_offset + k * byte_extent, + byte_extent)``.  A gather or an
        all-gather concatenates the same number of slots into the local
        endpoint, so the two arrays are the same size.  Both are dedicated
        staging objects rather than a borrowed activation buffer, because an
        activation buffer is sized for one operand and a participant array is
        sized for the fabric.

        The remote array carries ``REMOTE``: there is no implicit coherent
        global address space here, so an object another participant may touch
        has to be explicitly exported.
        """
        nbytes = max(int(count) * int(extent), 64)
        cached = self._link_endpoint_objects.get(nbytes)
        if cached is not None:
            return cached
        index = len(self._link_endpoint_objects)
        local = self.builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
            key=f"obj.link.local.{index:02d}",
        )
        remote = self.builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE | Permission.REMOTE),
            key=f"obj.link.remote.{index:02d}",
        )
        self._link_endpoint_objects[nbytes] = (local, remote)
        return local, remote

    # -- program ---------------------------------------------------------
    def emit_program(self) -> None:
        analysis = self.analysis
        self._prove_run_predicates_agree()
        emitted: list[Kernel] = []
        state_descriptors = sorted(set(self._state_descriptor.values()))
        for descriptor in state_descriptors:
            self.builder.emit(Major.STATE, State.PREPARE, descriptor_id=descriptor)
        for kernel in analysis.prologue:
            emitted.append(kernel)
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
                emitted.append(column[0])
                self._emit_kernel(column[0], run=run)
                self._emit_links(run, after.get(position, ()))
            self.builder.close_loop()
        for kernel in analysis.epilogue:
            emitted.append(kernel)
            if self._direct_state_groups and kernel.kind == "TOKEN_APPEND":
                self._deferred_token_appends.append(kernel)
                continue
            self._emit_kernel(kernel, run=None)
        self._prove_predicates_lowered(emitted)
        self._require_on_device_selection()
        for descriptor in state_descriptors:
            self.builder.emit(Major.STATE, State.COMMIT, descriptor_id=descriptor)
        if self._deferred_token_appends:
            self._token_step_fence_event = self._emit_terminal_fence()
            for kernel in self._deferred_token_appends:
                self._emit_kernel(kernel, run=None)
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
        span_max = int(self.capability.limits["max_context_positions"])
        max_new = _declared_new_token_budget(policy_body, span_max)
        # One host window serves both directions: the host stages the prompt
        # into it and on-device selection appends each new token to it.  The
        # graph's token-stream input is a view of that window, not a second
        # buffer -- a separate object would be one nothing could fill.
        token_bytes = max((self._padded_symbol_bound() + max_new) * 4, 4096)
        token_ring = builder.memory_object(
            storage_class=StorageClass.HOST,
            size_bytes=token_bytes,
            source=ObjectSource.zeros(token_bytes),
            permissions=int(
                Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE
            ),
            key="obj.token_ring",
        )
        stream = self._token_stream_input()
        if stream is not None:
            key = self._buffer_key(stream)
            self._buffer_object[key] = token_ring
            self._buffer_place[key] = BufferPlacement(
                StorageClass.HOST,
                token_bytes,
                int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
                0,
            )
            self._substituted_inputs[stream] = "host_input_window"
        generation_policy = builder.generation_policy(
            eos_token_ids=[int(i) for i in policy_body.get("eos_token_ids", [0])][:8],
            max_new_tokens=max_new,
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
        # Amendment A3.  What was predicated, on what condition, and what the
        # frozen predicate kinds could not state.  A declared predicate that is
        # not lowered is invisible at runtime -- the operator issues where the
        # source skips it -- so this is published beside the program rather
        # than left to be inferred from ``instructions.predicated_off``.  A
        # graph that declares no predicate says nothing here and its manifest
        # is byte-identical to the one it had before predicates existed, which
        # is what keeps the Qwen deployment digest a fixed point of this
        # change.
        predicates = self._predicate_report()
        if predicates:
            builder.notes["rom_predicates"] = predicates
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
            "state_row_widenings": dict(sorted(self._state_row_widenings.items())),
            "substituted_inputs": dict(sorted(self._substituted_inputs.items())),
            "token_block_rows": int(self.policy.token_block_rows or 0),
            "source_kernel_count": len(self.graph.kernels),
            "state_groups": self._state_group_count,
            "tile_mapping_owner": "schedule_descriptor",
        }
        if self._direct_state_groups:
            builder.notes["rom_lowering"]["direct_buffer_state"] = {
                "classes": sorted(set(self._direct_state_groups.values())),
                "physical_groups": len(self._direct_state_groups),
                "storage_class": StorageClass.HBM.name,
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
