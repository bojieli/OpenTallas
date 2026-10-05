"""Session-bound DeepSeek V4 KV row-space composition for sparse attention.

The pinned main attention source presents two different row spaces:

* prefill uses the complete current KV tensor and appends the completed
  compressed prefix; and
* decode uses the fixed circular-window capacity and appends the completed
  compressed prefix.

DSpark decode instead appends five current draft KV rows to the fixed main-KV
window.  The current draft rows are not the main KV row just committed to the
window.  This module freezes those distinctions while retaining the physical
window-slot layout required by the separately qualified index constructors.

Unused physical window slots can therefore remain in the returned decode
buffer, exactly as in the source, but ``valid_row_indices`` identifies the
only rows that a conforming index tensor may select.  Compressed input is an
already validated contiguous-prefix view, never raw cache capacity.

This is a pure, immutable semantic composition.  It does not execute sparse
attention, authenticate producer artifacts, provide inter-request atomic
compare-and-swap, assign HBM/SRAM, or claim cycles, bandwidth, RTL, PPA, or
end-to-end model behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Literal, TypeAlias

from .compressed_kv import (
    COMPRESSED_KV_VALID_VIEW_PROFILE,
    CompressedKVValidViewCounters,
    CompressedKVValidViewResult,
)
from .formats import decode_bf16
from .kv_window import (
    BF16_BYTES,
    MAX_STATE_VERSION,
    PINNED_KV_ROW_WIDTH,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    KVWindowState,
    kv_window_state_bf16,
    kv_window_valid_view_bf16,
)


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
ATTENTION_KV_VIEW_PROFILE = "opentallas.deepseek_v4_attention_kv_view.v1"
PINNED_WINDOW_SIZE = 128
PINNED_HEAD_DIM = 512
PINNED_DSPARK_BLOCK_SIZE = 5
PINNED_COMPRESSION_RATIOS = (0, 4, 128)
SESSION_ID_HEX_DIGITS = 64
BF16_MAX_ENCODING = (1 << 16) - 1

EXCLUDED_CLAIMS = (
    "kv_projection_normalization_rope_or_qdq",
    "index_construction_or_sparse_attention_arithmetic",
    "authenticated_producer_origin",
    "atomic_inter_request_compare_and_swap",
    "compiler_service_or_rtl_execution",
    "physical_hbm_sram_cycles_latency_bandwidth_energy_area_routing_ppa",
    "checkpoint_activation_or_end_to_end_model_evidence",
)


SessionId: TypeAlias = str
BF16Vector: TypeAlias = tuple[int, ...]
BF16Sequence: TypeAlias = tuple[BF16Vector, ...]
BF16Batch: TypeAlias = tuple[BF16Sequence, ...]
AttentionKVViewMode: TypeAlias = Literal[
    "main_prefill",
    "main_decode",
    "dspark_decode",
]
Region: TypeAlias = tuple[int, int] | None


class AttentionKVViewReferenceError(ValueError):
    """Raised when KV row-space composition is malformed or causally stale."""


@dataclass(frozen=True, slots=True)
class CompressedKVViewSnapshot:
    """Deeply immutable, independently reconciled compressed-prefix input."""

    numeric_profile: str
    ratio: int
    bf16_codes: BF16Batch
    session_ids: tuple[SessionId, ...]
    next_positions: tuple[int, ...]
    valid_prefix_lengths: tuple[int, ...]
    versions: tuple[int, ...]
    state_batch_capacity: int
    cache_capacity: int
    kv_head_count: int
    kv_value_width: int

    def __post_init__(self) -> None:
        _validate_compressed_snapshot(self)


@dataclass(frozen=True, slots=True)
class AttentionKVViewCounters:
    """Exact logical source, state, output, and metadata reconciliation."""

    active_batch_count: int
    current_sequence_length: int
    window_size: int
    kv_head_count: int
    kv_value_width: int
    kv_row_width: int
    compression_ratio: int
    current_source_rows_read: int
    current_source_bf16_values_read: int
    current_source_read_bytes: int
    window_state_rows_reconciled: int
    window_state_rows_read: int
    window_state_bf16_values_read: int
    window_state_read_bytes: int
    compressed_source_rows_read: int
    compressed_source_bf16_values_read: int
    compressed_source_read_bytes: int
    output_rows_written: int
    output_bf16_values_written: int
    output_write_bytes: int
    valid_output_rows: int
    invalid_window_capacity_rows_exposed: int
    logical_window_slot_modulo_evaluations: int
    logical_session_ids_read: int
    logical_lane_active_flags_read: int
    logical_next_positions_read: int
    logical_valid_prefix_lengths_read: int
    logical_versions_read: int
    logical_metadata_fields_read: int
    view_evaluations: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_counters(self)


@dataclass(frozen=True, slots=True)
class AttentionKVViewResult:
    """One exact KV buffer layout and its complete immutable source relation."""

    numeric_profile: str
    mode: AttentionKVViewMode
    dspark: bool
    compression_ratio: int
    start_position: int
    next_position: int
    session_ids: tuple[SessionId, ...]
    current_kv_bf16_codes: BF16Batch
    window_state: KVWindowState
    expected_window_state_versions: tuple[int, ...]
    compressed_view: CompressedKVViewSnapshot | None
    bf16_codes: BF16Batch
    window_region: Region
    current_region: Region
    compressed_region: Region
    valid_row_indices: tuple[int, ...]
    window_valid_absolute_start: int
    window_valid_row_count: int
    window_valid_physical_slots: tuple[int, ...]
    counters: AttentionKVViewCounters

    def __post_init__(self) -> None:
        _validate_result(self)


@dataclass(frozen=True, slots=True)
class _Composition:
    mode: AttentionKVViewMode
    next_position: int
    output: BF16Batch
    window_region: Region
    current_region: Region
    compressed_region: Region
    valid_row_indices: tuple[int, ...]
    window_valid_absolute_start: int
    window_valid_row_count: int
    window_valid_physical_slots: tuple[int, ...]
    counters: AttentionKVViewCounters


def _sequence(value: object, label: str) -> list[object] | tuple[object, ...]:
    if type(value) not in {list, tuple}:
        raise AttentionKVViewReferenceError(f"{label} must be an exact list or tuple")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise AttentionKVViewReferenceError(
            f"{label} must be an exact integer in [{minimum}, {maximum}]"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise AttentionKVViewReferenceError(f"{label} must be a 16-bit BF16 code")
    decoded = decode_bf16(value)
    if not decoded.finite:
        raise AttentionKVViewReferenceError(f"{label} must be finite BF16")
    return value


def _session(value: object, label: str) -> SessionId:
    if type(value) is not str or len(value) != SESSION_ID_HEX_DIGITS:
        raise AttentionKVViewReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
        )
    if any(character not in "0123456789abcdef" for character in value):
        raise AttentionKVViewReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
        )
    return value


def _sessions(value: object) -> tuple[SessionId, ...]:
    raw = _sequence(value, "active_session_ids")
    if not 1 <= len(raw) <= PINNED_MAX_BATCH_SIZE:
        raise AttentionKVViewReferenceError(
            "active_session_ids must contain one to four sessions"
        )
    result = tuple(
        _session(item, f"active_session_ids[{index}]")
        for index, item in enumerate(raw)
    )
    if len(set(result)) != len(result):
        raise AttentionKVViewReferenceError(
            "active_session_ids must be unique across lanes"
        )
    return result


def _versions(value: object, *, capacity: int) -> tuple[int, ...]:
    raw = _sequence(value, "expected_window_state_versions")
    if len(raw) != capacity:
        raise AttentionKVViewReferenceError(
            "expected_window_state_versions must cover complete state capacity"
        )
    return tuple(
        _integer(
            item,
            f"expected_window_state_versions[{index}]",
            minimum=0,
            maximum=MAX_STATE_VERSION,
        )
        for index, item in enumerate(raw)
    )


def _freeze_current(
    value: object,
    *,
    batch_count: int,
) -> tuple[BF16Batch, int, int]:
    raw_batches = _sequence(value, "current_kv_bf16_codes")
    if len(raw_batches) != batch_count:
        raise AttentionKVViewReferenceError(
            "current KV batch extent must match active sessions"
        )
    batches: list[BF16Sequence] = []
    sequence_length: int | None = None
    row_width: int | None = None
    for batch_index, batch_value in enumerate(raw_batches):
        raw_rows = _sequence(
            batch_value,
            f"current_kv_bf16_codes[{batch_index}]",
        )
        if sequence_length is None:
            sequence_length = len(raw_rows)
            if not 1 <= sequence_length <= PINNED_MAX_POSITION:
                raise AttentionKVViewReferenceError(
                    "current KV sequence extent is outside the position bound"
                )
        elif len(raw_rows) != sequence_length:
            raise AttentionKVViewReferenceError(
                "current KV must be rectangular on the sequence axis"
            )
        rows: list[BF16Vector] = []
        for row_index, row_value in enumerate(raw_rows):
            raw_codes = _sequence(
                row_value,
                f"current_kv_bf16_codes[{batch_index}][{row_index}]",
            )
            if row_width is None:
                row_width = len(raw_codes)
                if not 1 <= row_width <= PINNED_KV_ROW_WIDTH:
                    raise AttentionKVViewReferenceError(
                        "current KV row width is outside the pinned 512-value row"
                    )
            elif len(raw_codes) != row_width:
                raise AttentionKVViewReferenceError(
                    "current KV must be rectangular on the row axis"
                )
            rows.append(
                tuple(
                    _finite_bf16(
                        code,
                        f"current_kv_bf16_codes[{batch_index}]"
                        f"[{row_index}][{column}]",
                    )
                    for column, code in enumerate(raw_codes)
                )
            )
        batches.append(tuple(rows))
    assert sequence_length is not None
    assert row_width is not None
    return tuple(batches), sequence_length, row_width


def _flatten_head_row(value: object, label: str) -> BF16Vector:
    heads = _sequence(value, label)
    if not heads:
        raise AttentionKVViewReferenceError(f"{label} must contain a KV head")
    flattened: list[int] = []
    width: int | None = None
    for head_index, head_value in enumerate(heads):
        codes = _sequence(head_value, f"{label}[{head_index}]")
        if width is None:
            width = len(codes)
            if width == 0:
                raise AttentionKVViewReferenceError(
                    f"{label}[{head_index}] must not be empty"
                )
        elif len(codes) != width:
            raise AttentionKVViewReferenceError(f"{label} is not rectangular")
        flattened.extend(
            _finite_bf16(code, f"{label}[{head_index}][{column}]")
            for column, code in enumerate(codes)
        )
    return tuple(flattened)


def _validate_compressed_view_counters(
    counters: object,
    *,
    batch_count: int,
    state_capacity: int,
    cache_capacity: int,
    ratio: int,
    head_count: int,
    value_width: int,
    valid_rows: int,
) -> None:
    if type(counters) is not CompressedKVValidViewCounters:
        raise AttentionKVViewReferenceError(
            "compressed view counters must be exact CompressedKVValidViewCounters"
        )
    row_values = head_count * value_width
    expected = {
        "active_batch_count": batch_count,
        "state_batch_capacity": state_capacity,
        "ratio": ratio,
        "cache_capacity": cache_capacity,
        "kv_head_count": head_count,
        "kv_value_width": value_width,
        "logical_session_ids_read": batch_count,
        "logical_lane_active_flags_read": state_capacity,
        "logical_next_positions_read": batch_count,
        "logical_valid_prefix_lengths_read": batch_count,
        "logical_versions_read": batch_count,
        "logical_metadata_fields_read": state_capacity + 4 * batch_count,
        "logical_state_rows_read": valid_rows,
        "logical_state_bf16_values_read": valid_rows * row_values,
        "logical_state_read_bytes": valid_rows * row_values * BF16_BYTES,
        "valid_rows_returned": valid_rows,
        "active_capacity_rows_excluded": batch_count * cache_capacity - valid_rows,
        "inactive_capacity_rows_excluded": (
            state_capacity - batch_count
        ) * cache_capacity,
        "total_state_rows_not_exposed": state_capacity * cache_capacity - valid_rows,
        "view_evaluations": 1,
        "transaction_commits": 0,
    }
    for field in fields(counters):
        observed = getattr(counters, field.name)
        if type(observed) is not int or observed != expected[field.name]:
            raise AttentionKVViewReferenceError(
                f"compressed view counters.{field.name} does not reconcile"
            )


def _snapshot_compressed_view(
    value: object,
    *,
    sessions: tuple[SessionId, ...],
    expected_next_position: int,
    ratio: int,
    expected_row_width: int,
) -> CompressedKVViewSnapshot:
    if type(value) is not CompressedKVValidViewResult:
        raise AttentionKVViewReferenceError(
            "compressed_view must be an exact CompressedKVValidViewResult"
        )
    if (
        type(value.numeric_profile) is not str
        or value.numeric_profile != COMPRESSED_KV_VALID_VIEW_PROFILE
    ):
        raise AttentionKVViewReferenceError("compressed view numeric profile differs")
    if type(value.ratio) is not int or value.ratio != ratio:
        raise AttentionKVViewReferenceError("compressed view ratio differs")
    if type(value.session_ids) is not tuple or value.session_ids != sessions:
        raise AttentionKVViewReferenceError("compressed view sessions differ")
    if type(value.next_positions) is not tuple or value.next_positions != (
        expected_next_position,
    ) * len(sessions):
        raise AttentionKVViewReferenceError("compressed view cursor differs")
    expected_prefix = expected_next_position // ratio
    if (
        type(value.valid_prefix_lengths) is not tuple
        or value.valid_prefix_lengths != (expected_prefix,) * len(sessions)
    ):
        raise AttentionKVViewReferenceError(
            "compressed view valid-prefix length differs from cursor"
        )
    if type(value.versions) is not tuple or len(value.versions) != len(sessions):
        raise AttentionKVViewReferenceError("compressed view versions differ")
    versions = tuple(
        _integer(
            version,
            f"compressed_view.versions[{index}]",
            minimum=1,
            maximum=MAX_STATE_VERSION,
        )
        for index, version in enumerate(value.versions)
    )

    raw_batches = _sequence(value.bf16_codes, "compressed_view.bf16_codes")
    if len(raw_batches) != len(sessions):
        raise AttentionKVViewReferenceError("compressed view batch extent differs")
    flattened_batches: list[BF16Sequence] = []
    head_count: int | None = None
    value_width: int | None = None
    for batch_index, batch_value in enumerate(raw_batches):
        rows = _sequence(
            batch_value,
            f"compressed_view.bf16_codes[{batch_index}]",
        )
        if len(rows) != expected_prefix:
            raise AttentionKVViewReferenceError(
                "compressed view row extent differs from valid prefix"
            )
        flattened_rows: list[BF16Vector] = []
        for row_index, row_value in enumerate(rows):
            raw_heads = _sequence(
                row_value,
                f"compressed_view.bf16_codes[{batch_index}][{row_index}]",
            )
            if head_count is None:
                head_count = len(raw_heads)
                if head_count == 0:
                    raise AttentionKVViewReferenceError(
                        "compressed view rows must contain a KV head"
                    )
            elif len(raw_heads) != head_count:
                raise AttentionKVViewReferenceError(
                    "compressed view KV-head extent differs"
                )
            flattened = _flatten_head_row(
                row_value,
                f"compressed_view.bf16_codes[{batch_index}][{row_index}]",
            )
            if value_width is None:
                value_width = len(flattened) // head_count
            if len(flattened) != expected_row_width:
                raise AttentionKVViewReferenceError(
                    "compressed view row width differs from window KV"
                )
            flattened_rows.append(flattened)
        flattened_batches.append(tuple(flattened_rows))

    counters = value.counters
    if type(counters) is not CompressedKVValidViewCounters:
        raise AttentionKVViewReferenceError("compressed view counters are untyped")
    state_capacity = _integer(
        counters.state_batch_capacity,
        "compressed_view.counters.state_batch_capacity",
        minimum=len(sessions),
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    cache_capacity = _integer(
        counters.cache_capacity,
        "compressed_view.counters.cache_capacity",
        minimum=max(1, expected_prefix),
        maximum=PINNED_MAX_POSITION // ratio,
    )
    if head_count is None:
        head_count = _integer(
            counters.kv_head_count,
            "compressed_view.counters.kv_head_count",
            minimum=1,
            maximum=PINNED_KV_ROW_WIDTH,
        )
        value_width = _integer(
            counters.kv_value_width,
            "compressed_view.counters.kv_value_width",
            minimum=1,
            maximum=PINNED_KV_ROW_WIDTH,
        )
        if head_count * value_width != expected_row_width:
            raise AttentionKVViewReferenceError(
                "empty compressed view row width differs from window KV"
            )
    assert value_width is not None
    _validate_compressed_view_counters(
        counters,
        batch_count=len(sessions),
        state_capacity=state_capacity,
        cache_capacity=cache_capacity,
        ratio=ratio,
        head_count=head_count,
        value_width=value_width,
        valid_rows=len(sessions) * expected_prefix,
    )
    return CompressedKVViewSnapshot(
        numeric_profile=COMPRESSED_KV_VALID_VIEW_PROFILE,
        ratio=ratio,
        bf16_codes=tuple(flattened_batches),
        session_ids=sessions,
        next_positions=(expected_next_position,) * len(sessions),
        valid_prefix_lengths=(expected_prefix,) * len(sessions),
        versions=versions,
        state_batch_capacity=state_capacity,
        cache_capacity=cache_capacity,
        kv_head_count=head_count,
        kv_value_width=value_width,
    )


def _validate_compressed_snapshot(value: object) -> None:
    if type(value) is not CompressedKVViewSnapshot:
        raise AttentionKVViewReferenceError(
            "compressed snapshot must be exact CompressedKVViewSnapshot"
        )
    if value.numeric_profile != COMPRESSED_KV_VALID_VIEW_PROFILE:
        raise AttentionKVViewReferenceError("compressed snapshot profile differs")
    if type(value.ratio) is not int or value.ratio not in {4, 128}:
        raise AttentionKVViewReferenceError("compressed snapshot ratio differs")
    if type(value.session_ids) is not tuple or not value.session_ids:
        raise AttentionKVViewReferenceError("compressed snapshot sessions differ")
    sessions = tuple(
        _session(item, f"compressed_snapshot.session_ids[{index}]")
        for index, item in enumerate(value.session_ids)
    )
    if len(set(sessions)) != len(sessions):
        raise AttentionKVViewReferenceError("compressed snapshot sessions duplicate")
    batch_count = len(sessions)
    if not all(
        type(field) is tuple and len(field) == batch_count
        for field in (
            value.bf16_codes,
            value.next_positions,
            value.valid_prefix_lengths,
            value.versions,
        )
    ):
        raise AttentionKVViewReferenceError("compressed snapshot batch axes differ")
    state_capacity = _integer(
        value.state_batch_capacity,
        "compressed_snapshot.state_batch_capacity",
        minimum=batch_count,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    del state_capacity
    cache_capacity = _integer(
        value.cache_capacity,
        "compressed_snapshot.cache_capacity",
        minimum=1,
        maximum=PINNED_MAX_POSITION // value.ratio,
    )
    head_count = _integer(
        value.kv_head_count,
        "compressed_snapshot.kv_head_count",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    value_width = _integer(
        value.kv_value_width,
        "compressed_snapshot.kv_value_width",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    row_width = head_count * value_width
    if row_width > PINNED_KV_ROW_WIDTH:
        raise AttentionKVViewReferenceError("compressed snapshot row exceeds 512")
    for batch_index in range(batch_count):
        next_position = _integer(
            value.next_positions[batch_index],
            f"compressed_snapshot.next_positions[{batch_index}]",
            minimum=1,
            maximum=PINNED_MAX_POSITION,
        )
        prefix = _integer(
            value.valid_prefix_lengths[batch_index],
            f"compressed_snapshot.valid_prefix_lengths[{batch_index}]",
            minimum=0,
            maximum=cache_capacity,
        )
        if prefix != next_position // value.ratio:
            raise AttentionKVViewReferenceError(
                "compressed snapshot prefix does not reconcile to cursor"
            )
        _integer(
            value.versions[batch_index],
            f"compressed_snapshot.versions[{batch_index}]",
            minimum=1,
            maximum=MAX_STATE_VERSION,
        )
        rows = value.bf16_codes[batch_index]
        if type(rows) is not tuple or len(rows) != prefix:
            raise AttentionKVViewReferenceError(
                "compressed snapshot payload length differs from prefix"
            )
        for row_index, row in enumerate(rows):
            if type(row) is not tuple or len(row) != row_width:
                raise AttentionKVViewReferenceError(
                    "compressed snapshot row width differs"
                )
            for column, code in enumerate(row):
                _finite_bf16(
                    code,
                    f"compressed_snapshot.bf16_codes[{batch_index}]"
                    f"[{row_index}][{column}]",
                )


def _validate_counters(value: object) -> None:
    if type(value) is not AttentionKVViewCounters:
        raise AttentionKVViewReferenceError(
            "counters must be exact AttentionKVViewCounters"
        )
    for field in fields(value):
        observed = getattr(value, field.name)
        if type(observed) is not int or observed < 0:
            raise AttentionKVViewReferenceError(
                f"counters.{field.name} must be a nonnegative exact integer"
            )
    if not 1 <= value.active_batch_count <= PINNED_MAX_BATCH_SIZE:
        raise AttentionKVViewReferenceError("counter batch count differs")
    if not 1 <= value.current_sequence_length <= PINNED_MAX_POSITION:
        raise AttentionKVViewReferenceError("counter sequence length differs")
    if not 1 <= value.window_size <= PINNED_WINDOW_SIZE:
        raise AttentionKVViewReferenceError("counter window size differs")
    if value.kv_head_count * value.kv_value_width != value.kv_row_width:
        raise AttentionKVViewReferenceError("counter KV row width differs")
    if value.compression_ratio not in PINNED_COMPRESSION_RATIOS:
        raise AttentionKVViewReferenceError("counter compression ratio differs")
    if value.view_evaluations != 1 or value.transaction_commits != 0:
        raise AttentionKVViewReferenceError("view counter commit semantics differ")
    if (
        value.valid_output_rows + value.invalid_window_capacity_rows_exposed
        != value.output_rows_written
    ):
        raise AttentionKVViewReferenceError("counter output validity does not reconcile")


def _flatten_window_state(
    state: KVWindowState,
    *,
    batch_count: int,
) -> tuple[BF16Batch, int, int, int]:
    batches: list[BF16Sequence] = []
    head_count = len(state.bf16_codes[0][0])
    value_width = len(state.bf16_codes[0][0][0])
    for batch_index in range(batch_count):
        batches.append(
            tuple(
                _flatten_head_row(
                    row,
                    f"window_state.bf16_codes[{batch_index}][{slot}]",
                )
                for slot, row in enumerate(state.bf16_codes[batch_index])
            )
        )
    return tuple(batches), len(state.bf16_codes[0]), head_count, value_width


def _compose(
    *,
    current: BF16Batch,
    window_state: KVWindowState,
    expected_versions: tuple[int, ...],
    sessions: tuple[SessionId, ...],
    start_position: int,
    compression_ratio: int,
    compressed_view: CompressedKVViewSnapshot | None,
    dspark: bool,
) -> _Composition:
    frozen_state = kv_window_state_bf16(window_state)
    batch_count = len(sessions)
    if expected_versions != frozen_state.versions:
        raise AttentionKVViewReferenceError(
            "expected window-state versions are stale"
        )
    try:
        valid_view = kv_window_valid_view_bf16(
            frozen_state,
            expected_state_versions=expected_versions,
            active_session_ids=sessions,
        )
    except ValueError as exc:
        raise AttentionKVViewReferenceError(
            f"window-state authority failed: {exc}"
        ) from exc
    if len(valid_view.next_positions) != batch_count:
        raise AttentionKVViewReferenceError("window-state active lane count differs")
    next_positions = valid_view.next_positions
    if len(set(next_positions)) != 1:
        raise AttentionKVViewReferenceError(
            "window-state active lanes must share one cursor"
        )
    next_position = next_positions[0]
    current_sequence_length = len(current[0])
    row_width = len(current[0][0])
    physical, window_size, head_count, value_width = _flatten_window_state(
        frozen_state,
        batch_count=batch_count,
    )
    if head_count * value_width != row_width:
        raise AttentionKVViewReferenceError(
            "current and window-state KV row widths differ"
        )
    if dspark:
        if compression_ratio != 0 or compressed_view is not None:
            raise AttentionKVViewReferenceError(
                "DSpark KV view does not admit compressed KV"
            )
        if start_position == 0:
            raise AttentionKVViewReferenceError("DSpark KV view is decode-only")
        if current_sequence_length != PINNED_DSPARK_BLOCK_SIZE:
            raise AttentionKVViewReferenceError(
                f"DSpark KV view requires exactly {PINNED_DSPARK_BLOCK_SIZE} draft rows"
            )
        if next_position != start_position + 1:
            raise AttentionKVViewReferenceError(
                "DSpark main-window cursor differs from request position"
            )
        mode: AttentionKVViewMode = "dspark_decode"
    elif start_position == 0:
        if next_position != current_sequence_length:
            raise AttentionKVViewReferenceError(
                "prefill window cursor differs from current sequence length"
            )
        mode = "main_prefill"
    else:
        if current_sequence_length != 1:
            raise AttentionKVViewReferenceError(
                "main decode KV view requires exactly one current row"
            )
        if next_position != start_position + 1:
            raise AttentionKVViewReferenceError(
                "decode window cursor differs from request position"
            )
        mode = "main_decode"

    window_valid_count = min(next_position, window_size)
    window_absolute_start = next_position - window_valid_count
    valid_slots = tuple(
        sorted(position % window_size for position in range(window_absolute_start, next_position))
    )
    if len(valid_slots) != window_valid_count or len(set(valid_slots)) != len(
        valid_slots
    ):
        raise AttentionKVViewReferenceError("window valid-slot set does not reconcile")

    reconciled_rows = 0
    if mode == "main_prefill":
        source_start = max(0, current_sequence_length - window_size)
        for batch_index in range(batch_count):
            for absolute_position in range(source_start, current_sequence_length):
                slot = absolute_position % window_size
                if physical[batch_index][slot] != current[batch_index][absolute_position]:
                    raise AttentionKVViewReferenceError(
                        "prefill window payload differs from the current KV write"
                    )
        reconciled_rows = batch_count * min(current_sequence_length, window_size)
    elif mode == "main_decode":
        slot = start_position % window_size
        for batch_index in range(batch_count):
            if physical[batch_index][slot] != current[batch_index][0]:
                raise AttentionKVViewReferenceError(
                    "decode window slot differs from the current KV row"
                )
        reconciled_rows = batch_count

    compressed_prefix = 0
    if compression_ratio == 0:
        if compressed_view is not None:
            raise AttentionKVViewReferenceError(
                "uncompressed attention must not receive compressed KV"
            )
    else:
        if dspark or compression_ratio not in {4, 128}:
            raise AttentionKVViewReferenceError("compression ratio differs")
        if type(compressed_view) is not CompressedKVViewSnapshot:
            raise AttentionKVViewReferenceError(
                "compressed attention requires an exact compressed-prefix snapshot"
            )
        _validate_compressed_snapshot(compressed_view)
        if (
            compressed_view.ratio != compression_ratio
            or compressed_view.session_ids != sessions
            or compressed_view.next_positions != (next_position,) * batch_count
            or compressed_view.kv_head_count * compressed_view.kv_value_width
            != row_width
        ):
            raise AttentionKVViewReferenceError(
                "compressed prefix does not share window session/cursor/row authority"
            )
        compressed_prefix = next_position // compression_ratio
        if compressed_view.valid_prefix_lengths != (
            compressed_prefix,
        ) * batch_count:
            raise AttentionKVViewReferenceError(
                "compressed prefix length differs from request cursor"
            )

    output_batches: list[BF16Sequence] = []
    if mode == "main_prefill":
        window_region: Region = None
        current_region: Region = (0, current_sequence_length)
        compressed_region: Region = (
            (current_sequence_length, current_sequence_length + compressed_prefix)
            if compressed_view is not None
            else None
        )
        for batch_index in range(batch_count):
            suffix = (
                compressed_view.bf16_codes[batch_index]
                if compressed_view is not None
                else ()
            )
            output_batches.append(current[batch_index] + suffix)
        valid_indices = tuple(range(current_sequence_length + compressed_prefix))
        window_rows_read = 0
    elif mode == "main_decode":
        window_region = (0, window_size)
        current_region = None
        compressed_region = (
            (window_size, window_size + compressed_prefix)
            if compressed_view is not None
            else None
        )
        for batch_index in range(batch_count):
            suffix = (
                compressed_view.bf16_codes[batch_index]
                if compressed_view is not None
                else ()
            )
            output_batches.append(physical[batch_index] + suffix)
        valid_indices = valid_slots + tuple(
            window_size + index for index in range(compressed_prefix)
        )
        window_rows_read = batch_count * window_size
    else:
        window_region = (0, window_size)
        current_region = (
            window_size,
            window_size + current_sequence_length,
        )
        compressed_region = None
        for batch_index in range(batch_count):
            output_batches.append(physical[batch_index] + current[batch_index])
        valid_indices = valid_slots + tuple(
            window_size + index for index in range(current_sequence_length)
        )
        window_rows_read = batch_count * window_size

    output = tuple(output_batches)
    output_length = len(output[0])
    if any(len(batch) != output_length for batch in output):
        raise AttentionKVViewReferenceError("internal KV output is not rectangular")
    current_rows = batch_count * current_sequence_length
    compressed_rows = batch_count * compressed_prefix
    output_rows = batch_count * output_length
    valid_rows = batch_count * len(valid_indices)
    invalid_rows = output_rows - valid_rows
    metadata_session_reads = batch_count + (
        batch_count if compressed_view is not None else 0
    )
    metadata_next_reads = metadata_session_reads
    metadata_version_reads = metadata_session_reads
    metadata_prefix_reads = batch_count if compressed_view is not None else 0
    metadata_active_reads = len(frozen_state.lane_active)
    metadata_reads = (
        metadata_session_reads
        + metadata_next_reads
        + metadata_version_reads
        + metadata_prefix_reads
        + metadata_active_reads
    )
    counters = AttentionKVViewCounters(
        active_batch_count=batch_count,
        current_sequence_length=current_sequence_length,
        window_size=window_size,
        kv_head_count=head_count,
        kv_value_width=value_width,
        kv_row_width=row_width,
        compression_ratio=compression_ratio,
        current_source_rows_read=current_rows,
        current_source_bf16_values_read=current_rows * row_width,
        current_source_read_bytes=current_rows * row_width * BF16_BYTES,
        window_state_rows_reconciled=reconciled_rows,
        window_state_rows_read=window_rows_read,
        window_state_bf16_values_read=window_rows_read * row_width,
        window_state_read_bytes=window_rows_read * row_width * BF16_BYTES,
        compressed_source_rows_read=compressed_rows,
        compressed_source_bf16_values_read=compressed_rows * row_width,
        compressed_source_read_bytes=compressed_rows * row_width * BF16_BYTES,
        output_rows_written=output_rows,
        output_bf16_values_written=output_rows * row_width,
        output_write_bytes=output_rows * row_width * BF16_BYTES,
        valid_output_rows=valid_rows,
        invalid_window_capacity_rows_exposed=invalid_rows,
        logical_window_slot_modulo_evaluations=(
            batch_count * window_valid_count
            + (reconciled_rows if mode == "main_prefill" else 0)
        ),
        logical_session_ids_read=metadata_session_reads,
        logical_lane_active_flags_read=metadata_active_reads,
        logical_next_positions_read=metadata_next_reads,
        logical_valid_prefix_lengths_read=metadata_prefix_reads,
        logical_versions_read=metadata_version_reads,
        logical_metadata_fields_read=metadata_reads,
        view_evaluations=1,
        transaction_commits=0,
    )
    return _Composition(
        mode=mode,
        next_position=next_position,
        output=output,
        window_region=window_region,
        current_region=current_region,
        compressed_region=compressed_region,
        valid_row_indices=valid_indices,
        window_valid_absolute_start=window_absolute_start,
        window_valid_row_count=window_valid_count,
        window_valid_physical_slots=valid_slots,
        counters=counters,
    )


def _validate_result(value: object) -> None:
    if type(value) is not AttentionKVViewResult:
        raise AttentionKVViewReferenceError(
            "result must be exact AttentionKVViewResult"
        )
    if (
        type(value.numeric_profile) is not str
        or value.numeric_profile != ATTENTION_KV_VIEW_PROFILE
    ):
        raise AttentionKVViewReferenceError("result numeric profile differs")
    if type(value.dspark) is not bool:
        raise AttentionKVViewReferenceError("result dspark must be an exact boolean")
    if type(value.compression_ratio) is not int or value.compression_ratio not in (
        PINNED_COMPRESSION_RATIOS
    ):
        raise AttentionKVViewReferenceError("result compression ratio differs")
    start = _integer(
        value.start_position,
        "result.start_position",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    if type(value.session_ids) is not tuple:
        raise AttentionKVViewReferenceError(
            "result session_ids must be a deeply immutable exact tuple"
        )
    sessions = _sessions(value.session_ids)
    current, _, _ = _freeze_current(
        value.current_kv_bf16_codes,
        batch_count=len(sessions),
    )
    if current != value.current_kv_bf16_codes:
        raise AttentionKVViewReferenceError(
            "result current KV source must be a deeply immutable exact tuple"
        )
    if type(value.window_state) is not KVWindowState:
        raise AttentionKVViewReferenceError("result window state must be exact")
    state = kv_window_state_bf16(value.window_state)
    versions = _versions(
        value.expected_window_state_versions,
        capacity=len(state.versions),
    )
    if type(value.expected_window_state_versions) is not tuple:
        raise AttentionKVViewReferenceError(
            "result expected versions must be an exact tuple"
        )
    if value.compressed_view is not None:
        _validate_compressed_snapshot(value.compressed_view)
    composition = _compose(
        current=current,
        window_state=state,
        expected_versions=versions,
        sessions=sessions,
        start_position=start,
        compression_ratio=value.compression_ratio,
        compressed_view=value.compressed_view,
        dspark=value.dspark,
    )
    expected = {
        "mode": composition.mode,
        "next_position": composition.next_position,
        "bf16_codes": composition.output,
        "window_region": composition.window_region,
        "current_region": composition.current_region,
        "compressed_region": composition.compressed_region,
        "valid_row_indices": composition.valid_row_indices,
        "window_valid_absolute_start": composition.window_valid_absolute_start,
        "window_valid_row_count": composition.window_valid_row_count,
        "window_valid_physical_slots": composition.window_valid_physical_slots,
        "counters": composition.counters,
    }
    for name, expected_value in expected.items():
        observed = getattr(value, name)
        if type(observed) is not type(expected_value) or observed != expected_value:
            raise AttentionKVViewReferenceError(
                f"result {name} does not reconstruct from retained sources"
            )


def attention_kv_view_bf16(
    current_kv_bf16_codes: object,
    window_state: KVWindowState,
    *,
    expected_window_state_versions: object,
    active_session_ids: object,
    start_pos: int,
    compression_ratio: int = 0,
    compressed_view: CompressedKVValidViewResult | None = None,
    dspark: bool = False,
) -> AttentionKVViewResult:
    """Compose the exact sparse-attention KV row space for one request.

    ``current_kv_bf16_codes`` is rank three ``[B,S,D]``. For main prefill it
    is the complete current sequence; for main decode it is the one row already
    committed to ``window_state``; for DSpark decode it is the five-row draft
    KV block appended after the committed main window.
    """

    if type(dspark) is not bool:
        raise AttentionKVViewReferenceError("dspark must be an exact boolean")
    ratio = _integer(
        compression_ratio,
        "compression_ratio",
        minimum=0,
        maximum=128,
    )
    if ratio not in PINNED_COMPRESSION_RATIOS:
        raise AttentionKVViewReferenceError(
            "compression_ratio must be exactly 0, 4, or 128"
        )
    start = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    sessions = _sessions(active_session_ids)
    current, _, row_width = _freeze_current(
        current_kv_bf16_codes,
        batch_count=len(sessions),
    )
    try:
        state = kv_window_state_bf16(window_state)
    except ValueError as exc:
        raise AttentionKVViewReferenceError(f"window state is invalid: {exc}") from exc
    versions = _versions(
        expected_window_state_versions,
        capacity=len(state.versions),
    )
    snapshot: CompressedKVViewSnapshot | None
    if ratio:
        expected_next = start + 1 if start else len(current[0])
        snapshot = _snapshot_compressed_view(
            compressed_view,
            sessions=sessions,
            expected_next_position=expected_next,
            ratio=ratio,
            expected_row_width=row_width,
        )
    else:
        if compressed_view is not None:
            raise AttentionKVViewReferenceError(
                "compressed_view must be absent when compression_ratio is zero"
            )
        snapshot = None
    composition = _compose(
        current=current,
        window_state=state,
        expected_versions=versions,
        sessions=sessions,
        start_position=start,
        compression_ratio=ratio,
        compressed_view=snapshot,
        dspark=dspark,
    )
    return AttentionKVViewResult(
        numeric_profile=ATTENTION_KV_VIEW_PROFILE,
        mode=composition.mode,
        dspark=dspark,
        compression_ratio=ratio,
        start_position=start,
        next_position=composition.next_position,
        session_ids=sessions,
        current_kv_bf16_codes=current,
        window_state=state,
        expected_window_state_versions=versions,
        compressed_view=snapshot,
        bf16_codes=composition.output,
        window_region=composition.window_region,
        current_region=composition.current_region,
        compressed_region=composition.compressed_region,
        valid_row_indices=composition.valid_row_indices,
        window_valid_absolute_start=composition.window_valid_absolute_start,
        window_valid_row_count=composition.window_valid_row_count,
        window_valid_physical_slots=composition.window_valid_physical_slots,
        counters=composition.counters,
    )


__all__ = [
    "ATTENTION_KV_VIEW_PROFILE",
    "BF16Batch",
    "BF16Sequence",
    "BF16Vector",
    "EXCLUDED_CLAIMS",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_SOURCE_SHA256",
    "PINNED_COMPRESSION_RATIOS",
    "PINNED_DSPARK_BLOCK_SIZE",
    "PINNED_HEAD_DIM",
    "PINNED_WINDOW_SIZE",
    "AttentionKVViewCounters",
    "AttentionKVViewMode",
    "AttentionKVViewReferenceError",
    "AttentionKVViewResult",
    "CompressedKVViewSnapshot",
    "attention_kv_view_bf16",
]
