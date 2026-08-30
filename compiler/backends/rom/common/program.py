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

from compiler.ir.v3.kernel_ir import (
    Kernel,
    KernelGraph,
    StateResource,
    Symbolic,
    Tensor,
    require_neutral,
)
from compiler.ir.v3.lowering import EngineOp, KERNEL_TO_ENGINE
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
    LayoutClass,
    MAX_RANK,
    Phase,
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

#: ``TA-ABI3-OPCONV-1`` amendment A7: the sequential contract is the scalar
#: oracle used for numeric qualification; execution declares the blocked
#: contract.  The substitution is applied identically for ROM and HBM, so the
#: two deployments stay bit-comparable, and it is recorded in the manifest.
EXECUTION_CONTRACT: Mapping[str, str] = {
    "bf16_bf16_fp32_sequential_rne_v1": "bf16_bf16_fp32_blocked_rne_v1",
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

#: ABI input slots the operand convention requires to be ``NO_ID``, by neutral
#: kind.  ``VECTOR.COMPRESS`` sub-case 2 is the case: its ``in1`` is the
#: projection matrix, which a state update has none of, while its ``in2`` is
#: the position embedding, which is exactly what the APE table is.  The
#: operands are not renumbered around the hole -- they are placed either side
#: of it.  This mirrors ``_ABI_EMPTY_INPUT_SLOTS`` in
#: ``compiler/backends/hbm_sram/plan.py``: one convention, two backends.
ABI_EMPTY_INPUT_SLOTS: Mapping[str, tuple[int, ...]] = {
    "COMPRESS_STATE_UPDATE": (1,),
}

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

MHC_SUBCASE: Mapping[str, int] = {
    "HYPER_CONNECT_PRE": 0,
    "HYPER_CONNECT_POST": 1,
    "HYPER_CONNECT_HEAD": 2,
}
SCALE_SUBCASE: Mapping[str, int] = {"SCALE": 0, "MUL": 1, "SIGMOID": 2}

#: Neutral kinds whose *whole* content is an ordered sum, and which therefore
#: state their association in the graph rather than leaving it to a contract
#: name.
REDUCTION_KINDS = frozenset({"EXPERT_REDUCE", "ORDERED_SUM", "PARTITION_SUM"})

#: Spellings the exporters use for a reduction association, and the frozen ABI
#: order each names.  ``canonical_balanced_binary32_tree`` and ``pairwise_tree``
#: are the same NUM-6.1 tree written by two exporters.
DECLARED_REDUCTION_ORDER: Mapping[str, ReductionOrder] = {
    "balanced_tree": ReductionOrder.PAIRWISE_TREE,
    "canonical_balanced_binary32_tree": ReductionOrder.PAIRWISE_TREE,
    "pairwise_tree": ReductionOrder.PAIRWISE_TREE,
    "blocked_ascending": ReductionOrder.BLOCKED_ASCENDING,
    "sequential_ascending": ReductionOrder.SEQUENTIAL_ASCENDING,
}

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
    #: Amendment A18's unit: how many of ``symbol``'s units one element of the
    #: blocked axis holds.  ``rows``, ``block`` and every view extent are in the
    #: *axis's* units; the loop's ``bound_divisor`` is in the symbol's, so it is
    #: ``block * unit``.  One for a token axis, four for a ratio-4 group axis.
    unit: int = 1


#: Neutral symbol name -> the frozen runtime-symbol registry.
@dataclass(frozen=True)
class RequestAxis:
    """A neutral axis name resolved to an A5 symbol and an A18 unit.

    ``unit`` is how many of the symbol's units one element of the axis holds:
    a compressed group of four tokens is ``SPAN_TOKENS`` in units of four.
    Amendment A18 (wire format section 12.8) put the unit on the view rather
    than in the registry, and section 4 is why -- ``span_groups_ratio4`` names
    one model's compression ratio, and the frozen registries do not name a
    model.  A division of a symbol already in the registry is not a new symbol.
    """

    symbol: Symbol
    unit: int = 1


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
    # The compressor's group counts.  Each is a registered symbol divided by a
    # pinned compression ratio, which is exactly what an A18 unit states; before
    # the amendment there was no way to say it and all 704 tensors leading with
    # one of these presented their declared maximum -- 65,536 groups for a
    # 4-token request.  The ``attention_rows_*`` and ``selected_rows_*`` names
    # are deliberately absent: they are ``REDUCTION.GROUPED_CONCAT`` output
    # extents, and A17 already makes a join's output the sum of its inputs.
    "span_groups_ratio4": RequestAxis(Symbol.SPAN_TOKENS, 4),
    "span_groups_ratio128": RequestAxis(Symbol.SPAN_TOKENS, 128),
    "context_groups_ratio4": RequestAxis(Symbol.CONTEXT_LENGTH, 4),
    "context_groups_ratio128": RequestAxis(Symbol.CONTEXT_LENGTH, 128),
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
        self._link_endpoint_objects: dict[int, tuple[int, int]] = {}
        self._link_numeric: dict[tuple[str, str], int] = {}
        self._link_instruction_count = 0
        self._queue_cursor: dict[int, int] = {}
        self._contract_substitutions: dict[str, str] = {}
        self._state_class_aliases: dict[str, str] = {}
        self._state_row_widenings: dict[str, dict[str, int]] = {}
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
        order = self._reduction_order(contract, kernel.kind, attributes)
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

    @staticmethod
    def _reduction_order(
        contract: str, kind: str, attributes: Mapping[str, Any] = {}
    ) -> ReductionOrder:
        """Amendment A8: RMSNorm sums in a balanced tree, not sequentially.

        A reduction operator is the one place where the association is the
        whole content of the operation rather than an implementation detail of
        one, and the neutral IR states it: the mHC branch reduction declares
        ``pairwise_tree`` because its frozen reference reduces four binary32
        products with the NUM-6.1 balanced tree.  Deriving that from the
        contract *name* instead would have made it sequential, which is a
        different number.  The declaration is honoured only for the reduction
        kinds, because elsewhere the graph states the association of the
        qualification oracle while execution declares amendment A7's blocked
        substitute -- two names for a deliberate difference, not a drift.
        """
        if kind in REDUCTION_KINDS:
            declared = DECLARED_REDUCTION_ORDER.get(
                str(attributes.get("reduction_order", ""))
            )
            if declared is not None:
                return declared
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
        scale_block_rows: int = 0,
        extent_axis: int = 0,
        extent_unit: int = 0,
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
                    writes = direction == "out" and self._writes_resource(kernel, name)
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
            declared_row = members[0].row_elements
            row_elements = max(
                declared_row,
                max((plane_rows.get(m.state_id, 0) for m in members), default=0),
            )
            if row_elements != declared_row:
                self._state_row_widenings[members[0].state_class] = {
                    "declared_row_elements": declared_row,
                    "physical_row_elements": row_elements,
                }
            row_bytes = (row_elements * bits + 7) // 8
            capacity = self._extent(members[0].capacity_rows)
            slot_bytes = row_bytes * capacity
            if slot_bytes <= 0:
                raise RomLoweringError(f"state group {index} has no capacity")
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
            self._state_group_shape[group_key] = (slot_bytes, capacity, row_elements)
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
    def _leading_symbol(self, tensor: Tensor) -> tuple[int | None, int, int]:
        """The runtime symbol of a tensor's leading axis, its multiplier, unit."""
        if not tensor.shape or not isinstance(tensor.shape[0], Symbolic):
            return None, 1, 1
        axis = tensor.shape[0]
        request = SYMBOL_BY_NAME.get(axis.symbol)
        if request is None:
            return None, int(axis.multiplier or 1), 1
        return int(request.symbol), int(axis.multiplier or 1), int(request.unit)

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
        symbol, multiplier, unit = (
            self._leading_symbol(principal)
            if principal is not None
            else (None, 1, 1)
        )
        # A13 states the resolved leading extent as ``symbol - iteration *
        # bound_divisor``, so a *multiplied* symbolic extent -- six routed
        # copies of a span -- cannot be a token block: no static block and no
        # single clamp presents ``6 * span`` rows.  One token at a time does
        # present it, and exactly: iteration ``t`` covers routed rows
        # ``6t .. 6t+5`` and the token ``t`` they came from, so each operand
        # shows whatever multiple of a token it holds and the loop bound is the
        # span itself.  Leaving the extent unblocked instead is what made the
        # routed path address 1,572,864 rows of a 104-token request.
        per_token = symbol is not None and multiplier > 1
        row_symbolic = symbol is not None and (multiplier == 1 or per_token)
        # The rows a block loop may walk are bounded by the *smallest* extent
        # any of the kernel's symbolic-leading operands declares.  A graph may
        # give one operand a shorter maximum than the capability's context
        # bound, and a view that presented the capability's rows would run off
        # that operand's object.
        rows_bound = self._symbolic_row_bound(
            kernel, symbol if symbol is not None else -1, unit
        )
        configured = int(self.policy.token_block_rows or 0)
        block = max(min(configured or rows_bound, rows_bound), 1)
        # A view's row term advances by ``block * row width`` elements and that
        # stride is a 32-bit field, so the block is halved until every operand's
        # stride fits.  Halving costs iterations, never correctness; refusing
        # would cost the whole compression.
        widest = self._widest_row(kernel)
        while block > 1 and block * widest > 0xFFFFFFFF:
            block //= 2
        declared_rows = principal_dims[0] if principal_dims else 1
        trip = max(-(-rows_bound // block), 1) if row_symbolic else 1
        rows = min(block, rows_bound) if row_symbolic else max(declared_rows, 1)
        if per_token:
            # One token per iteration, and the loop counts tokens rather than
            # blocks.  The trip is the capability's loop bound because that is
            # the most tokens one instruction may walk; a longer span needs a
            # second dispatch, not a longer loop.
            block = 1
            trip = max(
                min(rows_bound, int(self.capability.limits["max_loop_trip"])), 1
            )
            rows = multiplier

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
            unit=unit,
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
            leading, multiplier, operand_unit = self._leading_symbol(tensor)
            if leading != symbol or operand_unit != unit or multiplier != 1:
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
            bound_divisor=shape.block * shape.unit,
            counter_class_id=self._counter_class("instruction", Major.CONTROL),
            key=f"loop.block.k{kernel.index:05d}",
        )
        self.builder.open_loop(loop)
        return loop

    def _open_context_loop(self, kernel: Kernel, capacity: int, unit: int) -> int:
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
            bound_symbol=Symbol.CONTEXT_LENGTH,
            bound_divisor=capacity * unit,
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

    def _ring_object(self, modulus: int) -> int:
        """The ``position mod modulus`` range, materialised once per modulus."""
        key = f"ring.{modulus}"
        cached = self._generated_objects.get(key)
        if cached is not None:
            return cached
        from runtime.sim.generators import GeneratorError, digest_of, generate

        span_max = int(self.capability.limits["max_context_positions"])
        parameters = {"count": max(2 * span_max, 1), "modulus": int(modulus)}
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
        symbol, multiplier, unit = self._leading_symbol(tensor)
        if symbol is None or (multiplier != 1 and not shape.per_token):
            return None
        width = 1
        for extent in self._dims(tensor)[1:]:
            width *= extent
        block = self._axis_block(shape, unit)
        stride = block * width * (multiplier if shape.per_token else 1)
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
            _symbol, _multiplier, unit = self._leading_symbol(tensor)
            extent_unit = unit if terms else 0
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

    def _axis_block(self, shape: KernelShape, unit: int) -> int:
        """The kernel's token block, counted in an operand axis's own units.

        ``shape.block`` is in the *principal's* units.  A kernel may hold
        operands in two -- the compressor's state update reads a token-major
        packed row and writes group-major pools -- and one block of the loop is
        one span of the symbol either way, so the same block is
        ``block * shape.unit`` symbol units and ``block * shape.unit / unit``
        elements of an axis counted in units of ``unit``.  Converting here is
        what keeps A18's walk test an identity: the term stride this produces
        and the divisor the loop carries are the same quantity in two units.
        """
        symbol_units = int(shape.block) * int(shape.unit)
        divisor = max(int(unit), 1)
        if symbol_units % divisor:
            raise RomLoweringError(
                f"a token block of {shape.block} in units of {shape.unit} is "
                f"{symbol_units} symbol units, which is not a whole number of "
                f"{divisor}-unit elements; amendment A18 needs one iteration to "
                "be a whole number of the axis it walks"
            )
        return max(symbol_units // divisor, 1)

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
        symbol, multiplier, unit = self._leading_symbol(tensor)
        if not dims or symbol is None or not shape.row_symbolic:
            return dims
        block = self._axis_block(shape, unit)
        if shape.per_token:
            # One token's worth of *this* operand: six routed rows, or the one
            # token they came from.
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
        self, dims: list[int], shape: KernelShape
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
        """
        principal = list(shape.principal)
        if shape.row_symbolic and principal:
            block = shape.rows if shape.per_token else shape.block
            principal[0] = min(block, principal[0])
        if shape.per_token and len(principal) > 1:
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
        terms: list[DynamicTerm] = []
        if absolute:
            terms.append(DynamicTerm.symbol(Symbol.POSITION_START, 1))
            if loop is not None and shape.row_symbolic:
                terms.append(DynamicTerm.loop(loop, shape.block * stride))
        elif count == 1:
            terms.append(DynamicTerm.symbol(Symbol.SPAN_LAST_INDEX, 1))
        elif loop is not None and shape.row_symbolic:
            terms.append(DynamicTerm.loop(loop, shape.block * stride))
        dtype = self._dtype(tensor.dtype)
        if name in self._position_inputs:
            object_id = (
                self._position_object(name)
                if modulus is None
                else self._ring_object(modulus)
            )
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
            strides=[stride],
            dynamic=terms,
            permissions=permissions,
            extent_unit=shape.unit if walked else 0,
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
        _symbol, multiplier, _unit = self._leading_symbol(contributions)
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
            named, multiplier, named_unit = self._leading_symbol(
                self.tensors[kernel.outputs[0]]
            )
            if named is not None and multiplier == 1:
                symbol, unit = Symbol(named), named_unit
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
        routed-row order, the same bytes in the same order.  One
        ``DMA.TRANSFER`` per token says exactly that.
        """
        ids = self.tensors[kernel.inputs[1]]
        routed = self.tensors[kernel.outputs[1]]
        slots = 1
        for extent in self._dims(ids)[1:]:
            slots *= extent

        def per_token(tensor: Tensor, *, writable: bool) -> int:
            return self._buffer_view(
                tensor,
                dims=[slots],
                strides=[1],
                shape=shape,
                loop=loop,
                writable=writable,
                blocked=False,
                term=(
                    DynamicTerm.loop(loop, slots) if loop is not None else None
                ),
            )

        self._emit_operator(
            kernel,
            Major.DMA,
            int(Dma.TRANSFER),
            [per_token(ids, writable=False)],
            [per_token(routed, writable=True)],
            loop=None,
            schedule_rows=1,
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
                kernel, shape, name, loop, count=shape.rows, absolute=True
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
            broadcast_dims, broadcast_strides = self._broadcast(dims, shape)
        else:
            broadcast_dims, broadcast_strides = dims, None
        return self._buffer_view(
            tensor,
            dims=broadcast_dims,
            strides=broadcast_strides,
            element_offset=element_offset,
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
        group_rows: int = 0,
        group: int = 0,
        bank: int = 0,
        narrow_dtype: DType | None = None,
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
        """The IR input each ABI input slot carries; ``None`` for an empty slot.

        A slot the operand convention requires to be ``NO_ID`` is not a missing
        operand, it is a stated one: ``VECTOR.COMPRESS`` sub-case 2 reads the
        projected candidates in ``in0`` and the absolute position embedding in
        ``in2``, because ``in1`` is the projection matrix that a state update
        does not have.  The engine refuses an operator that binds anything
        there, so packing the operands down would put the APE where the
        projection belongs and the operation would be rejected -- which is what
        it did.
        """
        holes = ABI_EMPTY_INPUT_SLOTS.get(kernel.kind, ())
        if not holes:
            return list(order)
        slots: list[int | None] = []
        remaining = list(order)
        position = 0
        while remaining:
            if position in holes:
                slots.append(None)
            else:
                slots.append(remaining.pop(0))
            position += 1
        return slots

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
            symbol, _, _ = self._leading_symbol(subject)
            absolute = symbol is None
        # One index per row the movement touches: the rows it writes for a
        # gather, the rows it reads for a scatter.
        counted = addressed if gather else source_name
        count = 1
        if counted is not None:
            count = max(self._blocked_dims(self.tensors[counted], shape)[0], 1)
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
        _symbol, _multiplier, unit = self._leading_symbol(key)
        if unit <= 1:
            raise RomLoweringError(
                f"kernel {kernel.kernel_id!r}: the index key leads with "
                f"{key.shape[0]!r}, which states no compression ratio; "
                "VECTOR.INDEX_SCORE scores compressed groups"
            )
        shape = self._shape_of(kernel, EngineOp(Major.VECTOR, Vector.INDEX_SCORE, 3, 1))
        token = self._open_token_loop(kernel)
        context = self._open_context_loop(kernel, candidates, unit)

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
        loop = self._open_row_loop(kernel, shape)
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
                )
                for abi_slot, name in enumerate(kernel.outputs[:MAX_OPERATOR_OUTPUTS])
            ]
        self._emit_operator(
            kernel,
            family,
            engine.sub,
            inputs,
            outputs,
            loop=loop,
            schedule_rows=schedule_rows,
        )

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
    ) -> None:
        """Bind one operator descriptor, issue it, and close its loop.

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
            for name in kernel.inputs
            if name in self._event_of_tensor
        ]
        wait = self._wait_set(producers)
        event = self.builder.new_event()
        self.builder.emit(
            family,
            sub,
            descriptor_id=operator,
            wait_set_id=wait,
            signal_event_id=event,
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

    def _state_for(self, kernel: Kernel) -> int:
        for state_id in (*kernel.state_writes, *kernel.state_reads):
            if state_id in self._state_descriptor:
                return self._state_descriptor[state_id]
        raise RomLoweringError(
            f"kernel {kernel.kernel_id!r} is a state operation naming no declared "
            "state resource"
        )

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
        span_max = int(self.capability.limits["max_context_positions"])
        max_new = _declared_new_token_budget(policy_body, span_max)
        # One host window serves both directions: the host stages the prompt
        # into it and on-device selection appends each new token to it.  The
        # graph's token-stream input is a view of that window, not a second
        # buffer -- a separate object would be one nothing could fill.
        token_bytes = max((span_max + max_new) * 4, 4096)
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
