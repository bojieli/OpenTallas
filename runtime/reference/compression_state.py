"""Transactional DeepSeek V4 compressor-state preparation semantics.

This module freezes the stateful portion of the pinned
``inference/model.py:Compressor.forward`` implementation.  It starts after the
learned ``wkv`` and ``wgate`` projections: callers provide their finite
binary32 outputs plus the finite binary32 APE parameter.  It produces the
updated decode state and, whenever a complete compression group exists, the
exact operands that the source passes to softmax pooling.

Two released profiles are admitted:

* ratio 4 is overlapping.  Projected rows have width ``2 * D`` and state has
  shape ``[B, 8, 2*D]``.  Pool operands have shape ``[B, G, 8, D]``.  Their
  first group is padded with zero KV and negative-infinity scores; later
  groups combine the preceding projection's first half with the current
  projection's second half.
* ratio 128 is non-overlapping.  Projected rows and state rows have width
  ``D`` and state has shape ``[B, 128, D]``.  Pool operands have shape
  ``[B, G, 128, D]``.

On decode, one projected row is written at ``start_pos % ratio`` (offset by
``ratio`` for overlap).  A complete overlap group first exposes the previous
state's first feature half and the current state's second feature half, then
copies the full current state into the previous state.  Inactive batches are
preserved bit-for-bit.

The result deliberately contains *pre-softmax operands*, not a compressed KV
vector.  Learned projection, softmax pooling, normalization, RoPE, QDQ, and
compressed-cache writes are separate downstream operations and are explicit
nonclaims of this reference.  Counters are logical source/state traffic only;
they do not claim transactions, bursts, cycles, bandwidth, latency, energy,
area, PPA, or a hardware schedule.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .formats import NumericReferenceError, binary32_add, decode_binary32


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
COMPRESS_STATE_PROFILE = "opentallas.deepseek_v4_compress_state_update.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
PINNED_MAIN_HEAD_DIM = 512
PINNED_INDEX_HEAD_DIM = 128
PINNED_OVERLAP_RATIO = 4
PINNED_NONOVERLAP_RATIO = 128
PINNED_COMPRESSION_RATIOS = (
    PINNED_OVERLAP_RATIO,
    PINNED_NONOVERLAP_RATIO,
)
F32_BYTES = 4
F32_MAX_ENCODING = (1 << 32) - 1
F32_NEGATIVE_INFINITY = 0xFF800000

EXCLUDED_DOWNSTREAM_OPERATIONS = (
    "learned_projection",
    "softmax_pooling",
    "rms_normalization",
    "rotary_embedding",
    "activation_qdq",
    "compressed_cache_write",
)


F32Vector: TypeAlias = tuple[int, ...]
F32Sequence: TypeAlias = tuple[F32Vector, ...]
F32Batch: TypeAlias = tuple[F32Sequence, ...]
F32PoolGroup: TypeAlias = tuple[F32Vector, ...]
F32PoolSequence: TypeAlias = tuple[F32PoolGroup, ...]
F32PoolBatch: TypeAlias = tuple[F32PoolSequence, ...]
CompressionMode: TypeAlias = Literal["prefill", "decode"]


class CompressionStateReferenceError(ValueError):
    """Raised when a compression-state transaction is malformed or poisoned."""


@dataclass(frozen=True)
class CompressionState:
    """Immutable projected-KV and biased-score state for one ratio profile."""

    ratio: int
    kv_f32_codes: F32Batch
    score_f32_codes: F32Batch


@dataclass(frozen=True)
class CompressionPoolInputs:
    """Immutable pre-softmax operands with axes ``[B,G,P,D]``.

    ``P`` is 8 for overlap ratio 4 and 128 for non-overlap ratio 128.  This is
    not a pooled, normalized, rotated, or quantized output.
    """

    kv_f32_codes: F32PoolBatch
    score_f32_codes: F32PoolBatch


@dataclass(frozen=True)
class CompressionStateCounters:
    """Exact logical value and byte accounting for one committed update."""

    active_batch_count: int
    state_batch_capacity: int
    sequence_length: int
    ratio: int
    overlap: bool
    head_dim: int
    projected_width: int
    complete_group_count: int
    input_kv_f32_values: int
    input_score_f32_values: int
    logical_source_kv_f32_values_read: int
    logical_source_score_f32_values_read: int
    logical_source_kv_read_bytes: int
    logical_source_score_read_bytes: int
    logical_ape_f32_values_read: int
    logical_ape_read_bytes: int
    logical_score_ape_additions: int
    logical_kv_state_f32_values_read: int
    logical_score_state_f32_values_read: int
    logical_kv_state_read_bytes: int
    logical_score_state_read_bytes: int
    logical_kv_state_f32_values_written: int
    logical_score_state_f32_values_written: int
    logical_kv_state_write_bytes: int
    logical_score_state_write_bytes: int
    kv_state_f32_values_preserved: int
    score_state_f32_values_preserved: int
    pool_kv_f32_values: int
    pool_score_f32_values: int
    overlap_pool_zero_f32_values: int
    overlap_pool_negative_infinity_f32_values: int
    kv_state_roll_f32_values: int
    score_state_roll_f32_values: int
    logical_ratio_modulo_evaluations: int
    transaction_commits: int


@dataclass(frozen=True)
class CompressionStateUpdateResult:
    """One committed state version and optional downstream pool operands."""

    state: CompressionState
    mode: CompressionMode
    start_pos: int
    end_pos: int
    prefill_cutoff: int | None
    prefill_remainder: int | None
    decode_phase: int | None
    should_compress: bool
    pool_inputs: CompressionPoolInputs | None
    counters: CompressionStateCounters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise CompressionStateReferenceError(f"{label} must be an exact list or tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise CompressionStateReferenceError(
            f"{label} must be an integer in [{minimum}, {maximum}]"
        )
    return value


def _ratio(value: object) -> int:
    if type(value) is not int or value not in PINNED_COMPRESSION_RATIOS:
        raise CompressionStateReferenceError(
            "ratio must be exactly 4 (overlap) or 128 (non-overlap)"
        )
    return value


def _f32_code(
    value: object,
    label: str,
    *,
    allow_negative_infinity: bool = False,
) -> int:
    if type(value) is not int or not 0 <= value <= F32_MAX_ENCODING:
        raise CompressionStateReferenceError(
            f"{label} must be a 32-bit binary32 encoding"
        )
    decoded = decode_binary32(value)
    if decoded.finite:
        return value
    if allow_negative_infinity and value == F32_NEGATIVE_INFINITY:
        return value
    permitted = "finite binary32 or the negative-infinity sentinel"
    if not allow_negative_infinity:
        permitted = "finite binary32"
    raise CompressionStateReferenceError(f"{label} must be {permitted}")


def _freeze_tensor3(
    value: object,
    label: str,
    *,
    batch_count: int | None = None,
    minimum_batches: int = 1,
    maximum_batches: int = PINNED_MAX_BATCH_SIZE,
    sequence_length: int | None = None,
    maximum_sequence_length: int | None = None,
    width: int | None = None,
    allow_negative_infinity: bool = False,
) -> tuple[F32Batch, int, int, int]:
    raw_batches = _sequence(value, label)
    if batch_count is None:
        if not minimum_batches <= len(raw_batches) <= maximum_batches:
            raise CompressionStateReferenceError(
                f"{label} batch extent must be in "
                f"[{minimum_batches}, {maximum_batches}]"
            )
        observed_batches = len(raw_batches)
    else:
        if len(raw_batches) != batch_count:
            raise CompressionStateReferenceError(
                f"{label} must contain exactly {batch_count} batches"
            )
        observed_batches = batch_count

    observed_sequence = sequence_length
    observed_width = width
    batches: list[F32Sequence] = []
    for batch_index, raw_sequence in enumerate(raw_batches):
        sequence = _sequence(raw_sequence, f"{label}[{batch_index}]")
        if observed_sequence is None:
            observed_sequence = len(sequence)
            if observed_sequence < 1:
                raise CompressionStateReferenceError(
                    f"{label} must contain at least one row per batch"
                )
            if (
                maximum_sequence_length is not None
                and observed_sequence > maximum_sequence_length
            ):
                raise CompressionStateReferenceError(
                    f"{label} sequence extent exceeds {maximum_sequence_length}"
                )
        elif len(sequence) != observed_sequence:
            raise CompressionStateReferenceError(
                f"{label} must be rectangular on the sequence axis"
            )

        rows: list[F32Vector] = []
        for position, raw_row in enumerate(sequence):
            row = _sequence(raw_row, f"{label}[{batch_index}][{position}]")
            if observed_width is None:
                observed_width = len(row)
                if observed_width < 1:
                    raise CompressionStateReferenceError(
                        f"{label} rows must contain at least one value"
                    )
            elif len(row) != observed_width:
                raise CompressionStateReferenceError(
                    f"{label} must be rectangular on the value axis"
                )
            rows.append(
                tuple(
                    _f32_code(
                        code,
                        f"{label}[{batch_index}][{position}][{column}]",
                        allow_negative_infinity=allow_negative_infinity,
                    )
                    for column, code in enumerate(row)
                )
            )
        batches.append(tuple(rows))

    assert observed_sequence is not None
    assert observed_width is not None
    return (
        tuple(batches),
        observed_batches,
        observed_sequence,
        observed_width,
    )


def _freeze_ape(
    value: object,
    *,
    ratio: int,
    width: int,
) -> tuple[F32Vector, ...]:
    raw_rows = _sequence(value, "ape_f32_codes")
    if len(raw_rows) != ratio:
        raise CompressionStateReferenceError(
            f"ape_f32_codes must contain exactly {ratio} rows"
        )
    rows: list[F32Vector] = []
    for position, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"ape_f32_codes[{position}]")
        if len(row) != width:
            raise CompressionStateReferenceError(
                f"ape_f32_codes[{position}] must contain exactly {width} values"
            )
        rows.append(
            tuple(
                _f32_code(
                    code,
                    f"ape_f32_codes[{position}][{column}]",
                )
                for column, code in enumerate(row)
            )
        )
    return tuple(rows)


def _validate_state(
    state: object,
) -> tuple[CompressionState, int, int, bool, int, int, int]:
    if type(state) is not CompressionState:
        raise CompressionStateReferenceError("state must be an exact CompressionState")
    ratio = _ratio(state.ratio)
    overlap = ratio == PINNED_OVERLAP_RATIO
    coefficient = 2 if overlap else 1
    slot_count = coefficient * ratio
    frozen_kv, capacity, _, width = _freeze_tensor3(
        state.kv_f32_codes,
        "state.kv_f32_codes",
        sequence_length=slot_count,
    )
    if width % coefficient:
        raise CompressionStateReferenceError(
            "state projected width must be divisible by its overlap coefficient"
        )
    head_dim = width // coefficient
    if not 1 <= head_dim <= PINNED_MAIN_HEAD_DIM:
        raise CompressionStateReferenceError(
            f"state head dimension must be in [1, {PINNED_MAIN_HEAD_DIM}]"
        )
    frozen_scores, _, _, _ = _freeze_tensor3(
        state.score_f32_codes,
        "state.score_f32_codes",
        batch_count=capacity,
        sequence_length=slot_count,
        width=width,
        allow_negative_infinity=True,
    )
    return (
        CompressionState(ratio, frozen_kv, frozen_scores),
        capacity,
        ratio,
        overlap,
        coefficient,
        head_dim,
        width,
    )


def zero_compression_state_f32(
    *,
    ratio: int,
    batch_capacity: int = PINNED_MAX_BATCH_SIZE,
    head_dim: int = PINNED_MAIN_HEAD_DIM,
) -> CompressionState:
    """Create the source's zero-KV/negative-infinity-score initial state."""

    ratio = _ratio(ratio)
    batch_capacity = _integer(
        batch_capacity,
        "batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    head_dim = _integer(
        head_dim,
        "head_dim",
        minimum=1,
        maximum=PINNED_MAIN_HEAD_DIM,
    )
    coefficient = 2 if ratio == PINNED_OVERLAP_RATIO else 1
    width = coefficient * head_dim
    slots = coefficient * ratio
    kv_row = (0,) * width
    score_row = (F32_NEGATIVE_INFINITY,) * width
    kv_sequence = (kv_row,) * slots
    score_sequence = (score_row,) * slots
    return CompressionState(
        ratio=ratio,
        kv_f32_codes=(kv_sequence,) * batch_capacity,
        score_f32_codes=(score_sequence,) * batch_capacity,
    )


def compression_state_f32(
    kv_f32_codes: object,
    score_f32_codes: object,
    *,
    ratio: int,
) -> CompressionState:
    """Validate and deeply freeze caller-provided projected state tensors."""

    candidate = CompressionState(
        ratio=ratio,
        kv_f32_codes=kv_f32_codes,  # type: ignore[arg-type]
        score_f32_codes=score_f32_codes,  # type: ignore[arg-type]
    )
    frozen, _, _, _, _, _, _ = _validate_state(candidate)
    return frozen


def _add_ape(
    score: F32Vector,
    ape: F32Vector,
    *,
    batch_index: int,
    source_position: int,
    ape_position: int,
) -> F32Vector:
    output: list[int] = []
    for column, (score_code, ape_code) in enumerate(zip(score, ape, strict=True)):
        try:
            output.append(binary32_add(score_code, ape_code))
        except NumericReferenceError as exc:
            raise CompressionStateReferenceError(
                "score + APE binary32 arithmetic failed at batch "
                f"{batch_index}, source position {source_position}, "
                f"APE position {ape_position}, column {column}: {exc}"
            ) from exc
    return tuple(output)


def _prefill_pool_inputs(
    kv: F32Batch,
    scores: F32Batch,
    ape: tuple[F32Vector, ...],
    *,
    ratio: int,
    overlap: bool,
    head_dim: int,
    cutoff: int,
) -> CompressionPoolInputs | None:
    group_count = cutoff // ratio
    if group_count == 0:
        return None

    batches_kv: list[F32PoolSequence] = []
    batches_scores: list[F32PoolSequence] = []
    zero_row = (0,) * head_dim
    negative_infinity_row = (F32_NEGATIVE_INFINITY,) * head_dim
    for batch_index, (kv_sequence, score_sequence) in enumerate(
        zip(kv, scores, strict=True)
    ):
        # The source adds APE to the full complete prefix before applying the
        # overlap transform.  This intentionally evaluates feature halves that
        # the transform later replaces with padding or a neighboring group.
        biased_scores = tuple(
            _add_ape(
                score_sequence[source_position],
                ape[source_position % ratio],
                batch_index=batch_index,
                source_position=source_position,
                ape_position=source_position % ratio,
            )
            for source_position in range(cutoff)
        )
        kv_groups: list[F32PoolGroup] = []
        score_groups: list[F32PoolGroup] = []
        for group_index in range(group_count):
            group_start = group_index * ratio
            if not overlap:
                kv_groups.append(
                    tuple(kv_sequence[group_start + phase] for phase in range(ratio))
                )
                score_groups.append(
                    tuple(biased_scores[group_start + phase] for phase in range(ratio))
                )
                continue

            if group_index == 0:
                kv_rows: list[F32Vector] = [zero_row] * ratio
                score_rows: list[F32Vector] = [negative_infinity_row] * ratio
            else:
                previous_start = group_start - ratio
                kv_rows = [
                    kv_sequence[previous_start + phase][:head_dim]
                    for phase in range(ratio)
                ]
                score_rows = [
                    biased_scores[previous_start + phase][:head_dim]
                    for phase in range(ratio)
                ]
            kv_rows.extend(
                kv_sequence[group_start + phase][head_dim:] for phase in range(ratio)
            )
            score_rows.extend(
                biased_scores[group_start + phase][head_dim:] for phase in range(ratio)
            )
            kv_groups.append(tuple(kv_rows))
            score_groups.append(tuple(score_rows))
        batches_kv.append(tuple(kv_groups))
        batches_scores.append(tuple(score_groups))
    return CompressionPoolInputs(tuple(batches_kv), tuple(batches_scores))


def compress_state_update_f32(
    state: CompressionState,
    projected_kv_f32_codes: object,
    projected_score_f32_codes: object,
    ape_f32_codes: object,
    *,
    start_pos: int,
) -> CompressionStateUpdateResult:
    """Commit one exact prefill or decode compressor-state transaction.

    All caller data and the entire old state are validated before address
    derivation or result construction.  The old state is never mutated.
    """

    (
        frozen_state,
        capacity,
        ratio,
        overlap,
        coefficient,
        head_dim,
        projected_width,
    ) = _validate_state(state)
    start_pos = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    frozen_kv, batch_size, sequence_length, _ = _freeze_tensor3(
        projected_kv_f32_codes,
        "projected_kv_f32_codes",
        maximum_batches=PINNED_MAX_BATCH_SIZE,
        maximum_sequence_length=PINNED_MAX_POSITION,
        width=projected_width,
    )
    if batch_size > capacity:
        raise CompressionStateReferenceError(
            "projected inputs active batches exceed state batch capacity"
        )
    frozen_scores, _, _, _ = _freeze_tensor3(
        projected_score_f32_codes,
        "projected_score_f32_codes",
        batch_count=batch_size,
        sequence_length=sequence_length,
        width=projected_width,
    )
    frozen_ape = _freeze_ape(
        ape_f32_codes,
        ratio=ratio,
        width=projected_width,
    )
    if start_pos + sequence_length > PINNED_MAX_POSITION:
        raise CompressionStateReferenceError(
            "compression-state end position exceeds the pinned maximum position"
        )
    if start_pos > 0 and sequence_length != 1:
        raise CompressionStateReferenceError(
            "decode COMPRESS_STATE_UPDATE requires sequence length exactly 1"
        )

    mutable_kv = [list(sequence) for sequence in frozen_state.kv_f32_codes]
    mutable_scores = [list(sequence) for sequence in frozen_state.score_f32_codes]
    pool_inputs: CompressionPoolInputs | None
    prefill_cutoff: int | None
    prefill_remainder: int | None
    decode_phase: int | None
    state_source_rows_per_batch: int
    roll_values = 0

    if start_pos == 0:
        mode: CompressionMode = "prefill"
        remainder = sequence_length % ratio
        cutoff = sequence_length - remainder
        group_count = cutoff // ratio
        should_compress = group_count > 0
        prefill_cutoff = cutoff
        prefill_remainder = remainder
        decode_phase = None

        previous_rows = ratio if overlap and cutoff >= ratio else 0
        state_source_rows_per_batch = previous_rows + remainder
        if previous_rows:
            source_start = cutoff - ratio
            for batch_index in range(batch_size):
                for phase in range(ratio):
                    source_position = source_start + phase
                    mutable_kv[batch_index][phase] = frozen_kv[batch_index][
                        source_position
                    ]
                    mutable_scores[batch_index][phase] = _add_ape(
                        frozen_scores[batch_index][source_position],
                        frozen_ape[phase],
                        batch_index=batch_index,
                        source_position=source_position,
                        ape_position=phase,
                    )

        if remainder:
            destination_offset = ratio if overlap else 0
            for batch_index in range(batch_size):
                for phase in range(remainder):
                    source_position = cutoff + phase
                    destination = destination_offset + phase
                    mutable_kv[batch_index][destination] = frozen_kv[batch_index][
                        source_position
                    ]
                    mutable_scores[batch_index][destination] = _add_ape(
                        frozen_scores[batch_index][source_position],
                        frozen_ape[phase],
                        batch_index=batch_index,
                        source_position=source_position,
                        ape_position=phase,
                    )

        pool_inputs = _prefill_pool_inputs(
            frozen_kv,
            frozen_scores,
            frozen_ape,
            ratio=ratio,
            overlap=overlap,
            head_dim=head_dim,
            cutoff=cutoff,
        )
        modulo_evaluations = 1
    else:
        mode = "decode"
        phase = start_pos % ratio
        should_compress = (start_pos + 1) % ratio == 0
        group_count = 1 if should_compress else 0
        prefill_cutoff = None
        prefill_remainder = None
        decode_phase = phase
        state_source_rows_per_batch = 1
        destination = ratio + phase if overlap else phase

        for batch_index in range(batch_size):
            mutable_kv[batch_index][destination] = frozen_kv[batch_index][0]
            mutable_scores[batch_index][destination] = _add_ape(
                frozen_scores[batch_index][0],
                frozen_ape[phase],
                batch_index=batch_index,
                source_position=0,
                ape_position=phase,
            )

        if should_compress:
            pool_kv_batches: list[F32PoolSequence] = []
            pool_score_batches: list[F32PoolSequence] = []
            for batch_index in range(batch_size):
                if overlap:
                    kv_group = tuple(
                        row[:head_dim] for row in mutable_kv[batch_index][:ratio]
                    ) + tuple(row[head_dim:] for row in mutable_kv[batch_index][ratio:])
                    score_group = tuple(
                        row[:head_dim] for row in mutable_scores[batch_index][:ratio]
                    ) + tuple(
                        row[head_dim:] for row in mutable_scores[batch_index][ratio:]
                    )
                else:
                    kv_group = tuple(mutable_kv[batch_index])
                    score_group = tuple(mutable_scores[batch_index])
                pool_kv_batches.append((kv_group,))
                pool_score_batches.append((score_group,))
            pool_inputs = CompressionPoolInputs(
                tuple(pool_kv_batches),
                tuple(pool_score_batches),
            )
        else:
            pool_inputs = None

        if overlap and should_compress:
            roll_values = batch_size * ratio * projected_width
            for batch_index in range(batch_size):
                current = tuple(mutable_kv[batch_index][ratio:])
                current_scores = tuple(mutable_scores[batch_index][ratio:])
                mutable_kv[batch_index][:ratio] = current
                mutable_scores[batch_index][:ratio] = current_scores
        modulo_evaluations = 3

    committed_state = CompressionState(
        ratio=ratio,
        kv_f32_codes=tuple(tuple(sequence) for sequence in mutable_kv),
        score_f32_codes=tuple(tuple(sequence) for sequence in mutable_scores),
    )

    state_source_values = batch_size * state_source_rows_per_batch * projected_width
    pool_values = batch_size * group_count * coefficient * ratio * head_dim
    overlap_padding = (
        batch_size * ratio * head_dim
        if mode == "prefill" and overlap and group_count
        else 0
    )
    pool_kv_source_values = pool_values - overlap_padding if mode == "prefill" else 0
    pool_score_source_values = (
        batch_size * (prefill_cutoff or 0) * projected_width if mode == "prefill" else 0
    )
    kv_source_values_read = state_source_values + pool_kv_source_values
    score_source_values_read = state_source_values + pool_score_source_values
    state_values_read = (pool_values if mode == "decode" else 0) + roll_values
    state_values_written = state_source_values + roll_values
    total_state_values = capacity * coefficient * ratio * projected_width
    input_values = batch_size * sequence_length * projected_width
    counters = CompressionStateCounters(
        active_batch_count=batch_size,
        state_batch_capacity=capacity,
        sequence_length=sequence_length,
        ratio=ratio,
        overlap=overlap,
        head_dim=head_dim,
        projected_width=projected_width,
        complete_group_count=group_count,
        input_kv_f32_values=input_values,
        input_score_f32_values=input_values,
        logical_source_kv_f32_values_read=kv_source_values_read,
        logical_source_score_f32_values_read=score_source_values_read,
        logical_source_kv_read_bytes=kv_source_values_read * F32_BYTES,
        logical_source_score_read_bytes=score_source_values_read * F32_BYTES,
        logical_ape_f32_values_read=score_source_values_read,
        logical_ape_read_bytes=score_source_values_read * F32_BYTES,
        logical_score_ape_additions=score_source_values_read,
        logical_kv_state_f32_values_read=state_values_read,
        logical_score_state_f32_values_read=state_values_read,
        logical_kv_state_read_bytes=state_values_read * F32_BYTES,
        logical_score_state_read_bytes=state_values_read * F32_BYTES,
        logical_kv_state_f32_values_written=state_values_written,
        logical_score_state_f32_values_written=state_values_written,
        logical_kv_state_write_bytes=state_values_written * F32_BYTES,
        logical_score_state_write_bytes=state_values_written * F32_BYTES,
        kv_state_f32_values_preserved=total_state_values - state_values_written,
        score_state_f32_values_preserved=total_state_values - state_values_written,
        pool_kv_f32_values=pool_values,
        pool_score_f32_values=pool_values,
        overlap_pool_zero_f32_values=overlap_padding,
        overlap_pool_negative_infinity_f32_values=overlap_padding,
        kv_state_roll_f32_values=roll_values,
        score_state_roll_f32_values=roll_values,
        logical_ratio_modulo_evaluations=modulo_evaluations,
        transaction_commits=1,
    )
    return CompressionStateUpdateResult(
        state=committed_state,
        mode=mode,
        start_pos=start_pos,
        end_pos=start_pos + sequence_length,
        prefill_cutoff=prefill_cutoff,
        prefill_remainder=prefill_remainder,
        decode_phase=decode_phase,
        should_compress=should_compress,
        pool_inputs=pool_inputs,
        counters=counters,
    )


__all__ = [
    "COMPRESS_STATE_PROFILE",
    "EXCLUDED_DOWNSTREAM_OPERATIONS",
    "F32_BYTES",
    "F32_MAX_ENCODING",
    "F32_NEGATIVE_INFINITY",
    "INFERENCE_CONFIG_SHA256",
    "MODEL_SOURCE_SHA256",
    "OFFICIAL_REVISION",
    "PINNED_COMPRESSION_RATIOS",
    "PINNED_INDEX_HEAD_DIM",
    "PINNED_MAIN_HEAD_DIM",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "PINNED_NONOVERLAP_RATIO",
    "PINNED_OVERLAP_RATIO",
    "CompressionMode",
    "CompressionPoolInputs",
    "CompressionState",
    "CompressionStateCounters",
    "CompressionStateReferenceError",
    "CompressionStateUpdateResult",
    "F32Batch",
    "F32PoolBatch",
    "F32PoolGroup",
    "F32PoolSequence",
    "F32Sequence",
    "F32Vector",
    "compress_state_update_f32",
    "compression_state_f32",
    "zero_compression_state_f32",
]
