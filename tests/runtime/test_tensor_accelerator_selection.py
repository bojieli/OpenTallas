from __future__ import annotations

import numpy as np
import pytest

from runtime.reference.tensor_accelerator_selection import (
    SelectionReferenceError,
    last_token_select_bf16 as reference_select,
)
from runtime.tensor_accelerator.selection import (
    SelectionKernelError,
    last_token_select_bf16,
)


def test_last_token_selection_matches_independent_scalar_oracle() -> None:
    values = np.asarray(
        [
            [0x0000, 0x3F80, 0xBF80, 0x7F7F],
            [0x0080, 0x4000, 0xC000, 0x3F00],
            [0x8000, 0x4040, 0xC040, 0x3E80],
        ],
        dtype=np.uint16,
    )
    for logical_rows in (1, 2, 3):
        executed = last_token_select_bf16(values, logical_rows=logical_rows)
        reference = reference_select(values.tolist(), logical_rows=logical_rows)
        assert executed.index == reference.index
        assert tuple(tuple(int(item) for item in row) for row in executed.values) == (
            reference.values
        )


@pytest.mark.parametrize(
    ("values", "logical_rows", "message"),
    [
        ([], 1, "rank-2"),
        ([[0x3F80], [0x7F80]], 2, "NaN or infinity"),
        ([[0x3F80]], 0, "logical_rows"),
        ([[0x3F80]], True, "logical_rows"),
    ],
)
def test_optimized_selection_rejects_invalid_requests(
    values: object,
    logical_rows: object,
    message: str,
) -> None:
    with pytest.raises(SelectionKernelError, match=message):
        last_token_select_bf16(values, logical_rows=logical_rows)  # type: ignore[arg-type]


def test_scalar_selection_rejects_ragged_and_nonfinite_inputs() -> None:
    with pytest.raises(SelectionReferenceError, match="rectangular"):
        reference_select([[0x3F80], [0x3F80, 0x4000]], logical_rows=2)
    with pytest.raises(SelectionReferenceError, match="finite"):
        reference_select([[0x7F80]], logical_rows=1)


def test_unread_capacity_rows_cannot_influence_selection() -> None:
    values = [[0x3F80, 0xBF80], [0x7F80, -1]]
    executed = last_token_select_bf16(values, logical_rows=1)
    reference = reference_select(values, logical_rows=1)
    assert executed.index == reference.index == 0
    assert executed.values.tolist() == [[0x3F80, 0xBF80]]
    assert reference.values == ((0x3F80, 0xBF80),)
