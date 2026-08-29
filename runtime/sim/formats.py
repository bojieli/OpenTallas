"""Vectorised NumPy decoders for the ABI 3.0 block-scaled storage formats.

``runtime/reference/formats.py`` is the exact scalar authority for E4M3FN,
E2M1 and E8M0: it decodes with :class:`fractions.Fraction` so no host floating
point mode participates.  A simulator engine cannot afford one Fraction per
weight element, so this module builds *lookup tables* by enumerating the exact
decoder over the complete code space at import time.  The tables are therefore
correct by construction and cannot drift from the reference: if the reference
changes, these tables change with it.

Every decoded value is exactly representable in binary32 -- E4M3FN spans
``2**-9 .. 448``, E2M1 spans ``0 .. 6`` and E8M0 spans ``2**-127 .. 2**127`` --
so the tables lose nothing.  Reserved encodings (E4M3FN ``0x7f``/``0xff`` and
E8M0 ``0xff``) decode to NaN; an engine must treat that as a poisoned block
rather than as data.

BF16 is *not* decoded here in the sense of a table: a BF16 view already carries
the architectural bit pattern in ``uint16``, so widening is a shift and
narrowing is the frozen round-to-nearest-even conversion in
``runtime/tensor_accelerator/bf16.py``.  Both directions live here so that the
tensor and vector engines share one conversion site.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from runtime.abi3.constants import DType
from runtime.reference import formats as exact
from runtime.tensor_accelerator.bf16 import finalize_bf16_accumulator


class FormatError(ValueError):
    """Raised when a storage format cannot carry a requested value."""


def _decode_table(decode: Any, count: int) -> np.ndarray:
    """Enumerate one exact scalar decoder into a binary32 lookup table."""
    table = np.empty(count, dtype=np.float32)
    for code in range(count):
        decoded = decode(code)
        if decoded.finite and decoded.value is not None:
            table[code] = np.float32(float(decoded.value))
        else:
            table[code] = np.float32(np.nan)
    table.flags.writeable = False
    return table


#: One binary32 value per E4M3FN code; ``0x7f``/``0xff`` are NaN.
E4M3FN_VALUES = _decode_table(exact.decode_e4m3fn, 256)
#: One binary32 value per unsigned E8M0 scale code; ``0xff`` is reserved.
E8M0_VALUES = _decode_table(exact.decode_e8m0, 256)
#: One binary32 value per E2M1 nibble.
MXFP4_VALUES = _decode_table(exact.decode_e2m1, 16)

#: Storage formats this module can widen into binary32.
WIDENABLE = frozenset(
    {
        int(DType.BF16),
        int(DType.FP16),
        int(DType.FP32),
        int(DType.FP8_E4M3FN),
        int(DType.MXFP4_E2M1),
        int(DType.E8M0_SCALE),
    }
)

#: Storage formats this module can narrow a binary32 result into.
NARROWABLE = frozenset({int(DType.BF16), int(DType.FP16), int(DType.FP32)})


def _uint8(codes: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(codes)
    if array.dtype != np.uint8:
        raise FormatError(f"{label} must be carried as uint8, not {array.dtype}")
    return array


def decode_e4m3fn(codes: np.ndarray) -> np.ndarray:
    """Decode OCP/PyTorch finite-only FP8 E4M3FN codes into binary32."""
    return E4M3FN_VALUES[_uint8(codes, "E4M3FN codes")]


def decode_e8m0(codes: np.ndarray) -> np.ndarray:
    """Decode unsigned E8M0 block-scale codes into binary32 powers of two."""
    return E8M0_VALUES[_uint8(codes, "E8M0 scale codes")]


def decode_mxfp4_nibble(nibbles: np.ndarray) -> np.ndarray:
    """Decode unpacked MXFP4 E2M1 nibbles into binary32.

    The view resolver already splits each checkpoint byte low-nibble-first, so
    this receives one nibble per element rather than packed bytes.
    """
    array = _uint8(nibbles, "MXFP4 nibbles")
    if array.size and int(array.max()) > 0xF:
        raise FormatError("MXFP4 element is not a 4-bit nibble")
    return MXFP4_VALUES[array]


def widen_bf16(codes: np.ndarray) -> np.ndarray:
    """Widen architectural BF16 bit patterns to binary32 (exact)."""
    array = np.asarray(codes)
    if array.dtype != np.uint16:
        raise FormatError(f"BF16 codes must be carried as uint16, not {array.dtype}")
    bits = np.ascontiguousarray(array, dtype=np.uint16).astype(np.uint32) << np.uint32(16)
    return np.ascontiguousarray(bits).view(np.float32)


def narrow_bf16_rne(values: np.ndarray) -> tuple[np.ndarray, int]:
    """Round binary32 values to BF16, ties to even, with saturation counted.

    The rounding itself is the frozen ``bf16_bf16_fp32_sequential_rne_v1``
    conversion from ``runtime/tensor_accelerator/bf16.py``; this only reshapes
    around it so that any rank can use one validated conversion.
    """
    array = np.ascontiguousarray(values, dtype=np.float32)
    if array.size == 0:
        raise FormatError("BF16 conversion of an empty tensor")
    flat = array.reshape(1, array.size)
    result = finalize_bf16_accumulator(flat.view(np.uint32))
    return (
        result.values.reshape(array.shape),
        result.output_saturated_element_count,
    )


def widen(dtype: int, array: np.ndarray) -> np.ndarray:
    """Widen one storage-format array to binary32 without applying scales."""
    dtype = int(dtype)
    if dtype == DType.BF16:
        return widen_bf16(array)
    if dtype == DType.FP32:
        return np.ascontiguousarray(array, dtype=np.float32)
    if dtype == DType.FP16:
        return np.ascontiguousarray(array).astype(np.float32)
    if dtype == DType.FP8_E4M3FN:
        return decode_e4m3fn(array)
    if dtype == DType.MXFP4_E2M1:
        return decode_mxfp4_nibble(array)
    if dtype == DType.E8M0_SCALE:
        return decode_e8m0(array)
    raise FormatError(
        f"storage format {DType(dtype).name} has no binary32 widening in this engine"
    )


def narrow(dtype: int, values: np.ndarray) -> tuple[np.ndarray, int]:
    """Narrow a binary32 result into one storage format, counting saturation."""
    dtype = int(dtype)
    if dtype == DType.BF16:
        return narrow_bf16_rne(values)
    if dtype == DType.FP32:
        array = np.ascontiguousarray(values, dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise FormatError("binary32 result is NaN or infinity")
        return array, 0
    if dtype == DType.FP16:
        array = np.ascontiguousarray(values, dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise FormatError("binary32 result is NaN or infinity")
        narrowed = array.astype(np.float16)
        saturated = int(np.count_nonzero(~np.isfinite(narrowed)))
        if saturated:
            raise FormatError("binary32 result overflows FP16")
        return narrowed, 0
    raise FormatError(
        f"storage format {DType(dtype).name} is not a narrowing target in this engine"
    )


__all__ = [
    "E4M3FN_VALUES",
    "E8M0_VALUES",
    "MXFP4_VALUES",
    "FormatError",
    "NARROWABLE",
    "WIDENABLE",
    "decode_e4m3fn",
    "decode_e8m0",
    "decode_mxfp4_nibble",
    "narrow",
    "narrow_bf16_rne",
    "widen",
    "widen_bf16",
]
