"""Transactional DeepSeek V4 circular KV-window write semantics.

This module freezes the two assignments in the pinned
``inference/model.py:Attention.forward`` implementation:

* prefill (``start_pos == 0``) writes all rows when ``S <= W`` and otherwise
  retains only the final ``W`` input rows in circular slot order; and
* decode (``start_pos > 0``) requires ``S == 1`` and replaces slot
  ``start_pos % W``.

The official attention cache has source shape ``[B, W, 512]``.  Its one latent
KV row is shared by all 64 query heads.  The reference makes this sharing axis
explicit as ``[B, W, H, V]`` with the pinned mapping ``H=1, V=512``; it must not
be interpreted as a 64-head KV cache.  Smaller factorizations with
``H*V <= 512`` are admitted so the structural semantics can be exhaustively
tested without allocating the full official tensor.

Every input and prior-state BF16 encoding is validated before any output state
is constructed.  The state and result are deeply immutable tuples, and a
failed transaction exposes no partially updated cache.  Counters describe
logical operator reads, writes, and retained state only.  Host validation and
immutable tuple construction are deliberately excluded.  In particular, the
byte counters are not HBM transactions, bursts, cycles, bandwidth, latency,
energy, area, PPA, or a service/RTL schedule claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .formats import decode_bf16


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
KV_WINDOW_PROFILE = "opentallas.deepseek_v4_kv_window_write.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
PINNED_WINDOW_SIZE = 128
PINNED_KV_HEAD_COUNT = 1
PINNED_KV_VALUE_WIDTH = 512
PINNED_QUERY_HEAD_COUNT = 64
PINNED_KV_ROW_WIDTH = PINNED_KV_HEAD_COUNT * PINNED_KV_VALUE_WIDTH
BF16_BYTES = 2
BF16_MAX_ENCODING = (1 << 16) - 1


BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadRow: TypeAlias = tuple[BF16Vector, ...]
BF16Window: TypeAlias = tuple[BF16HeadRow, ...]
BF16WindowTensor: TypeAlias = tuple[BF16Window, ...]
BF16InputSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16InputTensor: TypeAlias = tuple[BF16InputSequence, ...]
KVWindowMode: TypeAlias = Literal["prefill", "decode"]


class KVWindowReferenceError(ValueError):
    """Raised when a KV-window transaction is malformed or poisoned."""


@dataclass(frozen=True)
class KVWindowState:
    """Immutable BF16 circular-window cache with axes ``[B,W,H,V]``."""

    bf16_codes: BF16WindowTensor


@dataclass(frozen=True)
class KVWindowWriteSegment:
    """One nonempty source/destination slice in source assignment order."""

    source_sequence_start: int
    source_sequence_stop: int
    absolute_position_start: int
    absolute_position_stop: int
    destination_slot_start: int
    destination_slot_stop: int


@dataclass(frozen=True)
class KVWindowWriteCounters:
    """Exact logical traffic and state accounting for one committed command.

    ``logical_state_*_read`` is zero because ``Attention.forward`` does not
    consume old destination values before replacing them.  Untouched state is
    counted separately as preserved state, not as logical traffic.
    """

    active_batch_count: int
    state_batch_capacity: int
    sequence_length: int
    window_size: int
    kv_head_count: int
    kv_value_width: int
    input_rows: int
    input_bf16_values: int
    committed_positions_per_batch: int
    uncommitted_positions_per_batch: int
    logical_source_rows_read: int
    logical_source_bf16_values_read: int
    logical_source_read_bytes: int
    logical_state_rows_read: int
    logical_state_bf16_values_read: int
    logical_state_read_bytes: int
    logical_state_rows_written: int
    logical_state_bf16_values_written: int
    logical_state_write_bytes: int
    state_rows_preserved: int
    state_bf16_values_preserved: int
    source_slice_assignments: int
    nonempty_source_slice_assignments: int
    logical_slot_modulo_evaluations: int
    transaction_commits: int


@dataclass(frozen=True)
class KVWindowWriteResult:
    """One fully committed cache version and its exact write mapping."""

    state: KVWindowState
    mode: KVWindowMode
    start_pos: int
    end_pos: int
    segments: tuple[KVWindowWriteSegment, ...]
    counters: KVWindowWriteCounters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise KVWindowReferenceError(f"{label} must be an exact list or tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise KVWindowReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise KVWindowReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite:
        raise KVWindowReferenceError(f"{label} must be finite BF16")
    return value


def _validate_state(
    state: object,
) -> tuple[BF16WindowTensor, int, int, int, int]:
    if type(state) is not KVWindowState:
        raise KVWindowReferenceError("state must be an exact KVWindowState")
    raw_batches = _sequence(state.bf16_codes, "state.bf16_codes")
    if not raw_batches:
        raise KVWindowReferenceError("state.bf16_codes must contain at least one batch")
    if len(raw_batches) > PINNED_MAX_BATCH_SIZE:
        raise KVWindowReferenceError(
            f"state batch capacity exceeds pinned maximum {PINNED_MAX_BATCH_SIZE}"
        )

    window_size: int | None = None
    head_count: int | None = None
    value_width: int | None = None
    batches: list[BF16Window] = []
    for batch_index, raw_window in enumerate(raw_batches):
        window = _sequence(raw_window, f"state.bf16_codes[{batch_index}]")
        if window_size is None:
            window_size = len(window)
            if not 1 <= window_size <= PINNED_WINDOW_SIZE:
                raise KVWindowReferenceError(
                    f"state window extent must be in [1, {PINNED_WINDOW_SIZE}]"
                )
        elif len(window) != window_size:
            raise KVWindowReferenceError(
                "state.bf16_codes must be rectangular on the window axis"
            )

        rows: list[BF16HeadRow] = []
        for slot, raw_heads in enumerate(window):
            heads = _sequence(raw_heads, f"state.bf16_codes[{batch_index}][{slot}]")
            if head_count is None:
                head_count = len(heads)
                if not 1 <= head_count <= PINNED_KV_ROW_WIDTH:
                    raise KVWindowReferenceError(
                        f"state KV-head extent must be in [1, {PINNED_KV_ROW_WIDTH}]"
                    )
            elif len(heads) != head_count:
                raise KVWindowReferenceError(
                    "state.bf16_codes must be rectangular on the KV-head axis"
                )

            output_heads: list[BF16Vector] = []
            for head, raw_values in enumerate(heads):
                values = _sequence(
                    raw_values,
                    f"state.bf16_codes[{batch_index}][{slot}][{head}]",
                )
                if value_width is None:
                    value_width = len(values)
                    if not 1 <= value_width <= PINNED_KV_ROW_WIDTH:
                        raise KVWindowReferenceError(
                            "state KV-value extent must be in "
                            f"[1, {PINNED_KV_ROW_WIDTH}]"
                        )
                elif len(values) != value_width:
                    raise KVWindowReferenceError(
                        "state.bf16_codes must be rectangular on the value axis"
                    )
                output_heads.append(
                    tuple(
                        _finite_bf16(
                            code,
                            f"state.bf16_codes[{batch_index}]"
                            f"[{slot}][{head}][{column}]",
                        )
                        for column, code in enumerate(values)
                    )
                )
            rows.append(tuple(output_heads))
        batches.append(tuple(rows))

    assert window_size is not None
    assert head_count is not None
    assert value_width is not None
    if head_count * value_width > PINNED_KV_ROW_WIDTH:
        raise KVWindowReferenceError(
            "state KV-head/value product exceeds the pinned 512-value KV row"
        )
    return (
        tuple(batches),
        len(batches),
        window_size,
        head_count,
        value_width,
    )


def _validate_input(
    value: object,
    *,
    batch_capacity: int,
    head_count: int,
    value_width: int,
) -> tuple[BF16InputTensor, int, int]:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if not raw_batches:
        raise KVWindowReferenceError(
            "kv_bf16_codes must contain at least one active batch"
        )
    if len(raw_batches) > batch_capacity:
        raise KVWindowReferenceError(
            "kv_bf16_codes active batches exceed state batch capacity"
        )

    sequence_length: int | None = None
    batches: list[BF16InputSequence] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"kv_bf16_codes[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(sequence)
            if not 1 <= sequence_length <= PINNED_MAX_POSITION:
                raise KVWindowReferenceError(
                    "kv_bf16_codes sequence extent must be in "
                    f"[1, {PINNED_MAX_POSITION}]"
                )
        elif len(sequence) != sequence_length:
            raise KVWindowReferenceError(
                "kv_bf16_codes must be rectangular on the sequence axis"
            )

        positions: list[BF16HeadRow] = []
        for position, raw_heads in enumerate(sequence):
            heads = _sequence(raw_heads, f"kv_bf16_codes[{batch_index}][{position}]")
            if len(heads) != head_count:
                raise KVWindowReferenceError(
                    f"kv_bf16_codes[{batch_index}][{position}] must contain "
                    f"exactly {head_count} KV heads"
                )
            output_heads: list[BF16Vector] = []
            for head, raw_values in enumerate(heads):
                values = _sequence(
                    raw_values,
                    f"kv_bf16_codes[{batch_index}][{position}][{head}]",
                )
                if len(values) != value_width:
                    raise KVWindowReferenceError(
                        f"kv_bf16_codes[{batch_index}][{position}][{head}] "
                        f"must contain exactly {value_width} values"
                    )
                output_heads.append(
                    tuple(
                        _finite_bf16(
                            code,
                            f"kv_bf16_codes[{batch_index}]"
                            f"[{position}][{head}][{column}]",
                        )
                        for column, code in enumerate(values)
                    )
                )
            positions.append(tuple(output_heads))
        batches.append(tuple(positions))

    assert sequence_length is not None
    return tuple(batches), len(batches), sequence_length


def zero_kv_window_state_bf16(
    *,
    batch_capacity: int = PINNED_MAX_BATCH_SIZE,
    window_size: int = PINNED_WINDOW_SIZE,
    kv_head_count: int = PINNED_KV_HEAD_COUNT,
    kv_value_width: int = PINNED_KV_VALUE_WIDTH,
) -> KVWindowState:
    """Create a validated all-positive-zero cache with explicit axes."""

    batch_capacity = _integer(
        batch_capacity,
        "batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    window_size = _integer(
        window_size,
        "window_size",
        minimum=1,
        maximum=PINNED_WINDOW_SIZE,
    )
    kv_head_count = _integer(
        kv_head_count,
        "kv_head_count",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    kv_value_width = _integer(
        kv_value_width,
        "kv_value_width",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    if kv_head_count * kv_value_width > PINNED_KV_ROW_WIDTH:
        raise KVWindowReferenceError(
            "kv_head_count * kv_value_width exceeds the pinned 512-value KV row"
        )
    vector = (0x0000,) * kv_value_width
    row = (vector,) * kv_head_count
    window = (row,) * window_size
    state = KVWindowState((window,) * batch_capacity)
    _validate_state(state)
    return state


def kv_window_state_bf16(value: object) -> KVWindowState:
    """Validate and deeply freeze caller-provided ``[B,W,H,V]`` state."""

    state = KVWindowState(value)  # type: ignore[arg-type]
    frozen, _, _, _, _ = _validate_state(state)
    return KVWindowState(frozen)


def _write_plan(
    *,
    start_pos: int,
    sequence_length: int,
    window_size: int,
) -> tuple[
    KVWindowMode,
    tuple[KVWindowWriteSegment, ...],
    int,
    int,
    int,
]:
    if start_pos == 0:
        mode: KVWindowMode = "prefill"
        if sequence_length <= window_size:
            return (
                mode,
                (
                    KVWindowWriteSegment(
                        source_sequence_start=0,
                        source_sequence_stop=sequence_length,
                        absolute_position_start=0,
                        absolute_position_stop=sequence_length,
                        destination_slot_start=0,
                        destination_slot_stop=sequence_length,
                    ),
                ),
                sequence_length,
                1,
                0,
            )

        cutoff = sequence_length % window_size
        first_length = window_size - cutoff
        source_start = sequence_length - window_size
        segments = [
            KVWindowWriteSegment(
                source_sequence_start=source_start,
                source_sequence_stop=source_start + first_length,
                absolute_position_start=source_start,
                absolute_position_stop=source_start + first_length,
                destination_slot_start=cutoff,
                destination_slot_stop=window_size,
            )
        ]
        if cutoff:
            segments.append(
                KVWindowWriteSegment(
                    source_sequence_start=sequence_length - cutoff,
                    source_sequence_stop=sequence_length,
                    absolute_position_start=sequence_length - cutoff,
                    absolute_position_stop=sequence_length,
                    destination_slot_start=0,
                    destination_slot_stop=cutoff,
                )
            )
        return mode, tuple(segments), window_size, 2, 1

    if sequence_length != 1:
        raise KVWindowReferenceError(
            "decode KV_WINDOW_WRITE requires sequence length exactly 1"
        )
    slot = start_pos % window_size
    return (
        "decode",
        (
            KVWindowWriteSegment(
                source_sequence_start=0,
                source_sequence_stop=1,
                absolute_position_start=start_pos,
                absolute_position_stop=start_pos + 1,
                destination_slot_start=slot,
                destination_slot_stop=slot + 1,
            ),
        ),
        1,
        1,
        1,
    )


def kv_window_write_bf16(
    state: KVWindowState,
    kv_bf16_codes: object,
    *,
    start_pos: int,
) -> KVWindowWriteResult:
    """Commit one exact prefill or decode circular-window transaction.

    ``state`` is never mutated.  Active batches are the prefix
    ``state[:B]``, matching the source's ``self.kv_cache[:bsz]`` addressing;
    inactive batch rows are preserved bit-for-bit.
    """

    frozen_state, batch_capacity, window_size, head_count, value_width = (
        _validate_state(state)
    )
    start_pos = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    frozen_input, batch_size, sequence_length = _validate_input(
        kv_bf16_codes,
        batch_capacity=batch_capacity,
        head_count=head_count,
        value_width=value_width,
    )
    if start_pos + sequence_length > PINNED_MAX_POSITION:
        raise KVWindowReferenceError(
            "KV_WINDOW_WRITE end position exceeds the pinned maximum position"
        )
    mode, segments, committed_positions, slice_assignments, modulo_evaluations = (
        _write_plan(
            start_pos=start_pos,
            sequence_length=sequence_length,
            window_size=window_size,
        )
    )

    # All validation and address derivation complete before construction of the
    # new immutable state begins. Every segment is nonempty and destination
    # slots are unique within this transaction.
    mutable_batches = [list(window) for window in frozen_state]
    for batch_index in range(batch_size):
        output_window = mutable_batches[batch_index]
        source_sequence = frozen_input[batch_index]
        for segment in segments:
            source_rows = source_sequence[
                segment.source_sequence_start : segment.source_sequence_stop
            ]
            expected_length = (
                segment.destination_slot_stop - segment.destination_slot_start
            )
            if len(source_rows) != expected_length:  # pragma: no cover - invariant
                raise KVWindowReferenceError(
                    "internal KV-window segment extents differ"
                )
            output_window[
                segment.destination_slot_start : segment.destination_slot_stop
            ] = source_rows

    committed_state = KVWindowState(tuple(tuple(window) for window in mutable_batches))
    row_values = head_count * value_width
    input_rows = batch_size * sequence_length
    written_rows = batch_size * committed_positions
    state_rows = batch_capacity * window_size
    counters = KVWindowWriteCounters(
        active_batch_count=batch_size,
        state_batch_capacity=batch_capacity,
        sequence_length=sequence_length,
        window_size=window_size,
        kv_head_count=head_count,
        kv_value_width=value_width,
        input_rows=input_rows,
        input_bf16_values=input_rows * row_values,
        committed_positions_per_batch=committed_positions,
        uncommitted_positions_per_batch=sequence_length - committed_positions,
        logical_source_rows_read=written_rows,
        logical_source_bf16_values_read=written_rows * row_values,
        logical_source_read_bytes=written_rows * row_values * BF16_BYTES,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=written_rows,
        logical_state_bf16_values_written=written_rows * row_values,
        logical_state_write_bytes=written_rows * row_values * BF16_BYTES,
        state_rows_preserved=state_rows - written_rows,
        state_bf16_values_preserved=(state_rows - written_rows) * row_values,
        source_slice_assignments=slice_assignments,
        nonempty_source_slice_assignments=len(segments),
        logical_slot_modulo_evaluations=modulo_evaluations,
        transaction_commits=1,
    )
    return KVWindowWriteResult(
        state=committed_state,
        mode=mode,
        start_pos=start_pos,
        end_pos=start_pos + sequence_length,
        segments=segments,
        counters=counters,
    )


__all__ = [
    "BF16_BYTES",
    "BF16_MAX_ENCODING",
    "INFERENCE_CONFIG_SHA256",
    "KV_WINDOW_PROFILE",
    "MODEL_SOURCE_SHA256",
    "PINNED_KV_HEAD_COUNT",
    "PINNED_KV_ROW_WIDTH",
    "PINNED_KV_VALUE_WIDTH",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "PINNED_QUERY_HEAD_COUNT",
    "PINNED_WINDOW_SIZE",
    "BF16HeadRow",
    "BF16InputSequence",
    "BF16InputTensor",
    "BF16Vector",
    "BF16Window",
    "BF16WindowTensor",
    "KVWindowMode",
    "KVWindowReferenceError",
    "KVWindowState",
    "KVWindowWriteCounters",
    "KVWindowWriteResult",
    "KVWindowWriteSegment",
    "kv_window_state_bf16",
    "kv_window_write_bf16",
    "zero_kv_window_state_bf16",
]
