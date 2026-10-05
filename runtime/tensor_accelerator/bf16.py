"""Data-bearing BF16 tensor kernel for the accelerator simulator.

This implementation is deliberately separate from the exact scalar oracle.  It
uses NumPy binary32 ufuncs over bounded output tiles, explicitly materializes
each product (preventing contraction), and accumulates in increasing K as
``bf16_bf16_fp32_sequential_rne_v1`` requires.

Two schedules produce that reduction, chosen per work tile by size alone.  A
small tile materializes the whole ``[M,N,K]`` product block and reduces it with
``add.accumulate``.  A large tile walks K in the outer position instead,
forming every product of one reduction index at a time and adding it into an
``[M,N]`` accumulator.  Both give output element ``[m,n]`` the same K products
in the same ascending order -- they differ only in which output element is
worked on when, which the contract does not constrain -- and the differential
in the change that introduced the second schedule checks that, bit for bit,
including the signed zeros and the two overflow diagnostics.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np


NUMERIC_CONTRACT = "bf16_bf16_fp32_sequential_rne_v1"


class BF16KernelError(ValueError):
    """Raised when data or host arithmetic violates the target contract."""


@dataclass(frozen=True)
class BF16KernelResult:
    """Contiguous output codes and sticky final-conversion saturation count."""

    output_saturated_element_count: int
    values: np.ndarray[Any, np.dtype[np.uint16]]


@dataclass(frozen=True)
class BF16AccumulatorResult:
    """Raw binary32 accumulator encodings after one ordered K segment."""

    values: np.ndarray[Any, np.dtype[np.uint32]]


def _codes(value: object, label: str) -> np.ndarray[Any, np.dtype[np.uint16]]:
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise BF16KernelError(f"{label} must be a nonempty rank-2 matrix") from exc
    if raw.ndim != 2 or not raw.shape[0] or not raw.shape[1]:
        raise BF16KernelError(f"{label} must be a nonempty rank-2 matrix")
    if raw.dtype.kind not in {"i", "u"}:
        raise BF16KernelError(f"{label} must contain integer BF16 encodings")
    if np.any(raw < 0) or np.any(raw > 0xFFFF):
        raise BF16KernelError(f"{label} contains a value outside 16-bit BF16")
    codes = np.ascontiguousarray(raw, dtype=np.uint16)
    exponent = codes & np.uint16(0x7F80)
    if np.any(exponent == np.uint16(0x7F80)):
        raise BF16KernelError(f"{label} contains BF16 NaN or infinity")
    return codes


def _decode(codes: np.ndarray[Any, np.dtype[np.uint16]]) -> np.ndarray[Any, np.dtype[np.float32]]:
    bits = codes.astype(np.uint32) << np.uint32(16)
    return np.ascontiguousarray(bits).view(np.float32)


def _encode_bf16_rne(
    values: np.ndarray[Any, np.dtype[np.float32]],
) -> tuple[np.ndarray[Any, np.dtype[np.uint16]], int]:
    if not np.all(np.isfinite(values)):
        raise BF16KernelError("binary32 accumulation produced NaN or infinity")
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    upper = bits >> np.uint32(16)
    discarded = bits & np.uint32(0xFFFF)
    increment = (discarded > np.uint32(0x8000)) | (
        (discarded == np.uint32(0x8000)) & ((upper & np.uint32(1)) != 0)
    )
    rounded = upper + increment.astype(np.uint32)
    saturated = (rounded & np.uint32(0x7F80)) == np.uint32(0x7F80)
    saturation_count = int(np.count_nonzero(saturated))
    signs = rounded & np.uint32(0x8000)
    rounded = np.where(saturated, signs | np.uint32(0x7F7F), rounded)
    rounded = np.where((rounded & np.uint32(0x7FFF)) == 0, 0, rounded)
    return np.ascontiguousarray(rounded, dtype=np.uint16), saturation_count


def accumulate_bf16_tile_fp32(
    input_codes: Sequence[Sequence[int]] | np.ndarray[Any, Any],
    weight_codes: Sequence[Sequence[int]] | np.ndarray[Any, Any],
    accumulator_codes: np.ndarray[Any, Any] | None = None,
) -> BF16AccumulatorResult:
    """Accumulate one contiguous K segment into binary32 state.

    Inputs have shapes ``[M,K]`` and ``[N,K]``.  If supplied, accumulator codes
    have shape ``[M,N]`` and represent the result of all immediately preceding K
    segments.  No BF16 output rounding occurs in this operation.
    """

    inputs = _codes(input_codes, "input_codes")
    weights = _codes(weight_codes, "weight_codes")
    if inputs.shape[1] != weights.shape[1]:
        raise BF16KernelError("input and weight reduction widths differ")
    input_values = _decode(inputs)
    weight_values = _decode(weights)
    expected_shape = (inputs.shape[0], weights.shape[0])
    if accumulator_codes is None:
        accumulator_values = np.zeros(expected_shape, dtype=np.float32)
    else:
        raw_accumulator = np.asarray(accumulator_codes)
        if raw_accumulator.shape != expected_shape or raw_accumulator.dtype.kind not in {
            "i",
            "u",
        }:
            raise BF16KernelError(
                "accumulator_codes must be an integer [M,N] matrix"
            )
        if np.any(raw_accumulator < 0) or np.any(raw_accumulator > 0xFFFFFFFF):
            raise BF16KernelError("accumulator_codes contains a value outside uint32")
        accumulator_bits = np.ascontiguousarray(raw_accumulator, dtype=np.uint32)
        exponent = accumulator_bits & np.uint32(0x7F800000)
        if np.any(exponent == np.uint32(0x7F800000)):
            raise BF16KernelError("accumulator_codes contains binary32 NaN or infinity")
        accumulator_values = accumulator_bits.view(np.float32)

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        products = np.multiply(
            input_values[:, None, :],
            weight_values[None, :, :],
            dtype=np.float32,
        )
        if not np.all(np.isfinite(products)):
            raise BF16KernelError("BF16 multiplication overflowed binary32")
        products[products == 0] = np.float32(0.0)
        ordered = np.concatenate((accumulator_values[:, :, None], products), axis=2)
        accumulated = np.add.accumulate(ordered, axis=2, dtype=np.float32)[:, :, -1]
        if not np.all(np.isfinite(accumulated)):
            raise BF16KernelError("BF16 accumulation overflowed binary32")
    finally:
        np.seterr(**previous)
    return BF16AccumulatorResult(
        np.ascontiguousarray(accumulated, dtype=np.float32).view(np.uint32)
    )


def finalize_bf16_accumulator(
    accumulator_codes: np.ndarray[Any, Any],
) -> BF16KernelResult:
    """Round a finite binary32 accumulator matrix once to BF16."""

    raw = np.asarray(accumulator_codes)
    if raw.ndim != 2 or not raw.shape[0] or not raw.shape[1] or raw.dtype.kind not in {
        "i",
        "u",
    }:
        raise BF16KernelError("accumulator_codes must be a nonempty integer matrix")
    if np.any(raw < 0) or np.any(raw > 0xFFFFFFFF):
        raise BF16KernelError("accumulator_codes contains a value outside uint32")
    bits = np.ascontiguousarray(raw, dtype=np.uint32)
    values = bits.view(np.float32)
    encoded, saturation_count = _encode_bf16_rne(values)
    return BF16KernelResult(saturation_count, encoded)


#: Reduction width below which the K-major schedule cannot pay for itself.
_K_MAJOR_MINIMUM_REDUCTION = 8
#: Work-tile element count below which one NumPy call per K step costs more
#: than it saves.  Measured on this machine: the crossover sits near 1 Ki
#: elements per tile, and the K-major schedule wins by 5x-8x above 64 Ki.
_K_MAJOR_MINIMUM_TILE = 1024
#: Element count the K-major schedule keeps a sub-tile under so its accumulator
#: and product buffer stay resident in cache.  This only *subdivides* the
#: caller's declared work tile; it never exceeds it.
_K_MAJOR_TILE_ELEMENTS = 1 << 18
#: Row count of a K-major sub-tile.  Wide-and-short beats tall-and-narrow here
#: because both operand slices of a rank-1 update stay contiguous.
_K_MAJOR_TILE_ROWS = 256


def _accumulate_tile_k_last(
    input_tile: np.ndarray[Any, np.dtype[np.float32]],
    weight_tile: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """Ascending-K accumulation with the whole ``[M,N,K]`` product resident.

    Cheapest schedule when a work tile holds only a handful of output
    elements, because it costs three NumPy calls regardless of ``K``.
    """

    products = np.multiply(
        input_tile[:, None, :],
        weight_tile[None, :, :],
        dtype=np.float32,
    )
    if not np.all(np.isfinite(products)):
        raise BF16KernelError("BF16 multiplication overflowed binary32")
    # The scalar contract canonicalizes every exact zero.  Doing so before
    # accumulation also prevents negative-zero history from becoming
    # host-sign-mode dependent.
    products[products == 0] = np.float32(0.0)
    accumulated = np.add.accumulate(products, axis=2, dtype=np.float32)
    final = accumulated[:, :, -1]
    if not np.all(np.isfinite(final)):
        raise BF16KernelError("BF16 accumulation overflowed binary32")
    return final


def _accumulate_tile_k_major(
    input_tile_t: np.ndarray[Any, np.dtype[np.float32]],
    weight_tile_t: np.ndarray[Any, np.dtype[np.float32]],
) -> np.ndarray[Any, np.dtype[np.float32]]:
    """The same ascending-K accumulation, scheduled as rank-1 updates.

    ``input_tile_t`` is ``[K,M]`` and ``weight_tile_t`` is ``[K,N]``.  Step
    ``k`` forms every product of reduction index ``k`` and adds it into the
    accumulator, so output element ``[m,n]`` still sees its own ``K`` products
    in strictly ascending ``K`` and in no other order.  This reorders *which
    output element is worked on when*, which the contract does not constrain;
    it does not reorder any element's reduction, which the contract does.

    Only the first product is zero-canonicalized.  A binary32 sum is an integer
    multiple of ``2**-149`` whenever both addends are, so a nonzero exact sum
    never rounds to zero, and ``x + y`` is ``-0.0`` only when both addends are
    ``-0.0``.  The accumulator therefore never holds ``-0.0`` after a
    canonicalized first step, and ``a + (-0.0) == a + (+0.0)`` for every other
    ``a``: canonicalizing the remaining products is provably a no-op.
    """

    reduction = int(input_tile_t.shape[0])
    accumulator = np.multiply(
        input_tile_t[0][:, None], weight_tile_t[0][None, :], dtype=np.float32
    )
    accumulator[accumulator == 0] = np.float32(0.0)
    if reduction > 1:
        product = np.empty_like(accumulator)
        for index in range(1, reduction):
            np.multiply(
                input_tile_t[index][:, None], weight_tile_t[index][None, :], out=product
            )
            np.add(accumulator, product, out=accumulator)
    if not np.all(np.isfinite(accumulator)):
        # A non-finite product poisons every later partial sum, so the finite
        # check on the finished accumulator catches both faults.  Re-form the
        # products one reduction index at a time -- an error path, never the
        # hot one -- so the two faults keep the distinct diagnostics the
        # K-last schedule raises.
        for index in range(reduction):
            product = np.multiply(
                input_tile_t[index][:, None],
                weight_tile_t[index][None, :],
                dtype=np.float32,
            )
            if not np.all(np.isfinite(product)):
                raise BF16KernelError("BF16 multiplication overflowed binary32")
        raise BF16KernelError("BF16 accumulation overflowed binary32")
    return accumulator


def dense_bf16_linear_bf16(
    input_codes: Sequence[Sequence[int]] | np.ndarray[Any, Any],
    weight_codes: Sequence[Sequence[int]] | np.ndarray[Any, Any],
    *,
    input_tile_rows: int = 8,
    output_tile_rows: int = 64,
) -> BF16KernelResult:
    """Execute ``[M,K] @ [N,K]^T`` with bounded deterministic work tiles.

    ``input_tile_rows`` and ``output_tile_rows`` bound how many rows and
    columns of the *output* one work tile covers.  They partition the output;
    they never partition the reduction, so every output element accumulates its
    own ``K`` products in strictly ascending ``K`` whatever the tile shape is.
    Tiling is therefore a memory bound and a scheduling choice, and changing it
    cannot change a single result bit.  The kernel may subdivide a declared
    tile further for cache residency; it never exceeds one.
    """

    if (
        isinstance(input_tile_rows, bool)
        or not isinstance(input_tile_rows, int)
        or input_tile_rows < 1
        or isinstance(output_tile_rows, bool)
        or not isinstance(output_tile_rows, int)
        or output_tile_rows < 1
    ):
        raise BF16KernelError("tile row counts must be positive integers")
    inputs = _codes(input_codes, "input_codes")
    weights = _codes(weight_codes, "weight_codes")
    if inputs.shape[1] != weights.shape[1]:
        raise BF16KernelError("input and weight reduction widths differ")
    input_values = _decode(inputs)
    weight_values = _decode(weights)
    rows = int(inputs.shape[0])
    columns = int(weights.shape[0])
    reduction = int(inputs.shape[1])
    output = np.empty((rows, columns), dtype=np.float32)

    row_step = min(input_tile_rows, rows)
    column_step = min(output_tile_rows, columns)
    k_major = (
        reduction >= _K_MAJOR_MINIMUM_REDUCTION
        and row_step * column_step >= _K_MAJOR_MINIMUM_TILE
    )
    input_values_t: np.ndarray[Any, np.dtype[np.float32]] | None = None
    weight_values_t: np.ndarray[Any, np.dtype[np.float32]] | None = None
    if k_major:
        # Subdivide the declared tile so the accumulator and the product buffer
        # stay cache resident, and transpose both operands once so every
        # rank-1 update reads contiguous memory.
        row_step = min(row_step, _K_MAJOR_TILE_ROWS)
        column_step = min(column_step, max(1, _K_MAJOR_TILE_ELEMENTS // row_step))
        input_values_t = np.ascontiguousarray(input_values.T)
        weight_values_t = np.ascontiguousarray(weight_values.T)

    previous = np.seterr(over="ignore", invalid="ignore", under="ignore")
    try:
        for input_start in range(0, rows, row_step):
            input_end = min(input_start + row_step, rows)
            for output_start in range(0, columns, column_step):
                output_end = min(output_start + column_step, columns)
                if k_major:
                    assert input_values_t is not None
                    assert weight_values_t is not None
                    final = _accumulate_tile_k_major(
                        input_values_t[:, input_start:input_end],
                        weight_values_t[:, output_start:output_end],
                    )
                else:
                    final = _accumulate_tile_k_last(
                        input_values[input_start:input_end],
                        weight_values[output_start:output_end],
                    )
                output[input_start:input_end, output_start:output_end] = final
    finally:
        np.seterr(**previous)
    encoded, saturation_count = _encode_bf16_rne(output)
    return BF16KernelResult(saturation_count, encoded)


__all__ = [
    "BF16KernelError",
    "BF16KernelResult",
    "BF16AccumulatorResult",
    "NUMERIC_CONTRACT",
    "accumulate_bf16_tile_fp32",
    "dense_bf16_linear_bf16",
    "finalize_bf16_accumulator",
]
