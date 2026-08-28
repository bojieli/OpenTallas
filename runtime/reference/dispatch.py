"""Deterministic DeepSeek V4 routed-expert dispatch semantics.

The pinned MoE flattens batch/sequence tokens, counts selected experts, and uses
``torch.where(indices == expert_id)`` before gathering hidden rows and routing
weights. This reference makes the resulting logical order explicit: nonempty
experts ascend by ID, and assignments within an expert ascend by flattened token
and then selected slot. Duplicate expert IDs remain distinct assignments.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypeAlias

from .formats import decode_bf16, decode_binary32


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BF16_MAX_ENCODING = (1 << 16) - 1

BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
IndexRow: TypeAlias = tuple[int, ...]
IndexMatrix: TypeAlias = tuple[IndexRow, ...]
Binary32Row: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Row, ...]


class DispatchReferenceError(ValueError):
    """Raised when routed-dispatch inputs violate the target contract."""


@dataclass(frozen=True)
class ExpertDispatchGroup:
    """Aligned source rows, slots, payloads, and weights for one expert."""

    expert_id: int
    token_indices: tuple[int, ...]
    selected_slots: tuple[int, ...]
    hidden_bf16_rows: tuple[BF16Vector, ...]
    routed_weight_codes: Binary32Row


@dataclass(frozen=True)
class ExpertDispatchResult:
    """Complete logical dispatch plus the shape needed for inverse checking."""

    batch_size: int
    sequence_length: int
    hidden_width: int
    expert_count: int
    top_k: int
    groups: tuple[ExpertDispatchGroup, ...]


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise DispatchReferenceError(f"{label} must be a sequence")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DispatchReferenceError(f"{label} must be an integer >= 1")
    return value


def _finite_bf16_batch(value: object) -> BF16Batch:
    batches = _sequence(value, "hidden_bf16_codes")
    if not batches:
        raise DispatchReferenceError(
            "hidden_bf16_codes must contain at least one batch"
        )
    result: list[BF16Sequence] = []
    sequence_length: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(
            raw_sequence, f"hidden_bf16_codes[{batch_index}]"
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise DispatchReferenceError(
                    "hidden_bf16_codes must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise DispatchReferenceError(
                "hidden_bf16_codes must be a rectangular rank-3 tensor"
            )

        output_sequence: list[BF16Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(
                raw_vector, f"hidden_bf16_codes[{batch_index}][{position}]"
            )
            if hidden_width is None:
                hidden_width = len(vector)
                if hidden_width == 0:
                    raise DispatchReferenceError(
                        "hidden_bf16_codes vectors must contain at least one BF16 value"
                    )
            elif len(vector) != hidden_width:
                raise DispatchReferenceError(
                    "hidden_bf16_codes must be a rectangular rank-3 tensor"
                )

            output_vector: list[int] = []
            for column, code in enumerate(vector):
                label = f"hidden_bf16_codes[{batch_index}][{position}][{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise DispatchReferenceError(
                        f"{label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite:
                    raise DispatchReferenceError(f"{label} must be finite BF16")
                output_vector.append(code)
            output_sequence.append(tuple(output_vector))
        result.append(tuple(output_sequence))
    return tuple(result)


def _index_matrix(
    value: object, *, token_count: int, expert_count: int, top_k: int
) -> IndexMatrix:
    raw_rows = _sequence(value, "expert_indices")
    if len(raw_rows) != token_count:
        raise DispatchReferenceError(
            "expert_indices token count must equal flattened hidden token count"
        )
    result: list[IndexRow] = []
    for token_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"expert_indices[{token_index}]")
        if len(row) != top_k:
            raise DispatchReferenceError(
                f"expert_indices[{token_index}] must contain exactly top_k entries"
            )
        output_row: list[int] = []
        for selected_slot, expert_id in enumerate(row):
            if (
                isinstance(expert_id, bool)
                or not isinstance(expert_id, int)
                or not 0 <= expert_id < expert_count
            ):
                raise DispatchReferenceError(
                    f"expert_indices[{token_index}][{selected_slot}] must be in "
                    f"[0, {expert_count})"
                )
            output_row.append(expert_id)
        result.append(tuple(output_row))
    return tuple(result)


def _weight_matrix(
    value: object, *, token_count: int, top_k: int
) -> Binary32Matrix:
    raw_rows = _sequence(value, "routed_weight_codes")
    if len(raw_rows) != token_count:
        raise DispatchReferenceError(
            "routed_weight_codes token count must equal flattened hidden token count"
        )
    result: list[Binary32Row] = []
    for token_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"routed_weight_codes[{token_index}]")
        if len(row) != top_k:
            raise DispatchReferenceError(
                f"routed_weight_codes[{token_index}] must contain exactly top_k entries"
            )
        output_row: list[int] = []
        for selected_slot, code in enumerate(row):
            label = f"routed_weight_codes[{token_index}][{selected_slot}]"
            if isinstance(code, bool) or not isinstance(code, int):
                raise DispatchReferenceError(
                    f"{label} must be a binary32 encoding"
                )
            try:
                decoded = decode_binary32(code)
            except ValueError as exc:
                raise DispatchReferenceError(
                    f"{label} must be a binary32 encoding"
                ) from exc
            if not decoded.finite or decoded.value is None:
                raise DispatchReferenceError(f"{label} must be finite binary32")
            if decoded.value < 0:
                raise DispatchReferenceError(f"{label} must be nonnegative")
            output_row.append(code)
        result.append(tuple(output_row))
    return tuple(result)


def dispatch_routed_experts_bf16(
    hidden_bf16_codes: Sequence[Sequence[Sequence[int]]],
    expert_indices: Sequence[Sequence[int]],
    routed_weight_codes: Sequence[Sequence[int]],
    *,
    expert_count: int,
    top_k: int,
) -> ExpertDispatchResult:
    """Group flattened tokens and selected slots for routed expert execution.

    ``hidden_bf16_codes`` has shape ``[batch, sequence, width]``. Routing rows
    have shape ``[batch * sequence, top_k]`` in the same row-major flattening
    used by ``MoE.forward``. Payload bits are copied; this operation performs no
    expert arithmetic or routed-output reduction.
    """

    expert_count = _positive_integer(expert_count, "expert_count")
    top_k = _positive_integer(top_k, "top_k")
    if top_k > expert_count:
        raise DispatchReferenceError("top_k must not exceed expert_count")

    hidden = _finite_bf16_batch(hidden_bf16_codes)
    batch_size = len(hidden)
    sequence_length = len(hidden[0])
    hidden_width = len(hidden[0][0])
    flat_hidden = tuple(vector for sequence in hidden for vector in sequence)
    indices = _index_matrix(
        expert_indices,
        token_count=len(flat_hidden),
        expert_count=expert_count,
        top_k=top_k,
    )
    weights = _weight_matrix(
        routed_weight_codes,
        token_count=len(flat_hidden),
        top_k=top_k,
    )

    token_buckets: list[list[int]] = [[] for _ in range(expert_count)]
    slot_buckets: list[list[int]] = [[] for _ in range(expert_count)]
    hidden_buckets: list[list[BF16Vector]] = [[] for _ in range(expert_count)]
    weight_buckets: list[list[int]] = [[] for _ in range(expert_count)]
    for token_index, (index_row, weight_row) in enumerate(
        zip(indices, weights, strict=True)
    ):
        for selected_slot, (expert_id, weight_code) in enumerate(
            zip(index_row, weight_row, strict=True)
        ):
            token_buckets[expert_id].append(token_index)
            slot_buckets[expert_id].append(selected_slot)
            hidden_buckets[expert_id].append(flat_hidden[token_index])
            weight_buckets[expert_id].append(weight_code)

    groups = tuple(
        ExpertDispatchGroup(
            expert_id=expert_id,
            token_indices=tuple(token_buckets[expert_id]),
            selected_slots=tuple(slot_buckets[expert_id]),
            hidden_bf16_rows=tuple(hidden_buckets[expert_id]),
            routed_weight_codes=tuple(weight_buckets[expert_id]),
        )
        for expert_id in range(expert_count)
        if token_buckets[expert_id]
    )
    return ExpertDispatchResult(
        batch_size=batch_size,
        sequence_length=sequence_length,
        hidden_width=hidden_width,
        expert_count=expert_count,
        top_k=top_k,
        groups=groups,
    )


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "Binary32Matrix",
    "Binary32Row",
    "DispatchReferenceError",
    "ExpertDispatchGroup",
    "ExpertDispatchResult",
    "IndexMatrix",
    "IndexRow",
    "dispatch_routed_experts_bf16",
]
