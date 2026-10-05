"""Transactional DeepSeek V4 compressed-KV cache and causal session semantics.

The pinned ``Compressor.forward`` writes a row only after a ratio-sized raw
compression window has been pooled, normalized, position transformed, and
activation-QDQ reconstructed to BF16. Prefill writes the complete prefix
``:seqlen // ratio``; one-token decode writes slot ``start_pos // ratio`` only
when ``(start_pos + 1) % ratio == 0``.

The released PyTorch module relies on its caller to delimit sessions and does
not carry cache validity or a causal cursor. This target reference makes that
missing contract explicit. Every fixed-capacity batch lane carries a canonical
session identity, active status, absolute next position, contiguous
valid-prefix length, and monotonic version. A retired lane retains its last
session identity as a tombstone, so omission followed by re-entry cannot
resurrect the same session. Payload outside the authoritative valid prefix is
bit-preserved but is never exposed by :func:`compressed_kv_valid_view_bf16`.

A separate validity bitmap would duplicate the checked prefix without adding
independent information, so this revision deliberately removes it. Every
input, state field, session identity, cursor, prefix, and version validates
before a new immutable state is assembled. Logical counters describe source
rows and semantic metadata fields only; they do not claim HBM bursts, SRAM
banking, cycles, bandwidth, latency, throughput, energy, area, routing, or PPA.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .formats import decode_bf16


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
COMPRESSED_KV_PROFILE = "opentallas.deepseek_v4_compressed_kv_write.v2"
COMPRESSED_KV_VALID_VIEW_PROFILE = "opentallas.deepseek_v4_compressed_kv_valid_view.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = 1_048_576
PINNED_MAIN_HEAD_DIM = 512
PINNED_INDEX_HEAD_DIM = 128
PINNED_COMPRESSION_RATIOS = (4, 128)
SESSION_ID_HEX_DIGITS = 64
MAX_STATE_VERSION = (1 << 64) - 1
BF16_BYTES = 2
BF16_MAX_ENCODING = (1 << 16) - 1

EXCLUDED_CLAIMS = (
    "compression_numeric_operators",
    "checkpoint_or_artifact_loading",
    "scheduler_or_service_execution",
    "physical_hbm_or_sram_transactions",
    "cycles_latency_throughput_energy_area_routing_ppa",
    "end_to_end_model_execution",
)


SessionId: TypeAlias = str
OptionalSessionId: TypeAlias = str | None
BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadRow: TypeAlias = tuple[BF16Vector, ...]
BF16CacheSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16CacheTensor: TypeAlias = tuple[BF16CacheSequence, ...]
BF16InputSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16InputTensor: TypeAlias = tuple[BF16InputSequence, ...]
CompressedKVMode: TypeAlias = Literal["prefill", "decode"]


class CompressedKVReferenceError(ValueError):
    """Raised when a compressed-KV transaction is malformed or poisoned."""


@dataclass(frozen=True)
class CompressedKVState:
    """Immutable payload and per-lane causal metadata, payload axes ``[B,C,H,V]``."""

    ratio: int
    bf16_codes: BF16CacheTensor
    session_ids: tuple[OptionalSessionId, ...]
    lane_active: tuple[bool, ...]
    next_positions: tuple[int, ...]
    valid_prefix_lengths: tuple[int, ...]
    versions: tuple[int, ...]


@dataclass(frozen=True)
class CompressedKVWriteCounters:
    """Exact logical payload, validity-prefix, and metadata accounting."""

    active_batch_count: int
    previous_active_batch_count: int
    removed_batch_count: int
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
    valid_rows_after: int
    logical_session_ids_read: int
    logical_session_ids_written: int
    logical_lane_active_flags_read: int
    logical_lane_active_flags_written: int
    logical_next_positions_read: int
    logical_next_positions_written: int
    logical_valid_prefix_lengths_read: int
    logical_valid_prefix_lengths_written: int
    logical_versions_read: int
    logical_versions_written: int
    logical_metadata_fields_read: int
    logical_metadata_fields_written: int
    transaction_commits: int


@dataclass(frozen=True)
class CompressedKVWriteResult:
    """A fully committed state version and its source-derived cache slots."""

    state: CompressedKVState
    mode: CompressedKVMode
    cache_slots: tuple[int, ...]
    start_pos: int
    end_pos: int
    active_session_ids: tuple[SessionId, ...]
    counters: CompressedKVWriteCounters


@dataclass(frozen=True)
class CompressedKVValidViewCounters:
    """Exact logical metadata checks and valid payload returned by one view."""

    active_batch_count: int
    state_batch_capacity: int
    ratio: int
    cache_capacity: int
    kv_head_count: int
    kv_value_width: int
    logical_session_ids_read: int
    logical_lane_active_flags_read: int
    logical_next_positions_read: int
    logical_valid_prefix_lengths_read: int
    logical_versions_read: int
    logical_metadata_fields_read: int
    logical_state_rows_read: int
    logical_state_bf16_values_read: int
    logical_state_read_bytes: int
    valid_rows_returned: int
    active_capacity_rows_excluded: int
    inactive_capacity_rows_excluded: int
    total_state_rows_not_exposed: int
    view_evaluations: int
    transaction_commits: int


@dataclass(frozen=True)
class CompressedKVValidViewResult:
    """Immutable valid prefixes and the exact causal snapshot they represent."""

    numeric_profile: str
    ratio: int
    bf16_codes: tuple[BF16CacheSequence, ...]
    session_ids: tuple[SessionId, ...]
    next_positions: tuple[int, ...]
    valid_prefix_lengths: tuple[int, ...]
    versions: tuple[int, ...]
    counters: CompressedKVValidViewCounters


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


def _canonical_session_id(value: object, label: str) -> SessionId:
    if type(value) is not str or len(value) != SESSION_ID_HEX_DIGITS:
        raise CompressedKVReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
        )
    if any(character not in "0123456789abcdef" for character in value):
        raise CompressedKVReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
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
) -> tuple[CompressedKVState, int, int, int, int, int]:
    if type(state) is not CompressedKVState:
        raise CompressedKVReferenceError("state must be an exact CompressedKVState")
    ratio = _ratio(state.ratio)
    raw_batches = _sequence(state.bf16_codes, "state.bf16_codes")
    if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
        raise CompressedKVReferenceError(
            f"state batch capacity must be in [1, {PINNED_MAX_BATCH_SIZE}]"
        )
    batch_capacity = len(raw_batches)

    metadata_fields = (
        (state.session_ids, "state.session_ids"),
        (state.lane_active, "state.lane_active"),
        (state.next_positions, "state.next_positions"),
        (state.valid_prefix_lengths, "state.valid_prefix_lengths"),
        (state.versions, "state.versions"),
    )
    materialized_metadata: list[list[object] | tuple[object, ...]] = []
    for raw_field, label in metadata_fields:
        field = _sequence(raw_field, label)
        if len(field) != batch_capacity:
            raise CompressedKVReferenceError(
                f"{label} extent must match state batch capacity"
            )
        materialized_metadata.append(field)

    capacity: int | None = None
    head_count: int | None = None
    value_width: int | None = None
    batches: list[BF16CacheSequence] = []
    for batch_index, raw_cache in enumerate(raw_batches):
        cache = _sequence(raw_cache, f"state.bf16_codes[{batch_index}]")
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

    assert capacity is not None
    assert head_count is not None
    assert value_width is not None
    if head_count * value_width > PINNED_MAIN_HEAD_DIM:
        raise CompressedKVReferenceError(
            "state KV-head/value product exceeds the pinned 512-value row"
        )

    raw_session_ids, raw_active, raw_next, raw_prefixes, raw_versions = (
        materialized_metadata
    )
    session_ids: list[OptionalSessionId] = []
    active_flags: list[bool] = []
    next_positions: list[int] = []
    valid_prefixes: list[int] = []
    versions: list[int] = []
    seen_sessions: set[str] = set()
    seen_inactive = False
    max_lane_position = min(PINNED_MAX_POSITION, capacity * ratio)

    for batch_index in range(batch_capacity):
        raw_session = raw_session_ids[batch_index]
        if raw_session is None:
            session: OptionalSessionId = None
        else:
            session = _canonical_session_id(
                raw_session,
                f"state.session_ids[{batch_index}]",
            )
            if session in seen_sessions:
                raise CompressedKVReferenceError(
                    "state session identities must be unique across lanes"
                )
            seen_sessions.add(session)

        active = raw_active[batch_index]
        if type(active) is not bool:
            raise CompressedKVReferenceError(
                f"state.lane_active[{batch_index}] must be bool"
            )
        if seen_inactive and active:
            raise CompressedKVReferenceError(
                "state active lanes must form a contiguous prefix"
            )
        seen_inactive |= not active

        next_position = _integer(
            raw_next[batch_index],
            f"state.next_positions[{batch_index}]",
            minimum=0,
            maximum=max_lane_position,
        )
        valid_prefix = _integer(
            raw_prefixes[batch_index],
            f"state.valid_prefix_lengths[{batch_index}]",
            minimum=0,
            maximum=capacity,
        )
        version = _integer(
            raw_versions[batch_index],
            f"state.versions[{batch_index}]",
            minimum=0,
            maximum=MAX_STATE_VERSION,
        )

        if active:
            if session is None:
                raise CompressedKVReferenceError(
                    f"active state lane {batch_index} must have a session identity"
                )
            if version == 0:
                raise CompressedKVReferenceError(
                    f"active state lane {batch_index} must have nonzero version"
                )
            if next_position == 0:
                raise CompressedKVReferenceError(
                    f"active state lane {batch_index} must be initialized by prefill"
                )
            expected_prefix = next_position // ratio
            if valid_prefix != expected_prefix:
                raise CompressedKVReferenceError(
                    f"state valid prefix for lane {batch_index} is {valid_prefix}, "
                    f"expected floor(next_pos/ratio)={expected_prefix}"
                )
        else:
            if next_position != 0 or valid_prefix != 0:
                raise CompressedKVReferenceError(
                    f"inactive state lane {batch_index} must have zero cursor and prefix"
                )
            if session is None and version != 0:
                raise CompressedKVReferenceError(
                    f"never-initialized state lane {batch_index} must have version zero"
                )
            if session is not None and version == 0:
                raise CompressedKVReferenceError(
                    f"retired state lane {batch_index} must have nonzero version"
                )

        session_ids.append(session)
        active_flags.append(active)
        next_positions.append(next_position)
        valid_prefixes.append(valid_prefix)
        versions.append(version)

    active_count = sum(active_flags)
    return (
        CompressedKVState(
            ratio=ratio,
            bf16_codes=tuple(batches),
            session_ids=tuple(session_ids),
            lane_active=tuple(active_flags),
            next_positions=tuple(next_positions),
            valid_prefix_lengths=tuple(valid_prefixes),
            versions=tuple(versions),
        ),
        batch_capacity,
        capacity,
        head_count,
        value_width,
        active_count,
    )


def zero_compressed_kv_state_bf16(
    *,
    ratio: int,
    cache_capacity: int,
    kv_head_count: int = 1,
    kv_value_width: int,
    batch_capacity: int = PINNED_MAX_BATCH_SIZE,
) -> CompressedKVState:
    """Create an all-positive-zero cache with uninitialized session lanes."""

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
        session_ids=(None,) * batch_capacity,
        lane_active=(False,) * batch_capacity,
        next_positions=(0,) * batch_capacity,
        valid_prefix_lengths=(0,) * batch_capacity,
        versions=(0,) * batch_capacity,
    )
    return _validate_state(state)[0]


def compressed_kv_state_bf16(value: object) -> CompressedKVState:
    """Validate and deeply freeze caller-provided cache and causal metadata."""

    return _validate_state(value)[0]


def _active_session_ids(
    value: object,
    *,
    batch_capacity: int,
    allow_empty: bool,
) -> tuple[SessionId, ...]:
    raw = _sequence(value, "active_session_ids")
    minimum = 0 if allow_empty else 1
    if not minimum <= len(raw) <= batch_capacity:
        if allow_empty:
            raise CompressedKVReferenceError(
                "active_session_ids extent is outside state batch capacity"
            )
        raise CompressedKVReferenceError(
            "active_session_ids must identify at least one lane and remain "
            "within state batch capacity"
        )
    sessions = tuple(
        _canonical_session_id(session, f"active_session_ids[{index}]")
        for index, session in enumerate(raw)
    )
    if len(set(sessions)) != len(sessions):
        raise CompressedKVReferenceError(
            "active_session_ids must be unique across active lanes"
        )
    return sessions


def _validate_input(
    value: object,
    *,
    expected_batch_size: int,
    expected_rows: int,
    head_count: int,
    value_width: int,
) -> BF16InputTensor:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if len(raw_batches) != expected_batch_size:
        raise CompressedKVReferenceError(
            "kv_bf16_codes batch extent must exactly match active_session_ids"
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
    return tuple(batches)


def compressed_kv_write_bf16(
    state: CompressedKVState,
    kv_bf16_codes: object,
    *,
    active_session_ids: object,
    start_pos: int,
    sequence_length: int,
) -> CompressedKVWriteResult:
    """Commit one new-session prefill or causally exact one-token decode.

    ``active_session_ids`` names every leading lane participating in this
    transaction. Omitting previously active trailing lanes retires them. A
    later prefill may reactivate such a lane only with an identity not retained
    by any current or retired lane in this state.
    """

    (
        frozen,
        batch_capacity,
        capacity,
        head_count,
        value_width,
        previous_active_count,
    ) = _validate_state(state)
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
    end_pos = start_pos + sequence_length
    if end_pos > PINNED_MAX_POSITION:
        raise CompressedKVReferenceError(
            "compressed KV end position exceeds the pinned maximum position"
        )
    if end_pos > capacity * frozen.ratio:
        raise CompressedKVReferenceError("compressed KV cursor exceeds cache capacity")

    sessions = _active_session_ids(
        active_session_ids,
        batch_capacity=batch_capacity,
        allow_empty=False,
    )
    batch_size = len(sessions)

    if start_pos == 0:
        mode: CompressedKVMode = "prefill"
        completed_rows = sequence_length // frozen.ratio
        cache_slots = tuple(range(completed_rows))
        retained_sessions = {
            session for session in frozen.session_ids if session is not None
        }
        reused = tuple(session for session in sessions if session in retained_sessions)
        if reused:
            raise CompressedKVReferenceError(
                "new-session prefill requires a fresh identity for every active lane"
            )
    else:
        mode = "decode"
        if sequence_length != 1:
            raise CompressedKVReferenceError(
                "decode compressed KV write requires sequence length exactly 1"
            )
        if batch_size > previous_active_count:
            raise CompressedKVReferenceError(
                "decode cannot reactivate an inactive lane; new-session prefill required"
            )
        for batch_index, session in enumerate(sessions):
            if not frozen.lane_active[batch_index]:
                raise CompressedKVReferenceError(
                    f"decode lane {batch_index} is not initialized and active"
                )
            if frozen.session_ids[batch_index] != session:
                raise CompressedKVReferenceError(
                    f"decode session identity mismatch for lane {batch_index}"
                )
            observed_next = frozen.next_positions[batch_index]
            if start_pos != observed_next:
                raise CompressedKVReferenceError(
                    f"decode start_pos for lane {batch_index} is {start_pos}, "
                    f"expected next_pos {observed_next}"
                )
            observed_prefix = frozen.valid_prefix_lengths[batch_index]
            expected_prefix = start_pos // frozen.ratio
            if observed_prefix != expected_prefix:
                raise CompressedKVReferenceError(
                    f"compressed KV valid prefix for lane {batch_index} is "
                    f"{observed_prefix}, expected {expected_prefix}"
                )
        completed_rows = int((start_pos + 1) % frozen.ratio == 0)
        cache_slots = (start_pos // frozen.ratio,) if completed_rows else ()

    if cache_slots and cache_slots[-1] >= capacity:
        raise CompressedKVReferenceError("compressed KV write exceeds cache capacity")
    source = _validate_input(
        kv_bf16_codes,
        expected_batch_size=batch_size,
        expected_rows=completed_rows,
        head_count=head_count,
        value_width=value_width,
    )

    removed_count = max(0, previous_active_count - batch_size)
    changed_lane_count = max(previous_active_count, batch_size)
    for batch_index in range(changed_lane_count):
        if frozen.versions[batch_index] == MAX_STATE_VERSION:
            raise CompressedKVReferenceError(
                f"state version overflow for lane {batch_index}"
            )

    # All state, sessions, shape, addresses, cursors, prefixes, versions, and
    # payload encodings have now validated. Assembly below is the sole commit.
    mutable_payload = [list(sequence) for sequence in frozen.bf16_codes]
    mutable_sessions = list(frozen.session_ids)
    mutable_active = list(frozen.lane_active)
    mutable_next = list(frozen.next_positions)
    mutable_prefixes = list(frozen.valid_prefix_lengths)
    mutable_versions = list(frozen.versions)

    valid_before = sum(frozen.valid_prefix_lengths)
    invalidated = 0
    if mode == "prefill":
        invalidated += sum(
            frozen.valid_prefix_lengths[: max(previous_active_count, batch_size)]
        )
        for batch_index, session in enumerate(sessions):
            mutable_sessions[batch_index] = session
            mutable_active[batch_index] = True
            mutable_next[batch_index] = sequence_length
            mutable_prefixes[batch_index] = completed_rows
            mutable_versions[batch_index] += 1
    else:
        for batch_index in range(batch_size):
            mutable_next[batch_index] = start_pos + 1
            if completed_rows:
                mutable_prefixes[batch_index] += 1
            mutable_versions[batch_index] += 1

    for batch_index in range(batch_size, previous_active_count):
        if mode == "decode":
            invalidated += frozen.valid_prefix_lengths[batch_index]
        mutable_active[batch_index] = False
        mutable_next[batch_index] = 0
        mutable_prefixes[batch_index] = 0
        mutable_versions[batch_index] += 1

    for batch_index in range(batch_size):
        for source_row, slot in enumerate(cache_slots):
            mutable_payload[batch_index][slot] = source[batch_index][source_row]

    committed = CompressedKVState(
        ratio=frozen.ratio,
        bf16_codes=tuple(tuple(sequence) for sequence in mutable_payload),
        session_ids=tuple(mutable_sessions),
        lane_active=tuple(mutable_active),
        next_positions=tuple(mutable_next),
        valid_prefix_lengths=tuple(mutable_prefixes),
        versions=tuple(mutable_versions),
    )
    committed = _validate_state(committed)[0]

    row_values = head_count * value_width
    written_rows = batch_size * completed_rows
    written_values = written_rows * row_values
    state_rows = batch_capacity * capacity

    session_reads = batch_capacity if mode == "prefill" else batch_size
    active_reads = batch_capacity
    next_reads = batch_size if mode == "decode" else 0
    prefix_reads = batch_capacity
    version_reads = changed_lane_count
    session_writes = batch_size if mode == "prefill" else 0
    active_writes = changed_lane_count if mode == "prefill" else removed_count
    next_writes = batch_size + removed_count
    prefix_writes = (
        batch_size + removed_count
        if mode == "prefill" or completed_rows
        else removed_count
    )
    version_writes = changed_lane_count
    metadata_reads = (
        session_reads + active_reads + next_reads + prefix_reads + version_reads
    )
    metadata_writes = (
        session_writes + active_writes + next_writes + prefix_writes + version_writes
    )

    counters = CompressedKVWriteCounters(
        active_batch_count=batch_size,
        previous_active_batch_count=previous_active_count,
        removed_batch_count=removed_count,
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
        valid_rows_after=sum(committed.valid_prefix_lengths),
        logical_session_ids_read=session_reads,
        logical_session_ids_written=session_writes,
        logical_lane_active_flags_read=active_reads,
        logical_lane_active_flags_written=active_writes,
        logical_next_positions_read=next_reads,
        logical_next_positions_written=next_writes,
        logical_valid_prefix_lengths_read=prefix_reads,
        logical_valid_prefix_lengths_written=prefix_writes,
        logical_versions_read=version_reads,
        logical_versions_written=version_writes,
        logical_metadata_fields_read=metadata_reads,
        logical_metadata_fields_written=metadata_writes,
        transaction_commits=1,
    )
    return CompressedKVWriteResult(
        state=committed,
        mode=mode,
        cache_slots=cache_slots,
        start_pos=start_pos,
        end_pos=end_pos,
        active_session_ids=sessions,
        counters=counters,
    )


def compressed_kv_valid_view_bf16(
    state: CompressedKVState,
    *,
    active_session_ids: object,
) -> CompressedKVValidViewResult:
    """Return only each exact active session's immutable valid BF16 prefix.

    The caller must name the complete active-lane prefix in order. Capacity
    rows at or beyond a lane's validated prefix and every inactive lane remain
    inaccessible even when their preserved payload bits are nonzero.
    """

    frozen, batch_capacity, capacity, head_count, value_width, active_count = (
        _validate_state(state)
    )
    sessions = _active_session_ids(
        active_session_ids,
        batch_capacity=batch_capacity,
        allow_empty=True,
    )
    if len(sessions) != active_count:
        raise CompressedKVReferenceError(
            "active_session_ids must exactly identify every active state lane"
        )

    prefixes: list[BF16CacheSequence] = []
    next_positions: list[int] = []
    valid_prefixes: list[int] = []
    versions: list[int] = []
    for batch_index, session in enumerate(sessions):
        if not frozen.lane_active[batch_index]:
            raise CompressedKVReferenceError(
                f"valid view lane {batch_index} is not active"
            )
        if frozen.session_ids[batch_index] != session:
            raise CompressedKVReferenceError(
                f"valid view session identity mismatch for lane {batch_index}"
            )
        next_position = frozen.next_positions[batch_index]
        valid_prefix = frozen.valid_prefix_lengths[batch_index]
        expected_prefix = next_position // frozen.ratio
        if valid_prefix != expected_prefix:
            raise CompressedKVReferenceError(
                f"valid view prefix for lane {batch_index} is {valid_prefix}, "
                f"expected {expected_prefix} from next_pos"
            )
        if not 1 <= frozen.versions[batch_index] <= MAX_STATE_VERSION:
            raise CompressedKVReferenceError(
                f"valid view lane {batch_index} has an invalid version"
            )
        prefixes.append(frozen.bf16_codes[batch_index][:valid_prefix])
        next_positions.append(next_position)
        valid_prefixes.append(valid_prefix)
        versions.append(frozen.versions[batch_index])

    valid_rows = sum(valid_prefixes)
    valid_values = valid_rows * head_count * value_width
    active_capacity_rows = active_count * capacity
    inactive_capacity_rows = (batch_capacity - active_count) * capacity
    metadata_reads = batch_capacity + 4 * active_count
    counters = CompressedKVValidViewCounters(
        active_batch_count=active_count,
        state_batch_capacity=batch_capacity,
        ratio=frozen.ratio,
        cache_capacity=capacity,
        kv_head_count=head_count,
        kv_value_width=value_width,
        logical_session_ids_read=active_count,
        logical_lane_active_flags_read=batch_capacity,
        logical_next_positions_read=active_count,
        logical_valid_prefix_lengths_read=active_count,
        logical_versions_read=active_count,
        logical_metadata_fields_read=metadata_reads,
        logical_state_rows_read=valid_rows,
        logical_state_bf16_values_read=valid_values,
        logical_state_read_bytes=valid_values * BF16_BYTES,
        valid_rows_returned=valid_rows,
        active_capacity_rows_excluded=active_capacity_rows - valid_rows,
        inactive_capacity_rows_excluded=inactive_capacity_rows,
        total_state_rows_not_exposed=(batch_capacity * capacity) - valid_rows,
        view_evaluations=1,
        transaction_commits=0,
    )
    return CompressedKVValidViewResult(
        numeric_profile=COMPRESSED_KV_VALID_VIEW_PROFILE,
        ratio=frozen.ratio,
        bf16_codes=tuple(prefixes),
        session_ids=sessions,
        next_positions=tuple(next_positions),
        valid_prefix_lengths=tuple(valid_prefixes),
        versions=tuple(versions),
        counters=counters,
    )


__all__ = [
    "BF16_BYTES",
    "BF16_MAX_ENCODING",
    "COMPRESSED_KV_PROFILE",
    "COMPRESSED_KV_VALID_VIEW_PROFILE",
    "EXCLUDED_CLAIMS",
    "INFERENCE_CONFIG_SHA256",
    "MAX_STATE_VERSION",
    "MODEL_SOURCE_SHA256",
    "PINNED_COMPRESSION_RATIOS",
    "PINNED_INDEX_HEAD_DIM",
    "PINNED_MAIN_HEAD_DIM",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "SESSION_ID_HEX_DIGITS",
    "CompressedKVMode",
    "CompressedKVReferenceError",
    "CompressedKVState",
    "CompressedKVValidViewCounters",
    "CompressedKVValidViewResult",
    "CompressedKVWriteCounters",
    "CompressedKVWriteResult",
    "compressed_kv_state_bf16",
    "compressed_kv_valid_view_bf16",
    "compressed_kv_write_bf16",
    "zero_compressed_kv_state_bf16",
]
