"""Independent scalar oracle for exact sequence-row selection."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import decode_bf16


NUMERIC_CONTRACT = "exact_index_select_v1"
BF16Matrix: TypeAlias = tuple[tuple[int, ...], ...]


class SelectionReferenceError(ValueError):
    """Raised when a scalar selection fixture violates the contract."""


@dataclass(frozen=True)
class SelectionReferenceResult:
    """One selected row represented only by architectural encodings."""

    index: int
    values: BF16Matrix


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SelectionReferenceError(f"{label} must be a sequence")
    return value


def last_token_select_bf16(
    input_codes: object,
    *,
    logical_rows: int,
) -> SelectionReferenceResult:
    """Select the final logical row without importing NumPy or simulator code."""

    raw_rows = _sequence(input_codes, "input_codes")
    if not raw_rows:
        raise SelectionReferenceError("input_codes must contain at least one row")
    if (
        isinstance(logical_rows, bool)
        or not isinstance(logical_rows, int)
        or not 1 <= logical_rows <= len(raw_rows)
    ):
        raise SelectionReferenceError(
            f"logical_rows must be an integer in [1, {len(raw_rows)}]"
        )
    index = logical_rows - 1
    width: int | None = None
    selected: tuple[int, ...] | None = None
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"input_codes[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise SelectionReferenceError("input rows must be nonempty")
        elif len(row) != width:
            raise SelectionReferenceError("input_codes must be rectangular")
        if row_index != index:
            continue
        output: list[int] = []
        for column, raw_code in enumerate(row):
            if (
                isinstance(raw_code, bool)
                or not isinstance(raw_code, int)
                or not 0 <= raw_code <= 0xFFFF
            ):
                raise SelectionReferenceError(
                    f"input_codes[{row_index}][{column}] is not a BF16 encoding"
                )
            if not decode_bf16(raw_code).finite:
                raise SelectionReferenceError(
                    f"input_codes[{row_index}][{column}] must be finite"
                )
            output.append(raw_code)
        selected = tuple(output)
    if selected is None:  # pragma: no cover - guarded by the logical-row bound.
        raise SelectionReferenceError("selected row is missing")
    return SelectionReferenceResult(index=index, values=(selected,))


__all__ = [
    "BF16Matrix",
    "NUMERIC_CONTRACT",
    "SelectionReferenceError",
    "SelectionReferenceResult",
    "last_token_select_bf16",
]
