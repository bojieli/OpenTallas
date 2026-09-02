"""DMA engine family: ``TRANSFER``, ``FILL``, ``GATHER`` and ``SCATTER``.

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
"""

from __future__ import annotations

import numpy as np

from runtime.abi3.constants import DTYPE_BITS, DType, Dma, Major, NO_ID
from runtime.abi3.descriptors import Descriptor
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


__all__ = ["fill", "gather", "scatter", "transfer"]
