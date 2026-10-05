"""DMA engine family: ``TRANSFER``, ``FILL``, ``GATHER``, ``SCATTER`` and ``NGRAM_HASH``.

The DMA engine moves *codes*, never values.  A BF16 view moved into another
BF16 view is a byte move; converting between storage types is an explicit
VECTOR.CONVERT operation, so a dtype mismatch here is a descriptor fault rather
than an implicit cast.  Every index is range-checked against the extent it
addresses: an out-of-range index raises trap class 3 and poisons the
transaction, because a silently clamped or wrapped index is how a functional
model starts disagreeing with the hardware it is supposed to be a model of.

``DMA.TRANSFER``
    ``input_view_0`` to ``output_view_0``; identical dtype and element count.

``DMA.FILL``
    Fills ``output_view_0``.  ``input_view_0``, when present, is a one-element
    view holding the fill code; otherwise ``aux_id_0`` carries the fill code as
    an immediate raw bit pattern that must fit the output element width.

``DMA.GATHER``
    ``input_view_0`` is a U32 index view, ``input_view_1`` the source
    ``[rows, ...]``, ``output_view_0`` is ``[indices, ...]``.

``DMA.SCATTER``
    ``input_view_0`` is a U32 index view, ``input_view_1`` the values
    ``[indices, ...]``, ``output_view_0`` the destination ``[rows, ...]``.
    Slots are applied in ascending slot order, so a repeated index resolves to
    the last write deterministically.  The destination is read back first, so
    rows no index names keep their prior contents.

``DMA.NGRAM_HASH``
    Amendment AM-E10, the Engram n-gram row addresser, and the exact semantics
    of :func:`runtime.reference.engram.ngram_row_ids`.  ``input_view_0`` is a
    U32 view of compressed token IDs, one per position of the sequence;
    ``input_view_1`` the per-lookback multipliers ``[max_order]``, whose extent
    *is* the Engram layer's maximum n-gram size; ``input_view_2`` the column
    table ``[2, orders, heads]``, plane 0 the prime bucket size of each
    ``(order, head)`` column and plane 1 that column's base row, ngram-major and
    head-minor exactly as the released layout flattens them; ``input_view_3`` an
    optional per-position flag view marking dead positions (an image span),
    absent meaning none.  ``output_view_0`` is U32 row IDs
    ``[positions, heads]`` -- a rank-1 output is one position -- for the single
    order ``aux_id_0`` names.  ``aux_id_1`` is the pad ID substituted for a
    blocked lookback, ``aux_id_2`` the compressed vocabulary size every ID is
    range-checked against, and ``aux_id_3`` the first order the column table
    covers (``NO_ID`` meaning two, the released layout's first prime row).

    Nothing here is model geometry: the multipliers, the primes, the offsets,
    the pad ID, the vocabulary and the order set all arrive as operands, because
    the two released tables differ in every one of their 24 column primes.  It
    belongs to the DMA family because it produces *addresses* and reads no
    table: the read behind it is ``TENSOR.EMBED_LOOKUP`` of the rows it names,
    unchanged.  The fold is an XOR of the per-lookback products, the lookback is
    sticky (once the sequence start or a dead position blocks one lookback,
    every deeper lookback of that position is blocked too), and a product that
    reaches the contract's dividend window is refused rather than wrapped.
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import DTYPE_BITS, DType, Dma, Major, NO_ID
from runtime.abi3.descriptors import Descriptor
from runtime.reference.engram import ngram_row_ids
from runtime.sim.engine import EngineContext, EngineError, register
from runtime.sim.memory import ResolvedView


def _require(condition: bool, message: str, trap_class: int = 3) -> None:
    if not condition:
        raise EngineError(message, trap_class=trap_class)


def _check_operator(descriptor: Descriptor, sub: int) -> None:
    payload = descriptor.payload
    _require(
        int(payload["engine_family"]) == int(Major.DMA)
        and int(payload["engine_sub"]) == int(sub),
        f"operator {descriptor.descriptor_id} does not describe "
        f"DMA.{Dma(sub).name}",
    )


def _aux(descriptor: Descriptor, slot: int) -> int | None:
    value = int(descriptor.payload[f"aux_id_{slot}"])
    return None if value == NO_ID else value


def _indices(ctx: EngineContext, view: ResolvedView, rows: int) -> np.ndarray:
    """Read a U32 index view and range-check every entry against ``rows``."""
    _require(
        view.dtype == int(DType.U32),
        f"DMA index view {view.descriptor_id} is dtype {view.dtype:#04x}, "
        "expected U32",
    )
    indices = np.asarray(ctx.read(view), dtype=np.uint64).reshape(-1)
    if indices.size and int(indices.max()) >= rows:
        offender = int(indices.max())
        raise EngineError(
            f"DMA index view {view.descriptor_id} names row {offender}, "
            f"outside the {rows} rows of the addressed view",
            trap_class=3,
        )
    return indices.astype(np.intp)


def _same_codes(source: ResolvedView, destination: ResolvedView, op: str) -> None:
    _require(
        source.dtype == destination.dtype,
        f"{op} moves {source.dtype:#04x} codes into a {destination.dtype:#04x} "
        "view; a storage conversion is an explicit VECTOR.CONVERT operation",
    )


@register(Major.DMA, Dma.TRANSFER)
def transfer(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Dma.TRANSFER))
    source = ctx.input_view(descriptor, 0)
    destination = ctx.output_view(descriptor, 0)
    _same_codes(source, destination, "DMA.TRANSFER")
    _require(
        source.element_count == destination.element_count,
        f"DMA.TRANSFER operator {descriptor.descriptor_id} moves "
        f"{source.element_count} elements from view {source.descriptor_id} "
        f"into view {destination.descriptor_id} with "
        f"{destination.element_count} elements",
    )
    payload = np.array(ctx.read(source)).reshape(destination.dims)
    ctx.write(destination, payload)
    ctx.counters.add("dma.transfers")


@register(Major.DMA, Dma.FILL)
def fill(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Dma.FILL))
    destination = ctx.output_view(descriptor, 0)
    source = ctx.optional_input(descriptor, 0)
    dtype = destination.numpy_dtype
    if source is not None:
        _same_codes(source, destination, "DMA.FILL")
        _require(
            source.element_count == 1,
            f"DMA.FILL source view {source.descriptor_id} holds "
            f"{source.element_count} elements; a fill code is one element",
        )
        code = np.asarray(ctx.read(source)).reshape(-1)[0]
    else:
        immediate = _aux(descriptor, 0)
        _require(
            immediate is not None,
            f"operator {descriptor.descriptor_id}: DMA.FILL declares neither a "
            "fill view nor an immediate fill code",
        )
        assert immediate is not None
        width = DTYPE_BITS[DType(destination.dtype)]
        _require(
            width >= 32 or immediate < (1 << width),
            f"DMA.FILL immediate {immediate:#x} does not fit the "
            f"{width}-bit output element",
        )
        code = np.array(immediate, dtype=np.uint64).astype(dtype)
    ctx.write(destination, np.full(destination.dims, code, dtype=dtype))
    ctx.counters.add("dma.transfers")


@register(Major.DMA, Dma.GATHER)
def gather(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Dma.GATHER))
    index_view = ctx.input_view(descriptor, 0)
    source = ctx.input_view(descriptor, 1)
    destination = ctx.output_view(descriptor, 0)
    _same_codes(source, destination, "DMA.GATHER")
    rows = int(source.dims[0])
    indices = _indices(ctx, index_view, rows)
    trailing = tuple(source.dims[1:])
    _require(
        destination.dims == (int(indices.size),) + trailing,
        f"DMA.GATHER output view {destination.descriptor_id} dims "
        f"{destination.dims} differ from the gathered shape "
        f"{(int(indices.size),) + trailing}",
    )
    gathered = np.array(ctx.read(source))[indices]
    ctx.write(destination, gathered.reshape(destination.dims))
    ctx.counters.add("dma.gather_elements", int(gathered.size))
    ctx.counters.add("dma.transfers")


@register(Major.DMA, Dma.SCATTER)
def scatter(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    _check_operator(descriptor, int(Dma.SCATTER))
    index_view = ctx.input_view(descriptor, 0)
    values_view = ctx.input_view(descriptor, 1)
    destination = ctx.output_view(descriptor, 0)
    _same_codes(values_view, destination, "DMA.SCATTER")
    rows = int(destination.dims[0])
    indices = _indices(ctx, index_view, rows)
    trailing = tuple(destination.dims[1:])
    _require(
        values_view.dims == (int(indices.size),) + trailing,
        f"DMA.SCATTER value view {values_view.descriptor_id} dims "
        f"{values_view.dims} differ from the scattered shape "
        f"{(int(indices.size),) + trailing}",
    )
    values = np.array(ctx.read(values_view))
    current = np.array(ctx.read(destination))
    for slot in range(int(indices.size)):
        current[indices[slot]] = values[slot]
    ctx.write(destination, current.reshape(destination.dims))
    ctx.counters.add("dma.scatter_elements", int(values.size))
    ctx.counters.add("dma.transfers")


#: The numeric contract this sub-op executes (plan section 6.4).  The whole
#: computation is exact integer arithmetic, so there is no rounding mode and no
#: reduction order to declare.
NGRAM_HASH_CONTRACT = "ngram_hash_u32_v1"

#: The first n-gram order the released column layout covers, used when
#: ``aux_id_3`` is ``NO_ID``.  A default of the *reference*, not a bound of this
#: engine: ``aux_id_3`` overrides it and every extent is derived from it.
NGRAM_HASH_DEFAULT_ORDER_MIN = 2


def _hash_geometry(view: ResolvedView, label: str) -> tuple[int, int]:
    """Interpret an output view as ``[positions, heads]``, rank-1 being one row.

    The ROUTE family reads ``[groups, width]`` with a rank-1 single group; the
    row-ID plane is the same shape statement, so it is read the same way rather
    than by a private rule.
    """
    _require(
        len(view.dims) in (1, 2),
        f"DMA.NGRAM_HASH {label} view {view.descriptor_id} has rank "
        f"{len(view.dims)}, expected [positions, heads] or [heads]",
    )
    if len(view.dims) == 1:
        return 1, int(view.dims[0])
    return int(view.dims[0]), int(view.dims[1])


@register(Major.DMA, Dma.NGRAM_HASH)
def ngram_hash(ctx: EngineContext, sub: int, descriptor: Descriptor) -> None:
    """Engram n-gram row IDs: ``ngram_hash_u32_v1``.

    The arithmetic is :func:`runtime.reference.engram.ngram_row_ids`, called
    once per hash head, because that function *is* the contract: it is derived
    from the pinned ``NgramHashState.forward`` and it refuses, rather than
    wraps, a product that reaches the dividend window.  This engine's own work
    is the operand reading -- which view carries the multipliers, which aux
    field carries the pad ID -- and the range checks the DMA family applies to
    every index it produces.

    Every extent comes from an operand: the maximum n-gram size is the
    multiplier view's extent, the order count and the head count are the column
    table's, and the position count is the output's.  A V4.1 Engram module's 24
    columns are three of these operators, one per order, and a module with a
    different order set is the same operator with a different column table.
    """
    _check_operator(descriptor, int(Dma.NGRAM_HASH))
    id_view = ctx.input_view(descriptor, 0)
    multiplier_view = ctx.input_view(descriptor, 1)
    column_view = ctx.input_view(descriptor, 2)
    dead_view = ctx.optional_input(descriptor, 3)
    out_view = ctx.output_view(descriptor, 0)
    _require(
        id_view.dtype == int(DType.U32),
        f"DMA.NGRAM_HASH token ID view {id_view.descriptor_id} is dtype "
        f"{id_view.dtype:#04x}, expected U32",
    )
    _require(
        out_view.dtype == int(DType.U32),
        f"DMA.NGRAM_HASH row ID view {out_view.descriptor_id} is dtype "
        f"{out_view.dtype:#04x}, expected U32",
    )
    _require(
        multiplier_view.dtype in (int(DType.U32), int(DType.U64)),
        f"DMA.NGRAM_HASH multiplier view {multiplier_view.descriptor_id} is "
        f"dtype {multiplier_view.dtype:#04x}, expected U32 or U64",
    )
    _require(
        column_view.dtype in (int(DType.U32), int(DType.U64)),
        f"DMA.NGRAM_HASH column table view {column_view.descriptor_id} is dtype "
        f"{column_view.dtype:#04x}, expected U32 or U64",
    )

    order = _aux(descriptor, 0)
    pad_id = _aux(descriptor, 1)
    vocabulary = _aux(descriptor, 2)
    order_min = _aux(descriptor, 3)
    order_min = NGRAM_HASH_DEFAULT_ORDER_MIN if order_min is None else order_min
    for value, slot, what in (
        (order, 0, "the n-gram order"),
        (pad_id, 1, "the pad ID of a blocked lookback"),
        (vocabulary, 2, "the compressed vocabulary size"),
    ):
        _require(
            value is not None,
            f"operator {descriptor.descriptor_id}: DMA.NGRAM_HASH declares no "
            f"{what} in aux_id_{slot}",
        )
    assert order is not None and pad_id is not None and vocabulary is not None

    positions, heads = _hash_geometry(out_view, "row ID")
    _require(
        positions > 0 and heads > 0,
        f"DMA.NGRAM_HASH row ID view {out_view.descriptor_id} is "
        f"{out_view.dims}; both extents must be positive",
    )
    #: THE SEQUENCE MAY BE LONGER THAN THE OUTPUT, and in decode it must be: an
    #: n-gram at the current position looks back over ids the current span does
    #: not hold, so the operand is the committed prefix ENDING at the last output
    #: position.  Prefill from position zero is the degenerate case where the two
    #: are equal, which is the only case the equality admitted -- so a decode
    #: step could never have issued this operator at all.  The output rows are the
    #: LAST ``positions`` of the sequence; ``lead`` below is what makes that
    #: correspondence explicit rather than implied by an equal length.
    _require(
        int(id_view.element_count) >= positions,
        f"DMA.NGRAM_HASH token ID view {id_view.descriptor_id} holds "
        f"{id_view.element_count} IDs for {positions} output position(s); the "
        "sequence must reach at least as far as the positions emitted",
    )
    _require(
        len(column_view.dims) == 3 and int(column_view.dims[0]) == 2,
        f"DMA.NGRAM_HASH column table view {column_view.descriptor_id} is "
        f"{column_view.dims}; expected [2, orders, heads], plane 0 the prime "
        "bucket sizes and plane 1 the base rows",
    )
    orders = int(column_view.dims[1])
    _require(
        int(column_view.dims[2]) == heads,
        f"DMA.NGRAM_HASH column table view {column_view.descriptor_id} covers "
        f"{column_view.dims[2]} heads, but the row ID view holds {heads}",
    )
    max_order = int(multiplier_view.element_count)
    _require(
        orders == max_order - order_min + 1,
        f"DMA.NGRAM_HASH column table covers {orders} order(s) while "
        f"{max_order} multiplier(s) from order {order_min} are "
        f"{max_order - order_min + 1}; a column table that does not span the "
        "declared orders cannot be indexed by one",
    )

    identifiers = [
        int(value)
        for value in np.asarray(ctx.read(id_view), dtype=np.uint64).reshape(-1)
    ]
    #: Sequence entries ahead of the first emitted position: the lookback the
    #: n-grams need and the output does not name.
    lead = len(identifiers) - positions
    multipliers = [
        int(value)
        for value in np.asarray(
            ctx.read(multiplier_view), dtype=np.uint64
        ).reshape(-1)
    ]
    table = np.asarray(ctx.read(column_view), dtype=np.uint64).reshape(
        2, orders, heads
    )
    primes = [[int(value) for value in row] for row in table[0]]
    offsets = [int(value) for value in table[1].reshape(-1)]
    dead: tuple[int, ...] = ()
    if dead_view is not None:
        _require(
            int(dead_view.element_count) == positions,
            f"DMA.NGRAM_HASH dead-position view {dead_view.descriptor_id} holds "
            f"{dead_view.element_count} flags for {positions} position(s)",
        )
        flags = np.asarray(ctx.read(dead_view), dtype=np.uint64).reshape(-1)
        _require(
            bool(np.all(flags <= np.uint64(1))),
            f"DMA.NGRAM_HASH dead-position view {dead_view.descriptor_id} holds "
            "a value other than 0 or 1",
        )
        #: The flags are per OUTPUT position and the reference indexes the whole
        #: sequence, so they are shifted by the same lead the rows are.
        dead = tuple(int(index) + lead for index in np.nonzero(flags)[0])

    rows = np.empty((positions, heads), dtype=np.uint64)
    for head in range(heads):
        try:
            records = ngram_row_ids(
                identifiers,
                order=int(order),
                head=head,
                multipliers=multipliers,
                primes=primes,
                offsets=offsets,
                pad_id=int(pad_id),
                compressed_vocab_size=int(vocabulary),
                dead_positions=dead,
                n_heads=heads,
                order_min=int(order_min),
            )
        except ValueError as exc:
            # The reference refuses a request the contract does not define: an
            # ID outside the compressed vocabulary, a product that reaches the
            # dividend window, a malformed column table.  Every one of those is
            # a descriptor or data fault here, never a wrapped row.
            raise EngineError(
                f"DMA.NGRAM_HASH operator {descriptor.descriptor_id}: {exc}",
                trap_class=3,
            ) from exc
        for position, record in enumerate(records[lead:]):
            rows[position, head] = int(record["row_id"])

    _require(
        bool(np.all(rows <= np.uint64(0xFFFFFFFF))),
        f"DMA.NGRAM_HASH operator {descriptor.descriptor_id} derived a row "
        "outside the U32 row IDs its output view can hold",
    )
    ctx.write(out_view, rows.astype(np.uint32).reshape(out_view.dims))
    # The frozen counter registry has no n-gram event, and a counter from
    # another group would misreport the family that did the work, so the
    # descriptor is counted and the hashed n-gram count is not reported.
    ctx.counters.add("dma.transfers")


__all__ = [
    "NGRAM_HASH_CONTRACT",
    "NGRAM_HASH_DEFAULT_ORDER_MIN",
    "fill",
    "gather",
    "ngram_hash",
    "scatter",
    "transfer",
]
