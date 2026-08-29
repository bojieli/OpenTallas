from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
import inspect

import pytest

from runtime.reference import compressed_kv as compressed_kv_module
from runtime.reference.compressed_kv import (
    BF16_BYTES,
    COMPRESSED_KV_PROFILE,
    COMPRESSED_KV_VALID_VIEW_PROFILE,
    EXCLUDED_CLAIMS,
    INFERENCE_CONFIG_SHA256,
    MAX_STATE_VERSION,
    MODEL_SOURCE_SHA256,
    PINNED_COMPRESSION_RATIOS,
    PINNED_INDEX_HEAD_DIM,
    PINNED_MAIN_HEAD_DIM,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    SESSION_ID_HEX_DIGITS,
    CompressedKVReferenceError,
    CompressedKVState,
    CompressedKVValidViewCounters,
    CompressedKVValidViewResult,
    CompressedKVWriteCounters,
    CompressedKVWriteResult,
    compressed_kv_state_bf16,
    compressed_kv_valid_view_bf16,
    compressed_kv_write_bf16,
    zero_compressed_kv_state_bf16,
)
from runtime.reference.formats import binary32_bits_to_bf16_rne, encode_binary32_rne


class _ListSubclass(list):
    pass


class _StateSubclass(CompressedKVState):
    pass


def _session(index: int) -> str:
    return f"{index:0{SESSION_ID_HEX_DIGITS}x}"


SESSION_A = _session(0xA)
SESSION_B = _session(0xB)
SESSION_C = _session(0xC)
SESSION_D = _session(0xD)


def _bf16(value: int) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _head_row(*values: int) -> tuple[tuple[int, ...], ...]:
    return (tuple(_bf16(value) for value in values),)


def _one_batch_rows(*rows: tuple[int, ...]) -> tuple:
    return (tuple(_head_row(*row) for row in rows),)


def _empty_batches(count: int) -> tuple[tuple[()], ...]:
    return ((),) * count


def _two_batch_rows(
    first: tuple[tuple[int, ...], ...],
    second: tuple[tuple[int, ...], ...],
) -> tuple:
    return (
        tuple(_head_row(*row) for row in first),
        tuple(_head_row(*row) for row in second),
    )


def _tagged_payload(
    *,
    batches: int,
    capacity: int,
    width: int,
) -> tuple:
    return tuple(
        tuple(
            (
                tuple(
                    _bf16(100 * batch + 10 * slot + column + 1)
                    for column in range(width)
                ),
            )
            for slot in range(capacity)
        )
        for batch in range(batches)
    )


def _tagged_state(
    *,
    ratio: int = 4,
    batches: int = 2,
    capacity: int = 4,
    width: int = 2,
    session_ids: tuple[str | None, ...] = (SESSION_A, SESSION_B),
    lane_active: tuple[bool, ...] = (True, True),
    next_positions: tuple[int, ...] = (12, 4),
    valid_prefix_lengths: tuple[int, ...] = (3, 1),
    versions: tuple[int, ...] = (5, 7),
) -> CompressedKVState:
    return compressed_kv_state_bf16(
        CompressedKVState(
            ratio=ratio,
            bf16_codes=_tagged_payload(
                batches=batches,
                capacity=capacity,
                width=width,
            ),
            session_ids=session_ids,
            lane_active=lane_active,
            next_positions=next_positions,
            valid_prefix_lengths=valid_prefix_lengths,
            versions=versions,
        )
    )


def _prefill(
    state: CompressedKVState,
    *,
    sessions: tuple[str, ...],
    sequence_length: int,
    rows: object,
) -> CompressedKVWriteResult:
    return compressed_kv_write_bf16(
        state,
        rows,
        active_session_ids=sessions,
        start_pos=0,
        sequence_length=sequence_length,
    )


def _decode(
    state: CompressedKVState,
    *,
    sessions: tuple[str, ...],
    start_pos: int,
    rows: object,
) -> CompressedKVWriteResult:
    return compressed_kv_write_bf16(
        state,
        rows,
        active_session_ids=sessions,
        start_pos=start_pos,
        sequence_length=1,
    )


def test_contract_is_bound_to_pinned_source_profiles_and_nonclaims() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert COMPRESSED_KV_PROFILE == "opentallas.deepseek_v4_compressed_kv_write.v2"
    assert COMPRESSED_KV_VALID_VIEW_PROFILE == (
        "opentallas.deepseek_v4_compressed_kv_valid_view.v1"
    )
    assert PINNED_COMPRESSION_RATIOS == (4, 128)
    assert PINNED_MAIN_HEAD_DIM == 512
    assert PINNED_INDEX_HEAD_DIM == 128
    assert PINNED_MAX_BATCH_SIZE == 4
    assert PINNED_MAX_POSITION == 1_048_576
    assert BF16_BYTES == 2
    assert SESSION_ID_HEX_DIGITS == 64
    assert MAX_STATE_VERSION == (1 << 64) - 1
    assert set(EXCLUDED_CLAIMS) == {
        "compression_numeric_operators",
        "checkpoint_or_artifact_loading",
        "scheduler_or_service_execution",
        "physical_hbm_or_sram_transactions",
        "cycles_latency_throughput_energy_area_routing_ppa",
        "end_to_end_model_execution",
    }


def test_state_uses_one_authoritative_prefix_not_a_duplicate_bitmap() -> None:
    assert [field.name for field in fields(CompressedKVState)] == [
        "ratio",
        "bf16_codes",
        "session_ids",
        "lane_active",
        "next_positions",
        "valid_prefix_lengths",
        "versions",
    ]
    source = inspect.getsource(compressed_kv_module)
    assert "ValidityTensor" not in source
    assert "validity bitmap" in source


def test_zero_state_has_explicit_uninitialized_metadata_and_immutability() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=3,
        kv_head_count=2,
        kv_value_width=4,
        batch_capacity=2,
    )
    assert len(state.bf16_codes) == 2
    assert len(state.bf16_codes[0]) == 3
    assert len(state.bf16_codes[0][0]) == 2
    assert state.bf16_codes[0][0][0] == (0,) * 4
    assert state.session_ids == (None, None)
    assert state.lane_active == (False, False)
    assert state.next_positions == (0, 0)
    assert state.valid_prefix_lengths == (0, 0)
    assert state.versions == (0, 0)
    with pytest.raises(FrozenInstanceError):
        state.ratio = 128  # type: ignore[misc]


def test_empty_valid_view_of_zero_state_exposes_no_capacity_rows() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=3,
        kv_value_width=2,
        batch_capacity=2,
    )
    view = compressed_kv_valid_view_bf16(state, active_session_ids=())
    assert view.bf16_codes == ()
    assert view.session_ids == ()
    assert view.next_positions == ()
    assert view.valid_prefix_lengths == ()
    assert view.versions == ()
    assert view.counters.valid_rows_returned == 0
    assert view.counters.inactive_capacity_rows_excluded == 6
    assert view.counters.total_state_rows_not_exposed == 6
    assert view.counters.transaction_commits == 0


@pytest.mark.parametrize(
    ("sequence_length", "expected_rows", "slots"),
    [
        (1, 0, ()),
        (3, 0, ()),
        (4, 1, (0,)),
        (10, 2, (0, 1)),
        (16, 4, (0, 1, 2, 3)),
    ],
)
def test_new_session_prefill_commits_complete_groups_and_sets_causal_metadata(
    sequence_length: int,
    expected_rows: int,
    slots: tuple[int, ...],
) -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=4,
        kv_value_width=2,
        batch_capacity=1,
    )
    source = _one_batch_rows(
        *(tuple((10 * row + 1, 10 * row + 2)) for row in range(expected_rows))
    )
    result = _prefill(
        state,
        sessions=(SESSION_A,),
        sequence_length=sequence_length,
        rows=source,
    )
    assert result.mode == "prefill"
    assert result.cache_slots == slots
    assert result.start_pos == 0
    assert result.end_pos == sequence_length
    assert result.active_session_ids == (SESSION_A,)
    assert result.state.session_ids == (SESSION_A,)
    assert result.state.lane_active == (True,)
    assert result.state.next_positions == (sequence_length,)
    assert result.state.valid_prefix_lengths == (expected_rows,)
    assert result.state.versions == (1,)
    assert result.state.bf16_codes[0][:expected_rows] == source[0]
    assert result.counters.completed_rows_per_batch == expected_rows
    assert result.counters.logical_source_rows_read == expected_rows
    assert result.counters.logical_state_rows_written == expected_rows
    assert result.counters.logical_source_read_bytes == expected_rows * 4
    assert result.counters.logical_state_write_bytes == expected_rows * 4
    view = compressed_kv_valid_view_bf16(
        result.state,
        active_session_ids=(SESSION_A,),
    )
    assert view.bf16_codes == (source[0],)
    assert view.next_positions == (sequence_length,)
    assert view.valid_prefix_lengths == (expected_rows,)
    assert view.versions == (1,)


def test_ratio_128_prefill_uses_floor_division_and_absolute_cursor() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=128,
        cache_capacity=3,
        kv_value_width=1,
        batch_capacity=1,
    )
    result = _prefill(
        state,
        sessions=(SESSION_A,),
        sequence_length=300,
        rows=_one_batch_rows((1,), (2,)),
    )
    assert result.cache_slots == (0, 1)
    assert result.state.next_positions == (300,)
    assert result.state.valid_prefix_lengths == (2,)
    assert result.end_pos == 300


def test_dirty_short_prefill_resets_validity_but_preserves_stale_payload_bits() -> None:
    state = _tagged_state()
    before = deepcopy(state)
    result = _prefill(
        state,
        sessions=(SESSION_C,),
        sequence_length=1,
        rows=_empty_batches(1),
    )

    assert state == before
    assert result.state.bf16_codes == before.bf16_codes
    assert result.state.session_ids == (SESSION_C, SESSION_B)
    assert result.state.lane_active == (True, False)
    assert result.state.next_positions == (1, 0)
    assert result.state.valid_prefix_lengths == (0, 0)
    assert result.state.versions == (6, 8)
    assert result.counters.valid_rows_before == 4
    assert result.counters.valid_rows_invalidated == 4
    assert result.counters.valid_rows_after == 0

    view = compressed_kv_valid_view_bf16(
        result.state,
        active_session_ids=(SESSION_C,),
    )
    assert view.bf16_codes == ((),)
    assert view.counters.valid_rows_returned == 0
    assert view.counters.total_state_rows_not_exposed == 8
    assert result.state.bf16_codes[0][0] != ((0, 0),)


def test_prefill_invalidates_old_prefix_writes_new_rows_and_counts_metadata() -> None:
    state = _tagged_state()
    before = deepcopy(state)
    source = _one_batch_rows((1, 2), (3, 4))
    result = _prefill(
        state,
        sessions=(SESSION_C,),
        sequence_length=10,
        rows=source,
    )

    assert state == before
    assert result.state.bf16_codes[0][:2] == source[0]
    assert result.state.bf16_codes[0][2:] == before.bf16_codes[0][2:]
    assert result.state.bf16_codes[1] == before.bf16_codes[1]
    assert result.state.session_ids == (SESSION_C, SESSION_B)
    assert result.state.lane_active == (True, False)
    assert result.state.next_positions == (10, 0)
    assert result.state.valid_prefix_lengths == (2, 0)
    assert result.state.versions == (6, 8)
    assert result.counters == CompressedKVWriteCounters(
        active_batch_count=1,
        previous_active_batch_count=2,
        removed_batch_count=1,
        state_batch_capacity=2,
        sequence_length=10,
        ratio=4,
        cache_capacity=4,
        kv_head_count=1,
        kv_value_width=2,
        completed_rows_per_batch=2,
        logical_source_rows_read=2,
        logical_source_bf16_values_read=4,
        logical_source_read_bytes=8,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=2,
        logical_state_bf16_values_written=4,
        logical_state_write_bytes=8,
        state_rows_preserved=6,
        state_bf16_values_preserved=12,
        valid_rows_before=4,
        valid_rows_invalidated=4,
        valid_rows_after=2,
        logical_session_ids_read=2,
        logical_session_ids_written=1,
        logical_lane_active_flags_read=2,
        logical_lane_active_flags_written=2,
        logical_next_positions_read=0,
        logical_next_positions_written=2,
        logical_valid_prefix_lengths_read=2,
        logical_valid_prefix_lengths_written=2,
        logical_versions_read=2,
        logical_versions_written=2,
        logical_metadata_fields_read=8,
        logical_metadata_fields_written=9,
        transaction_commits=1,
    )


def test_decode_advances_cursor_and_version_on_every_nonboundary_token() -> None:
    initial = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=4,
        kv_value_width=2,
        batch_capacity=1,
    )
    prefill = _prefill(
        initial,
        sessions=(SESSION_A,),
        sequence_length=5,
        rows=_one_batch_rows((1, 2)),
    )
    current = prefill.state

    for expected_version, start_pos in ((2, 5), (3, 6)):
        before = current
        result = _decode(
            current,
            sessions=(SESSION_A,),
            start_pos=start_pos,
            rows=_empty_batches(1),
        )
        assert result.mode == "decode"
        assert result.cache_slots == ()
        assert result.state != before
        assert result.state.next_positions == (start_pos + 1,)
        assert result.state.valid_prefix_lengths == (1,)
        assert result.state.versions == (expected_version,)
        assert result.counters.completed_rows_per_batch == 0
        assert result.counters.logical_state_rows_written == 0
        assert result.counters.logical_next_positions_written == 1
        assert result.counters.logical_valid_prefix_lengths_written == 0
        assert result.counters.logical_versions_written == 1
        assert result.counters.logical_metadata_fields_read == 5
        assert result.counters.logical_metadata_fields_written == 2
        current = result.state

    boundary = _decode(
        current,
        sessions=(SESSION_A,),
        start_pos=7,
        rows=_one_batch_rows((7, 8)),
    )
    assert boundary.cache_slots == (1,)
    assert boundary.state.next_positions == (8,)
    assert boundary.state.valid_prefix_lengths == (2,)
    assert boundary.state.versions == (4,)
    assert boundary.state.bf16_codes[0][1] == _head_row(7, 8)
    assert boundary.counters.logical_valid_prefix_lengths_written == 1
    assert boundary.counters.logical_metadata_fields_written == 3


def test_skipped_and_replayed_positions_in_the_same_window_fail_atomically() -> None:
    initial = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=3,
        kv_value_width=1,
        batch_capacity=1,
    )
    current = _prefill(
        initial,
        sessions=(SESSION_A,),
        sequence_length=5,
        rows=_one_batch_rows((1,)),
    ).state
    before = deepcopy(current)
    for invalid_pos in (4, 6, 7):
        with pytest.raises(CompressedKVReferenceError, match="expected next_pos 5"):
            _decode(
                current,
                sessions=(SESSION_A,),
                start_pos=invalid_pos,
                rows=_empty_batches(1),
            )
        assert current == before

    advanced = _decode(
        current,
        sessions=(SESSION_A,),
        start_pos=5,
        rows=_empty_batches(1),
    ).state
    advanced_before = deepcopy(advanced)
    with pytest.raises(CompressedKVReferenceError, match="expected next_pos 6"):
        _decode(
            advanced,
            sessions=(SESSION_A,),
            start_pos=5,
            rows=_empty_batches(1),
        )
    assert advanced == advanced_before


def test_session_mismatch_and_same_session_prefill_reuse_fail_atomically() -> None:
    initial = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=1,
    )
    current = _prefill(
        initial,
        sessions=(SESSION_A,),
        sequence_length=4,
        rows=_one_batch_rows((1,)),
    ).state
    before = deepcopy(current)
    with pytest.raises(CompressedKVReferenceError, match="session identity mismatch"):
        _decode(
            current,
            sessions=(SESSION_B,),
            start_pos=4,
            rows=_empty_batches(1),
        )
    with pytest.raises(CompressedKVReferenceError, match="fresh identity"):
        _prefill(
            current,
            sessions=(SESSION_A,),
            sequence_length=1,
            rows=_empty_batches(1),
        )
    assert current == before


def test_lane_remove_and_readd_requires_a_fresh_session_identity() -> None:
    initial = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=3,
        kv_value_width=1,
        batch_capacity=2,
    )
    current = _prefill(
        initial,
        sessions=(SESSION_A, SESSION_B),
        sequence_length=4,
        rows=_two_batch_rows(((1,),), ((2,),)),
    ).state
    removed = _decode(
        current,
        sessions=(SESSION_A,),
        start_pos=4,
        rows=_empty_batches(1),
    )
    assert removed.state.session_ids == (SESSION_A, SESSION_B)
    assert removed.state.lane_active == (True, False)
    assert removed.state.next_positions == (5, 0)
    assert removed.state.valid_prefix_lengths == (1, 0)
    assert removed.state.versions == (2, 2)
    assert removed.counters.removed_batch_count == 1
    assert removed.counters.valid_rows_invalidated == 1

    with pytest.raises(CompressedKVReferenceError, match="cannot reactivate"):
        _decode(
            removed.state,
            sessions=(SESSION_A, SESSION_B),
            start_pos=5,
            rows=_empty_batches(2),
        )
    with pytest.raises(CompressedKVReferenceError, match="fresh identity"):
        _prefill(
            removed.state,
            sessions=(SESSION_C, SESSION_B),
            sequence_length=1,
            rows=_empty_batches(2),
        )

    readded = _prefill(
        removed.state,
        sessions=(SESSION_C, SESSION_D),
        sequence_length=1,
        rows=_empty_batches(2),
    )
    assert readded.state.session_ids == (SESSION_C, SESSION_D)
    assert readded.state.lane_active == (True, True)
    assert readded.state.next_positions == (1, 1)
    assert readded.state.valid_prefix_lengths == (0, 0)
    assert readded.state.versions == (3, 3)


def test_multiple_active_batches_commit_and_preserve_inactive_capacity() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=3,
    )
    result = _prefill(
        state,
        sessions=(SESSION_A, SESSION_B),
        sequence_length=4,
        rows=_two_batch_rows(((1,),), ((2,),)),
    )
    assert result.state.bf16_codes[0][0] == _head_row(1)
    assert result.state.bf16_codes[1][0] == _head_row(2)
    assert result.state.bf16_codes[2] == state.bf16_codes[2]
    assert result.state.session_ids == (SESSION_A, SESSION_B, None)
    assert result.state.lane_active == (True, True, False)
    assert result.state.next_positions == (4, 4, 0)
    assert result.state.valid_prefix_lengths == (1, 1, 0)
    assert result.state.versions == (1, 1, 0)


def test_valid_view_never_exposes_stale_capacity_or_inactive_lane_payload() -> None:
    state = _tagged_state(
        batches=3,
        session_ids=(SESSION_A, SESSION_B, SESSION_C),
        lane_active=(True, True, False),
        next_positions=(12, 4, 0),
        valid_prefix_lengths=(3, 1, 0),
        versions=(5, 7, 9),
    )
    view = compressed_kv_valid_view_bf16(
        state,
        active_session_ids=(SESSION_A, SESSION_B),
    )
    assert view.numeric_profile == COMPRESSED_KV_VALID_VIEW_PROFILE
    assert view.bf16_codes == (
        state.bf16_codes[0][:3],
        state.bf16_codes[1][:1],
    )
    assert view.bf16_codes[0][-1] == state.bf16_codes[0][2]
    assert state.bf16_codes[0][3] not in view.bf16_codes[0]
    assert state.bf16_codes[1][1] not in view.bf16_codes[1]
    assert state.bf16_codes[2][0] not in tuple(
        row for batch in view.bf16_codes for row in batch
    )
    assert view.session_ids == (SESSION_A, SESSION_B)
    assert view.next_positions == (12, 4)
    assert view.valid_prefix_lengths == (3, 1)
    assert view.versions == (5, 7)
    assert view.counters == CompressedKVValidViewCounters(
        active_batch_count=2,
        state_batch_capacity=3,
        ratio=4,
        cache_capacity=4,
        kv_head_count=1,
        kv_value_width=2,
        logical_session_ids_read=2,
        logical_lane_active_flags_read=3,
        logical_next_positions_read=2,
        logical_valid_prefix_lengths_read=2,
        logical_versions_read=2,
        logical_metadata_fields_read=11,
        logical_state_rows_read=4,
        logical_state_bf16_values_read=8,
        logical_state_read_bytes=16,
        valid_rows_returned=4,
        active_capacity_rows_excluded=4,
        inactive_capacity_rows_excluded=4,
        total_state_rows_not_exposed=8,
        view_evaluations=1,
        transaction_commits=0,
    )


def test_valid_view_requires_the_exact_complete_active_session_vector() -> None:
    state = _tagged_state()
    for invalid, message in (
        ((SESSION_A,), "exactly identify every active"),
        ((SESSION_A, SESSION_B, SESSION_C), "outside state batch capacity"),
        ((SESSION_B, SESSION_A), "identity mismatch"),
        ((SESSION_A, SESSION_C), "identity mismatch"),
        ((SESSION_A, SESSION_A), "unique"),
    ):
        with pytest.raises(CompressedKVReferenceError, match=message):
            compressed_kv_valid_view_bf16(
                state,
                active_session_ids=invalid,
            )


def test_invalid_capacity_prefix_or_cursor_can_never_reach_valid_view() -> None:
    valid = _tagged_state(
        batches=1,
        session_ids=(SESSION_A,),
        lane_active=(True,),
        next_positions=(4,),
        valid_prefix_lengths=(1,),
        versions=(1,),
    )
    for forged, message in (
        (replace(valid, valid_prefix_lengths=(4,)), "expected floor"),
        (replace(valid, valid_prefix_lengths=(5,)), "integer in"),
        (replace(valid, next_positions=(17,)), "integer in"),
    ):
        before = deepcopy(forged)
        with pytest.raises(CompressedKVReferenceError, match=message):
            compressed_kv_valid_view_bf16(
                forged,
                active_session_ids=(SESSION_A,),
            )
        assert forged == before


def test_view_result_and_nested_payload_are_deeply_immutable() -> None:
    state = _tagged_state(
        batches=1,
        session_ids=(SESSION_A,),
        lane_active=(True,),
        next_positions=(4,),
        valid_prefix_lengths=(1,),
        versions=(1,),
    )
    view = compressed_kv_valid_view_bf16(
        state,
        active_session_ids=(SESSION_A,),
    )
    assert type(view) is CompressedKVValidViewResult
    assert type(view.bf16_codes) is tuple
    assert type(view.bf16_codes[0][0][0]) is tuple
    with pytest.raises(FrozenInstanceError):
        view.ratio = 128  # type: ignore[misc]
    with pytest.raises(TypeError):
        view.bf16_codes[0][0][0][0][0] = 0  # type: ignore[index]


@pytest.mark.parametrize(
    "invalid",
    (
        None,
        1,
        True,
        "a" * 63,
        "a" * 65,
        "A" * 64,
        "g" * 64,
        b"a" * 64,
    ),
)
def test_session_identity_is_strict_canonical_lowercase_hex(invalid: object) -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=1,
        kv_value_width=1,
        batch_capacity=1,
    )
    with pytest.raises(CompressedKVReferenceError, match="64 lowercase hex"):
        _prefill(
            state,
            sessions=(invalid,),  # type: ignore[arg-type]
            sequence_length=1,
            rows=_empty_batches(1),
        )


def test_active_session_and_payload_batch_extents_must_match_exactly() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=2,
    )
    with pytest.raises(CompressedKVReferenceError, match="exactly match"):
        _prefill(
            state,
            sessions=(SESSION_A, SESSION_B),
            sequence_length=1,
            rows=_empty_batches(1),
        )
    with pytest.raises(CompressedKVReferenceError, match="unique"):
        _prefill(
            state,
            sessions=(SESSION_A, SESSION_A),
            sequence_length=1,
            rows=_empty_batches(2),
        )
    with pytest.raises(CompressedKVReferenceError, match="at least one lane"):
        _prefill(
            state,
            sessions=(),
            sequence_length=1,
            rows=(),
        )


@pytest.mark.parametrize(
    ("mutator", "message"),
    (
        (lambda state: replace(state, session_ids=()), "extent must match"),
        (lambda state: replace(state, lane_active=(True,)), "extent must match"),
        (lambda state: replace(state, next_positions=(0,)), "extent must match"),
        (
            lambda state: replace(state, valid_prefix_lengths=(0,)),
            "extent must match",
        ),
        (lambda state: replace(state, versions=(0,)), "extent must match"),
        (
            lambda state: replace(
                state,
                session_ids=(SESSION_A, SESSION_A),
                versions=(1, 1),
            ),
            "unique across lanes",
        ),
        (
            lambda state: replace(state, lane_active=(False, True)),
            "contiguous prefix",
        ),
        (
            lambda state: replace(
                state,
                session_ids=(None, None),
                lane_active=(True, False),
                next_positions=(1, 0),
                versions=(1, 0),
            ),
            "must have a session identity",
        ),
        (
            lambda state: replace(
                state,
                session_ids=(SESSION_A, None),
                lane_active=(True, False),
                next_positions=(1, 0),
                versions=(0, 0),
            ),
            "nonzero version",
        ),
        (
            lambda state: replace(
                state,
                session_ids=(SESSION_A, None),
                lane_active=(True, False),
                next_positions=(0, 0),
                versions=(1, 0),
            ),
            "initialized by prefill",
        ),
        (
            lambda state: replace(
                state,
                session_ids=(SESSION_A, None),
                lane_active=(True, False),
                next_positions=(5, 0),
                valid_prefix_lengths=(0, 0),
                versions=(1, 0),
            ),
            "expected floor",
        ),
        (
            lambda state: replace(
                state,
                session_ids=(SESSION_A, None),
                lane_active=(False, False),
                next_positions=(1, 0),
                versions=(1, 0),
            ),
            "zero cursor and prefix",
        ),
        (
            lambda state: replace(state, versions=(1, 0)),
            "never-initialized",
        ),
        (
            lambda state: replace(state, session_ids=(SESSION_A, None)),
            "retired.*nonzero version",
        ),
    ),
)
def test_state_metadata_invariants_fail_closed(mutator, message: str) -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=2,
    )
    forged = mutator(state)
    before = deepcopy(forged)
    with pytest.raises(CompressedKVReferenceError, match=message):
        compressed_kv_state_bf16(forged)
    assert forged == before


def test_version_overflow_and_cursor_capacity_overflow_poison_atomically() -> None:
    max_version = _tagged_state(
        batches=1,
        capacity=2,
        width=1,
        session_ids=(SESSION_A,),
        lane_active=(True,),
        next_positions=(4,),
        valid_prefix_lengths=(1,),
        versions=(MAX_STATE_VERSION,),
    )
    before_version = deepcopy(max_version)
    with pytest.raises(CompressedKVReferenceError, match="version overflow"):
        _decode(
            max_version,
            sessions=(SESSION_A,),
            start_pos=4,
            rows=_empty_batches(1),
        )
    assert max_version == before_version

    full = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=1,
        kv_value_width=1,
        batch_capacity=1,
    )
    full = _prefill(
        full,
        sessions=(SESSION_A,),
        sequence_length=4,
        rows=_one_batch_rows((1,)),
    ).state
    before_cursor = deepcopy(full)
    with pytest.raises(CompressedKVReferenceError, match="cursor exceeds"):
        _decode(
            full,
            sessions=(SESSION_A,),
            start_pos=4,
            rows=_empty_batches(1),
        )
    assert full == before_cursor


def test_poisoned_payload_and_shape_leave_old_state_cursor_and_version_unchanged() -> (
    None
):
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=1,
    )
    state = _prefill(
        state,
        sessions=(SESSION_A,),
        sequence_length=3,
        rows=_empty_batches(1),
    ).state
    before = deepcopy(state)
    operations = (
        lambda: _decode(
            state,
            sessions=(SESSION_A,),
            start_pos=3,
            rows=((((0x7F80,),),),),
        ),
        lambda: _decode(
            state,
            sessions=(SESSION_A,),
            start_pos=3,
            rows=_empty_batches(1),
        ),
        lambda: compressed_kv_write_bf16(
            state,
            _one_batch_rows((1,)),
            active_session_ids=(SESSION_A,),
            start_pos=3,
            sequence_length=2,
        ),
    )
    matches = ("finite BF16", "exactly 1 completed rows", "exactly 1")
    for operation, message in zip(operations, matches, strict=True):
        with pytest.raises(CompressedKVReferenceError, match=message):
            operation()
        assert state == before
        assert state.next_positions == (3,)
        assert state.versions == (1,)


def test_caller_lists_are_not_mutated_and_committed_state_is_deeply_immutable() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=2,
        batch_capacity=1,
    )
    rows = [[[[_bf16(1), _bf16(2)]]]]
    sessions = [SESSION_A]
    rows_before = deepcopy(rows)
    sessions_before = deepcopy(sessions)
    result = compressed_kv_write_bf16(
        state,
        rows,
        active_session_ids=sessions,
        start_pos=0,
        sequence_length=4,
    )
    assert rows == rows_before
    assert sessions == sessions_before
    assert result.state.bf16_codes[0][0] == _head_row(1, 2)
    with pytest.raises(FrozenInstanceError):
        result.state.versions = (99,)  # type: ignore[misc]
    with pytest.raises(TypeError):
        result.state.bf16_codes[0][0][0][0] = 0  # type: ignore[index]


def test_result_dataclasses_and_counter_fields_are_explicit() -> None:
    assert [field.name for field in fields(CompressedKVWriteResult)] == [
        "state",
        "mode",
        "cache_slots",
        "start_pos",
        "end_pos",
        "active_session_ids",
        "counters",
    ]
    assert len(fields(CompressedKVWriteCounters)) == 37
    assert [field.name for field in fields(CompressedKVValidViewResult)] == [
        "numeric_profile",
        "ratio",
        "bf16_codes",
        "session_ids",
        "next_positions",
        "valid_prefix_lengths",
        "versions",
        "counters",
    ]
    assert len(fields(CompressedKVValidViewCounters)) == 21


@pytest.mark.parametrize(
    ("operation", "match"),
    (
        (
            lambda: zero_compressed_kv_state_bf16(
                ratio=8,
                cache_capacity=1,
                kv_value_width=1,
            ),
            "ratio must be exactly",
        ),
        (lambda: compressed_kv_state_bf16(object()), "exact CompressedKVState"),
        (
            lambda: compressed_kv_state_bf16(
                _StateSubclass(
                    4,
                    ((((0,),),),),
                    (None,),
                    (False,),
                    (0,),
                    (0,),
                    (0,),
                )
            ),
            "exact CompressedKVState",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(4, (), (), (), (), (), ())
            ),
            "batch capacity",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(
                    4,
                    _ListSubclass([(((0,),),)]),
                    (None,),
                    (False,),
                    (0,),
                    (0,),
                    (0,),
                )
            ),
            "exact list or tuple",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(
                    4,
                    ((((0x7F80,),),),),
                    (None,),
                    (False,),
                    (0,),
                    (0,),
                    (0,),
                )
            ),
            "finite BF16",
        ),
        (
            lambda: _prefill(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=2,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                sessions=(SESSION_A,),
                sequence_length=3,
                rows=_one_batch_rows((1,)),
            ),
            "exactly 0 completed rows",
        ),
        (
            lambda: compressed_kv_write_bf16(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=2,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                _one_batch_rows((1,), (2,)),
                active_session_ids=(SESSION_A,),
                start_pos=5,
                sequence_length=2,
            ),
            "sequence length exactly 1",
        ),
        (
            lambda: _prefill(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=1,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                sessions=(SESSION_A,),
                sequence_length=5,
                rows=_one_batch_rows((1,)),
            ),
            "cursor exceeds cache capacity",
        ),
        (
            lambda: _prefill(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=2,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                sessions=(SESSION_A,),
                sequence_length=4,
                rows=((((True,),),),),
            ),
            "16-bit BF16",
        ),
    ),
)
def test_malformed_nonfinite_and_out_of_range_requests_fail_closed(
    operation,
    match: str,
) -> None:
    with pytest.raises(CompressedKVReferenceError, match=match):
        operation()
