"""Exact table-lookup references for DeepSeek V4 embedding and hash routing.

Both operators are pure gathers in the pinned source. The global embedding
reference is mathematically equivalent to the vocabulary-parallel zero-mask and
all-reduce implementation because exactly one shard owns every valid token row.
BF16 values are carried as their raw 16-bit encodings, so the lookup introduces
no host floating-point conversion. Hash routing likewise returns the exact
checkpoint table entries without consulting or reordering router scores.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BF16_MAX_ENCODING = (1 << 16) - 1

TokenMatrix: TypeAlias = tuple[tuple[int, ...], ...]
BF16Row: TypeAlias = tuple[int, ...]
BF16EmbeddingTensor: TypeAlias = tuple[tuple[BF16Row, ...], ...]
RouteTable: TypeAlias = tuple[tuple[int, ...], ...]


class LookupReferenceError(ValueError):
    """Raised when a table or lookup request is structurally invalid."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise LookupReferenceError(f"{label} must be a sequence")
    return value


def _integer(value: object, label: str, *, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LookupReferenceError(f"{label} must be a nonnegative integer")
    if maximum is not None and value > maximum:
        raise LookupReferenceError(f"{label}={value} exceeds {maximum}")
    return value


def _token_matrix(value: object, *, vocabulary_size: int) -> TokenMatrix:
    batches = _sequence(value, "token_ids")
    if not batches:
        raise LookupReferenceError("token_ids must contain at least one batch")
    result: list[tuple[int, ...]] = []
    sequence_length: int | None = None
    for batch_index, raw_row in enumerate(batches):
        row = _sequence(raw_row, f"token_ids[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(row)
            if sequence_length == 0:
                raise LookupReferenceError(
                    "token_ids must contain at least one token per batch"
                )
        elif len(row) != sequence_length:
            raise LookupReferenceError("token_ids must be a rectangular rank-2 tensor")
        result.append(
            tuple(
                _integer(
                    token_id,
                    f"token_ids[{batch_index}][{position}]",
                    maximum=vocabulary_size - 1,
                )
                for position, token_id in enumerate(row)
            )
        )
    return tuple(result)


def _bf16_table(value: object) -> tuple[BF16Row, ...]:
    rows = _sequence(value, "embedding_weight")
    if not rows:
        raise LookupReferenceError("embedding_weight must contain at least one row")
    result: list[BF16Row] = []
    width: int | None = None
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"embedding_weight[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise LookupReferenceError(
                    "embedding_weight rows must contain at least one BF16 value"
                )
        elif len(row) != width:
            raise LookupReferenceError(
                "embedding_weight must be a rectangular rank-2 tensor"
            )
        result.append(
            tuple(
                _integer(
                    code,
                    f"embedding_weight[{row_index}][{column}]",
                    maximum=BF16_MAX_ENCODING,
                )
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def bf16_token_embedding(
    token_ids: Sequence[Sequence[int]],
    embedding_weight: Sequence[Sequence[int]],
) -> BF16EmbeddingTensor:
    """Gather global BF16 embedding rows for a rectangular token-ID tensor.

    Elements of ``embedding_weight`` and the result are exact BF16 bit patterns,
    not Python floating-point approximations.
    """

    weight = _bf16_table(embedding_weight)
    tokens = _token_matrix(token_ids, vocabulary_size=len(weight))
    return tuple(tuple(weight[token_id] for token_id in batch) for batch in tokens)


def _route_table(value: object, *, expert_count: int) -> RouteTable:
    rows = _sequence(value, "route_table")
    if not rows:
        raise LookupReferenceError("route_table must contain at least one row")
    result: list[tuple[int, ...]] = []
    top_k: int | None = None
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"route_table[{row_index}]")
        if top_k is None:
            top_k = len(row)
            if top_k == 0:
                raise LookupReferenceError(
                    "route_table rows must contain at least one expert"
                )
        elif len(row) != top_k:
            raise LookupReferenceError("route_table must be a rectangular rank-2 tensor")
        result.append(
            tuple(
                _integer(
                    expert_id,
                    f"route_table[{row_index}][{slot}]",
                    maximum=expert_count - 1,
                )
                for slot, expert_id in enumerate(row)
            )
        )
    return tuple(result)


def hash_route_indices(
    token_ids: Sequence[int],
    route_table: Sequence[Sequence[int]],
    *,
    expert_count: int,
) -> tuple[tuple[int, ...], ...]:
    """Gather checkpoint-pinned expert IDs for flattened input token IDs.

    Duplicate expert IDs are preserved: the pinned source performs a plain table
    lookup and does not declare uniqueness enforcement at this boundary.
    """

    expert_count = _integer(expert_count, "expert_count")
    if expert_count == 0:
        raise LookupReferenceError("expert_count must be greater than zero")
    table = _route_table(route_table, expert_count=expert_count)
    raw_tokens = _sequence(token_ids, "token_ids")
    if not raw_tokens:
        raise LookupReferenceError("token_ids must contain at least one token")
    tokens = tuple(
        _integer(token_id, f"token_ids[{index}]", maximum=len(table) - 1)
        for index, token_id in enumerate(raw_tokens)
    )
    return tuple(table[token_id] for token_id in tokens)


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "BF16EmbeddingTensor",
    "BF16Row",
    "LookupReferenceError",
    "RouteTable",
    "TokenMatrix",
    "bf16_token_embedding",
    "hash_route_indices",
]
