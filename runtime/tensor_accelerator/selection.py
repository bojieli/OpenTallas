"""Bounded byte-exact sequence-row selection for the tensor accelerator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


NUMERIC_CONTRACT = "exact_index_select_v1"


class SelectionKernelError(ValueError):
    """Raised when a selection request violates the architectural contract."""


@dataclass(frozen=True)
class SelectionKernelResult:
    """One contiguous selected BF16 row and its zero-based logical index."""

    index: int
    values: np.ndarray[Any, np.dtype[np.uint16]]


def _bounded_integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise SelectionKernelError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def last_token_select_bf16(
    input_codes: object,
    *,
    logical_rows: int,
) -> SelectionKernelResult:
    """Select ``logical_rows - 1`` from a row-major BF16 matrix.

    The physical input may contain capacity rows after the logical sequence.
    They are not read and therefore cannot influence the result.
    """

    try:
        raw = np.asarray(input_codes)
    except (TypeError, ValueError) as exc:
        raise SelectionKernelError(
            "input_codes must be a nonempty rank-2 BF16 matrix"
        ) from exc
    if raw.ndim != 2 or not raw.shape[0] or not raw.shape[1]:
        raise SelectionKernelError("input_codes must be a nonempty rank-2 BF16 matrix")
    if raw.dtype.kind not in {"i", "u"}:
        raise SelectionKernelError("input_codes must contain integer BF16 encodings")
    rows = _bounded_integer(
        logical_rows,
        "logical_rows",
        minimum=1,
        maximum=int(raw.shape[0]),
    )
    index = rows - 1
    selected_raw = raw[index : index + 1]
    if np.any(selected_raw < 0) or np.any(selected_raw > 0xFFFF):
        raise SelectionKernelError("selected row contains a value outside 16-bit BF16")
    selected = np.ascontiguousarray(selected_raw, dtype=np.uint16)
    if np.any((selected & np.uint16(0x7F80)) == np.uint16(0x7F80)):
        raise SelectionKernelError("selected row contains BF16 NaN or infinity")
    selected = selected.copy()
    return SelectionKernelResult(index=index, values=selected)


__all__ = [
    "NUMERIC_CONTRACT",
    "SelectionKernelError",
    "SelectionKernelResult",
    "last_token_select_bf16",
]
