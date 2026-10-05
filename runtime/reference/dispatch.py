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

from .formats import (
    NumericReferenceError,
    binary32_add,
    binary32_balanced_sum,
    binary32_bits_to_bf16_rne,
    decode_bf16,
    decode_binary32,
    encode_binary32_rne,
)


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


@dataclass(frozen=True)
class ExpertOutputGroup:
    """BF16 expert outputs aligned one-for-one with a dispatch group."""

    expert_id: int
    output_bf16_rows: tuple[BF16Vector, ...]


@dataclass(frozen=True)
class ExpertReduceResult:
    """Reduced BF16 tensor plus sticky final-output saturation count."""

    output_bf16_codes: BF16Batch
    output_saturation_count: int


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise DispatchReferenceError(f"{label} must be a sequence")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise DispatchReferenceError(f"{label} must be an integer >= 1")
    return value


def _finite_bf16_batch(
    value: object, *, label: str = "hidden_bf16_codes"
) -> BF16Batch:
    batches = _sequence(value, label)
    if not batches:
        raise DispatchReferenceError(f"{label} must contain at least one batch")
    result: list[BF16Sequence] = []
    sequence_length: int | None = None
    hidden_width: int | None = None
    for batch_index, raw_sequence in enumerate(batches):
        sequence = _sequence(
            raw_sequence, f"{label}[{batch_index}]"
        )
        if sequence_length is None:
            sequence_length = len(sequence)
            if sequence_length == 0:
                raise DispatchReferenceError(
                    f"{label} must contain at least one position per batch"
                )
        elif len(sequence) != sequence_length:
            raise DispatchReferenceError(
                f"{label} must be a rectangular rank-3 tensor"
            )

        output_sequence: list[BF16Vector] = []
        for position, raw_vector in enumerate(sequence):
            vector = _sequence(
                raw_vector, f"{label}[{batch_index}][{position}]"
            )
            if hidden_width is None:
                hidden_width = len(vector)
                if hidden_width == 0:
                    raise DispatchReferenceError(
                        f"{label} vectors must contain at least one BF16 value"
                    )
            elif len(vector) != hidden_width:
                raise DispatchReferenceError(
                    f"{label} must be a rectangular rank-3 tensor"
                )

            output_vector: list[int] = []
            for column, code in enumerate(vector):
                element_label = f"{label}[{batch_index}][{position}][{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise DispatchReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite:
                    raise DispatchReferenceError(
                        f"{element_label} must be finite BF16"
                    )
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


def _validated_dispatch(value: object) -> ExpertDispatchResult:
    if not isinstance(value, ExpertDispatchResult):
        raise DispatchReferenceError("dispatch must be an ExpertDispatchResult")

    batch_size = _positive_integer(value.batch_size, "dispatch.batch_size")
    sequence_length = _positive_integer(
        value.sequence_length, "dispatch.sequence_length"
    )
    hidden_width = _positive_integer(value.hidden_width, "dispatch.hidden_width")
    expert_count = _positive_integer(value.expert_count, "dispatch.expert_count")
    top_k = _positive_integer(value.top_k, "dispatch.top_k")
    if top_k > expert_count:
        raise DispatchReferenceError(
            "dispatch.top_k must not exceed dispatch.expert_count"
        )

    raw_groups = _sequence(value.groups, "dispatch.groups")
    token_count = batch_size * sequence_length
    seen_assignments: set[tuple[int, int]] = set()
    hidden_by_token: dict[int, BF16Vector] = {}
    previous_expert_id = -1
    for group_index, raw_group in enumerate(raw_groups):
        label = f"dispatch.groups[{group_index}]"
        if not isinstance(raw_group, ExpertDispatchGroup):
            raise DispatchReferenceError(f"{label} must be an ExpertDispatchGroup")
        expert_id = raw_group.expert_id
        if (
            isinstance(expert_id, bool)
            or not isinstance(expert_id, int)
            or not 0 <= expert_id < expert_count
        ):
            raise DispatchReferenceError(
                f"{label}.expert_id must be in [0, {expert_count})"
            )
        if expert_id <= previous_expert_id:
            raise DispatchReferenceError(
                "dispatch groups must have unique ascending expert IDs"
            )
        previous_expert_id = expert_id

        token_indices = _sequence(raw_group.token_indices, f"{label}.token_indices")
        selected_slots = _sequence(raw_group.selected_slots, f"{label}.selected_slots")
        hidden_rows = _sequence(raw_group.hidden_bf16_rows, f"{label}.hidden_bf16_rows")
        weight_codes = _sequence(
            raw_group.routed_weight_codes, f"{label}.routed_weight_codes"
        )
        group_size = len(token_indices)
        if group_size == 0:
            raise DispatchReferenceError("dispatch groups must be nonempty")
        if not (
            len(selected_slots) == len(hidden_rows) == len(weight_codes) == group_size
        ):
            raise DispatchReferenceError(
                f"{label} assignment payload lengths must match"
            )

        previous_pair = (-1, -1)
        for assignment_index, (
            token_index,
            selected_slot,
            raw_hidden,
            weight_code,
        ) in enumerate(
            zip(
                token_indices,
                selected_slots,
                hidden_rows,
                weight_codes,
                strict=True,
            )
        ):
            assignment_label = f"{label}.assignment[{assignment_index}]"
            if (
                isinstance(token_index, bool)
                or not isinstance(token_index, int)
                or not 0 <= token_index < token_count
            ):
                raise DispatchReferenceError(
                    f"{assignment_label}.token_index must be in [0, {token_count})"
                )
            if (
                isinstance(selected_slot, bool)
                or not isinstance(selected_slot, int)
                or not 0 <= selected_slot < top_k
            ):
                raise DispatchReferenceError(
                    f"{assignment_label}.selected_slot must be in [0, {top_k})"
                )
            pair = (token_index, selected_slot)
            if pair <= previous_pair:
                raise DispatchReferenceError(
                    f"{label} assignments must ascend by token then selected slot"
                )
            previous_pair = pair
            if pair in seen_assignments:
                raise DispatchReferenceError(
                    "dispatch must contain each token/selected-slot pair exactly once"
                )
            seen_assignments.add(pair)

            hidden = _sequence(raw_hidden, f"{assignment_label}.hidden_bf16_row")
            if len(hidden) != hidden_width:
                raise DispatchReferenceError(
                    f"{assignment_label}.hidden_bf16_row must have hidden width "
                    f"{hidden_width}"
                )
            validated_hidden: list[int] = []
            for column, code in enumerate(hidden):
                element_label = f"{assignment_label}.hidden_bf16_row[{column}]"
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise DispatchReferenceError(
                        f"{element_label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite:
                    raise DispatchReferenceError(f"{element_label} must be finite BF16")
                validated_hidden.append(code)
            hidden_row = tuple(validated_hidden)
            if token_index in hidden_by_token:
                if hidden_by_token[token_index] != hidden_row:
                    raise DispatchReferenceError(
                        "dispatch assignments for one token must carry one hidden row"
                    )
            else:
                hidden_by_token[token_index] = hidden_row

            if isinstance(weight_code, bool) or not isinstance(weight_code, int):
                raise DispatchReferenceError(
                    f"{assignment_label}.routed_weight_code must be binary32"
                )
            try:
                decoded_weight = decode_binary32(weight_code)
            except ValueError as exc:
                raise DispatchReferenceError(
                    f"{assignment_label}.routed_weight_code must be binary32"
                ) from exc
            if not decoded_weight.finite or decoded_weight.value is None:
                raise DispatchReferenceError(
                    f"{assignment_label}.routed_weight_code must be finite binary32"
                )
            if decoded_weight.value < 0:
                raise DispatchReferenceError(
                    f"{assignment_label}.routed_weight_code must be nonnegative"
                )

    expected_assignments = token_count * top_k
    if len(seen_assignments) != expected_assignments:
        raise DispatchReferenceError(
            "dispatch must contain each token/selected-slot pair exactly once"
        )
    return value


def _expert_output_groups(
    value: object,
    *,
    dispatch: ExpertDispatchResult,
) -> tuple[ExpertOutputGroup, ...]:
    raw_groups = _sequence(value, "routed_output_groups")
    if len(raw_groups) != len(dispatch.groups):
        raise DispatchReferenceError(
            "routed_output_groups must align one-for-one with dispatch groups"
        )
    result: list[ExpertOutputGroup] = []
    for group_index, (raw_group, dispatch_group) in enumerate(
        zip(raw_groups, dispatch.groups, strict=True)
    ):
        if not isinstance(raw_group, ExpertOutputGroup):
            raise DispatchReferenceError(
                f"routed_output_groups[{group_index}] must be an ExpertOutputGroup"
            )
        if raw_group.expert_id != dispatch_group.expert_id:
            raise DispatchReferenceError(
                f"routed_output_groups[{group_index}] expert_id must match dispatch"
            )
        raw_rows = _sequence(
            raw_group.output_bf16_rows,
            f"routed_output_groups[{group_index}].output_bf16_rows",
        )
        if len(raw_rows) != len(dispatch_group.token_indices):
            raise DispatchReferenceError(
                f"routed_output_groups[{group_index}] row count must match dispatch"
            )
        output_rows: list[BF16Vector] = []
        for row_index, raw_row in enumerate(raw_rows):
            row = _sequence(
                raw_row,
                f"routed_output_groups[{group_index}].output_bf16_rows[{row_index}]",
            )
            if len(row) != dispatch.hidden_width:
                raise DispatchReferenceError(
                    f"routed_output_groups[{group_index}] rows must have hidden width "
                    f"{dispatch.hidden_width}"
                )
            output_row: list[int] = []
            for column, code in enumerate(row):
                label = (
                    f"routed_output_groups[{group_index}]."
                    f"output_bf16_rows[{row_index}][{column}]"
                )
                if (
                    isinstance(code, bool)
                    or not isinstance(code, int)
                    or not 0 <= code <= BF16_MAX_ENCODING
                ):
                    raise DispatchReferenceError(
                        f"{label} must be a 16-bit BF16 encoding"
                    )
                decoded = decode_bf16(code)
                if not decoded.finite or decoded.value is None:
                    raise DispatchReferenceError(f"{label} must be finite BF16")
                output_row.append(code)
            output_rows.append(tuple(output_row))
        result.append(ExpertOutputGroup(raw_group.expert_id, tuple(output_rows)))
    return tuple(result)


def reduce_expert_outputs_bf16(
    dispatch: ExpertDispatchResult,
    routed_output_groups: Sequence[ExpertOutputGroup],
    shared_output_bf16_codes: Sequence[Sequence[Sequence[int]]],
) -> ExpertReduceResult:
    """Reduce routed slots and the shared expert into architectural BF16.

    Duplicate selected slots for one expert are all retained and reduced first.
    Distinct expert contributions then reduce in ascending logical expert-ID
    order with the NUM-6.1 tree. The BF16 shared expert is added last with one
    binary32 RNE addition, matching the source-visible operation boundary, and
    the result converts once to BF16.
    """

    dispatch = _validated_dispatch(dispatch)
    groups = _expert_output_groups(routed_output_groups, dispatch=dispatch)
    shared = _finite_bf16_batch(
        shared_output_bf16_codes, label="shared_output_bf16_codes"
    )
    if (
        len(shared) != dispatch.batch_size
        or len(shared[0]) != dispatch.sequence_length
        or len(shared[0][0]) != dispatch.hidden_width
    ):
        raise DispatchReferenceError(
            "shared_output_bf16_codes shape must match the dispatch output shape"
        )

    token_count = dispatch.batch_size * dispatch.sequence_length
    grouped_rows_by_token: list[list[tuple[int, tuple[BF16Vector, ...]]]] = [
        [] for _ in range(token_count)
    ]
    for dispatch_group, output_group in zip(dispatch.groups, groups, strict=True):
        rows_by_token: dict[int, list[BF16Vector]] = {}
        for token_index, output_row in zip(
            dispatch_group.token_indices,
            output_group.output_bf16_rows,
            strict=True,
        ):
            rows_by_token.setdefault(token_index, []).append(output_row)
        for token_index, rows in rows_by_token.items():
            grouped_rows_by_token[token_index].append(
                (dispatch_group.expert_id, tuple(rows))
            )

    output_flat: list[BF16Vector] = []
    saturation_count = 0
    shared_flat = tuple(row for sequence in shared for row in sequence)
    for token_index in range(token_count):
        expert_groups = grouped_rows_by_token[token_index]
        expert_ids = [expert_id for expert_id, _ in expert_groups]
        if not expert_groups or expert_ids != sorted(set(expert_ids)):
            raise DispatchReferenceError(
                f"token {token_index} must have unique ascending routed experts"
            )
        output_row: list[int] = []
        for column in range(dispatch.hidden_width):
            expert_contributions: list[int] = []
            try:
                for _, expert_rows in expert_groups:
                    slot_codes = [row[column] for row in expert_rows]
                    widened_slots = []
                    for code in slot_codes:
                        decoded = decode_bf16(code)
                        if decoded.value is None:  # pragma: no cover - validated
                            raise RuntimeError(
                                "validated routed output became nonfinite"
                            )
                        widened_slots.append(encode_binary32_rne(decoded.value))
                    expert_contributions.append(binary32_balanced_sum(widened_slots))
                routed = binary32_balanced_sum(expert_contributions)
                shared_value = decode_bf16(shared_flat[token_index][column])
                if shared_value.value is None:  # pragma: no cover - validated
                    raise RuntimeError("validated shared output became nonfinite")
                combined = binary32_add(
                    routed,
                    encode_binary32_rne(shared_value.value),
                )
                converted = binary32_bits_to_bf16_rne(combined)
            except NumericReferenceError as exc:
                raise DispatchReferenceError(
                    f"expert reduction failed at token {token_index}, "
                    f"column {column}: {exc}"
                ) from exc
            saturation_count += int(converted.saturated)
            output_row.append(converted.code)
        output_flat.append(tuple(output_row))

    output = tuple(
        tuple(
            output_flat[batch * dispatch.sequence_length + position]
            for position in range(dispatch.sequence_length)
        )
        for batch in range(dispatch.batch_size)
    )
    return ExpertReduceResult(output, saturation_count)


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "Binary32Matrix",
    "Binary32Row",
    "DispatchReferenceError",
    "ExpertDispatchGroup",
    "ExpertDispatchResult",
    "ExpertOutputGroup",
    "ExpertReduceResult",
    "IndexMatrix",
    "IndexRow",
    "dispatch_routed_experts_bf16",
    "reduce_expert_outputs_bf16",
]
