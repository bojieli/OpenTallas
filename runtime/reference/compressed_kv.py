"""Transactional DeepSeek V4 compressed-KV cache-write semantics.

The pinned ``Compressor.forward`` writes a row only after a ratio-sized raw
compression window has been pooled, normalized, position transformed, and
activation-QDQ reconstructed to BF16.  Prefill writes the complete prefix
``:seqlen // ratio``; one-token decode writes slot ``start_pos // ratio`` only
when ``(start_pos + 1) % ratio == 0``.

The released module relies on its caller to delimit sessions and does not carry
an explicit validity bitmap.  This target reference adds a committed-prefix
bitmap so a new-session prefill invalidates stale rows and a decode cannot read
or extend a forged prefix.  Payload rows outside the valid prefix remain
bit-preserved.  This is an explicit accelerator transaction adaptation, not a
claim that the PyTorch object stores validity bits.

Every input and prior-state encoding validates before a new immutable state is
constructed.  Counters are logical operator traffic and committed state only;
they are not HBM bursts, SRAM banking, cycles, bandwidth, latency, energy, or
PPA claims.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .formats import decode_bf16


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
COMPRESSED_KV_PROFILE = "opentallas.deepseek_v4_compressed_kv_write.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
PINNED_MAIN_HEAD_DIM = 512
PINNED_INDEX_HEAD_DIM = 128
PINNED_COMPRESSION_RATIOS = (4, 128)
BF16_BYTES = 2
BF16_MAX_ENCODING = (1 << 16) - 1


BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadRow: TypeAlias = tuple[BF16Vector, ...]
BF16CacheSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16CacheTensor: TypeAlias = tuple[BF16CacheSequence, ...]
BF16InputSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16InputTensor: TypeAlias = tuple[BF16InputSequence, ...]
ValidityTensor: TypeAlias = tuple[tuple[bool, ...], ...]
CompressedKVMode: TypeAlias = Literal["prefill", "decode"]


class CompressedKVReferenceError(ValueError):
    """Raised when a compressed-KV transaction is malformed or poisoned."""


@dataclass(frozen=True)
class CompressedKVState:
    """Immutable BF16 cache and committed-prefix validity, axes ``[B,C,H,V]``."""

    ratio: int
    bf16_codes: BF16CacheTensor
    valid: ValidityTensor


@dataclass(frozen=True)
class CompressedKVWriteCounters:
    """Exact logical payload and validity accounting for one commit."""

    active_batch_count: int
    state_batch_capacity: int
    sequence_length: int
    ratio: int
    cache_capacity: int
    kv_head_count: int
    kv_value_width: int
    completed_rows_per_batch: int
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
    valid_rows_before: int
    valid_rows_invalidated: int
    validity_bits_written: int
    valid_rows_after: int
    transaction_commits: int


@dataclass(frozen=True)
class CompressedKVWriteResult:
    """A fully committed state version and its source-derived cache slots."""

    state: CompressedKVState
    mode: CompressedKVMode
    cache_slots: tuple[int, ...]
    start_pos: int
    end_pos: int
    counters: CompressedKVWriteCounters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise CompressedKVReferenceError(f"{label} must be an exact list or tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CompressedKVReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _ratio(value: object) -> int:
    if type(value) is not int or value not in PINNED_COMPRESSION_RATIOS:
        raise CompressedKVReferenceError(
            "ratio must be exactly 4 (overlap) or 128 (non-overlap)"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise CompressedKVReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite or decoded.value is None:
        raise CompressedKVReferenceError(f"{label} must be finite BF16")
    return value


def _validate_state(
    state: object,
) -> tuple[CompressedKVState, int, int, int, int]:
    if type(state) is not CompressedKVState:
        raise CompressedKVReferenceError("state must be an exact CompressedKVState")
    ratio = _ratio(state.ratio)
    raw_batches = _sequence(state.bf16_codes, "state.bf16_codes")
    raw_valid_batches = _sequence(state.valid, "state.valid")
    if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
        raise CompressedKVReferenceError(
            f"state batch capacity must be in [1, {PINNED_MAX_BATCH_SIZE}]"
        )
    if len(raw_valid_batches) != len(raw_batches):
        raise CompressedKVReferenceError(
            "state payload and validity batch capacities must match"
        )

    capacity: int | None = None
    head_count: int | None = None
    value_width: int | None = None
    batches: list[BF16CacheSequence] = []
    valid_batches: list[tuple[bool, ...]] = []
    for batch_index, (raw_cache, raw_valid) in enumerate(
        zip(raw_batches, raw_valid_batches, strict=True)
    ):
        cache = _sequence(raw_cache, f"state.bf16_codes[{batch_index}]")
        validity = _sequence(raw_valid, f"state.valid[{batch_index}]")
        if capacity is None:
            capacity = len(cache)
            if not 1 <= capacity <= PINNED_MAX_POSITION // ratio:
                raise CompressedKVReferenceError(
                    "state cache capacity is outside the pinned range"
                )
        elif len(cache) != capacity:
            raise CompressedKVReferenceError(
                "state payload must be rectangular on the cache axis"
            )
        if len(validity) != len(cache):
            raise CompressedKVReferenceError(
                "state payload and validity cache extents must match"
            )

        frozen_validity: list[bool] = []
        seen_invalid = False
        for slot, flag in enumerate(validity):
            if type(flag) is not bool:
                raise CompressedKVReferenceError(
                    f"state.valid[{batch_index}][{slot}] must be bool"
                )
            if seen_invalid and flag:
                raise CompressedKVReferenceError(
                    "state valid rows must form a contiguous prefix"
                )
            seen_invalid |= not flag
            frozen_validity.append(flag)

        rows: list[BF16HeadRow] = []
        for slot, raw_heads in enumerate(cache):
            heads = _sequence(
                raw_heads,
                f"state.bf16_codes[{batch_index}][{slot}]",
            )
            if head_count is None:
                head_count = len(heads)
                if not 1 <= head_count <= PINNED_MAIN_HEAD_DIM:
                    raise CompressedKVReferenceError(
                        "state KV-head extent is outside the pinned row width"
                    )
            elif len(heads) != head_count:
                raise CompressedKVReferenceError(
                    "state payload must be rectangular on the KV-head axis"
                )

            frozen_heads: list[BF16Vector] = []
            for head, raw_values in enumerate(heads):
                values = _sequence(
                    raw_values,
                    f"state.bf16_codes[{batch_index}][{slot}][{head}]",
                )
                if value_width is None:
                    value_width = len(values)
                    if not 1 <= value_width <= PINNED_MAIN_HEAD_DIM:
                        raise CompressedKVReferenceError(
                            "state KV-value extent is outside the pinned row width"
                        )
                elif len(values) != value_width:
                    raise CompressedKVReferenceError(
                        "state payload must be rectangular on the value axis"
                    )
                frozen_heads.append(
                    tuple(
                        _finite_bf16(
                            code,
                            f"state.bf16_codes[{batch_index}]"
                            f"[{slot}][{head}][{column}]",
                        )
                        for column, code in enumerate(values)
                    )
                )
            rows.append(tuple(frozen_heads))
        batches.append(tuple(rows))
        valid_batches.append(tuple(frozen_validity))

    assert capacity is not None
    assert head_count is not None
    assert value_width is not None
    if head_count * value_width > PINNED_MAIN_HEAD_DIM:
        raise CompressedKVReferenceError(
            "state KV-head/value product exceeds the pinned 512-value row"
        )
    return (
        CompressedKVState(
            ratio=ratio,
            bf16_codes=tuple(batches),
            valid=tuple(valid_batches),
        ),
        len(batches),
        capacity,
        head_count,
        value_width,
    )


def zero_compressed_kv_state_bf16(
    *,
    ratio: int,
    cache_capacity: int,
    kv_head_count: int = 1,
    kv_value_width: int,
    batch_capacity: int = PINNED_MAX_BATCH_SIZE,
) -> CompressedKVState:
    """Create an all-positive-zero cache with no committed rows."""

    ratio = _ratio(ratio)
    batch_capacity = _integer(
        batch_capacity,
        "batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    cache_capacity = _integer(
        cache_capacity,
        "cache_capacity",
        minimum=1,
        maximum=PINNED_MAX_POSITION // ratio,
    )
    kv_head_count = _integer(
        kv_head_count,
        "kv_head_count",
        minimum=1,
        maximum=PINNED_MAIN_HEAD_DIM,
    )
    kv_value_width = _integer(
        kv_value_width,
        "kv_value_width",
        minimum=1,
        maximum=PINNED_MAIN_HEAD_DIM,
    )
    if kv_head_count * kv_value_width > PINNED_MAIN_HEAD_DIM:
        raise CompressedKVReferenceError(
            "kv_head_count * kv_value_width exceeds the pinned 512-value row"
        )
    vector = (0x0000,) * kv_value_width
    row = (vector,) * kv_head_count
    cache = (row,) * cache_capacity
    state = CompressedKVState(
        ratio=ratio,
        bf16_codes=(cache,) * batch_capacity,
        valid=((False,) * cache_capacity,) * batch_capacity,
    )
    return _validate_state(state)[0]


def compressed_kv_state_bf16(value: object) -> CompressedKVState:
    """Validate and deeply freeze caller-provided cache state."""

    return _validate_state(value)[0]


def _validate_input(
    value: object,
    *,
    batch_capacity: int,
    expected_rows: int,
    head_count: int,
    value_width: int,
) -> tuple[BF16InputTensor, int]:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if not 1 <= len(raw_batches) <= batch_capacity:
        raise CompressedKVReferenceError(
            "kv_bf16_codes active batch extent is outside state capacity"
        )
    batches: list[BF16InputSequence] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"kv_bf16_codes[{batch_index}]")
        if len(sequence) != expected_rows:
            raise CompressedKVReferenceError(
                f"kv_bf16_codes[{batch_index}] must contain exactly "
                f"{expected_rows} completed rows"
            )
        rows: list[BF16HeadRow] = []
        for row_index, raw_heads in enumerate(sequence):
            heads = _sequence(
                raw_heads,
                f"kv_bf16_codes[{batch_index}][{row_index}]",
            )
            if len(heads) != head_count:
                raise CompressedKVReferenceError(
                    f"kv_bf16_codes[{batch_index}][{row_index}] must contain "
                    f"exactly {head_count} KV heads"
                )
            frozen_heads: list[BF16Vector] = []
            for head, raw_values in enumerate(heads):
                values = _sequence(
                    raw_values,
                    f"kv_bf16_codes[{batch_index}][{row_index}][{head}]",
                )
                if len(values) != value_width:
                    raise CompressedKVReferenceError(
                        "compressed KV input value width differs from state"
                    )
                frozen_heads.append(
                    tuple(
                        _finite_bf16(
                            code,
                            f"kv_bf16_codes[{batch_index}]"
                            f"[{row_index}][{head}][{column}]",
                        )
                        for column, code in enumerate(values)
                    )
                )
            rows.append(tuple(frozen_heads))
        batches.append(tuple(rows))
    return tuple(batches), len(batches)


def compressed_kv_write_bf16(
    state: CompressedKVState,
    kv_bf16_codes: object,
    *,
    start_pos: int,
    sequence_length: int,
) -> CompressedKVWriteResult:
    """Commit one exact prefill or one-token decode compressed-cache transaction."""

    frozen, batch_capacity, capacity, head_count, value_width = _validate_state(state)
    start_pos = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    sequence_length = _integer(
        sequence_length,
        "sequence_length",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    if start_pos + sequence_length > PINNED_MAX_POSITION:
        raise CompressedKVReferenceError(
            "compressed KV end position exceeds the pinned maximum position"
        )

    if start_pos == 0:
        mode: CompressedKVMode = "prefill"
        completed_rows = sequence_length // frozen.ratio
        cache_slots = tuple(range(completed_rows))
    else:
        mode = "decode"
        if sequence_length != 1:
            raise CompressedKVReferenceError(
                "decode compressed KV write requires sequence length exactly 1"
            )
        completed_rows = int((start_pos + 1) % frozen.ratio == 0)
        cache_slots = (start_pos // frozen.ratio,) if completed_rows else ()
    if cache_slots and cache_slots[-1] >= capacity:
        raise CompressedKVReferenceError(
            "compressed KV write exceeds cache capacity"
        )
    source, batch_size = _validate_input(
        kv_bf16_codes,
        batch_capacity=batch_capacity,
        expected_rows=completed_rows,
        head_count=head_count,
        value_width=value_width,
    )

    # Validation, shape checks, address derivation, and decode-prefix checks all
    # complete before any new state is assembled.
    if mode == "decode":
        expected_prefix = start_pos // frozen.ratio
        for batch_index in range(batch_size):
            observed_prefix = sum(frozen.valid[batch_index])
            if observed_prefix != expected_prefix:
                raise CompressedKVReferenceError(
                    f"compressed KV valid prefix for batch {batch_index} is "
                    f"{observed_prefix}, expected {expected_prefix}"
                )

    mutable_payload = [list(sequence) for sequence in frozen.bf16_codes]
    mutable_validity = [list(validity) for validity in frozen.valid]
    valid_before = sum(sum(validity) for validity in frozen.valid)
    invalidated = 0
    validity_writes = 0
    for batch_index in range(batch_size):
        if mode == "prefill":
            invalidated += sum(mutable_validity[batch_index])
            mutable_validity[batch_index] = [False] * capacity
            validity_writes += capacity
        for source_row, slot in enumerate(cache_slots):
            mutable_payload[batch_index][slot] = source[batch_index][source_row]
            mutable_validity[batch_index][slot] = True
            validity_writes += 1

    committed = CompressedKVState(
        ratio=frozen.ratio,
        bf16_codes=tuple(tuple(sequence) for sequence in mutable_payload),
        valid=tuple(tuple(validity) for validity in mutable_validity),
    )
    row_values = head_count * value_width
    written_rows = batch_size * completed_rows
    written_values = written_rows * row_values
    state_rows = batch_capacity * capacity
    counters = CompressedKVWriteCounters(
        active_batch_count=batch_size,
        state_batch_capacity=batch_capacity,
        sequence_length=sequence_length,
        ratio=frozen.ratio,
        cache_capacity=capacity,
        kv_head_count=head_count,
        kv_value_width=value_width,
        completed_rows_per_batch=completed_rows,
        logical_source_rows_read=written_rows,
        logical_source_bf16_values_read=written_values,
        logical_source_read_bytes=written_values * BF16_BYTES,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=written_rows,
        logical_state_bf16_values_written=written_values,
        logical_state_write_bytes=written_values * BF16_BYTES,
        state_rows_preserved=state_rows - written_rows,
        state_bf16_values_preserved=(state_rows - written_rows) * row_values,
        valid_rows_before=valid_before,
        valid_rows_invalidated=invalidated,
        validity_bits_written=validity_writes,
        valid_rows_after=sum(sum(validity) for validity in committed.valid),
        transaction_commits=1,
    )
    return CompressedKVWriteResult(
        state=committed,
        mode=mode,
        cache_slots=cache_slots,
        start_pos=start_pos,
        end_pos=start_pos + sequence_length,
        counters=counters,
    )


__all__ = [
    "BF16_BYTES",
    "BF16_MAX_ENCODING",
    "COMPRESSED_KV_PROFILE",
    "INFERENCE_CONFIG_SHA256",
    "MODEL_SOURCE_SHA256",
    "PINNED_COMPRESSION_RATIOS",
    "PINNED_INDEX_HEAD_DIM",
    "PINNED_MAIN_HEAD_DIM",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "CompressedKVMode",
    "CompressedKVReferenceError",
    "CompressedKVState",
    "CompressedKVWriteCounters",
    "CompressedKVWriteResult",
    "compressed_kv_state_bf16",
    "compressed_kv_write_bf16",
    "zero_compressed_kv_state_bf16",
]
