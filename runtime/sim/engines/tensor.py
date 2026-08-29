"""TENSOR engine: contraction, grouped and routed contraction, embedding gather.

Four frozen subopcodes live here.

``TENSOR.MATMUL``
    ``[rows, K] x [N, K]^T -> [rows, N]``.  Input 1 is n-major (already
    transposed), which is the layout every checkpoint in this repository
    stores a linear weight in, so no relayout pass exists.  The reduction is
    strictly increasing in K under ``ReductionOrder.SEQUENTIAL_ASCENDING``.

``TENSOR.GROUPED_MATMUL``
    One contraction per group against a stacked weight tensor.  Input 2 is the
    per-group row count, so the activation rows are partitioned in ascending
    group order.  This is the "grouped projection through descriptors" of
    ADR-003 section 8.2.

``TENSOR.ROUTED_MATMUL``
    One contraction per (row, routing slot) against a stacked expert weight
    tensor selected by the routed expert IDs, combined in ascending slot order
    under the optional routing weights.

``TENSOR.EMBED_LOOKUP``
    Exact row gather from an embedding table.  No arithmetic, therefore no
    conversion and no numeric profile is required.

Numeric contracts
-----------------
BF16 x BF16 -> FP32 -> BF16 is ``bf16_bf16_fp32_sequential_rne_v1`` and is
executed by the frozen kernels in ``runtime/tensor_accelerator/bf16.py``.  The
block-scaled formats (FP8 E4M3FN, MXFP4 E2M1 with E8M0 scales) use the same
shape of arithmetic -- exact binary32 products, ordered binary32 accumulation,
one rounding at the output boundary -- which is what
``runtime/reference/formats.binary32_ordered_dot`` specifies exactly.  Both
operand formats carry at most eight significand bits, so their binary32
product is exact and the accumulate-then-round-once identity holds.

Everything fails closed.  An operand whose dtype contradicts the numeric
profile, a reduction order this engine does not implement, a reserved E8M0
scale, an out-of-range expert or token ID, and any non-finite intermediate all
raise :class:`EngineError` rather than producing a substituted value.
"""

from __future__ import annotations

import contextlib
from typing import Iterator, Sequence

import numpy as np

from runtime.abi3.constants import (
    NO_ID,
    DType,
    Major,
    ReductionOrder,
    RoundingMode,
    Tensor,
    TrapClass,
)
from runtime.abi3.descriptors import Descriptor
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.sim.formats import (
    FormatError,
    decode_e8m0,
    narrow,
    widen,
)
from runtime.sim.memory import ResolvedView
from runtime.tensor_accelerator.bf16 import dense_bf16_linear_bf16

#: Storage-class to counter name for reads this engine performs itself.
_READ_COUNTER = {
    "HBM": "hbm.bytes_read",
    "SRAM": "sram.bytes_read",
    "ROM": "rom.bytes_read",
    "HOST": "host.bytes_read",
    "STATE": "state.bytes_read",
}

#: Bounded work tile, matching the frozen dense BF16 kernel.
_ROW_TILE = 8
_COL_TILE = 64


# ---------------------------------------------------------------------------
# Shared validation
# ---------------------------------------------------------------------------
def _require(
    condition: bool,
    message: str,
    trap_class: int = TrapClass.DESCRIPTOR_OR_ADDRESS,
) -> None:
    if not condition:
        raise EngineError(message, trap_class=int(trap_class))


@contextlib.contextmanager
def _numeric_guard(what: str) -> Iterator[None]:
    """Turn a frozen kernel's numeric refusal into an architectural trap."""
    try:
        yield
    except EngineError:
        raise
    except ValueError as exc:
        raise EngineError(
            f"{what}: {exc}", trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE)
        ) from exc


def _profile(ctx: EngineContext, operator: Descriptor) -> NumericProfile:
    profile = ctx.numeric(operator.payload["numeric_profile_id"])
    _require(
        profile.rounding_mode == RoundingMode.NEAREST_EVEN,
        f"numeric profile {profile.descriptor_id} selects rounding mode "
        f"{RoundingMode(profile.rounding_mode).name}; the tensor engine "
        "implements round-to-nearest-even only",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    _require(
        profile.accumulator_dtype == DType.FP32,
        f"numeric profile {profile.descriptor_id} declares accumulator "
        f"{DType(profile.accumulator_dtype).name}; the tensor engine accumulates "
        "in binary32 only",
        TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE,
    )
    _require(
        profile.reduction_order == ReductionOrder.SEQUENTIAL_ASCENDING,
        f"numeric profile {profile.descriptor_id} selects reduction order "
        f"{ReductionOrder(profile.reduction_order).name}; the tensor engine "
        "implements the strictly increasing reduction index only",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    return profile


def _check_dtype(view: ResolvedView, expected: int, label: str) -> None:
    _require(
        view.dtype == expected,
        f"{label} view {view.descriptor_id} stores {DType(view.dtype).name} but "
        f"its numeric profile declares {DType(expected).name}",
    )


def _account_read(ctx: EngineContext, view: ResolvedView, nbytes: int) -> None:
    """Account a partial read this engine performed without ``ctx.read``."""
    obj = ctx.memory[view.object_id]
    ctx.counters.add(_READ_COUNTER[obj.storage_class.name], int(nbytes))


def _element_bytes(view: ResolvedView, elements: int) -> int:
    bits = 4 if view.is_sub_byte else view.numpy_dtype.itemsize * 8
    return (int(elements) * bits) // 8


# ---------------------------------------------------------------------------
# Operand decoding
# ---------------------------------------------------------------------------
def _block_scales(ctx: EngineContext, view: ResolvedView, dims: Sequence[int]) -> np.ndarray:
    """Read the E8M0 block scales of a block-scaled view.

    The scale object holds one unsigned E8M0 code per block of
    ``scale_block_elements`` elements, in the view's own logical row-major
    order: block ``b`` of row ``r`` is code ``r * blocks_per_row + b``, and the
    view's element offset shifts that index by ``element_offset // block``.
    """
    block = int(view.scale_block_elements)
    _require(
        block > 0,
        f"view {view.descriptor_id} names a scale object but no block size",
    )
    width = int(dims[-1])
    _require(
        width % block == 0,
        f"view {view.descriptor_id}: reduction extent {width} is not a multiple "
        f"of its {block}-element scale block",
    )
    _require(
        view.strides[-1] == 1,
        f"view {view.descriptor_id}: a block-scaled view must be contiguous in "
        "its last axis so that block index and element index agree",
    )
    _require(
        view.element_offset % block == 0,
        f"view {view.descriptor_id}: element offset {view.element_offset} does "
        f"not start on a {block}-element scale block",
    )
    rows = 1
    for extent in dims[:-1]:
        rows *= int(extent)
    per_row = width // block
    count = rows * per_row
    obj = ctx.memory[view.scale_object_id]
    offset = view.element_offset // block
    _require(
        offset + count <= obj.size_bytes,
        f"view {view.descriptor_id}: scale object {view.scale_object_id} holds "
        f"{obj.size_bytes} codes, need {offset + count}",
        TrapClass.MEMORY_SUBSYSTEM,
    )
    payload = obj.read(offset, count)
    ctx.counters.add(_READ_COUNTER[obj.storage_class.name], count)
    codes = np.frombuffer(payload, dtype=np.uint8)
    with _numeric_guard(f"view {view.descriptor_id} block scales"):
        values = decode_e8m0(codes)
    if np.any(np.isnan(values)):
        ctx.counters.add(
            "tensor.exceptional_values", int(np.count_nonzero(np.isnan(values)))
        )
        raise EngineError(
            f"view {view.descriptor_id}: reserved E8M0 code 0xff poisons a block",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    return values.reshape(rows, per_row)


def _operand(
    ctx: EngineContext, view: ResolvedView, array: np.ndarray, label: str
) -> tuple[np.ndarray, int]:
    """Widen one operand to binary32, applying block scales when declared.

    Returns the values and the number of scale multiplications performed.
    """
    with _numeric_guard(f"{label} view {view.descriptor_id}"):
        values = widen(view.dtype, array)
    if np.any(np.isnan(values)):
        count = int(np.count_nonzero(np.isnan(values)))
        ctx.counters.add("tensor.exceptional_values", count)
        raise EngineError(
            f"{label} view {view.descriptor_id} contains {count} reserved or NaN "
            f"{DType(view.dtype).name} encoding(s)",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    if view.scale_object_id == NO_ID:
        return values, 0
    scales = _block_scales(ctx, view, values.shape)
    block = int(view.scale_block_elements)
    flat = values.reshape(scales.shape[0], scales.shape[1], block)
    scaled = np.multiply(flat, scales[:, :, None], dtype=np.float32)
    if not np.all(np.isfinite(scaled)):
        ctx.counters.add("tensor.exceptional_values", 1)
        raise EngineError(
            f"{label} view {view.descriptor_id}: block scale application left the "
            "binary32 range",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )
    return scaled.reshape(values.shape), int(values.size)


# ---------------------------------------------------------------------------
# Contraction
# ---------------------------------------------------------------------------
def _ordered_contract(
    activations: np.ndarray, weights: np.ndarray
) -> np.ndarray:
    """``[M,K] @ [N,K]^T`` with exact products and increasing-K accumulation.

    This is the generalisation of ``dense_bf16_linear_bf16`` to any operand
    format whose binary32 products are exact: the products are materialised so
    the host cannot contract them, every exact zero is canonicalised before
    accumulation, and ``np.add.accumulate`` performs the strictly ordered
    binary32 reduction.
    """
    rows = activations.shape[0]
    cols = weights.shape[0]
    output = np.empty((rows, cols), dtype=np.float32)
    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for row_start in range(0, rows, _ROW_TILE):
            row_end = min(row_start + _ROW_TILE, rows)
            row_tile = activations[row_start:row_end]
            for col_start in range(0, cols, _COL_TILE):
                col_end = min(col_start + _COL_TILE, cols)
                col_tile = weights[col_start:col_end]
                products = np.multiply(
                    row_tile[:, None, :], col_tile[None, :, :], dtype=np.float32
                )
                if not np.all(np.isfinite(products)):
                    raise FormatError("contraction product left the binary32 range")
                products[products == 0] = np.float32(0.0)
                accumulated = np.add.accumulate(products, axis=2, dtype=np.float32)
                final = accumulated[:, :, -1]
                if not np.all(np.isfinite(final)):
                    raise FormatError("contraction sum left the binary32 range")
                output[row_start:row_end, col_start:col_end] = final
    finally:
        np.seterr(**previous)
    return output


def _uses_bf16_kernel(
    activation_view: ResolvedView, weight_view: ResolvedView, output_dtype: int
) -> bool:
    """Whether the frozen BF16 dense kernel covers this operand combination."""
    return (
        activation_view.dtype == DType.BF16
        and weight_view.dtype == DType.BF16
        and activation_view.scale_object_id == NO_ID
        and weight_view.scale_object_id == NO_ID
        and int(output_dtype) == int(DType.BF16)
    )


def _contract(
    ctx: EngineContext,
    profile: NumericProfile,
    activation_view: ResolvedView,
    activations: np.ndarray,
    weight_view: ResolvedView,
    weights: np.ndarray,
    output_dtype: int,
) -> tuple[np.ndarray, int, int]:
    """Execute one contraction.

    Returns ``(values, saturations, scale_multiplications)``.  ``values`` is
    BF16 codes when the output view is BF16 and the frozen BF16 kernel applied,
    otherwise a binary32 accumulator the caller narrows.
    """
    if _uses_bf16_kernel(activation_view, weight_view, output_dtype):
        with _numeric_guard("bf16_bf16_fp32_sequential_rne_v1"):
            result = dense_bf16_linear_bf16(
                activations,
                weights,
                input_tile_rows=_ROW_TILE,
                output_tile_rows=_COL_TILE,
            )
        return result.values, result.output_saturated_element_count, 0
    left, left_scale = _operand(ctx, activation_view, activations, "activation")
    right, right_scale = _operand(ctx, weight_view, weights, "weight")
    with _numeric_guard("binary32 ordered contraction"):
        accumulator = _ordered_contract(
            np.ascontiguousarray(left), np.ascontiguousarray(right)
        )
    return accumulator, 0, left_scale + right_scale


def _write_result(
    ctx: EngineContext, view: ResolvedView, values: np.ndarray
) -> tuple[int, int]:
    """Narrow a binary32 result into ``view`` and write it.

    Returns ``(saturations, conversions)``.
    """
    if values.dtype == np.uint16 and view.dtype == DType.BF16:
        ctx.write(view, np.ascontiguousarray(values.reshape(view.dims)))
        return 0, int(values.size)
    with _numeric_guard(f"output view {view.descriptor_id}"):
        narrowed, saturations = narrow(view.dtype, values.reshape(view.dims))
    ctx.write(view, np.ascontiguousarray(narrowed))
    conversions = 0 if view.dtype == DType.FP32 else int(narrowed.size)
    return saturations, conversions


def _account_contraction(
    ctx: EngineContext, rows: int, cols: int, depth: int, scale_multiplications: int
) -> None:
    ctx.counters.add("tensor.multiplications", rows * cols * depth + scale_multiplications)
    ctx.counters.add("tensor.additions", rows * cols * max(depth - 1, 0))


def _matmul_shapes(
    activation_view: ResolvedView, weight_view: ResolvedView, output_view: ResolvedView
) -> tuple[int, int, int]:
    _require(
        len(activation_view.dims) == 2,
        f"MATMUL activation view {activation_view.descriptor_id} has rank "
        f"{len(activation_view.dims)}; expected [rows, K]",
    )
    _require(
        len(weight_view.dims) == 2,
        f"MATMUL weight view {weight_view.descriptor_id} has rank "
        f"{len(weight_view.dims)}; expected [N, K]",
    )
    rows, depth = activation_view.dims
    cols, weight_depth = weight_view.dims
    _require(
        depth == weight_depth,
        f"MATMUL reduction extents differ: activation K={depth}, weight K="
        f"{weight_depth}",
    )
    _require(
        tuple(output_view.dims) == (rows, cols),
        f"MATMUL output view {output_view.descriptor_id} is {output_view.dims}; "
        f"expected {(rows, cols)}",
    )
    _require(rows > 0 and cols > 0 and depth > 0, "MATMUL has an empty extent")
    return rows, cols, depth


# ---------------------------------------------------------------------------
# TENSOR.MATMUL
# ---------------------------------------------------------------------------
@register(Major.TENSOR, Tensor.MATMUL)
def _tensor_matmul(ctx: EngineContext, sub: int, operator: Descriptor) -> None:
    profile = _profile(ctx, operator)
    activation_view = ctx.input_view(operator, 0)
    weight_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(activation_view, profile.input_dtype, "MATMUL activation")
    _check_dtype(weight_view, profile.second_input_dtype, "MATMUL weight")
    _check_dtype(output_view, profile.output_dtype, "MATMUL output")
    rows, cols, depth = _matmul_shapes(activation_view, weight_view, output_view)

    activations = ctx.read(activation_view)
    weights = ctx.read(weight_view)
    values, saturations, scale_multiplications = _contract(
        ctx,
        profile,
        activation_view,
        activations,
        weight_view,
        weights,
        output_view.dtype,
    )
    write_saturations, conversions = _write_result(ctx, output_view, values)

    _account_contraction(ctx, rows, cols, depth, scale_multiplications)
    ctx.counters.add("tensor.output_elements", rows * cols)
    ctx.counters.add("tensor.conversions", conversions)
    ctx.counters.add("tensor.saturations", saturations + write_saturations)


# ---------------------------------------------------------------------------
# TENSOR.GROUPED_MATMUL
# ---------------------------------------------------------------------------
@register(Major.TENSOR, Tensor.GROUPED_MATMUL)
def _tensor_grouped_matmul(
    ctx: EngineContext, sub: int, operator: Descriptor
) -> None:
    """Contract activation row segments against a stacked weight tensor.

    ``input 0`` is ``[rows, K]``, ``input 1`` is ``[G, N, K]`` and ``input 2``
    is a ``[G]`` unsigned row count per group.  Segment ``g`` covers the rows
    ``[sum(counts[:g]), sum(counts[:g+1]))``, so the groups partition the
    activation rows in ascending group order and the counts must sum to
    ``rows``.  ``output 0`` is ``[rows, N]``.
    """
    profile = _profile(ctx, operator)
    activation_view = ctx.input_view(operator, 0)
    weight_view = ctx.input_view(operator, 1)
    count_view = ctx.input_view(operator, 2)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(activation_view, profile.input_dtype, "GROUPED_MATMUL activation")
    _check_dtype(weight_view, profile.second_input_dtype, "GROUPED_MATMUL weight")
    _check_dtype(output_view, profile.output_dtype, "GROUPED_MATMUL output")
    _require(
        len(weight_view.dims) == 3,
        f"GROUPED_MATMUL weight view {weight_view.descriptor_id} has rank "
        f"{len(weight_view.dims)}; expected [G, N, K]",
    )
    _require(
        count_view.dtype in (DType.U32, DType.I32) and len(count_view.dims) == 1,
        f"GROUPED_MATMUL group-count view {count_view.descriptor_id} must be a "
        "rank-1 32-bit integer vector",
    )
    groups, cols, depth = weight_view.dims
    _require(
        count_view.dims[0] == groups,
        f"GROUPED_MATMUL declares {count_view.dims[0]} group counts for "
        f"{groups} weight groups",
    )
    _require(
        len(activation_view.dims) == 2 and activation_view.dims[1] == depth,
        f"GROUPED_MATMUL activation view {activation_view.descriptor_id} is "
        f"{activation_view.dims}; expected [rows, {depth}]",
    )
    rows = activation_view.dims[0]
    _require(
        tuple(output_view.dims) == (rows, cols),
        f"GROUPED_MATMUL output view {output_view.descriptor_id} is "
        f"{output_view.dims}; expected {(rows, cols)}",
    )

    counts = np.asarray(ctx.read(count_view)).astype(np.int64, copy=False)
    _require(
        int(counts.sum()) == rows,
        f"GROUPED_MATMUL group counts sum to {int(counts.sum())} but the "
        f"activation has {rows} rows",
    )
    activations = ctx.read(activation_view)
    stack = ctx.views.read_array(weight_view)

    codes_path = _uses_bf16_kernel(activation_view, weight_view, output_view.dtype)
    output = np.empty((rows, cols), dtype=np.uint16 if codes_path else np.float32)
    cursor = 0
    launches = 0
    saturations = 0
    scale_multiplications = 0
    for group in range(groups):
        span = int(counts[group])
        _require(span >= 0, "GROUPED_MATMUL group count is negative")
        if span == 0:
            continue
        _account_read(ctx, weight_view, _element_bytes(weight_view, cols * depth))
        values, group_saturations, group_scale = _contract(
            ctx,
            profile,
            activation_view,
            np.ascontiguousarray(activations[cursor : cursor + span]),
            _slice_view(weight_view, (cols, depth), group),
            stack[group],
            output_view.dtype,
        )
        output[cursor : cursor + span] = values
        saturations += group_saturations
        scale_multiplications += group_scale
        launches += 1
        cursor += span
    _require(cursor == rows, "GROUPED_MATMUL left activation rows unassigned")

    write_saturations, conversions = _write_result(ctx, output_view, output)
    _account_contraction(ctx, rows, cols, depth, scale_multiplications)
    ctx.counters.add("tensor.output_elements", rows * cols)
    ctx.counters.add("tensor.conversions", conversions)
    ctx.counters.add("tensor.saturations", saturations + write_saturations)
    ctx.counters.add("tensor.grouped_launches", launches)


def _slice_view(
    view: ResolvedView, dims: tuple[int, ...], index: int = 0
) -> ResolvedView:
    """A view record describing slice ``index`` of a stacked weight view.

    Only the fields the operand decoder reads are meaningful here: the slice
    keeps the stack's storage format, scale object and last-axis stride, and
    advances the element offset so that a block-scaled stack indexes its own
    scales per slice.
    """
    span = 1
    for extent in dims:
        span *= int(extent)
    return ResolvedView(
        descriptor_id=view.descriptor_id,
        object_id=view.object_id,
        dtype=view.dtype,
        dims=tuple(dims),
        strides=view.strides[-len(dims) :],
        element_offset=view.element_offset + index * span,
        writable=view.writable,
        scale_object_id=view.scale_object_id,
        scale_block_elements=view.scale_block_elements,
    )


# ---------------------------------------------------------------------------
# TENSOR.ROUTED_MATMUL
# ---------------------------------------------------------------------------
@register(Major.TENSOR, Tensor.ROUTED_MATMUL)
def _tensor_routed_matmul(
    ctx: EngineContext, sub: int, operator: Descriptor
) -> None:
    """Contract each row against the experts its routing slots select.

    ``input 0`` is ``[rows, K]``, ``input 1`` is the stacked expert weight
    tensor ``[E, N, K]``, ``input 2`` is ``[rows, topk]`` expert IDs and the
    optional ``input 3`` is ``[rows, topk]`` routing weights.  ``output 0`` is
    ``[rows, N]``.

    Each ``(row, slot)`` contraction accumulates in binary32 with the frozen
    increasing-K order.  Its routing weight is applied in binary32, and the
    slots are combined in ascending slot order, so the output boundary is the
    only rounding to the output format.
    """
    profile = _profile(ctx, operator)
    activation_view = ctx.input_view(operator, 0)
    weight_view = ctx.input_view(operator, 1)
    id_view = ctx.input_view(operator, 2)
    routing_view = ctx.optional_input(operator, 3)
    output_view = ctx.output_view(operator, 0)
    _check_dtype(activation_view, profile.input_dtype, "ROUTED_MATMUL activation")
    _check_dtype(weight_view, profile.second_input_dtype, "ROUTED_MATMUL weight")
    _check_dtype(output_view, profile.output_dtype, "ROUTED_MATMUL output")
    _require(
        len(weight_view.dims) == 3,
        f"ROUTED_MATMUL weight view {weight_view.descriptor_id} has rank "
        f"{len(weight_view.dims)}; expected [E, N, K]",
    )
    experts, cols, depth = weight_view.dims
    _require(
        len(activation_view.dims) == 2 and activation_view.dims[1] == depth,
        f"ROUTED_MATMUL activation view {activation_view.descriptor_id} is "
        f"{activation_view.dims}; expected [rows, {depth}]",
    )
    rows = activation_view.dims[0]
    _require(
        id_view.dtype in (DType.U32, DType.I32) and len(id_view.dims) == 2,
        f"ROUTED_MATMUL expert-ID view {id_view.descriptor_id} must be a rank-2 "
        "32-bit integer matrix",
    )
    _require(
        id_view.dims[0] == rows,
        f"ROUTED_MATMUL expert-ID view {id_view.descriptor_id} has "
        f"{id_view.dims[0]} rows; the activation has {rows}",
    )
    topk = id_view.dims[1]
    _require(
        tuple(output_view.dims) == (rows, cols),
        f"ROUTED_MATMUL output view {output_view.descriptor_id} is "
        f"{output_view.dims}; expected {(rows, cols)}",
    )

    identifiers = np.asarray(ctx.read(id_view)).astype(np.int64, copy=False)
    if identifiers.size and (
        int(identifiers.min()) < 0 or int(identifiers.max()) >= experts
    ):
        raise EngineError(
            f"ROUTED_MATMUL expert ID outside [0, {experts})",
            trap_class=int(TrapClass.DESCRIPTOR_OR_ADDRESS),
        )
    routing = None
    if routing_view is not None:
        _require(
            tuple(routing_view.dims) == (rows, topk),
            f"ROUTED_MATMUL routing-weight view {routing_view.descriptor_id} is "
            f"{routing_view.dims}; expected {(rows, topk)}",
        )
        with _numeric_guard(f"routing weights {routing_view.descriptor_id}"):
            routing = widen(routing_view.dtype, ctx.read(routing_view))

    activations = ctx.read(activation_view)
    stack = ctx.views.read_array(weight_view)

    accumulator = np.zeros((rows, cols), dtype=np.float32)
    scale_multiplications = 0
    launches = 0
    for slot in range(topk):
        partial = np.zeros((rows, cols), dtype=np.float32)
        for expert in np.unique(identifiers[:, slot]):
            selected = np.flatnonzero(identifiers[:, slot] == expert)
            _account_read(
                ctx, weight_view, _element_bytes(weight_view, cols * depth)
            )
            values, _, group_scale = _contract(
                ctx,
                profile,
                activation_view,
                np.ascontiguousarray(activations[selected]),
                _slice_view(weight_view, (cols, depth), int(expert)),
                stack[int(expert)],
                DType.FP32,
            )
            partial[selected] = values
            scale_multiplications += group_scale
            launches += len(selected)
        if routing is not None:
            partial = np.multiply(partial, routing[:, slot : slot + 1], dtype=np.float32)
            scale_multiplications += rows * cols
        accumulator = np.add(accumulator, partial, dtype=np.float32)
    if not np.all(np.isfinite(accumulator)):
        ctx.counters.add("tensor.exceptional_values", 1)
        raise EngineError(
            "ROUTED_MATMUL expert combination left the binary32 range",
            trap_class=int(TrapClass.NUMERIC_OR_EXCEPTIONAL_VALUE),
        )

    saturations, conversions = _write_result(ctx, output_view, accumulator)
    _account_contraction(ctx, rows * topk, cols, depth, scale_multiplications)
    ctx.counters.add("tensor.additions", rows * cols * max(topk - 1, 0))
    ctx.counters.add("tensor.output_elements", rows * cols)
    ctx.counters.add("tensor.conversions", conversions)
    ctx.counters.add("tensor.saturations", saturations)
    ctx.counters.add("tensor.routed_launches", launches)


# ---------------------------------------------------------------------------
# TENSOR.EMBED_LOOKUP
# ---------------------------------------------------------------------------
@register(Major.TENSOR, Tensor.EMBED_LOOKUP)
def _tensor_embed_lookup(
    ctx: EngineContext, sub: int, operator: Descriptor
) -> None:
    """Gather embedding rows for a token-ID vector.

    ``input 0`` is the ``[tokens]`` unsigned token-ID view, ``input 1`` is the
    ``[vocabulary, width]`` embedding table and ``output 0`` is
    ``[tokens, width]``.  The gather is exact: the output view must store the
    table's format, because a lookup performs no arithmetic and therefore has
    no rounding boundary at which a conversion could be defined.
    """
    id_view = ctx.input_view(operator, 0)
    table_view = ctx.input_view(operator, 1)
    output_view = ctx.output_view(operator, 0)
    _require(
        id_view.dtype in (DType.U32, DType.I32),
        f"EMBED_LOOKUP token view {id_view.descriptor_id} stores "
        f"{DType(id_view.dtype).name}; expected a 32-bit token ID",
    )
    _require(
        len(table_view.dims) == 2,
        f"EMBED_LOOKUP table view {table_view.descriptor_id} has rank "
        f"{len(table_view.dims)}; expected [vocabulary, width]",
    )
    _require(
        output_view.dtype == table_view.dtype,
        f"EMBED_LOOKUP writes {DType(table_view.dtype).name} rows into a "
        f"{DType(output_view.dtype).name} view; a lookup performs no conversion",
    )
    vocabulary, width = table_view.dims
    identifiers = np.asarray(ctx.read(id_view)).reshape(-1).astype(np.int64, copy=False)
    tokens = int(identifiers.size)
    _require(
        tuple(output_view.dims) == (tokens, width),
        f"EMBED_LOOKUP output view {output_view.descriptor_id} is "
        f"{output_view.dims}; expected {(tokens, width)}",
    )
    if operator.payload["numeric_profile_id"] != NO_ID:
        profile = ctx.numeric(operator.payload["numeric_profile_id"])
        _check_dtype(output_view, profile.output_dtype, "EMBED_LOOKUP output")
    if tokens and (
        int(identifiers.min()) < 0 or int(identifiers.max()) >= vocabulary
    ):
        raise EngineError(
            f"EMBED_LOOKUP token ID outside [0, {vocabulary})",
            trap_class=int(TrapClass.DESCRIPTOR_OR_ADDRESS),
        )

    # The table is read row by row: accounting the whole view would charge a
    # 16 GB embedding table to every single-token lookup.
    table = ctx.views.read_array(table_view)
    rows = np.ascontiguousarray(table[identifiers])
    _account_read(ctx, table_view, _element_bytes(table_view, tokens * width))
    ctx.write(output_view, rows.reshape(output_view.dims))
    ctx.counters.add("tensor.embedding_rows", tokens)
    ctx.counters.add("tensor.output_elements", tokens * width)
