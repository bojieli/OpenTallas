"""Independent structural-index references for pinned DeepSeek V4 operators.

The three functions in this module reproduce the integer tensors constructed by
the content-pinned ``inference/model.py`` helpers without importing PyTorch or
checkpoint code.  They deliberately return immutable Python tuples so callers
cannot confuse a known-answer reference with an accelerator buffer.

The official helpers cast their result to signed int32.  This reference rejects
inputs whose valid output indices would overflow int32 instead of inheriting a
backend-specific wraparound.  ``-1`` is the only invalid/padded index.
"""

from __future__ import annotations

from typing import TypeAlias


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
INT32_MAX = (1 << 31) - 1

IndexRow: TypeAlias = tuple[int, ...]
IndexMatrix: TypeAlias = tuple[IndexRow, ...]
IndexTensor: TypeAlias = tuple[IndexMatrix, ...]


class IndexReferenceError(ValueError):
    """Raised when an index request is outside the pinned source contract."""


def _integer(value: int, label: str, *, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IndexReferenceError(f"{label} must be an integer >= {minimum}")
    return value


def _int32_index(value: int, label: str) -> None:
    if value > INT32_MAX:
        raise IndexReferenceError(
            f"{label} produces index {value}, exceeding signed int32"
        )


def _broadcast(rows: IndexMatrix, batch_size: int) -> IndexTensor:
    return tuple(rows for _ in range(batch_size))


def window_indices(
    window_size: int,
    batch_size: int,
    sequence_length: int,
    start_position: int,
) -> IndexTensor:
    """Reproduce ``get_window_topk_idxs`` causal circular-window indices.

    At ``start_position == 0`` the source emits one row per prefill token, with
    future slots padded by ``-1``.  Once decoding has begun it emits one row: a
    partially filled linear window before wrap, then oldest-to-newest circular
    slots after wrap.  This one-row behavior is preserved even if a caller gives
    a sequence length greater than one in the decode branch.
    """

    window_size = _integer(window_size, "window_size", minimum=1)
    batch_size = _integer(batch_size, "batch_size", minimum=1)
    sequence_length = _integer(sequence_length, "sequence_length", minimum=1)
    start_position = _integer(start_position, "start_position", minimum=0)
    _int32_index(window_size - 1, "window_size")

    if start_position >= window_size - 1:
        current_slot = start_position % window_size
        row = tuple(range(current_slot + 1, window_size)) + tuple(
            range(current_slot + 1)
        )
        rows: IndexMatrix = (row,)
    elif start_position > 0:
        row = tuple(range(start_position + 1)) + (-1,) * (
            window_size - start_position - 1
        )
        rows = (row,)
    else:
        width = min(sequence_length, window_size)
        rows = tuple(
            tuple(
                candidate if candidate <= query_position else -1
                for candidate in range(
                    max(0, query_position - window_size + 1),
                    max(0, query_position - window_size + 1) + width,
                )
            )
            for query_position in range(sequence_length)
        )
        _int32_index(sequence_length - 1, "sequence_length")
    return _broadcast(rows, batch_size)


def compressed_dense_indices(
    ratio: int,
    batch_size: int,
    sequence_length: int,
    start_position: int,
    offset: int,
) -> IndexTensor:
    """Reproduce ``get_compress_topk_idxs`` complete-compression indices.

    Only fully completed ``ratio``-token groups are visible.  During prefill the
    output is padded to ``sequence_length // ratio`` columns for every query;
    decode emits one unpadded row.  ``offset`` places compressed entries after
    the ordinary window-cache address range.
    """

    ratio = _integer(ratio, "ratio", minimum=1)
    batch_size = _integer(batch_size, "batch_size", minimum=1)
    sequence_length = _integer(sequence_length, "sequence_length", minimum=1)
    start_position = _integer(start_position, "start_position", minimum=0)
    offset = _integer(offset, "offset", minimum=0)

    if start_position > 0:
        complete_groups = (start_position + 1) // ratio
        if complete_groups:
            _int32_index(offset + complete_groups - 1, "compressed decode")
        rows: IndexMatrix = (
            tuple(offset + group for group in range(complete_groups)),
        )
    else:
        width = sequence_length // ratio
        if width:
            _int32_index(offset + width - 1, "compressed prefill")
        rows = tuple(
            tuple(
                offset + group
                if group < (query_position + 1) // ratio
                else -1
                for group in range(width)
            )
            for query_position in range(sequence_length)
        )
    return _broadcast(rows, batch_size)


def dspark_window_indices(
    window_size: int,
    batch_size: int,
    block_size: int,
    start_position: int,
) -> IndexTensor:
    """Reproduce ``get_dspark_topk_idxs`` history-plus-draft indices.

    Each of the ``block_size`` draft queries receives the same key list: the
    populated prefix of the main circular window followed by the draft block in
    the disjoint address range beginning at ``window_size``.
    """

    window_size = _integer(window_size, "window_size", minimum=1)
    batch_size = _integer(batch_size, "batch_size", minimum=1)
    block_size = _integer(block_size, "block_size", minimum=1)
    start_position = _integer(start_position, "start_position", minimum=1)
    _int32_index(window_size + block_size - 1, "DSpark window")

    row = tuple(range(min(window_size, start_position + 1))) + tuple(
        window_size + draft_position for draft_position in range(block_size)
    )
    rows: IndexMatrix = tuple(row for _ in range(block_size))
    return _broadcast(rows, batch_size)


__all__ = [
    "INT32_MAX",
    "MODEL_SOURCE_SHA256",
    "IndexMatrix",
    "IndexReferenceError",
    "IndexRow",
    "IndexTensor",
    "compressed_dense_indices",
    "dspark_window_indices",
    "window_indices",
]
