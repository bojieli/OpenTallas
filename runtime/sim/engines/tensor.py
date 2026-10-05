"""TENSOR engine: contraction, grouped and routed contraction, embedding gather.

Four frozen subopcodes live here.

``TENSOR.MATMUL``
    ``[rows, K] x [N, K]^T -> [rows, N]``.  Input 1 is n-major (already
    transposed), which is the layout every checkpoint in this repository
    stores a linear weight in, so no relayout pass exists.  The accumulation
    order is the one the numeric descriptor's contract fixes.

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
Amendment A7 declares two contraction contracts and this engine executes
whichever one the numeric descriptor names.

``bf16_bf16_fp32_sequential_rne_v1``
    Exact products, strictly ascending-K binary32 accumulation, one RNE output
    rounding.  Executed by the frozen kernels in
    ``runtime/tensor_accelerator/bf16.py`` for the BF16 x BF16 -> BF16 case and
    by ``runtime.sim.backend.sequential_matmul_binary32`` otherwise.  It is
    reproducible on any machine and is the oracle -- and, at 0.15 GMAC/s on
    Qwen3-8B shapes, it is about 112 hours per 8,000-token prefill, so it
    qualifies numerics rather than producing tokens.

``bf16_bf16_fp32_blocked_rne_v1``
    Exact products, binary32 accumulation in the executing implementation's
    declared deterministic blocked association, one RNE output rounding.
    Executed through ``runtime/sim/backend.py``, whose
    ``implementation_identity()`` -- library, version, device -- every
    execution report must record alongside the shape.  Two runs of the same
    implementation are bit-identical; the contract claims nothing across
    implementations, and every target of a comparison must run on the same
    backend so that a ROM-versus-HBM token difference is a real difference.

A descriptor that names *neither* contract is executed under the sequential,
exact interpretation when it declares ``SEQUENTIAL_ASCENDING``, and is refused
otherwise.  Only an explicitly named blocked contract may use a library
association; an unnamed one never silently acquires one.

The block-scaled formats (FP8 E4M3FN, MXFP4 E2M1 with E8M0 scales) use the same
shape of arithmetic -- exact binary32 products, binary32 accumulation, one
rounding at the output boundary.  Both operand formats carry at most eight
significand bits, so their binary32 product is exact and the
accumulate-then-round-once identity holds under either association.

Everything fails closed.  An operand whose dtype contradicts the numeric
profile, a reduction order this engine does not implement, a reserved E8M0
scale, an out-of-range expert or token ID, and any non-finite intermediate all
raise :class:`EngineError` rather than producing a substituted value.
"""

from __future__ import annotations

import contextlib
import time
from typing import Iterator, Sequence

import numpy as np

from runtime.abi3.constants import (
    NO_ID,
    DType,
    Major,
    Permission,
    ReductionOrder,
    RoundingMode,
    Tensor,
    TrapClass,
)
from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType, Symbol
from runtime.sim.backend import (
    CONTRACT_BLOCKED,
    CONTRACT_SEQUENTIAL,
    MATMUL_CONTRACTS,
    BackendError,
    declared_contract,
    get_backend,
    required_reduction_order,
)
from runtime.sim.engine import EngineContext, EngineError, NumericProfile, register
from runtime.sim.formats import (
    decode_e8m0,
    narrow,
    widen,
)
from runtime.sim.memory import ResolvedView
from runtime.sim.weight_cache import backend_identity_digest
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

# Changing widening, E8M0 application, or output contiguity changes the cached
# value even when every ABI descriptor stays the same.  Bind that implementation
# boundary explicitly rather than trusting an object ID to mean decoded bytes.
_DECODED_WEIGHT_MATERIALIZER = "abi3_widen_e8m0_fp32_v1"


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
    except (ValueError, BackendError) as exc:
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
    profile.contract = _execution_contract(ctx, profile)
    return profile


def _execution_contract(ctx: EngineContext, profile: NumericProfile) -> str:
    """Which contraction contract this numeric descriptor selects.

    A descriptor that names one of the two frozen contraction contracts must
    also declare the reduction order that contract fixes; the two fields cannot
    disagree, because then neither would say what the engine executed.

    A descriptor that names some other contract -- the digest space is open, and
    several emitters pin a reference owner instead -- is executed under the
    *sequential* contract when it declares ``SEQUENTIAL_ASCENDING``, and refused
    otherwise.  An unnamed contract therefore never acquires a library
    association by accident: only ``bf16_bf16_fp32_blocked_rne_v1``, named
    outright, may use one.
    """
    contract = declared_contract(ctx.table, profile.descriptor_id)
    order = int(profile.reduction_order)
    if contract in MATMUL_CONTRACTS:
        fixed = required_reduction_order(contract)
        if fixed is not None and order != fixed:
            raise EngineError(
                f"numeric profile {profile.descriptor_id} names contract "
                f"{contract} but declares reduction order "
                f"{ReductionOrder(order).name}; that contract accumulates "
                f"under {ReductionOrder(fixed).name}",
                trap_class=int(TrapClass.CAPABILITY_OR_RESOURCE),
            )
        return contract
    _require(
        order == int(ReductionOrder.SEQUENTIAL_ASCENDING),
        f"numeric profile {profile.descriptor_id} selects reduction order "
        f"{ReductionOrder(order).name} without naming a contract that fixes "
        "it; the tensor engine executes an unnamed contract under the strictly "
        "increasing reduction index only",
        TrapClass.CAPABILITY_OR_RESOURCE,
    )
    return CONTRACT_SEQUENTIAL


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
def _block_scales(
    ctx: EngineContext,
    view: ResolvedView,
    dims: Sequence[int],
    *,
    rows: Sequence[int] | None = None,
) -> np.ndarray:
    """Read the E8M0 block scales of a block-scaled view.

    The scale object holds one unsigned E8M0 code per block of the view's own
    logical row-major order.  Amendment A15 (wire format section 12.6) states
    the block as two extents -- ``scale_block_elements`` along the last axis and
    ``scale_block_rows`` along the leading one -- so the code for element
    ``(row, col)`` of a view over ``cols`` columns is

        (row // scale_block_rows) * (cols // scale_block_elements)
      + (col // scale_block_elements)

    Amendment A8 is the ``scale_block_rows = 1`` case of that, exactly:
    substituting one gives ``row * (cols // block) + col // block``, which is
    ``element_offset // block`` whenever the block divides the row, which A8
    already requires.  The released DeepSeek FP8 weights need the general case
    -- ``layers.0.attn.wq_a`` is ``[1024, 4096]`` with a 128-element block and
    ships 256 codes shaped ``[8, 32]``, which is a 128 x 128 tiling -- and
    MXFP4's 32-element blocks along the reduction axis are the A8 case
    untouched.

    The returned array is expanded to one scale per ``(row, block)``, because
    that is what applies the scale; the object is read once per *tile*.

    ``rows`` names which of the *view's* leading positions the caller is
    scaling, for the operators that contract a row subset of a view against a
    weight the subset selected: ``GROUPED_MATMUL`` takes one segment at a time
    and ``ROUTED_MATMUL`` takes the rows one expert won.  Without it the scales
    are read from the view's origin, so a subset that does not begin at row
    zero is scaled by the *first* rows' exponents.  That was silent: the codes
    are legal E8M0, every shape agrees, and the result is a plain power of two
    away from the truth -- which on the released DeepSeek MoE made every routed
    expert but the one holding row zero wrong, by up to 2**16 on the down
    projection, while the gate and up projections stayed exact because their
    activation rows are one token's vector repeated and so share one exponent.
    """
    block = int(view.scale_block_elements)
    row_block = max(int(view.scale_block_rows), 1)
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
    row_count = 1
    for extent in dims[:-1]:
        row_count *= int(extent)
    _require(
        row_count % row_block == 0,
        f"view {view.descriptor_id}: leading extent {row_count} is not a "
        f"multiple of its {row_block}-row scale block",
    )
    # The element offset is a position in the same row-major space, so it
    # splits into a row and a column exactly as any element does.
    row_origin, column_origin = divmod(int(view.element_offset), width)
    _require(
        column_origin % block == 0 and row_origin % row_block == 0,
        f"view {view.descriptor_id}: element offset {view.element_offset} does "
        f"not start on a {row_block} x {block} scale block",
    )
    per_row = width // block
    obj = ctx.memory[view.scale_object_id]
    base = (row_origin // row_block) * per_row + column_origin // block
    selection: np.ndarray | None = None
    if rows is not None:
        selection = np.asarray(rows, dtype=np.int64).reshape(-1)
        _require(
            selection.size == row_count,
            f"view {view.descriptor_id}: {int(selection.size)} rows selected "
            f"for a {row_count}-row operand",
        )
        _require(
            row_block == 1,
            f"view {view.descriptor_id}: a row-selected block-scaled operand "
            f"needs a one-row scale block; this view tiles {row_block} rows",
            TrapClass.CAPABILITY_OR_RESOURCE,
        )
        leading = 1
        for extent in view.dims[:-1]:
            leading *= int(extent)
        _require(
            bool(np.all((selection >= 0) & (selection < leading))),
            f"view {view.descriptor_id}: selected row outside [0, {leading})",
            TrapClass.DESCRIPTOR_OR_ADDRESS,
        )
    if selection is None:
        tile_rows = row_count // row_block
        count = tile_rows * per_row
        _require(
            base + count <= obj.size_bytes,
            f"view {view.descriptor_id}: scale object {view.scale_object_id} "
            f"holds {obj.size_bytes} codes, need {base + count}",
            TrapClass.MEMORY_SUBSYSTEM,
        )
        payload = obj.read(base, count)
        ctx.counters.add(_READ_COUNTER[obj.storage_class.name], count)
        codes = np.frombuffer(payload, dtype=np.uint8)
    else:
        tile_rows = int(selection.size)
        chunks: list[np.ndarray] = []
        for tile in selection.tolist():
            offset = base + int(tile) * per_row
            _require(
                offset + per_row <= obj.size_bytes,
                f"view {view.descriptor_id}: scale object "
                f"{view.scale_object_id} holds {obj.size_bytes} codes, need "
                f"{offset + per_row}",
                TrapClass.MEMORY_SUBSYSTEM,
            )
            chunks.append(np.frombuffer(obj.read(offset, per_row), dtype=np.uint8))
        ctx.counters.add(
            _READ_COUNTER[obj.storage_class.name], per_row * tile_rows
        )
        codes = (
            np.concatenate(chunks) if chunks else np.empty(0, dtype=np.uint8)
        )
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
    tiles = values.reshape(tile_rows, per_row)
    if row_block == 1:
        return tiles
    return np.repeat(tiles, row_block, axis=0)


def _operand(
    ctx: EngineContext,
    view: ResolvedView,
    array: np.ndarray,
    label: str,
    *,
    rows: Sequence[int] | None = None,
) -> tuple[np.ndarray, int]:
    """Widen one operand to binary32, applying block scales when declared.

    ``rows`` names which of ``view``'s leading positions ``array`` holds, for
    the callers that hand a row subset of a view.  Returns the values and the
    number of scale multiplications performed.
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
    scales = _block_scales(ctx, view, values.shape, rows=rows)
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


def _decoded_weight_source_bytes(view: ResolvedView) -> int:
    """Architectural bytes consumed to materialise one complete weight view."""

    source = _element_bytes(view, view.element_count)
    if view.scale_object_id == NO_ID:
        return source
    block = int(view.scale_block_elements)
    row_block = max(int(view.scale_block_rows), 1)
    if block <= 0 or not view.dims:
        return source
    width = int(view.dims[-1])
    leading = 1
    for extent in view.dims[:-1]:
        leading *= int(extent)
    # One E8M0 byte per declared two-dimensional scale tile.
    return source + (leading // row_block) * (width // block)


def _scale_range(view: ResolvedView) -> tuple[int, int]:
    """First E8M0 byte and byte count read for one complete weight view."""

    if view.scale_object_id == NO_ID:
        return 0, 0
    block = int(view.scale_block_elements)
    row_block = max(int(view.scale_block_rows), 1)
    width = int(view.dims[-1])
    row_origin, column_origin = divmod(int(view.element_offset), width)
    per_row = width // block
    leading = 1
    for extent in view.dims[:-1]:
        leading *= int(extent)
    return (
        (row_origin // row_block) * per_row + column_origin // block,
        (leading // row_block) * per_row,
    )


def _cached_scale_accounting(ctx: EngineContext, view: ResolvedView) -> int:
    """Charge immutable scale reads/work that a cache hit still performs."""

    if view.scale_object_id == NO_ID:
        return 0
    _offset, count = _scale_range(view)
    obj = ctx.memory[view.scale_object_id]
    ctx.counters.add(_READ_COUNTER[obj.storage_class.name], count)
    return int(view.element_count)


def _immutable_content_identity(
    ctx: EngineContext, object_id: int
) -> str | None:
    """Authenticated object identity, or ``None`` when caching is forbidden."""

    obj = ctx.memory[object_id]
    if obj.writable or not (int(obj.permissions) & int(Permission.IMMUTABLE)):
        return None
    descriptor = ctx.table.get(object_id, ExtendedDescriptorType.MEMORY_OBJECT)
    recorded = descriptor.payload["content_digest"]
    if not isinstance(recorded, bytes) or len(recorded) != 32 or not any(recorded):
        return None
    deployment = getattr(ctx.device, "deployment", None)
    source = None if deployment is None else deployment.objects.get(object_id)
    if source is None:
        return None
    try:
        expected = source.authenticated_content_digest()
    except Exception:
        return None
    if expected != recorded:
        return None
    return recorded.hex()


def _decoded_weight_cache_key(
    ctx: EngineContext,
    view: ResolvedView,
    *,
    contract: str,
    backend_identity: dict[str, object],
) -> tuple[object, ...] | None:
    """Complete immutable identity for one decoded routed weight slice."""

    weight_identity = _immutable_content_identity(ctx, view.object_id)
    if weight_identity is None:
        return None
    scale_identity = ""
    if view.scale_object_id != NO_ID:
        found = _immutable_content_identity(ctx, view.scale_object_id)
        if found is None:
            return None
        scale_identity = found
    deployment = ctx.device.deployment
    node_id = int(ctx.symbols.get(int(Symbol.NODE_ID), 0))
    backend_key = backend_identity_digest(backend_identity)
    scale_offset, scale_bytes = _scale_range(view)
    return (
        deployment.deployment_digest.hex(),
        int(deployment.generation),
        node_id,
        int(view.object_id),
        weight_identity,
        int(view.element_offset),
        tuple(int(value) for value in view.dims),
        tuple(int(value) for value in view.strides),
        int(view.dtype),
        int(view.scale_object_id),
        scale_identity,
        scale_offset,
        scale_bytes,
        int(view.scale_block_elements),
        int(view.scale_block_rows),
        _DECODED_WEIGHT_MATERIALIZER,
        str(contract),
        backend_key,
    )


# ---------------------------------------------------------------------------
# Contraction
# ---------------------------------------------------------------------------
def _read_device(ctx: EngineContext, view: ResolvedView, backend) -> object:
    """Read one view straight onto the backend's device, accounting the read.

    ``ViewResolver.device_array`` hands the mapped bytes to the backend in
    their *storage* format, so a BF16 weight crosses the bus as 16-bit codes
    and is widened on the far side.  Widening on the host first would double
    the bytes moved for no numeric difference.  For a host backend the call
    returns the ``numpy.memmap`` view itself, so the zero-copy property is
    unchanged.
    """
    array = ctx.views.device_array(view, backend)
    _account_read(ctx, view, _element_bytes(view, view.element_count))
    return array


def _uses_bf16_kernel(
    activation_view: ResolvedView, weight_view: ResolvedView, output_dtype: int
) -> bool:
    """Whether the BF16 dense path covers this operand combination."""
    return (
        activation_view.dtype == DType.BF16
        and weight_view.dtype == DType.BF16
        and activation_view.scale_object_id == NO_ID
        and weight_view.scale_object_id == NO_ID
        and int(output_dtype) == int(DType.BF16)
    )


def _contract(
    ctx: EngineContext,
    activation_view: ResolvedView,
    activations,
    weight_view: ResolvedView,
    weights,
    output_dtype: int,
    *,
    contract: str,
    activation_rows: Sequence[int] | None = None,
    observation_scope: str | None = None,
    cache_scope: tuple[object, ...] | None = None,
) -> tuple[np.ndarray, int, int]:
    """Execute one contraction under the named numeric contract.

    ``activation_rows`` names which of ``activation_view``'s rows
    ``activations`` holds when the caller contracts a subset of them, so that
    a block-scaled activation is scaled by its *own* exponents.

    Returns ``(values, saturations, scale_multiplications)``.  ``values`` is
    BF16 codes when the output view is BF16 and the dense BF16 path applied,
    otherwise a binary32 accumulator the caller narrows.  Both are host arrays:
    a device handle never escapes this function, so nothing downstream has to
    know which backend ran.
    """
    backend = get_backend()
    if _uses_bf16_kernel(activation_view, weight_view, output_dtype):
        contraction_started = time.perf_counter_ns()
        if contract == CONTRACT_SEQUENTIAL:
            with _numeric_guard(CONTRACT_SEQUENTIAL):
                result = dense_bf16_linear_bf16(
                    _host(backend, activations),
                    _host(backend, weights),
                    input_tile_rows=_ROW_TILE,
                    output_tile_rows=_COL_TILE,
                )
            if observation_scope == "routed":
                ctx.observe_host_duration(
                    "routed_contraction",
                    time.perf_counter_ns() - contraction_started,
                )
                ctx.observe_host_total("routed_semantic_segments")
                ctx.observe_host_total("routed_physical_backend_calls")
                ctx.observe_host_total("routed_selected_rows", len(activations))
                ctx.observe_host_total(
                    "routed_weight_source_bytes",
                    _decoded_weight_source_bytes(weight_view),
                )
            return result.values, result.output_saturated_element_count, 0
        # Blocked: widen, contract and round on the backend's own device, so
        # the only host traffic is the BF16 codes in and the BF16 codes out.
        with _numeric_guard(contract):
            left = backend.widen_bf16(activations)
            right = backend.widen_bf16(weights)
            accumulator = backend.matmul_binary32(left, right, contract=contract)
            ctx.observe_blocked_association(
                contract=contract,
                activation_shape=tuple(int(value) for value in left.shape),
                weight_shape=tuple(int(value) for value in right.shape),
                output_shape=tuple(int(value) for value in accumulator.shape),
            )
            narrowed = backend.narrow_rne(accumulator)
            codes = np.ascontiguousarray(
                backend.fetch(narrowed.codes), dtype=np.uint16
            )
        if observation_scope == "routed":
            ctx.observe_host_duration(
                "routed_contraction",
                time.perf_counter_ns() - contraction_started,
            )
            ctx.observe_host_total("routed_semantic_segments")
            ctx.observe_host_total("routed_physical_backend_calls")
            ctx.observe_host_total("routed_selected_rows", len(codes))
            ctx.observe_host_total(
                "routed_weight_source_bytes",
                _decoded_weight_source_bytes(weight_view),
            )
        return codes, narrowed.saturations, 0
    left_values, left_scale = _operand(
        ctx,
        activation_view,
        _host(backend, activations),
        "activation",
        rows=activation_rows,
    )
    right_values: np.ndarray | None = None
    right_scale = 0
    cache = getattr(ctx.device, "decoded_weight_cache", None)
    cache_key: tuple[object, ...] | None = None
    cache_admissible = False
    cache_admission_epoch = 0
    backend_identity: dict[str, object] | None = None
    if cache_scope is not None and cache is not None:
        # Caching is a host implementation detail.  Failure to identify or
        # operate it must leave the architectural uncached path unchanged.
        try:
            backend_identity = backend.implementation_identity()
            cache_key = _decoded_weight_cache_key(
                ctx,
                weight_view,
                contract=contract,
                backend_identity=backend_identity,
            )
            if cache_key is None:
                cache.bypass(
                    scope=cache_scope, backend_identity=backend_identity
                )
            else:
                node_id = int(ctx.symbols.get(int(Symbol.NODE_ID), 0))
                probe = cache.probe(
                    scope=cache_scope,
                    key=cache_key,
                    node_id=node_id,
                    backend_identity=backend_identity,
                )
                right_values = probe.value
                cache_admissible = probe.admissible
                cache_admission_epoch = probe.admission_epoch
                if right_values is not None:
                    right_scale = _cached_scale_accounting(ctx, weight_view)
        except Exception:
            # Do not turn an optional cache bookkeeping defect into an ABI
            # trap.  The normal decoder below retains every numeric check.
            right_values = None
            cache_key = None
            cache_admissible = False
    if right_values is None:
        materialization_started = time.perf_counter_ns()
        right_values, right_scale = _operand(
            ctx, weight_view, _host(backend, weights), "weight"
        )
        if observation_scope == "routed":
            ctx.observe_host_total("decoded_weight_materializations")
            source_bytes = _decoded_weight_source_bytes(weight_view)
            ctx.observe_host_total("decoded_weight_source_bytes", source_bytes)
            ctx.observe_host_total(
                "decoded_weight_result_bytes", int(right_values.nbytes)
            )
            ctx.observe_host_duration(
                "decoded_weight_materialization",
                time.perf_counter_ns() - materialization_started,
            )
        if cache_admissible and cache_key is not None:
            try:
                node_id = int(ctx.symbols.get(int(Symbol.NODE_ID), 0))
                right_values = cache.admit(
                    key=cache_key,
                    node_id=node_id,
                    value=right_values,
                    admission_epoch=cache_admission_epoch,
                )
            except Exception:
                # The already validated uncached value remains authoritative.
                pass
    contraction_started = time.perf_counter_ns()
    with _numeric_guard(contract):
        accumulator = backend.fetch(
            backend.matmul_binary32(
                np.ascontiguousarray(left_values),
                np.ascontiguousarray(right_values),
                contract=contract,
            )
        )
    if contract == CONTRACT_BLOCKED:
        ctx.observe_blocked_association(
            contract=contract,
            activation_shape=tuple(int(value) for value in left_values.shape),
            weight_shape=tuple(int(value) for value in right_values.shape),
            output_shape=tuple(int(value) for value in accumulator.shape),
        )
    if observation_scope == "routed":
        ctx.observe_host_duration(
            "routed_contraction", time.perf_counter_ns() - contraction_started
        )
        ctx.observe_host_total("routed_semantic_segments")
        ctx.observe_host_total("routed_physical_backend_calls")
        ctx.observe_host_total("routed_selected_rows", len(left_values))
        ctx.observe_host_total(
            "routed_weight_source_bytes", _decoded_weight_source_bytes(weight_view)
        )
    return (
        np.ascontiguousarray(accumulator, dtype=np.float32),
        0,
        left_scale + right_scale,
    )


def _host(backend, values) -> np.ndarray:
    """The host view of an operand, whichever side of the bus it arrived on."""
    if isinstance(values, np.ndarray):
        return values
    return backend.fetch(values)


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
    #: THE CONTRACTION IS OVER THE LAST AXIS AND THE ROWS ARE EVERYTHING BEFORE
    #: IT, whatever rank that is.  The reduction dimension is the operand's final
    #: extent in every case, so a leading axis factored differently -- the
    #: grouped output projection presents ``[rows, 1, K]``, a degenerate axis
    #: inserted to match an operand row convention -- has byte-identical
    #: row-major layout to ``[rows, K]`` and contracts identically.  Demanding
    #: rank 2 refused that operand while ``_write_result`` below already reshapes
    #: into whatever rank the destination declares, so the two disagreed.
    #:
    #: The WEIGHT stays rank 2 exactly: its two axes are ``N`` and ``K`` and
    #: neither is a free factoring -- a rank-3 weight would be a different
    #: operator, not the same one written another way.
    _require(
        len(activation_view.dims) >= 2,
        f"MATMUL activation view {activation_view.descriptor_id} has rank "
        f"{len(activation_view.dims)}; expected [rows, K] or a view whose "
        "leading axes factor the rows",
    )
    _require(
        len(weight_view.dims) == 2,
        f"MATMUL weight view {weight_view.descriptor_id} has rank "
        f"{len(weight_view.dims)}; expected [N, K]",
    )
    rows = 1
    for extent in tuple(activation_view.dims)[:-1]:
        rows *= int(extent)
    depth = int(activation_view.dims[-1])
    cols, weight_depth = weight_view.dims
    _require(
        depth == weight_depth,
        f"MATMUL reduction extents differ: activation K={depth}, weight K="
        f"{weight_depth}",
    )
    output_rows = 1
    for extent in tuple(output_view.dims)[:-1]:
        output_rows *= int(extent)
    _require(
        len(output_view.dims) >= 2
        and output_rows == rows
        and int(output_view.dims[-1]) == int(cols),
        f"MATMUL output view {output_view.descriptor_id} is {output_view.dims}; "
        f"expected {(rows, cols)} or a view whose leading axes multiply to "
        f"{rows} over a final {cols}",
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

    backend = get_backend()
    if profile.contract == CONTRACT_BLOCKED and _uses_bf16_kernel(
        activation_view, weight_view, output_view.dtype
    ):
        activations = _read_device(ctx, activation_view, backend)
        weights = _read_device(ctx, weight_view, backend)
    else:
        activations = ctx.read(activation_view)
        weights = ctx.read(weight_view)
    #: The contraction kernels keep their strict ``[M,K] x [N,K]`` contract --
    #: they are the numeric definition and a rank they do not name is a rank they
    #: must not guess at.  So the CANONICAL 2-D FORM is presented here, from the
    #: row count ``_matmul_shapes`` has already established: the flattening is
    #: row-major over axes the operand's own strides make contiguous, so it moves
    #: no element and changes no reduction.
    if len(activation_view.dims) > 2:
        activations = np.ascontiguousarray(activations).reshape(rows, depth)
    values, saturations, scale_multiplications = _contract(
        ctx,
        activation_view,
        activations,
        weight_view,
        weights,
        output_view.dtype,
        contract=profile.contract,
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
    slices: dict[int, tuple[ResolvedView, np.ndarray]] = {}

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
        group_view, group_weights = _stack_slice(
            ctx, weight_view, (cols, depth), group, slices
        )
        values, group_saturations, group_scale = _contract(
            ctx,
            activation_view,
            np.ascontiguousarray(activations[cursor : cursor + span]),
            group_view,
            group_weights,
            output_view.dtype,
            contract=profile.contract,
            activation_rows=np.arange(cursor, cursor + span, dtype=np.int64),
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

    The step between slices is the stack's own leading stride when the stack
    has one, and the slice's element count otherwise.  For a row-major stack --
    every stack either model emits -- the two are the same number, so nothing
    changes; where they differ the stride is what the stack's own layout says,
    and the element count would address the wrong slice.
    """
    span = 1
    for extent in dims:
        span *= int(extent)
    step = int(view.strides[0]) if len(view.strides) == len(dims) + 1 else span
    return ResolvedView(
        descriptor_id=view.descriptor_id,
        object_id=view.object_id,
        dtype=view.dtype,
        dims=tuple(dims),
        strides=view.strides[-len(dims) :],
        element_offset=view.element_offset + index * step,
        writable=view.writable,
        scale_object_id=view.scale_object_id,
        scale_block_elements=view.scale_block_elements,
        scale_block_rows=view.scale_block_rows,
    )


def _stack_slice(
    ctx: EngineContext,
    view: ResolvedView,
    dims: tuple[int, ...],
    index: int,
    cache: dict[int, tuple[ResolvedView, np.ndarray]],
) -> tuple[ResolvedView, np.ndarray]:
    """Slice ``index`` of a stacked weight view, read through the slice itself.

    Reading the *stack* to reach one slice of it is what this exists to stop.
    ``ViewResolver.read_array`` is zero-copy only while the extent lies inside
    one mapped segment, and a released expert bank does not: DeepSeek-V4-Flash
    presents ``[256, 2048, 4096]`` -- 2.147 GB -- spanning many checkpoint
    segments, so ``MemoryObject.contiguous_base`` returns ``None`` and the read
    falls to the gathering copy path.  Measured on the released checkpoint that
    is 14.4 s cold and 2.0-3.6 s warm *per issue*, to use at most six experts:
    8.4 MB of 2,147 MB.  A 43-layer four-token prefill issues 516 of them.

    One slice is one expert's ``[N, K]`` block, which does lie inside one
    segment, so the same call returns the strided ``numpy.memmap`` view and
    nothing is copied at all.  The cache is per issue and keyed by slice index
    because two routing slots may select the same expert, and the second
    selection should not re-read it.
    """
    hit = cache.get(int(index))
    if hit is None:
        sliced = _slice_view(view, dims, int(index))
        hit = (sliced, ctx.views.read_array(sliced))
        cache[int(index)] = hit
    return hit


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
    operator_started = time.perf_counter_ns()
    ctx.observe_host_total("routed_operator_issues")
    ctx.observe_host_total("route_organization_passes")
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
    declared_global = int(operator.payload["aux_id_0"])
    global_experts = experts if declared_global == NO_ID else declared_global
    _require(
        global_experts >= experts,
        f"ROUTED_MATMUL declares {global_experts} global experts but its "
        f"weight view holds {experts}",
    )
    distributed = global_experts > experts
    if distributed:
        _require(
            ctx.node_count > 1 and global_experts == experts * ctx.node_count,
            f"ROUTED_MATMUL presents {experts} local experts out of "
            f"{global_experts} across {ctx.node_count} node(s); exact "
            "contiguous ownership is required",
        )
        node = int(ctx.symbols.get(int(Symbol.NODE_ID), 0))
        _require(
            0 <= node < ctx.node_count,
            f"ROUTED_MATMUL sees NODE_ID {node} outside {ctx.node_count} nodes",
        )
        expert_base = node * experts
    else:
        expert_base = 0
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
        int(identifiers.min()) < 0
        or int(identifiers.max()) >= global_experts
    ):
        raise EngineError(
            f"ROUTED_MATMUL expert ID outside [0, {global_experts})",
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
    slices: dict[int, tuple[ResolvedView, np.ndarray]] = {}
    cache_scope = (
        int(operator.descriptor_id),
        int(weight_view.descriptor_id),
        int(weight_view.object_id),
        int(weight_view.element_offset),
    )

    accumulator = np.zeros((rows, cols), dtype=np.float32)
    scale_multiplications = 0
    launches = 0
    for slot in range(topk):
        partial = np.zeros((rows, cols), dtype=np.float32)
        route_started = time.perf_counter_ns()
        occupied = np.unique(identifiers[:, slot])
        ctx.observe_host_duration(
            "route_organization", time.perf_counter_ns() - route_started
        )
        ctx.observe_host_total("route_unique_scans")
        for global_expert in occupied:
            if not expert_base <= int(global_expert) < expert_base + experts:
                # This row belongs to another node's consecutive expert shard.
                # It remains exact positive zero here and is filled by the
                # route-class-3 all-reduce before EXPERT_REDUCE consumes it.
                continue
            expert = int(global_expert) - expert_base
            route_started = time.perf_counter_ns()
            selected = np.flatnonzero(identifiers[:, slot] == global_expert)
            ctx.observe_host_duration(
                "route_organization", time.perf_counter_ns() - route_started
            )
            ctx.observe_host_total("route_row_selection_scans")
            _account_read(
                ctx, weight_view, _element_bytes(weight_view, cols * depth)
            )
            expert_view, expert_weights = _stack_slice(
                ctx, weight_view, (cols, depth), expert, slices
            )
            values, _, group_scale = _contract(
                ctx,
                activation_view,
                np.ascontiguousarray(activations[selected]),
                expert_view,
                expert_weights,
                DType.FP32,
                contract=profile.contract,
                activation_rows=selected,
                observation_scope="routed",
                cache_scope=cache_scope,
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
    # Each selected row is contracted only on the node that owns its expert.
    # ``rows * topk`` is the global route-slot count and would charge every
    # node for work it deliberately skipped above.  Routing-scale operations
    # remain in ``scale_multiplications`` because this node actually applies
    # those multiplications to its (possibly zero) partials.
    _account_contraction(ctx, launches, cols, depth, scale_multiplications)
    ctx.counters.add("tensor.additions", rows * cols * max(topk - 1, 0))
    ctx.counters.add("tensor.output_elements", rows * cols)
    ctx.counters.add("tensor.conversions", conversions)
    ctx.counters.add("tensor.saturations", saturations)
    ctx.counters.add("tensor.routed_launches", launches)
    ctx.observe_host_duration(
        "routed_operator", time.perf_counter_ns() - operator_started
    )


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
    #: A RANK-1 TABLE IS ONE VALUE PER ROW, which is a table this graph really
    #: declares: the Engram compressed-token map is ``u32[vocabulary]`` -- "one
    #: value per token" in its own reference's words -- and the two backends
    #: present it differently, ROM as ``[vocabulary, 1]`` and HBM as
    #: ``[vocabulary]``.  Both are the same bytes in the same order, and rank 2
    #: exactly refused the second one at instruction 8 of the HBM prefill.
    _require(
        1 <= len(table_view.dims) <= 2,
        f"EMBED_LOOKUP table view {table_view.descriptor_id} has rank "
        f"{len(table_view.dims)}; expected [vocabulary, width] or [vocabulary]",
    )
    _require(
        output_view.dtype == table_view.dtype,
        f"EMBED_LOOKUP writes {DType(table_view.dtype).name} rows into a "
        f"{DType(output_view.dtype).name} view; a lookup performs no conversion",
    )
    vocabulary = int(table_view.dims[0])
    width = int(table_view.dims[1]) if len(table_view.dims) == 2 else 1
    identifiers = np.asarray(ctx.read(id_view)).reshape(-1).astype(np.int64, copy=False)
    tokens = int(identifiers.size)
    #: The output holds ``tokens`` rows of ``width``, and the check is on that
    #: flattening rather than on rank 2 exactly -- the write below is already
    #: ``rows.reshape(output_view.dims)``, and a view whose leading axes are
    #: factored (the engram lookup declares ``[position, head, width]``) has
    #: byte-identical row-major layout to ``[tokens, width]``.  Demanding rank 2
    #: here contradicted that write and refused a legal view; the gather still
    #: performs no arithmetic, so exactness is unaffected.
    leading = 1
    for extent in tuple(output_view.dims)[:-1]:
        leading *= int(extent)
    _require(
        len(output_view.dims) >= 2
        and int(output_view.dims[-1]) == width
        and leading == tokens,
        f"EMBED_LOOKUP output view {output_view.descriptor_id} is "
        f"{output_view.dims}; expected {(tokens, width)} or a view whose "
        f"leading axes multiply to {tokens} over a final {width}",
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
