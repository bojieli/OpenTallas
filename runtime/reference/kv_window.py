"""Session-safe DeepSeek V4 circular KV-window state transitions.

This module freezes the two assignments in the pinned
``inference/model.py:Attention.forward`` and ``DSparkAttention.forward``:

* fresh prefill (``start_pos == 0``) writes every row when ``S <= W`` and
  otherwise retains only the final ``W`` input rows in circular slot order;
* decode (``start_pos > 0``) requires ``S == 1`` and replaces slot
  ``start_pos % W``.

The official cache has source shape ``[B,W,512]``. Its one latent KV row is
shared by all 64 query heads. The reference makes that sharing axis explicit
as ``[B,W,H,V]`` with the official mapping ``H=1,V=512``. Smaller
factorizations with ``H*V <= 512`` are admitted only for bounded structural
qualification; they are not model-output or performance evidence.

The released PyTorch object relies on its caller to delimit sessions and
advance positions. This target state makes those requirements explicit with a
canonical identity, active/retired status, absolute next position, and
monotonic uint64 version per fixed-capacity batch lane. Retired lanes retain
their prior identity as a tombstone. Every operation must hold the exact
full-capacity version vector, decode must match every active identity and the
one shared active-prefix cursor, and stale version authority poisons before a
transition or view. Session IDs may be deliberately reused only after their
current tombstone has been replaced and only with current epoch authority.
Atomic compare-and-swap across service requests remains outside this pure
reference.

The position ceiling used here is the architectural
``max_position_embeddings`` metadata in the hash-pinned top-level
``config.json``. It is not evidence that the pinned standalone inference
executable allocates or runs that length: its source default is 4,096 and its
interactive driver override is 65,536. All validation and address derivation
finish before the new immutable state is assembled.

For an active lane at next position ``N``, precisely the chronological range
``[max(0,N-W),N)`` is committed. :func:`kv_window_valid_view_bf16` returns only
that range in chronological order, with its absolute bounds, so unused or
stale capacity slots cannot enter a later ``ATTENTION_KV_VIEW``.

Counters are logical source/state/metadata reconciliation only. They do not
claim physical HBM or SRAM traffic, bursts, banking, cycles, latency,
throughput, bandwidth, energy, area, density, routing, PPA, compiler lowering,
service execution, or end-to-end model correctness.

Public result constructors retain and deeply freeze the exact source state and
the source activation where applicable. They reconstruct the complete
successor transition or chronological view, including exact lane versions.
That proves an internal semantic relation only; it does not establish
cryptographic or authenticated origin for the retained values.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from .formats import decode_bf16


MODEL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
MODEL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
MODEL_CONFIG_PATH = "config.json"
MODEL_CONFIG_SHA256 = "6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023"
MODEL_CONFIG_MAX_POSITION_FIELD = "max_position_embeddings"
MODEL_CONFIG_MAX_POSITION_EMBEDDINGS = 1_048_576
MODEL_CONFIG_MAX_POSITION_ANCHOR = (
    MODEL_CONFIG_PATH,
    MODEL_CONFIG_SHA256,
    MODEL_CONFIG_MAX_POSITION_FIELD,
    MODEL_CONFIG_MAX_POSITION_EMBEDDINGS,
)
MODEL_SOURCE_PATH = "inference/model.py"
MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
INFERENCE_CONFIG_PATH = "inference/config.json"
INFERENCE_CONFIG_SHA256 = (
    "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
)
INFERENCE_DRIVER_PATH = "inference/generate.py"
INFERENCE_DRIVER_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
INFERENCE_SOURCE_DEFAULT_MAX_SEQUENCE_LENGTH = 4_096
INFERENCE_DRIVER_INTERACTIVE_MAX_SEQUENCE_LENGTH = 65_536
KV_WINDOW_PROFILE = "opentallas.deepseek_v4_kv_window_write.v2"
KV_WINDOW_RETIRE_PROFILE = "opentallas.deepseek_v4_kv_window_retire.v1"
KV_WINDOW_VALID_VIEW_PROFILE = "opentallas.deepseek_v4_kv_window_valid_view.v1"

PINNED_MAX_BATCH_SIZE = 4
PINNED_MAX_POSITION = MODEL_CONFIG_MAX_POSITION_EMBEDDINGS
PINNED_WINDOW_SIZE = 128
PINNED_KV_HEAD_COUNT = 1
PINNED_KV_VALUE_WIDTH = 512
PINNED_QUERY_HEAD_COUNT = 64
PINNED_KV_ROW_WIDTH = PINNED_KV_HEAD_COUNT * PINNED_KV_VALUE_WIDTH
SESSION_ID_HEX_DIGITS = 64
MAX_STATE_VERSION = (1 << 64) - 1
BF16_BYTES = 2
BF16_MAX_ENCODING = (1 << 16) - 1

SOURCE_ASSIGNMENTS = (
    "self.kv_cache[:bsz, :seqlen] = kv",
    (
        "self.kv_cache[:bsz, cutoff: win], "
        "self.kv_cache[:bsz, :cutoff] = "
        "kv[:, -win:].split([win - cutoff, cutoff], dim=1)"
    ),
    "self.kv_cache[:bsz, start_pos % win] = kv.squeeze(1)",
)

EXCLUDED_CLAIMS = (
    "kv_projection_normalization_rope_or_qdq",
    "sparse_attention_or_attention_kv_composition",
    "checkpoint_numeric_output_evidence",
    "compiler_lowering",
    "service_or_rtl_execution",
    "atomic_service_compare_and_swap",
    "cryptographic_or_authenticated_transition_origin",
    "physical_hbm_sram_cycles_latency_bandwidth_energy_area_routing_ppa",
    "end_to_end_model_execution",
)


SessionId: TypeAlias = str
OptionalSessionId: TypeAlias = str | None
BF16Vector: TypeAlias = tuple[int, ...]
BF16HeadRow: TypeAlias = tuple[BF16Vector, ...]
BF16Window: TypeAlias = tuple[BF16HeadRow, ...]
BF16WindowTensor: TypeAlias = tuple[BF16Window, ...]
BF16InputSequence: TypeAlias = tuple[BF16HeadRow, ...]
BF16InputTensor: TypeAlias = tuple[BF16InputSequence, ...]
BF16ValidWindowTensor: TypeAlias = tuple[BF16Window, ...]
KVWindowMode: TypeAlias = Literal["prefill", "decode"]


class KVWindowReferenceError(ValueError):
    """Raised when an entire KV-window transaction must poison."""


@dataclass(frozen=True)
class KVWindowState:
    """Immutable circular payload and per-lane causal metadata."""

    profile: str
    bf16_codes: BF16WindowTensor
    session_ids: tuple[OptionalSessionId, ...]
    lane_active: tuple[bool, ...]
    next_positions: tuple[int, ...]
    versions: tuple[int, ...]

    def __post_init__(self) -> None:
        _validate_state(self)


@dataclass(frozen=True)
class KVWindowWriteSegment:
    """One nonempty source/destination slice in official assignment order."""

    source_sequence_start: int
    source_sequence_stop: int
    absolute_position_start: int
    absolute_position_stop: int
    destination_slot_start: int
    destination_slot_stop: int

    def __post_init__(self) -> None:
        _validate_write_segment(self)


@dataclass(frozen=True)
class KVWindowWriteCounters:
    """Exact logical payload, valid-window, and metadata accounting."""

    active_batch_count: int
    previous_active_batch_count: int
    removed_batch_count: int
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
    valid_window_rows_before: int
    valid_window_rows_invalidated: int
    valid_window_rows_after: int
    source_slice_assignments: int
    nonempty_source_slice_assignments: int
    logical_slot_modulo_evaluations: int
    logical_session_ids_read: int
    logical_session_ids_written: int
    logical_lane_active_flags_read: int
    logical_lane_active_flags_written: int
    logical_next_positions_read: int
    logical_next_positions_written: int
    logical_versions_read: int
    logical_versions_written: int
    logical_metadata_fields_read: int
    logical_metadata_fields_written: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_write_counters(self)


@dataclass(frozen=True)
class KVWindowWriteResult:
    """One fully committed state version and its exact write mapping."""

    profile: str
    prior_state: KVWindowState
    input_bf16_codes: BF16InputTensor
    state: KVWindowState
    mode: KVWindowMode
    start_pos: int
    end_pos: int
    active_session_ids: tuple[SessionId, ...]
    segments: tuple[KVWindowWriteSegment, ...]
    counters: KVWindowWriteCounters

    def __post_init__(self) -> None:
        _validate_write_result(self)


@dataclass(frozen=True)
class KVWindowRetireCounters:
    """Exact metadata and causal-window accounting for lane retirement."""

    previous_active_batch_count: int
    active_batch_count: int
    retired_batch_count: int
    state_batch_capacity: int
    window_size: int
    kv_head_count: int
    kv_value_width: int
    logical_state_rows_read: int
    logical_state_bf16_values_read: int
    logical_state_read_bytes: int
    logical_state_rows_written: int
    logical_state_bf16_values_written: int
    logical_state_write_bytes: int
    state_rows_preserved: int
    state_bf16_values_preserved: int
    valid_window_rows_before: int
    valid_window_rows_invalidated: int
    valid_window_rows_after: int
    logical_session_ids_read: int
    logical_session_ids_written: int
    logical_lane_active_flags_read: int
    logical_lane_active_flags_written: int
    logical_next_positions_read: int
    logical_next_positions_written: int
    logical_versions_read: int
    logical_versions_written: int
    logical_metadata_fields_read: int
    logical_metadata_fields_written: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_retire_counters(self)


@dataclass(frozen=True)
class KVWindowRetireResult:
    """One atomic retirement of an exact nonempty active trailing suffix."""

    profile: str
    prior_state: KVWindowState
    state: KVWindowState
    previous_active_session_ids: tuple[SessionId, ...]
    active_session_ids: tuple[SessionId, ...]
    retired_session_ids: tuple[SessionId, ...]
    retired_next_positions: tuple[int, ...]
    retired_previous_versions: tuple[int, ...]
    counters: KVWindowRetireCounters

    def __post_init__(self) -> None:
        _validate_retire_result(self)


@dataclass(frozen=True)
class KVWindowValidViewCounters:
    """Exact logical metadata and chronological payload-view accounting."""

    active_batch_count: int
    state_batch_capacity: int
    window_size: int
    kv_head_count: int
    kv_value_width: int
    logical_session_ids_read: int
    logical_lane_active_flags_read: int
    logical_next_positions_read: int
    logical_versions_read: int
    logical_metadata_fields_read: int
    logical_state_rows_read: int
    logical_state_bf16_values_read: int
    logical_state_read_bytes: int
    logical_slot_modulo_evaluations: int
    valid_rows_returned: int
    active_capacity_rows_excluded: int
    inactive_capacity_rows_excluded: int
    total_state_rows_not_exposed: int
    view_evaluations: int
    transaction_commits: int

    def __post_init__(self) -> None:
        _validate_valid_view_counters(self)


@dataclass(frozen=True)
class KVWindowValidViewResult:
    """Chronological committed windows with absolute causal bounds."""

    profile: str
    state: KVWindowState
    bf16_codes: BF16ValidWindowTensor
    session_ids: tuple[SessionId, ...]
    absolute_position_starts: tuple[int, ...]
    next_positions: tuple[int, ...]
    versions: tuple[int, ...]
    counters: KVWindowValidViewCounters

    def __post_init__(self) -> None:
        _validate_valid_view_result(self)


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


def _canonical_session_id(value: object, label: str) -> SessionId:
    if type(value) is not str or len(value) != SESSION_ID_HEX_DIGITS:
        raise KVWindowReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
        )
    if any(character not in "0123456789abcdef" for character in value):
        raise KVWindowReferenceError(
            f"{label} must be exactly {SESSION_ID_HEX_DIGITS} lowercase hex digits"
        )
    return value


def _finite_bf16(value: object, label: str) -> int:
    if type(value) is not int or not 0 <= value <= BF16_MAX_ENCODING:
        raise KVWindowReferenceError(f"{label} must be a 16-bit BF16 encoding")
    decoded = decode_bf16(value)
    if not decoded.finite:
        raise KVWindowReferenceError(f"{label} must be finite BF16")
    return value


def _nonnegative_integer(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise KVWindowReferenceError(f"{label} must be a nonnegative integer")
    return value


def _exact_profile(value: object, expected: str, label: str) -> str:
    if type(value) is not str or value != expected:
        raise KVWindowReferenceError(
            f"{label} must equal the exact profile {expected!r}"
        )
    return value


def _synchronized_valid_rows_per_lane(
    total_rows: int,
    lane_count: int,
    window_size: int,
    label: str,
) -> int:
    if lane_count == 0:
        if total_rows != 0:
            raise KVWindowReferenceError(
                f"{label} must be zero when there are no active lanes"
            )
        return 0
    if total_rows % lane_count:
        raise KVWindowReferenceError(
            f"{label} must be equal across cursor-synchronized active lanes"
        )
    per_lane = total_rows // lane_count
    if not 1 <= per_lane <= window_size:
        raise KVWindowReferenceError(
            f"{label} per active lane must be in [1, {window_size}]"
        )
    return per_lane


def _fields_match(value: object, expected: dict[str, int]) -> bool:
    return all(
        getattr(value, name) == expected_value
        for name, expected_value in expected.items()
    )


def _validate_write_segment(segment: object) -> KVWindowWriteSegment:
    if type(segment) is not KVWindowWriteSegment:
        raise KVWindowReferenceError(
            "write segment must be an exact KVWindowWriteSegment"
        )
    source_start = _integer(
        segment.source_sequence_start,
        "segment.source_sequence_start",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    source_stop = _integer(
        segment.source_sequence_stop,
        "segment.source_sequence_stop",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    absolute_start = _integer(
        segment.absolute_position_start,
        "segment.absolute_position_start",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    absolute_stop = _integer(
        segment.absolute_position_stop,
        "segment.absolute_position_stop",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    destination_start = _integer(
        segment.destination_slot_start,
        "segment.destination_slot_start",
        minimum=0,
        maximum=PINNED_WINDOW_SIZE - 1,
    )
    destination_stop = _integer(
        segment.destination_slot_stop,
        "segment.destination_slot_stop",
        minimum=1,
        maximum=PINNED_WINDOW_SIZE,
    )
    lengths = (
        source_stop - source_start,
        absolute_stop - absolute_start,
        destination_stop - destination_start,
    )
    if lengths[0] <= 0 or len(set(lengths)) != 1:
        raise KVWindowReferenceError(
            "write segment source, absolute, and destination extents must be "
            "equal and nonempty"
        )
    return segment


def _validate_write_counters(counters: object) -> KVWindowWriteCounters:
    if type(counters) is not KVWindowWriteCounters:
        raise KVWindowReferenceError(
            "write counters must be exact KVWindowWriteCounters"
        )
    for name in counters.__dataclass_fields__:
        _nonnegative_integer(getattr(counters, name), f"counters.{name}")

    capacity = _integer(
        counters.state_batch_capacity,
        "counters.state_batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    active = _integer(
        counters.active_batch_count,
        "counters.active_batch_count",
        minimum=1,
        maximum=capacity,
    )
    previous_active = _integer(
        counters.previous_active_batch_count,
        "counters.previous_active_batch_count",
        minimum=0,
        maximum=capacity,
    )
    sequence_length = _integer(
        counters.sequence_length,
        "counters.sequence_length",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    window_size = _integer(
        counters.window_size,
        "counters.window_size",
        minimum=1,
        maximum=PINNED_WINDOW_SIZE,
    )
    head_count = _integer(
        counters.kv_head_count,
        "counters.kv_head_count",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    value_width = _integer(
        counters.kv_value_width,
        "counters.kv_value_width",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    row_values = head_count * value_width
    if row_values > PINNED_KV_ROW_WIDTH:
        raise KVWindowReferenceError("write counters exceed the pinned KV-row width")
    if counters.removed_batch_count != max(0, previous_active - active):
        raise KVWindowReferenceError(
            "write counters removed batch count is inconsistent"
        )

    committed = min(sequence_length, window_size)
    input_rows = active * sequence_length
    written_rows = active * committed
    state_rows = capacity * window_size
    expected_values = {
        "input_rows": input_rows,
        "input_bf16_values": input_rows * row_values,
        "committed_positions_per_batch": committed,
        "uncommitted_positions_per_batch": sequence_length - committed,
        "logical_source_rows_read": written_rows,
        "logical_source_bf16_values_read": written_rows * row_values,
        "logical_source_read_bytes": written_rows * row_values * BF16_BYTES,
        "logical_state_rows_read": 0,
        "logical_state_bf16_values_read": 0,
        "logical_state_read_bytes": 0,
        "logical_state_rows_written": written_rows,
        "logical_state_bf16_values_written": written_rows * row_values,
        "logical_state_write_bytes": written_rows * row_values * BF16_BYTES,
        "state_rows_preserved": state_rows - written_rows,
        "state_bf16_values_preserved": (state_rows - written_rows) * row_values,
    }
    for name, expected in expected_values.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"write counters {name} does not reconcile to dimensions"
            )

    if counters.valid_window_rows_before > previous_active * window_size:
        raise KVWindowReferenceError("write counters valid rows before exceed capacity")
    if counters.valid_window_rows_after > active * window_size:
        raise KVWindowReferenceError("write counters valid rows after exceed capacity")
    if counters.valid_window_rows_invalidated > counters.valid_window_rows_before:
        raise KVWindowReferenceError("write counters invalidate unavailable valid rows")
    if (
        counters.valid_window_rows_before
        - counters.valid_window_rows_invalidated
        + written_rows
        != counters.valid_window_rows_after
    ):
        raise KVWindowReferenceError(
            "write counters valid-window rows do not reconcile"
        )
    if counters.source_slice_assignments not in {1, 2}:
        raise KVWindowReferenceError("write counters source assignments must be 1 or 2")
    if (
        not 1
        <= counters.nonempty_source_slice_assignments
        <= (counters.source_slice_assignments)
    ):
        raise KVWindowReferenceError(
            "write counters nonempty source assignments are inconsistent"
        )
    if counters.logical_slot_modulo_evaluations not in {0, 1}:
        raise KVWindowReferenceError(
            "write counters slot modulo evaluations must be 0 or 1"
        )
    if counters.logical_metadata_fields_read != (
        counters.logical_session_ids_read
        + counters.logical_lane_active_flags_read
        + counters.logical_next_positions_read
        + counters.logical_versions_read
    ):
        raise KVWindowReferenceError("write counters metadata reads do not reconcile")
    if counters.logical_metadata_fields_written != (
        counters.logical_session_ids_written
        + counters.logical_lane_active_flags_written
        + counters.logical_next_positions_written
        + counters.logical_versions_written
    ):
        raise KVWindowReferenceError("write counters metadata writes do not reconcile")
    if counters.transaction_commits != 1:
        raise KVWindowReferenceError("write counters must record exactly one commit")

    prior_valid_per_lane = _synchronized_valid_rows_per_lane(
        counters.valid_window_rows_before,
        previous_active,
        window_size,
        "write counters valid rows before",
    )
    changed = max(previous_active, active)
    removed = max(0, previous_active - active)
    if sequence_length <= window_size:
        prefill_assignments = 1
        prefill_nonempty_assignments = 1
        prefill_modulo = 0
    else:
        prefill_assignments = 2
        prefill_nonempty_assignments = 1 if sequence_length % window_size == 0 else 2
        prefill_modulo = 1
    prefill_pattern = {
        "valid_window_rows_invalidated": counters.valid_window_rows_before,
        "valid_window_rows_after": active * min(sequence_length, window_size),
        "source_slice_assignments": prefill_assignments,
        "nonempty_source_slice_assignments": prefill_nonempty_assignments,
        "logical_slot_modulo_evaluations": prefill_modulo,
        "logical_session_ids_read": capacity,
        "logical_session_ids_written": active,
        "logical_lane_active_flags_read": capacity,
        "logical_lane_active_flags_written": changed,
        "logical_next_positions_read": previous_active,
        "logical_next_positions_written": active + removed,
        "logical_versions_read": changed,
        "logical_versions_written": changed,
    }
    decode_pattern_matches = False
    if sequence_length == 1 and previous_active >= active:
        decode_pattern = {
            "valid_window_rows_invalidated": (
                removed * prior_valid_per_lane
                + (active if prior_valid_per_lane == window_size else 0)
            ),
            "valid_window_rows_after": active
            * min(prior_valid_per_lane + 1, window_size),
            "source_slice_assignments": 1,
            "nonempty_source_slice_assignments": 1,
            "logical_slot_modulo_evaluations": 1,
            "logical_session_ids_read": active,
            "logical_session_ids_written": 0,
            "logical_lane_active_flags_read": capacity,
            "logical_lane_active_flags_written": removed,
            "logical_next_positions_read": previous_active,
            "logical_next_positions_written": active + removed,
            "logical_versions_read": previous_active,
            "logical_versions_written": previous_active,
        }
        decode_pattern_matches = _fields_match(counters, decode_pattern)
    if not _fields_match(counters, prefill_pattern) and not decode_pattern_matches:
        raise KVWindowReferenceError(
            "write counters do not match a reachable synchronized prefill or decode"
        )
    return counters


def _validate_retire_counters(counters: object) -> KVWindowRetireCounters:
    if type(counters) is not KVWindowRetireCounters:
        raise KVWindowReferenceError(
            "retire counters must be exact KVWindowRetireCounters"
        )
    for name in counters.__dataclass_fields__:
        _nonnegative_integer(getattr(counters, name), f"counters.{name}")

    capacity = _integer(
        counters.state_batch_capacity,
        "counters.state_batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    previous_active = _integer(
        counters.previous_active_batch_count,
        "counters.previous_active_batch_count",
        minimum=1,
        maximum=capacity,
    )
    active = _integer(
        counters.active_batch_count,
        "counters.active_batch_count",
        minimum=0,
        maximum=previous_active - 1,
    )
    retired = _integer(
        counters.retired_batch_count,
        "counters.retired_batch_count",
        minimum=1,
        maximum=previous_active,
    )
    if previous_active != active + retired:
        raise KVWindowReferenceError("retire counters batch counts do not reconcile")
    window_size = _integer(
        counters.window_size,
        "counters.window_size",
        minimum=1,
        maximum=PINNED_WINDOW_SIZE,
    )
    head_count = _integer(
        counters.kv_head_count,
        "counters.kv_head_count",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    value_width = _integer(
        counters.kv_value_width,
        "counters.kv_value_width",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    row_values = head_count * value_width
    if row_values > PINNED_KV_ROW_WIDTH:
        raise KVWindowReferenceError("retire counters exceed the pinned KV-row width")
    state_rows = capacity * window_size
    expected_values = {
        "logical_state_rows_read": 0,
        "logical_state_bf16_values_read": 0,
        "logical_state_read_bytes": 0,
        "logical_state_rows_written": 0,
        "logical_state_bf16_values_written": 0,
        "logical_state_write_bytes": 0,
        "state_rows_preserved": state_rows,
        "state_bf16_values_preserved": state_rows * row_values,
        "logical_session_ids_read": previous_active,
        "logical_session_ids_written": 0,
        "logical_lane_active_flags_read": capacity,
        "logical_lane_active_flags_written": retired,
        "logical_next_positions_read": previous_active,
        "logical_next_positions_written": retired,
        "logical_versions_read": retired,
        "logical_versions_written": retired,
    }
    for name, expected in expected_values.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"retire counters {name} does not reconcile to dimensions"
            )
    prior_valid_per_lane = _synchronized_valid_rows_per_lane(
        counters.valid_window_rows_before,
        previous_active,
        window_size,
        "retire counters valid rows before",
    )
    if counters.valid_window_rows_after != active * prior_valid_per_lane:
        raise KVWindowReferenceError(
            "retire counters valid rows after do not preserve the synchronized prefix"
        )
    if counters.valid_window_rows_invalidated != retired * prior_valid_per_lane:
        raise KVWindowReferenceError(
            "retire counters invalidated rows do not match the synchronized suffix"
        )
    if counters.logical_metadata_fields_read != (
        counters.logical_session_ids_read
        + counters.logical_lane_active_flags_read
        + counters.logical_next_positions_read
        + counters.logical_versions_read
    ):
        raise KVWindowReferenceError("retire counters metadata reads do not reconcile")
    if counters.logical_metadata_fields_written != (
        counters.logical_session_ids_written
        + counters.logical_lane_active_flags_written
        + counters.logical_next_positions_written
        + counters.logical_versions_written
    ):
        raise KVWindowReferenceError("retire counters metadata writes do not reconcile")
    if counters.transaction_commits != 1:
        raise KVWindowReferenceError("retire counters must record exactly one commit")
    return counters


def _validate_valid_view_counters(
    counters: object,
) -> KVWindowValidViewCounters:
    if type(counters) is not KVWindowValidViewCounters:
        raise KVWindowReferenceError(
            "valid-view counters must be exact KVWindowValidViewCounters"
        )
    for name in counters.__dataclass_fields__:
        _nonnegative_integer(getattr(counters, name), f"counters.{name}")

    capacity = _integer(
        counters.state_batch_capacity,
        "counters.state_batch_capacity",
        minimum=1,
        maximum=PINNED_MAX_BATCH_SIZE,
    )
    active = _integer(
        counters.active_batch_count,
        "counters.active_batch_count",
        minimum=0,
        maximum=capacity,
    )
    window_size = _integer(
        counters.window_size,
        "counters.window_size",
        minimum=1,
        maximum=PINNED_WINDOW_SIZE,
    )
    head_count = _integer(
        counters.kv_head_count,
        "counters.kv_head_count",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    value_width = _integer(
        counters.kv_value_width,
        "counters.kv_value_width",
        minimum=1,
        maximum=PINNED_KV_ROW_WIDTH,
    )
    row_values = head_count * value_width
    if row_values > PINNED_KV_ROW_WIDTH:
        raise KVWindowReferenceError(
            "valid-view counters exceed the pinned KV-row width"
        )
    valid_rows = counters.valid_rows_returned
    _synchronized_valid_rows_per_lane(
        valid_rows,
        active,
        window_size,
        "valid-view rows returned",
    )
    expected_values = {
        "logical_session_ids_read": active,
        "logical_lane_active_flags_read": capacity,
        "logical_next_positions_read": active,
        "logical_versions_read": active,
        "logical_metadata_fields_read": capacity + 3 * active,
        "logical_state_rows_read": valid_rows,
        "logical_state_bf16_values_read": valid_rows * row_values,
        "logical_state_read_bytes": valid_rows * row_values * BF16_BYTES,
        "logical_slot_modulo_evaluations": valid_rows,
        "active_capacity_rows_excluded": active * window_size - valid_rows,
        "inactive_capacity_rows_excluded": (capacity - active) * window_size,
        "total_state_rows_not_exposed": capacity * window_size - valid_rows,
        "view_evaluations": 1,
        "transaction_commits": 0,
    }
    for name, expected in expected_values.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"valid-view counters {name} does not reconcile to dimensions"
            )
    return counters


def _validate_state(
    state: object,
) -> tuple[KVWindowState, int, int, int, int, int]:
    if type(state) is not KVWindowState:
        raise KVWindowReferenceError("state must be an exact KVWindowState")
    if type(state.profile) is not str or state.profile != KV_WINDOW_PROFILE:
        raise KVWindowReferenceError(
            f"state.profile must equal the exact profile {KV_WINDOW_PROFILE!r}"
        )
    raw_batches = _sequence(state.bf16_codes, "state.bf16_codes")
    if not 1 <= len(raw_batches) <= PINNED_MAX_BATCH_SIZE:
        raise KVWindowReferenceError(
            f"state batch capacity must be in [1, {PINNED_MAX_BATCH_SIZE}]"
        )
    batch_capacity = len(raw_batches)

    metadata_fields = (
        (state.session_ids, "state.session_ids"),
        (state.lane_active, "state.lane_active"),
        (state.next_positions, "state.next_positions"),
        (state.versions, "state.versions"),
    )
    materialized_metadata: list[list[object] | tuple[object, ...]] = []
    for raw_field, label in metadata_fields:
        field = _sequence(raw_field, label)
        if len(field) != batch_capacity:
            raise KVWindowReferenceError(
                f"{label} extent must match state batch capacity"
            )
        materialized_metadata.append(field)

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

    raw_sessions, raw_active, raw_next, raw_versions = materialized_metadata
    sessions: list[OptionalSessionId] = []
    active_flags: list[bool] = []
    next_positions: list[int] = []
    versions: list[int] = []
    seen_sessions: set[str] = set()
    seen_inactive = False
    for batch_index in range(batch_capacity):
        raw_session = raw_sessions[batch_index]
        if raw_session is None:
            session: OptionalSessionId = None
        else:
            session = _canonical_session_id(
                raw_session,
                f"state.session_ids[{batch_index}]",
            )
            if session in seen_sessions:
                raise KVWindowReferenceError(
                    "state session identities must be unique across lanes"
                )
            seen_sessions.add(session)

        active = raw_active[batch_index]
        if type(active) is not bool:
            raise KVWindowReferenceError(
                f"state.lane_active[{batch_index}] must be bool"
            )
        if seen_inactive and active:
            raise KVWindowReferenceError(
                "state active lanes must form a contiguous prefix"
            )
        seen_inactive |= not active
        next_position = _integer(
            raw_next[batch_index],
            f"state.next_positions[{batch_index}]",
            minimum=0,
            maximum=PINNED_MAX_POSITION,
        )
        version = _integer(
            raw_versions[batch_index],
            f"state.versions[{batch_index}]",
            minimum=0,
            maximum=MAX_STATE_VERSION,
        )

        if active:
            if session is None:
                raise KVWindowReferenceError(
                    f"active state lane {batch_index} must have a session identity"
                )
            if next_position == 0:
                raise KVWindowReferenceError(
                    f"active state lane {batch_index} must be initialized by prefill"
                )
            if version == 0:
                raise KVWindowReferenceError(
                    f"active state lane {batch_index} must have nonzero version"
                )
        else:
            if next_position != 0:
                raise KVWindowReferenceError(
                    f"inactive state lane {batch_index} must have next_pos zero"
                )
            if session is None:
                if version != 0:
                    raise KVWindowReferenceError(
                        f"never-initialized state lane {batch_index} must have "
                        "version zero"
                    )
                if any(
                    code != 0x0000
                    for row in batches[batch_index]
                    for vector in row
                    for code in vector
                ):
                    raise KVWindowReferenceError(
                        f"never-initialized state lane {batch_index} must contain "
                        "only positive-zero BF16 payload"
                    )
            elif version < 2:
                raise KVWindowReferenceError(
                    f"retired state lane {batch_index} must have version at least two"
                )

        sessions.append(session)
        active_flags.append(active)
        next_positions.append(next_position)
        versions.append(version)

    active_count = sum(active_flags)
    if active_count > 1 and len(set(next_positions[:active_count])) != 1:
        raise KVWindowReferenceError(
            "state active lanes must share one synchronized next position"
        )
    object.__setattr__(state, "bf16_codes", tuple(batches))
    object.__setattr__(state, "session_ids", tuple(sessions))
    object.__setattr__(state, "lane_active", tuple(active_flags))
    object.__setattr__(state, "next_positions", tuple(next_positions))
    object.__setattr__(state, "versions", tuple(versions))
    return (
        state,
        batch_capacity,
        window_size,
        head_count,
        value_width,
        active_count,
    )


def _validate_input(
    value: object,
    *,
    expected_batch_size: int,
    head_count: int,
    value_width: int,
) -> tuple[BF16InputTensor, int]:
    raw_batches = _sequence(value, "kv_bf16_codes")
    if len(raw_batches) != expected_batch_size:
        raise KVWindowReferenceError(
            "kv_bf16_codes batch extent must exactly match active_session_ids"
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
    return tuple(batches), sequence_length


def _session_ids(
    value: object,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> tuple[SessionId, ...]:
    raw = _sequence(value, label)
    if not minimum <= len(raw) <= maximum:
        raise KVWindowReferenceError(
            f"{label} extent must be in [{minimum}, {maximum}]"
        )
    sessions = tuple(
        _canonical_session_id(session, f"{label}[{index}]")
        for index, session in enumerate(raw)
    )
    if len(set(sessions)) != len(sessions):
        raise KVWindowReferenceError(f"{label} must contain unique identities")
    return sessions


def _active_session_ids(
    value: object,
    *,
    batch_capacity: int,
    allow_empty: bool,
) -> tuple[SessionId, ...]:
    return _session_ids(
        value,
        label="active_session_ids",
        minimum=0 if allow_empty else 1,
        maximum=batch_capacity,
    )


def _state_version_authority(
    value: object,
    state: KVWindowState,
    *,
    label: str = "expected_state_versions",
) -> tuple[int, ...]:
    raw = _sequence(value, label)
    if len(raw) != len(state.versions):
        raise KVWindowReferenceError(
            f"{label} must cover the full state batch capacity"
        )
    versions = tuple(
        _integer(
            version,
            f"{label}[{index}]",
            minimum=0,
            maximum=MAX_STATE_VERSION,
        )
        for index, version in enumerate(raw)
    )
    if versions != state.versions:
        raise KVWindowReferenceError(f"{label} does not match current state versions")
    return versions


def zero_kv_window_state_bf16(
    *,
    batch_capacity: int = PINNED_MAX_BATCH_SIZE,
    window_size: int = PINNED_WINDOW_SIZE,
    kv_head_count: int = PINNED_KV_HEAD_COUNT,
    kv_value_width: int = PINNED_KV_VALUE_WIDTH,
) -> KVWindowState:
    """Create an all-positive-zero cache with uninitialized session lanes."""

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
    state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=(window,) * batch_capacity,
        session_ids=(None,) * batch_capacity,
        lane_active=(False,) * batch_capacity,
        next_positions=(0,) * batch_capacity,
        versions=(0,) * batch_capacity,
    )
    return _validate_state(state)[0]


def kv_window_state_bf16(value: object) -> KVWindowState:
    """Validate and deeply freeze caller-provided payload and causal metadata."""

    return _validate_state(value)[0]


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


def _valid_window_rows(
    state: KVWindowState, active_count: int, window_size: int
) -> int:
    return sum(
        min(state.next_positions[batch_index], window_size)
        for batch_index in range(active_count)
    )


def _validate_write_result(result: object) -> KVWindowWriteResult:
    if type(result) is not KVWindowWriteResult:
        raise KVWindowReferenceError(
            "write result must be an exact KVWindowWriteResult"
        )
    _exact_profile(result.profile, KV_WINDOW_PROFILE, "write result.profile")
    (
        state,
        capacity,
        window_size,
        head_count,
        value_width,
        state_active_count,
    ) = _validate_state(result.state)
    (
        prior_state,
        prior_capacity,
        prior_window_size,
        prior_head_count,
        prior_value_width,
        previous_active,
    ) = _validate_state(result.prior_state)
    if (
        prior_capacity,
        prior_window_size,
        prior_head_count,
        prior_value_width,
    ) != (capacity, window_size, head_count, value_width):
        raise KVWindowReferenceError(
            "write result prior and successor state dimensions must match"
        )
    if type(result.mode) is not str or result.mode not in {"prefill", "decode"}:
        raise KVWindowReferenceError("write result.mode must be prefill or decode")
    start_pos = _integer(
        result.start_pos,
        "write result.start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    end_pos = _integer(
        result.end_pos,
        "write result.end_pos",
        minimum=1,
        maximum=PINNED_MAX_POSITION,
    )
    if end_pos <= start_pos:
        raise KVWindowReferenceError("write result positions must form a forward range")
    sessions = _active_session_ids(
        result.active_session_ids,
        batch_capacity=capacity,
        allow_empty=False,
    )
    frozen_input, sequence_length = _validate_input(
        result.input_bf16_codes,
        expected_batch_size=len(sessions),
        head_count=head_count,
        value_width=value_width,
    )
    if end_pos != start_pos + sequence_length:
        raise KVWindowReferenceError(
            "write result end position does not match its retained input extent"
        )
    raw_segments = _sequence(result.segments, "write result.segments")
    segments = tuple(_validate_write_segment(segment) for segment in raw_segments)
    counters = _validate_write_counters(result.counters)

    mode, expected_segments, committed, assignments, modulo = _write_plan(
        start_pos=start_pos,
        sequence_length=sequence_length,
        window_size=window_size,
    )
    if result.mode != mode:
        raise KVWindowReferenceError("write result mode does not match its positions")
    if segments != expected_segments:
        raise KVWindowReferenceError(
            "write result segments do not match the official assignment plan"
        )
    active = len(sessions)
    if mode == "prefill":
        retained_sessions = {
            session for session in prior_state.session_ids if session is not None
        }
        if any(session in retained_sessions for session in sessions):
            raise KVWindowReferenceError(
                "write result prefill does not use currently fresh session identities"
            )
    else:
        if active > previous_active:
            raise KVWindowReferenceError(
                "decode write result cannot increase its active batch count"
            )
        for batch_index, session in enumerate(sessions):
            if (
                not prior_state.lane_active[batch_index]
                or prior_state.session_ids[batch_index] != session
                or prior_state.next_positions[batch_index] != start_pos
            ):
                raise KVWindowReferenceError(
                    "decode write result does not match prior lane authority"
                )

    changed = max(previous_active, active)
    for batch_index in range(changed):
        if prior_state.versions[batch_index] == MAX_STATE_VERSION:
            raise KVWindowReferenceError(
                f"write result prior version overflows at lane {batch_index}"
            )
    expected_payload = [list(window) for window in prior_state.bf16_codes]
    expected_sessions = list(prior_state.session_ids)
    expected_active = list(prior_state.lane_active)
    expected_next = list(prior_state.next_positions)
    expected_versions = list(prior_state.versions)
    for batch_index in range(active):
        for segment in segments:
            expected_payload[batch_index][
                segment.destination_slot_start : segment.destination_slot_stop
            ] = frozen_input[batch_index][
                segment.source_sequence_start : segment.source_sequence_stop
            ]
        if mode == "prefill":
            expected_sessions[batch_index] = sessions[batch_index]
            expected_active[batch_index] = True
        expected_next[batch_index] = end_pos
        expected_versions[batch_index] += 1
    for batch_index in range(active, previous_active):
        expected_active[batch_index] = False
        expected_next[batch_index] = 0
        expected_versions[batch_index] += 1
    expected_state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=tuple(tuple(window) for window in expected_payload),
        session_ids=tuple(expected_sessions),
        lane_active=tuple(expected_active),
        next_positions=tuple(expected_next),
        versions=tuple(expected_versions),
    )
    if state != expected_state:
        raise KVWindowReferenceError(
            "write result successor does not exactly reconstruct from prior state and input"
        )
    if state_active_count != active:
        raise KVWindowReferenceError(
            "write result active sessions do not match state active lanes"
        )
    dimension_values = {
        "active_batch_count": active,
        "previous_active_batch_count": previous_active,
        "removed_batch_count": max(0, previous_active - active),
        "state_batch_capacity": capacity,
        "sequence_length": sequence_length,
        "window_size": window_size,
        "kv_head_count": head_count,
        "kv_value_width": value_width,
        "committed_positions_per_batch": committed,
        "source_slice_assignments": assignments,
        "nonempty_source_slice_assignments": len(segments),
        "logical_slot_modulo_evaluations": modulo,
    }
    for name, expected in dimension_values.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"write result counters {name} does not reconcile to result"
            )

    removed = max(0, previous_active - active)
    expected_metadata = {
        "logical_session_ids_read": capacity if mode == "prefill" else active,
        "logical_session_ids_written": active if mode == "prefill" else 0,
        "logical_lane_active_flags_read": capacity,
        "logical_lane_active_flags_written": changed if mode == "prefill" else removed,
        "logical_next_positions_read": previous_active,
        "logical_next_positions_written": active + removed,
        "logical_versions_read": changed,
        "logical_versions_written": changed,
    }
    for name, expected in expected_metadata.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"write result counters {name} does not match its mode"
            )

    expected_valid_before = _valid_window_rows(
        prior_state,
        previous_active,
        window_size,
    )
    if counters.valid_window_rows_before != expected_valid_before:
        raise KVWindowReferenceError(
            "write result valid rows before do not match its prior state"
        )
    expected_valid_after = _valid_window_rows(state, active, window_size)
    if counters.valid_window_rows_after != expected_valid_after:
        raise KVWindowReferenceError(
            "write result valid rows after do not match committed cursors"
        )
    if mode == "prefill":
        expected_invalidated = expected_valid_before
    else:
        prior_valid_per_lane = min(start_pos, window_size)
        expected_decode_valid_before = previous_active * prior_valid_per_lane
        if counters.valid_window_rows_before != expected_decode_valid_before:
            raise KVWindowReferenceError(
                "decode write result valid rows before do not match its exact cursor"
            )
        expected_invalidated = removed * prior_valid_per_lane + (
            active if start_pos >= window_size else 0
        )
    if counters.valid_window_rows_invalidated != expected_invalidated:
        raise KVWindowReferenceError(
            "write result invalidated rows do not match its causal transition"
        )

    object.__setattr__(result, "prior_state", prior_state)
    object.__setattr__(result, "input_bf16_codes", frozen_input)
    object.__setattr__(result, "state", state)
    object.__setattr__(result, "active_session_ids", sessions)
    object.__setattr__(result, "segments", segments)
    object.__setattr__(result, "counters", counters)
    return result


def _validate_retire_result(result: object) -> KVWindowRetireResult:
    if type(result) is not KVWindowRetireResult:
        raise KVWindowReferenceError(
            "retire result must be an exact KVWindowRetireResult"
        )
    _exact_profile(result.profile, KV_WINDOW_RETIRE_PROFILE, "retire result.profile")
    (
        state,
        capacity,
        window_size,
        head_count,
        value_width,
        state_active_count,
    ) = _validate_state(result.state)
    (
        prior_state,
        prior_capacity,
        prior_window_size,
        prior_head_count,
        prior_value_width,
        prior_active_count,
    ) = _validate_state(result.prior_state)
    if (
        prior_capacity,
        prior_window_size,
        prior_head_count,
        prior_value_width,
    ) != (capacity, window_size, head_count, value_width):
        raise KVWindowReferenceError(
            "retire result prior and successor state dimensions must match"
        )
    previous_sessions = _session_ids(
        result.previous_active_session_ids,
        label="previous_active_session_ids",
        minimum=1,
        maximum=capacity,
    )
    active_sessions = _session_ids(
        result.active_session_ids,
        label="active_session_ids",
        minimum=0,
        maximum=len(previous_sessions) - 1,
    )
    retired_sessions = _session_ids(
        result.retired_session_ids,
        label="retired_session_ids",
        minimum=1,
        maximum=len(previous_sessions),
    )
    if previous_sessions != active_sessions + retired_sessions:
        raise KVWindowReferenceError(
            "retire result must split previous sessions into an exact active "
            "prefix and retired suffix"
        )
    active = len(active_sessions)
    retired = len(retired_sessions)
    if prior_active_count != len(previous_sessions):
        raise KVWindowReferenceError(
            "retire result previous sessions do not match prior active lanes"
        )
    if prior_state.session_ids[:prior_active_count] != previous_sessions:
        raise KVWindowReferenceError(
            "retire result previous sessions do not match prior identities"
        )
    if state_active_count != active:
        raise KVWindowReferenceError(
            "retire result active sessions do not match state active lanes"
        )
    raw_positions = _sequence(
        result.retired_next_positions,
        "retire result.retired_next_positions",
    )
    raw_versions = _sequence(
        result.retired_previous_versions,
        "retire result.retired_previous_versions",
    )
    if len(raw_positions) != retired or len(raw_versions) != retired:
        raise KVWindowReferenceError(
            "retire result prior metadata extents must match retired sessions"
        )
    retired_positions = tuple(
        _integer(
            position,
            f"retire result.retired_next_positions[{index}]",
            minimum=1,
            maximum=PINNED_MAX_POSITION,
        )
        for index, position in enumerate(raw_positions)
    )
    if len(set(retired_positions)) != 1:
        raise KVWindowReferenceError(
            "retire result prior cursors must be synchronized across retired lanes"
        )
    if retired_positions != prior_state.next_positions[active:prior_active_count]:
        raise KVWindowReferenceError(
            "retire result prior cursors do not match its retained prior state"
        )
    retired_versions = tuple(
        _integer(
            version,
            f"retire result.retired_previous_versions[{index}]",
            minimum=1,
            maximum=MAX_STATE_VERSION - 1,
        )
        for index, version in enumerate(raw_versions)
    )
    if retired_versions != prior_state.versions[active:prior_active_count]:
        raise KVWindowReferenceError(
            "retire result prior versions do not match its retained prior state"
        )

    expected_active = list(prior_state.lane_active)
    expected_next = list(prior_state.next_positions)
    expected_versions = list(prior_state.versions)
    for lane in range(active, prior_active_count):
        if expected_versions[lane] == MAX_STATE_VERSION:
            raise KVWindowReferenceError(
                f"retire result prior version overflows at lane {lane}"
            )
        expected_active[lane] = False
        expected_next[lane] = 0
        expected_versions[lane] += 1
    expected_state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=prior_state.bf16_codes,
        session_ids=prior_state.session_ids,
        lane_active=tuple(expected_active),
        next_positions=tuple(expected_next),
        versions=tuple(expected_versions),
    )
    if state != expected_state:
        raise KVWindowReferenceError(
            "retire result successor does not exactly reconstruct from prior state"
        )

    counters = _validate_retire_counters(result.counters)
    dimension_values = {
        "previous_active_batch_count": len(previous_sessions),
        "active_batch_count": active,
        "retired_batch_count": retired,
        "state_batch_capacity": capacity,
        "window_size": window_size,
        "kv_head_count": head_count,
        "kv_value_width": value_width,
        "valid_window_rows_before": _valid_window_rows(
            prior_state,
            prior_active_count,
            window_size,
        ),
        "valid_window_rows_after": _valid_window_rows(state, active, window_size),
        "valid_window_rows_invalidated": sum(
            min(position, window_size) for position in retired_positions
        ),
    }
    for name, expected in dimension_values.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"retire result counters {name} does not reconcile to result"
            )

    object.__setattr__(result, "prior_state", prior_state)
    object.__setattr__(result, "state", state)
    object.__setattr__(result, "previous_active_session_ids", previous_sessions)
    object.__setattr__(result, "active_session_ids", active_sessions)
    object.__setattr__(result, "retired_session_ids", retired_sessions)
    object.__setattr__(result, "retired_next_positions", retired_positions)
    object.__setattr__(result, "retired_previous_versions", retired_versions)
    object.__setattr__(result, "counters", counters)
    return result


def _validate_valid_view_result(result: object) -> KVWindowValidViewResult:
    if type(result) is not KVWindowValidViewResult:
        raise KVWindowReferenceError(
            "valid-view result must be an exact KVWindowValidViewResult"
        )
    _exact_profile(
        result.profile,
        KV_WINDOW_VALID_VIEW_PROFILE,
        "valid-view result.profile",
    )
    (
        state,
        capacity,
        window_size,
        head_count,
        value_width,
        active_count,
    ) = _validate_state(result.state)
    counters = _validate_valid_view_counters(result.counters)
    sessions = _session_ids(
        result.session_ids,
        label="valid-view result.session_ids",
        minimum=0,
        maximum=capacity,
    )
    if len(sessions) != active_count:
        raise KVWindowReferenceError(
            "valid-view result sessions do not match source active lanes"
        )
    if sessions != state.session_ids[:active_count]:
        raise KVWindowReferenceError(
            "valid-view result sessions do not match source state identities"
        )
    raw_windows = _sequence(result.bf16_codes, "valid-view result.bf16_codes")
    if len(raw_windows) != len(sessions):
        raise KVWindowReferenceError(
            "valid-view result payload batch extent does not match sessions"
        )
    windows: list[BF16Window] = []
    for batch_index, raw_window in enumerate(raw_windows):
        window = _sequence(
            raw_window,
            f"valid-view result.bf16_codes[{batch_index}]",
        )
        if not 1 <= len(window) <= window_size:
            raise KVWindowReferenceError(
                "each active valid-view window must be nonempty and within capacity"
            )
        rows: list[BF16HeadRow] = []
        for row_index, raw_heads in enumerate(window):
            heads = _sequence(
                raw_heads,
                f"valid-view result.bf16_codes[{batch_index}][{row_index}]",
            )
            if len(heads) != head_count:
                raise KVWindowReferenceError(
                    "valid-view result KV-head extent does not match counters"
                )
            output_heads: list[BF16Vector] = []
            for head_index, raw_values in enumerate(heads):
                values = _sequence(
                    raw_values,
                    "valid-view result.bf16_codes"
                    f"[{batch_index}][{row_index}][{head_index}]",
                )
                if len(values) != value_width:
                    raise KVWindowReferenceError(
                        "valid-view result value extent does not match counters"
                    )
                output_heads.append(
                    tuple(
                        _finite_bf16(
                            code,
                            "valid-view result.bf16_codes"
                            f"[{batch_index}][{row_index}]"
                            f"[{head_index}][{column}]",
                        )
                        for column, code in enumerate(values)
                    )
                )
            rows.append(tuple(output_heads))
        windows.append(tuple(rows))

    raw_starts = _sequence(
        result.absolute_position_starts,
        "valid-view result.absolute_position_starts",
    )
    raw_next = _sequence(
        result.next_positions,
        "valid-view result.next_positions",
    )
    raw_versions = _sequence(result.versions, "valid-view result.versions")
    if not (len(raw_starts) == len(raw_next) == len(raw_versions) == len(sessions)):
        raise KVWindowReferenceError(
            "valid-view result metadata extents must match sessions"
        )
    starts: list[int] = []
    next_positions: list[int] = []
    versions: list[int] = []
    for batch_index, window in enumerate(windows):
        start = _integer(
            raw_starts[batch_index],
            f"valid-view result.absolute_position_starts[{batch_index}]",
            minimum=0,
            maximum=PINNED_MAX_POSITION - 1,
        )
        next_position = _integer(
            raw_next[batch_index],
            f"valid-view result.next_positions[{batch_index}]",
            minimum=1,
            maximum=PINNED_MAX_POSITION,
        )
        version = _integer(
            raw_versions[batch_index],
            f"valid-view result.versions[{batch_index}]",
            minimum=1,
            maximum=MAX_STATE_VERSION,
        )
        if start != next_position - min(next_position, window_size):
            raise KVWindowReferenceError(
                "valid-view result absolute bounds are not the causal window"
            )
        if len(window) != next_position - start:
            raise KVWindowReferenceError(
                "valid-view result payload length does not match absolute bounds"
            )
        starts.append(start)
        next_positions.append(next_position)
        versions.append(version)
    expected_starts: list[int] = []
    expected_next: list[int] = []
    expected_versions: list[int] = []
    expected_windows: list[BF16Window] = []
    for batch_index in range(active_count):
        next_position = state.next_positions[batch_index]
        valid_count = min(next_position, window_size)
        absolute_start = next_position - valid_count
        expected_starts.append(absolute_start)
        expected_next.append(next_position)
        expected_versions.append(state.versions[batch_index])
        expected_windows.append(
            tuple(
                state.bf16_codes[batch_index][position % window_size]
                for position in range(absolute_start, next_position)
            )
        )
    expected_view = (
        tuple(expected_windows),
        tuple(expected_starts),
        tuple(expected_next),
        tuple(expected_versions),
    )
    observed_view = (
        tuple(windows),
        tuple(starts),
        tuple(next_positions),
        tuple(versions),
    )
    if observed_view != expected_view:
        raise KVWindowReferenceError(
            "valid-view result does not exactly reconstruct from its source state"
        )

    valid_rows = sum(len(window) for window in expected_windows)
    if valid_rows != counters.valid_rows_returned:
        raise KVWindowReferenceError(
            "valid-view result source rows do not reconcile to counters"
        )
    expected_counter_dimensions = {
        "active_batch_count": active_count,
        "state_batch_capacity": capacity,
        "window_size": window_size,
        "kv_head_count": head_count,
        "kv_value_width": value_width,
    }
    for name, expected in expected_counter_dimensions.items():
        if getattr(counters, name) != expected:
            raise KVWindowReferenceError(
                f"valid-view result counters {name} does not match source state"
            )

    object.__setattr__(result, "state", state)
    object.__setattr__(result, "bf16_codes", tuple(windows))
    object.__setattr__(result, "session_ids", sessions)
    object.__setattr__(result, "absolute_position_starts", tuple(starts))
    object.__setattr__(result, "next_positions", tuple(next_positions))
    object.__setattr__(result, "versions", tuple(versions))
    object.__setattr__(result, "counters", counters)
    return result


def kv_window_write_bf16(
    state: KVWindowState,
    kv_bf16_codes: object,
    *,
    active_session_ids: object,
    expected_state_versions: object,
    start_pos: int,
) -> KVWindowWriteResult:
    """Commit one fresh prefill or causally exact one-token decode.

    Active lanes are the leading batch prefix, matching the source's
    ``self.kv_cache[:bsz]`` addressing. Omitting previously active trailing
    lanes retires them while retaining their identity tombstones.
    """

    (
        frozen,
        batch_capacity,
        window_size,
        head_count,
        value_width,
        previous_active_count,
    ) = _validate_state(state)
    _state_version_authority(expected_state_versions, frozen)
    sessions = _active_session_ids(
        active_session_ids,
        batch_capacity=batch_capacity,
        allow_empty=False,
    )
    batch_size = len(sessions)
    frozen_input, sequence_length = _validate_input(
        kv_bf16_codes,
        expected_batch_size=batch_size,
        head_count=head_count,
        value_width=value_width,
    )
    start_pos = _integer(
        start_pos,
        "start_pos",
        minimum=0,
        maximum=PINNED_MAX_POSITION - 1,
    )
    end_pos = start_pos + sequence_length
    if end_pos > PINNED_MAX_POSITION:
        raise KVWindowReferenceError(
            "KV_WINDOW_WRITE end position exceeds the pinned maximum position"
        )

    if start_pos == 0:
        retained_sessions = {
            session for session in frozen.session_ids if session is not None
        }
        if any(session in retained_sessions for session in sessions):
            raise KVWindowReferenceError(
                "fresh prefill requires a new identity for every active lane"
            )
    else:
        if batch_size > previous_active_count:
            raise KVWindowReferenceError(
                "decode cannot reactivate an inactive lane; fresh prefill required"
            )
        for batch_index, session in enumerate(sessions):
            if not frozen.lane_active[batch_index]:
                raise KVWindowReferenceError(
                    f"decode lane {batch_index} is not initialized and active"
                )
            if frozen.session_ids[batch_index] != session:
                raise KVWindowReferenceError(
                    f"decode session identity mismatch for lane {batch_index}"
                )
            observed_next = frozen.next_positions[batch_index]
            if observed_next != start_pos:
                raise KVWindowReferenceError(
                    f"decode start_pos for lane {batch_index} is {start_pos}, "
                    f"expected next_pos {observed_next}"
                )

    mode, segments, committed_positions, slice_assignments, modulo_evaluations = (
        _write_plan(
            start_pos=start_pos,
            sequence_length=sequence_length,
            window_size=window_size,
        )
    )
    removed_count = max(0, previous_active_count - batch_size)
    changed_lane_count = max(previous_active_count, batch_size)
    for batch_index in range(changed_lane_count):
        if frozen.versions[batch_index] == MAX_STATE_VERSION:
            raise KVWindowReferenceError(
                f"state version overflow for lane {batch_index}"
            )

    # Every state field, source value, session, cursor, version, and address
    # has now validated. Construction below is the single immutable commit.
    mutable_batches = [list(window) for window in frozen.bf16_codes]
    mutable_sessions = list(frozen.session_ids)
    mutable_active = list(frozen.lane_active)
    mutable_next = list(frozen.next_positions)
    mutable_versions = list(frozen.versions)

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

        if mode == "prefill":
            mutable_sessions[batch_index] = sessions[batch_index]
            mutable_active[batch_index] = True
        mutable_next[batch_index] = end_pos
        mutable_versions[batch_index] += 1

    for batch_index in range(batch_size, previous_active_count):
        mutable_active[batch_index] = False
        mutable_next[batch_index] = 0
        mutable_versions[batch_index] += 1

    committed_state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=tuple(tuple(window) for window in mutable_batches),
        session_ids=tuple(mutable_sessions),
        lane_active=tuple(mutable_active),
        next_positions=tuple(mutable_next),
        versions=tuple(mutable_versions),
    )
    committed_state = _validate_state(committed_state)[0]

    row_values = head_count * value_width
    input_rows = batch_size * sequence_length
    written_rows = batch_size * committed_positions
    state_rows = batch_capacity * window_size
    valid_before = _valid_window_rows(frozen, previous_active_count, window_size)
    valid_after = _valid_window_rows(committed_state, batch_size, window_size)
    if mode == "prefill":
        invalidated = valid_before
    else:
        retired_invalidated = sum(
            min(frozen.next_positions[batch_index], window_size)
            for batch_index in range(batch_size, previous_active_count)
        )
        overwritten_invalidated = batch_size if start_pos >= window_size else 0
        invalidated = retired_invalidated + overwritten_invalidated

    session_reads = batch_capacity if mode == "prefill" else batch_size
    active_reads = batch_capacity
    next_reads = previous_active_count if mode == "prefill" else previous_active_count
    version_reads = changed_lane_count
    session_writes = batch_size if mode == "prefill" else 0
    active_writes = changed_lane_count if mode == "prefill" else removed_count
    next_writes = batch_size + removed_count
    version_writes = changed_lane_count
    metadata_reads = session_reads + active_reads + next_reads + version_reads
    metadata_writes = session_writes + active_writes + next_writes + version_writes

    counters = KVWindowWriteCounters(
        active_batch_count=batch_size,
        previous_active_batch_count=previous_active_count,
        removed_batch_count=removed_count,
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
        valid_window_rows_before=valid_before,
        valid_window_rows_invalidated=invalidated,
        valid_window_rows_after=valid_after,
        source_slice_assignments=slice_assignments,
        nonempty_source_slice_assignments=len(segments),
        logical_slot_modulo_evaluations=modulo_evaluations,
        logical_session_ids_read=session_reads,
        logical_session_ids_written=session_writes,
        logical_lane_active_flags_read=active_reads,
        logical_lane_active_flags_written=active_writes,
        logical_next_positions_read=next_reads,
        logical_next_positions_written=next_writes,
        logical_versions_read=version_reads,
        logical_versions_written=version_writes,
        logical_metadata_fields_read=metadata_reads,
        logical_metadata_fields_written=metadata_writes,
        transaction_commits=1,
    )
    return KVWindowWriteResult(
        profile=KV_WINDOW_PROFILE,
        prior_state=frozen,
        input_bf16_codes=frozen_input,
        state=committed_state,
        mode=mode,
        start_pos=start_pos,
        end_pos=end_pos,
        active_session_ids=sessions,
        segments=segments,
        counters=counters,
    )


def kv_window_retire_bf16(
    state: KVWindowState,
    *,
    expected_state_versions: object,
    expected_active_session_ids: object,
    retired_session_ids: object,
) -> KVWindowRetireResult:
    """Atomically retire an exact nonempty trailing suffix of active lanes.

    The caller must identify the complete current active prefix, then identify
    the suffix to retire. Payload rows and session tombstones remain unchanged;
    each retired lane resets its cursor and advances its version exactly once.
    """

    (
        frozen,
        capacity,
        window_size,
        head_count,
        value_width,
        previous_active_count,
    ) = _validate_state(state)
    _state_version_authority(expected_state_versions, frozen)
    if previous_active_count == 0:
        raise KVWindowReferenceError("cannot retire lanes from an inactive state")
    expected_sessions = _session_ids(
        expected_active_session_ids,
        label="expected_active_session_ids",
        minimum=1,
        maximum=capacity,
    )
    if len(expected_sessions) != previous_active_count:
        raise KVWindowReferenceError(
            "expected_active_session_ids must identify every active state lane"
        )
    if frozen.session_ids[:previous_active_count] != expected_sessions:
        raise KVWindowReferenceError(
            "expected_active_session_ids do not match active state identities"
        )
    retired_sessions = _session_ids(
        retired_session_ids,
        label="retired_session_ids",
        minimum=1,
        maximum=previous_active_count,
    )
    retired_count = len(retired_sessions)
    if expected_sessions[-retired_count:] != retired_sessions:
        raise KVWindowReferenceError(
            "retired_session_ids must be an exact nonempty trailing suffix of "
            "the active sessions"
        )
    active_count = previous_active_count - retired_count
    active_sessions = expected_sessions[:active_count]
    retired_positions = frozen.next_positions[active_count:previous_active_count]
    retired_versions = frozen.versions[active_count:previous_active_count]
    for offset, version in enumerate(retired_versions):
        if version == MAX_STATE_VERSION:
            raise KVWindowReferenceError(
                f"state version overflow for lane {active_count + offset}"
            )

    # Every identity, cursor, version, and suffix boundary has validated.
    # Construction below is the single immutable metadata commit.
    mutable_active = list(frozen.lane_active)
    mutable_next = list(frozen.next_positions)
    mutable_versions = list(frozen.versions)
    for batch_index in range(active_count, previous_active_count):
        mutable_active[batch_index] = False
        mutable_next[batch_index] = 0
        mutable_versions[batch_index] += 1
    committed_state = KVWindowState(
        profile=KV_WINDOW_PROFILE,
        bf16_codes=frozen.bf16_codes,
        session_ids=frozen.session_ids,
        lane_active=tuple(mutable_active),
        next_positions=tuple(mutable_next),
        versions=tuple(mutable_versions),
    )

    row_values = head_count * value_width
    state_rows = capacity * window_size
    valid_before = _valid_window_rows(frozen, previous_active_count, window_size)
    invalidated = sum(min(position, window_size) for position in retired_positions)
    valid_after = _valid_window_rows(committed_state, active_count, window_size)
    metadata_reads = capacity + 2 * previous_active_count + retired_count
    metadata_writes = 3 * retired_count
    counters = KVWindowRetireCounters(
        previous_active_batch_count=previous_active_count,
        active_batch_count=active_count,
        retired_batch_count=retired_count,
        state_batch_capacity=capacity,
        window_size=window_size,
        kv_head_count=head_count,
        kv_value_width=value_width,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=0,
        logical_state_bf16_values_written=0,
        logical_state_write_bytes=0,
        state_rows_preserved=state_rows,
        state_bf16_values_preserved=state_rows * row_values,
        valid_window_rows_before=valid_before,
        valid_window_rows_invalidated=invalidated,
        valid_window_rows_after=valid_after,
        logical_session_ids_read=previous_active_count,
        logical_session_ids_written=0,
        logical_lane_active_flags_read=capacity,
        logical_lane_active_flags_written=retired_count,
        logical_next_positions_read=previous_active_count,
        logical_next_positions_written=retired_count,
        logical_versions_read=retired_count,
        logical_versions_written=retired_count,
        logical_metadata_fields_read=metadata_reads,
        logical_metadata_fields_written=metadata_writes,
        transaction_commits=1,
    )
    return KVWindowRetireResult(
        profile=KV_WINDOW_RETIRE_PROFILE,
        prior_state=frozen,
        state=committed_state,
        previous_active_session_ids=expected_sessions,
        active_session_ids=active_sessions,
        retired_session_ids=retired_sessions,
        retired_next_positions=retired_positions,
        retired_previous_versions=retired_versions,
        counters=counters,
    )


def kv_window_valid_view_bf16(
    state: KVWindowState,
    *,
    expected_state_versions: object,
    active_session_ids: object,
) -> KVWindowValidViewResult:
    """Return only exact active sessions' chronological committed windows."""

    frozen, batch_capacity, window_size, head_count, value_width, active_count = (
        _validate_state(state)
    )
    _state_version_authority(expected_state_versions, frozen)
    sessions = _active_session_ids(
        active_session_ids,
        batch_capacity=batch_capacity,
        allow_empty=True,
    )
    if len(sessions) != active_count:
        raise KVWindowReferenceError(
            "active_session_ids must exactly identify every active state lane"
        )

    windows: list[BF16Window] = []
    absolute_starts: list[int] = []
    next_positions: list[int] = []
    versions: list[int] = []
    modulo_evaluations = 0
    for batch_index, session in enumerate(sessions):
        if not frozen.lane_active[batch_index]:
            raise KVWindowReferenceError(f"valid view lane {batch_index} is not active")
        if frozen.session_ids[batch_index] != session:
            raise KVWindowReferenceError(
                f"valid view session identity mismatch for lane {batch_index}"
            )
        next_position = frozen.next_positions[batch_index]
        valid_count = min(next_position, window_size)
        absolute_start = next_position - valid_count
        windows.append(
            tuple(
                frozen.bf16_codes[batch_index][position % window_size]
                for position in range(absolute_start, next_position)
            )
        )
        modulo_evaluations += valid_count
        absolute_starts.append(absolute_start)
        next_positions.append(next_position)
        versions.append(frozen.versions[batch_index])

    valid_rows = sum(len(window) for window in windows)
    valid_values = valid_rows * head_count * value_width
    active_capacity_rows = active_count * window_size
    inactive_capacity_rows = (batch_capacity - active_count) * window_size
    metadata_reads = batch_capacity + 3 * active_count
    counters = KVWindowValidViewCounters(
        active_batch_count=active_count,
        state_batch_capacity=batch_capacity,
        window_size=window_size,
        kv_head_count=head_count,
        kv_value_width=value_width,
        logical_session_ids_read=active_count,
        logical_lane_active_flags_read=batch_capacity,
        logical_next_positions_read=active_count,
        logical_versions_read=active_count,
        logical_metadata_fields_read=metadata_reads,
        logical_state_rows_read=valid_rows,
        logical_state_bf16_values_read=valid_values,
        logical_state_read_bytes=valid_values * BF16_BYTES,
        logical_slot_modulo_evaluations=modulo_evaluations,
        valid_rows_returned=valid_rows,
        active_capacity_rows_excluded=active_capacity_rows - valid_rows,
        inactive_capacity_rows_excluded=inactive_capacity_rows,
        total_state_rows_not_exposed=(batch_capacity * window_size) - valid_rows,
        view_evaluations=1,
        transaction_commits=0,
    )
    return KVWindowValidViewResult(
        profile=KV_WINDOW_VALID_VIEW_PROFILE,
        state=frozen,
        bf16_codes=tuple(windows),
        session_ids=sessions,
        absolute_position_starts=tuple(absolute_starts),
        next_positions=tuple(next_positions),
        versions=tuple(versions),
        counters=counters,
    )


__all__ = [
    "BF16_BYTES",
    "BF16_MAX_ENCODING",
    "EXCLUDED_CLAIMS",
    "INFERENCE_CONFIG_PATH",
    "INFERENCE_CONFIG_SHA256",
    "INFERENCE_DRIVER_INTERACTIVE_MAX_SEQUENCE_LENGTH",
    "INFERENCE_DRIVER_PATH",
    "INFERENCE_DRIVER_SHA256",
    "INFERENCE_SOURCE_DEFAULT_MAX_SEQUENCE_LENGTH",
    "KV_WINDOW_PROFILE",
    "KV_WINDOW_RETIRE_PROFILE",
    "KV_WINDOW_VALID_VIEW_PROFILE",
    "MAX_STATE_VERSION",
    "MODEL_REPOSITORY",
    "MODEL_REVISION",
    "MODEL_CONFIG_MAX_POSITION_ANCHOR",
    "MODEL_CONFIG_MAX_POSITION_EMBEDDINGS",
    "MODEL_CONFIG_MAX_POSITION_FIELD",
    "MODEL_CONFIG_PATH",
    "MODEL_CONFIG_SHA256",
    "MODEL_SOURCE_PATH",
    "MODEL_SOURCE_SHA256",
    "PINNED_KV_HEAD_COUNT",
    "PINNED_KV_ROW_WIDTH",
    "PINNED_KV_VALUE_WIDTH",
    "PINNED_MAX_BATCH_SIZE",
    "PINNED_MAX_POSITION",
    "PINNED_QUERY_HEAD_COUNT",
    "PINNED_WINDOW_SIZE",
    "SESSION_ID_HEX_DIGITS",
    "SOURCE_ASSIGNMENTS",
    "BF16HeadRow",
    "BF16InputSequence",
    "BF16InputTensor",
    "BF16ValidWindowTensor",
    "BF16Vector",
    "BF16Window",
    "BF16WindowTensor",
    "KVWindowMode",
    "KVWindowReferenceError",
    "KVWindowRetireCounters",
    "KVWindowRetireResult",
    "KVWindowState",
    "KVWindowValidViewCounters",
    "KVWindowValidViewResult",
    "KVWindowWriteCounters",
    "KVWindowWriteResult",
    "KVWindowWriteSegment",
    "kv_window_state_bf16",
    "kv_window_retire_bf16",
    "kv_window_valid_view_bf16",
    "kv_window_write_bf16",
    "zero_kv_window_state_bf16",
]
