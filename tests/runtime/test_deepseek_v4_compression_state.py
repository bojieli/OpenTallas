from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import hashlib
import random

import pytest

from runtime.reference.compression_state import (
    COMPRESS_STATE_PROFILE,
    EXCLUDED_DOWNSTREAM_OPERATIONS,
    F32_BYTES,
    F32_NEGATIVE_INFINITY,
    INFERENCE_CONFIG_SHA256,
    LANE_METADATA_BYTES,
    MODEL_SOURCE_SHA256,
    OFFICIAL_REVISION,
    PINNED_COMPRESSION_RATIOS,
    PINNED_INDEX_HEAD_DIM,
    PINNED_MAIN_HEAD_DIM,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    PINNED_NONOVERLAP_RATIO,
    PINNED_OVERLAP_RATIO,
    STATE_VERSION_MAX,
    CompressionLaneState,
    CompressionPoolInputs,
    CompressionState,
    CompressionStateCounters,
    CompressionStateReferenceError,
    CompressionStateUpdateResult,
    compress_state_update_f32,
    compression_state_f32,
    zero_compression_state_f32,
)
from runtime.reference.formats import binary32_add, encode_binary32_rne


class _ListSubclass(list):
    pass


class _StateSubclass(CompressionState):
    pass


def _f32(value: int) -> int:
    return encode_binary32_rne(value)


def _row(tag: int, width: int) -> tuple[int, ...]:
    return tuple(_f32(tag * 32 + column + 1) for column in range(width))


def _tensor(
    batches: int,
    sequence: int,
    width: int,
    *,
    base: int,
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    return tuple(
        tuple(
            _row(base + batch * sequence + position, width)
            for position in range(sequence)
        )
        for batch in range(batches)
    )


def _ape(ratio: int, width: int, *, base: int = 1) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(_f32(base + phase * width + column) for column in range(width))
        for phase in range(ratio)
    )


def _biased(row: tuple[int, ...], ape_row: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(
        binary32_add(left, right) for left, right in zip(row, ape_row, strict=True)
    )


def _mutable(value: object) -> object:
    if isinstance(value, tuple):
        return [_mutable(element) for element in value]
    return value


def _session(epoch: str, lane: int = 0) -> str:
    return hashlib.sha256(f"compression-state:{epoch}:{lane}".encode()).hexdigest()


def _sessions(count: int, epoch: str) -> tuple[str, ...]:
    return tuple(_session(epoch, lane) for lane in range(count))


def _current_sessions(state: CompressionState, count: int) -> tuple[str, ...]:
    sessions = tuple(lane.session_id for lane in state.lanes[:count])
    assert all(session is not None for session in sessions)
    return sessions  # type: ignore[return-value]


def _tagged_state(
    *,
    ratio: int,
    batches: int,
    head_dim: int,
    next_pos: int = 1,
    epoch: str = "tagged",
    version: int = 7,
) -> CompressionState:
    coefficient = 2 if ratio == 4 else 1
    slots = coefficient * ratio
    width = coefficient * head_dim
    return compression_state_f32(
        _tensor(batches, slots, width, base=10),
        _tensor(batches, slots, width, base=100),
        tuple(
            CompressionLaneState(_session(epoch, lane), next_pos, version)
            for lane in range(batches)
        ),
        ratio=ratio,
    )


def test_contract_is_bound_to_pinned_source_profiles_and_nonclaims() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert OFFICIAL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert COMPRESS_STATE_PROFILE == ("opentallas.deepseek_v4_compress_state_update.v2")
    assert PINNED_MAX_BATCH_SIZE == 4
    assert PINNED_MAX_POSITION == 1_048_576
    assert PINNED_MAIN_HEAD_DIM == 512
    assert PINNED_INDEX_HEAD_DIM == 128
    assert PINNED_COMPRESSION_RATIOS == (4, 128)
    assert PINNED_OVERLAP_RATIO == 4
    assert PINNED_NONOVERLAP_RATIO == 128
    assert F32_BYTES == 4
    assert LANE_METADATA_BYTES == 48
    assert STATE_VERSION_MAX == (1 << 64) - 1
    assert EXCLUDED_DOWNSTREAM_OPERATIONS == (
        "learned_projection",
        "softmax_pooling",
        "rms_normalization",
        "rotary_embedding",
        "activation_qdq",
        "compressed_cache_write",
    )


def test_official_zero_states_have_exact_source_axes_and_sentinels() -> None:
    overlap = zero_compression_state_f32(ratio=4)
    assert len(overlap.kv_f32_codes) == 4
    assert len(overlap.kv_f32_codes[0]) == 8
    assert len(overlap.kv_f32_codes[0][0]) == 1024
    assert overlap.kv_f32_codes[3][7] == (0,) * 1024
    assert overlap.score_f32_codes[3][7] == (F32_NEGATIVE_INFINITY,) * 1024
    assert overlap.lanes == (CompressionLaneState(None, 0, 0),) * 4

    nonoverlap = zero_compression_state_f32(ratio=128)
    assert len(nonoverlap.kv_f32_codes) == 4
    assert len(nonoverlap.kv_f32_codes[0]) == 128
    assert len(nonoverlap.kv_f32_codes[0][0]) == 512
    assert nonoverlap.score_f32_codes[0][127][511] == F32_NEGATIVE_INFINITY

    index = zero_compression_state_f32(ratio=4, head_dim=128)
    assert len(index.kv_f32_codes[0][0]) == 256
    with pytest.raises(FrozenInstanceError):
        overlap.ratio = 128  # type: ignore[misc]


def test_overlap_short_prefill_only_populates_current_remainder() -> None:
    state = _tagged_state(ratio=4, batches=2, head_dim=2)
    before = state
    kv = _tensor(1, 3, 4, base=300)
    scores = _tensor(1, 3, 4, base=400)
    ape = _ape(4, 4, base=2)

    sessions = _sessions(1, "short-prefill")
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=sessions,
        start_pos=0,
    )

    assert result.mode == "prefill"
    assert result.prefill_cutoff == 0
    assert result.prefill_remainder == 3
    assert result.decode_phase is None
    assert not result.should_compress
    assert result.pool_inputs is None
    assert result.state.kv_f32_codes[0][:4] == ((0,) * 4,) * 4
    assert result.state.kv_f32_codes[0][4:7] == kv[0]
    assert result.state.kv_f32_codes[0][7] == (0,) * 4
    assert result.state.score_f32_codes[0][:4] == ((F32_NEGATIVE_INFINITY,) * 4,) * 4
    assert result.state.score_f32_codes[0][4:7] == tuple(
        _biased(scores[0][phase], ape[phase]) for phase in range(3)
    )
    assert result.state.score_f32_codes[0][7] == (F32_NEGATIVE_INFINITY,) * 4
    assert result.state.kv_f32_codes[1] == before.kv_f32_codes[1]
    assert result.state.lanes == (
        CompressionLaneState(sessions[0], 3, 8),
        before.lanes[1],
    )
    assert state == before


def test_overlap_exact_one_group_pads_pool_and_retains_full_group() -> None:
    state = _tagged_state(ratio=4, batches=1, head_dim=2)
    kv = _tensor(1, 4, 4, base=20)
    scores = _tensor(1, 4, 4, base=40)
    ape = _ape(4, 4, base=3)

    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_sessions(1, "exact-group"),
        start_pos=0,
    )

    assert result.should_compress
    assert result.prefill_cutoff == 4
    assert result.prefill_remainder == 0
    assert result.state.kv_f32_codes[0][:4] == kv[0]
    assert result.state.kv_f32_codes[0][4:] == ((0,) * 4,) * 4
    assert result.state.score_f32_codes[0][4:] == ((F32_NEGATIVE_INFINITY,) * 4,) * 4
    assert result.state.score_f32_codes[0][:4] == tuple(
        _biased(scores[0][phase], ape[phase]) for phase in range(4)
    )
    assert result.pool_inputs == CompressionPoolInputs(
        kv_f32_codes=(
            (
                (
                    (0, 0),
                    (0, 0),
                    (0, 0),
                    (0, 0),
                    kv[0][0][2:],
                    kv[0][1][2:],
                    kv[0][2][2:],
                    kv[0][3][2:],
                ),
            ),
        ),
        score_f32_codes=(
            (
                (
                    (F32_NEGATIVE_INFINITY,) * 2,
                    (F32_NEGATIVE_INFINITY,) * 2,
                    (F32_NEGATIVE_INFINITY,) * 2,
                    (F32_NEGATIVE_INFINITY,) * 2,
                    _biased(scores[0][0], ape[0])[2:],
                    _biased(scores[0][1], ape[1])[2:],
                    _biased(scores[0][2], ape[2])[2:],
                    _biased(scores[0][3], ape[3])[2:],
                ),
            ),
        ),
    )


def test_overlap_long_prefill_uses_previous_and_current_feature_halves() -> None:
    state = _tagged_state(ratio=4, batches=2, head_dim=2)
    before = state
    kv = _tensor(1, 10, 4, base=30)
    scores = _tensor(1, 10, 4, base=60)
    ape = _ape(4, 4, base=5)

    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_sessions(1, "long-prefill"),
        start_pos=0,
    )

    assert result.prefill_cutoff == 8
    assert result.prefill_remainder == 2
    assert result.state.kv_f32_codes[0][:4] == kv[0][4:8]
    assert result.state.kv_f32_codes[0][4:6] == kv[0][8:10]
    assert result.state.kv_f32_codes[0][6:] == ((0,) * 4,) * 2
    assert result.state.score_f32_codes[0][:4] == tuple(
        _biased(scores[0][4 + phase], ape[phase]) for phase in range(4)
    )
    assert result.state.score_f32_codes[0][4:6] == tuple(
        _biased(scores[0][8 + phase], ape[phase]) for phase in range(2)
    )
    assert result.state.score_f32_codes[0][6:] == ((F32_NEGATIVE_INFINITY,) * 4,) * 2
    assert result.state.kv_f32_codes[1] == before.kv_f32_codes[1]

    assert result.pool_inputs is not None
    assert result.pool_inputs.kv_f32_codes[0][0] == (
        *((0, 0),) * 4,
        *(kv[0][phase][2:] for phase in range(4)),
    )
    assert result.pool_inputs.kv_f32_codes[0][1] == (
        *(kv[0][phase][:2] for phase in range(4)),
        *(kv[0][4 + phase][2:] for phase in range(4)),
    )
    assert result.pool_inputs.score_f32_codes[0][1] == (
        *(_biased(scores[0][phase], ape[phase])[:2] for phase in range(4)),
        *(_biased(scores[0][4 + phase], ape[phase])[2:] for phase in range(4)),
    )

    counters = result.counters
    assert counters == CompressionStateCounters(
        active_batch_count=1,
        state_batch_capacity=2,
        sequence_length=10,
        ratio=4,
        overlap=True,
        head_dim=2,
        projected_width=4,
        complete_group_count=2,
        input_kv_f32_values=40,
        input_score_f32_values=40,
        logical_source_kv_f32_values_read=48,
        logical_source_score_f32_values_read=56,
        logical_source_kv_read_bytes=192,
        logical_source_score_read_bytes=224,
        logical_ape_f32_values_read=56,
        logical_ape_read_bytes=224,
        logical_score_ape_additions=56,
        logical_kv_state_f32_values_read=0,
        logical_score_state_f32_values_read=0,
        logical_kv_state_read_bytes=0,
        logical_score_state_read_bytes=0,
        logical_kv_state_f32_values_written=56,
        logical_score_state_f32_values_written=56,
        logical_kv_state_write_bytes=224,
        logical_score_state_write_bytes=224,
        kv_state_f32_values_preserved=32,
        score_state_f32_values_preserved=32,
        pool_kv_f32_values=32,
        pool_score_f32_values=32,
        overlap_pool_zero_f32_values=8,
        overlap_pool_negative_infinity_f32_values=8,
        kv_state_roll_f32_values=0,
        score_state_roll_f32_values=0,
        kv_state_reset_f32_values=32,
        score_state_reset_f32_values=32,
        lane_metadata_records_read=2,
        lane_metadata_read_bytes=96,
        lane_metadata_records_written=1,
        lane_metadata_write_bytes=48,
        lane_metadata_records_preserved=1,
        logical_ratio_modulo_evaluations=1,
        transaction_commits=1,
    )


def test_overlap_exact_multiple_leaves_current_half_reset() -> None:
    state = _tagged_state(ratio=4, batches=1, head_dim=1)
    kv = _tensor(1, 8, 2, base=10)
    scores = _tensor(1, 8, 2, base=20)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        _ape(4, 2),
        session_ids=_sessions(1, "exact-multiple"),
        start_pos=0,
    )
    assert result.state.kv_f32_codes[0][:4] == kv[0][4:8]
    assert result.state.kv_f32_codes[0][4:] == ((0, 0),) * 4
    assert (
        result.state.score_f32_codes[0][4:]
        == ((F32_NEGATIVE_INFINITY, F32_NEGATIVE_INFINITY),) * 4
    )


def test_nonoverlap_short_prefill_stores_only_remainder_without_pool() -> None:
    state = _tagged_state(ratio=128, batches=1, head_dim=1)
    kv = _tensor(1, 3, 1, base=20)
    scores = _tensor(1, 3, 1, base=40)
    ape = _ape(128, 1)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_sessions(1, "nonoverlap-short"),
        start_pos=0,
    )

    assert not result.should_compress
    assert result.pool_inputs is None
    assert result.prefill_cutoff == 0
    assert result.prefill_remainder == 3
    assert result.state.kv_f32_codes[0][:3] == kv[0]
    assert result.state.kv_f32_codes[0][3:] == ((0,),) * 125
    assert result.state.score_f32_codes[0][:3] == tuple(
        _biased(scores[0][phase], ape[phase]) for phase in range(3)
    )
    assert result.state.score_f32_codes[0][3:] == ((F32_NEGATIVE_INFINITY,),) * 125


def test_nonoverlap_prefill_emits_complete_prefix_and_stores_remainder() -> None:
    state = _tagged_state(ratio=128, batches=2, head_dim=1)
    before = state
    kv = _tensor(1, 130, 1, base=20)
    scores = _tensor(1, 130, 1, base=200)
    ape = _ape(128, 1, base=2)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_sessions(1, "nonoverlap-long"),
        start_pos=0,
    )

    assert result.should_compress
    assert result.prefill_cutoff == 128
    assert result.prefill_remainder == 2
    assert result.state.kv_f32_codes[0][:2] == kv[0][128:]
    assert result.state.kv_f32_codes[0][2:] == ((0,),) * 126
    assert result.state.score_f32_codes[0][:2] == (
        _biased(scores[0][128], ape[0]),
        _biased(scores[0][129], ape[1]),
    )
    assert result.state.kv_f32_codes[1] == before.kv_f32_codes[1]
    assert result.pool_inputs is not None
    assert result.pool_inputs.kv_f32_codes == ((kv[0][:128],),)
    assert result.pool_inputs.score_f32_codes == (
        (tuple(_biased(scores[0][phase], ape[phase]) for phase in range(128)),),
    )
    counters = result.counters
    assert counters.input_kv_f32_values == 130
    assert counters.logical_source_kv_f32_values_read == 130
    assert counters.logical_source_score_f32_values_read == 130
    assert counters.logical_ape_f32_values_read == 130
    assert counters.logical_kv_state_f32_values_written == 130
    assert counters.logical_kv_state_f32_values_read == 0
    assert counters.kv_state_f32_values_preserved == 128
    assert counters.pool_kv_f32_values == 128
    assert counters.overlap_pool_zero_f32_values == 0


def test_nonoverlap_exact_multiple_resets_decode_state() -> None:
    state = _tagged_state(ratio=128, batches=1, head_dim=1)
    kv = _tensor(1, 128, 1, base=20)
    scores = _tensor(1, 128, 1, base=200)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        _ape(128, 1),
        session_ids=_sessions(1, "nonoverlap-exact"),
        start_pos=0,
    )
    assert result.state.kv_f32_codes == (((0,),) * 128,)
    assert result.state.score_f32_codes == (((F32_NEGATIVE_INFINITY,),) * 128,)
    assert result.should_compress
    assert result.counters.logical_kv_state_f32_values_written == 128
    assert result.counters.kv_state_f32_values_preserved == 0


def test_overlap_decode_nonboundary_writes_current_slot_only() -> None:
    state = _tagged_state(ratio=4, batches=2, head_dim=2, next_pos=5)
    before = state
    kv = _tensor(1, 1, 4, base=300)
    scores = _tensor(1, 1, 4, base=400)
    ape = _ape(4, 4)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_current_sessions(state, 1),
        start_pos=5,
    )

    assert result.mode == "decode"
    assert result.decode_phase == 1
    assert result.prefill_cutoff is None
    assert result.prefill_remainder is None
    assert not result.should_compress
    assert result.pool_inputs is None
    assert result.state.kv_f32_codes[0][5] == kv[0][0]
    assert result.state.score_f32_codes[0][5] == _biased(scores[0][0], ape[1])
    assert result.state.kv_f32_codes[0][:5] == before.kv_f32_codes[0][:5]
    assert result.state.kv_f32_codes[0][6:] == before.kv_f32_codes[0][6:]
    assert result.state.kv_f32_codes[1] == before.kv_f32_codes[1]
    assert result.state.lanes == (
        CompressionLaneState(before.lanes[0].session_id, 6, 8),
        before.lanes[1],
    )
    assert result.counters.logical_kv_state_f32_values_read == 0
    assert result.counters.logical_kv_state_f32_values_written == 4
    assert result.counters.logical_ratio_modulo_evaluations == 3


def test_overlap_decode_boundary_emits_then_rolls_full_current_state() -> None:
    state = _tagged_state(ratio=4, batches=2, head_dim=2, next_pos=7)
    old_previous_kv = state.kv_f32_codes[0][:4]
    old_previous_score = state.score_f32_codes[0][:4]
    old_current_kv = state.kv_f32_codes[0][4:]
    old_current_score = state.score_f32_codes[0][4:]
    kv = _tensor(1, 1, 4, base=500)
    scores = _tensor(1, 1, 4, base=600)
    ape = _ape(4, 4, base=2)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_current_sessions(state, 1),
        start_pos=7,
    )

    written_score = _biased(scores[0][0], ape[3])
    current_kv = (*old_current_kv[:3], kv[0][0])
    current_score = (*old_current_score[:3], written_score)
    assert result.should_compress
    assert result.pool_inputs == CompressionPoolInputs(
        kv_f32_codes=(
            (
                (
                    *(row[:2] for row in old_previous_kv),
                    *(row[2:] for row in current_kv),
                ),
            ),
        ),
        score_f32_codes=(
            (
                (
                    *(row[:2] for row in old_previous_score),
                    *(row[2:] for row in current_score),
                ),
            ),
        ),
    )
    assert result.state.kv_f32_codes[0][:4] == current_kv
    assert result.state.kv_f32_codes[0][4:] == current_kv
    assert result.state.score_f32_codes[0][:4] == current_score
    assert result.state.score_f32_codes[0][4:] == current_score
    assert result.state.kv_f32_codes[1] == state.kv_f32_codes[1]

    counters = result.counters
    assert counters.pool_kv_f32_values == 16
    assert counters.logical_kv_state_f32_values_read == 32
    assert counters.logical_score_state_f32_values_read == 32
    assert counters.logical_kv_state_f32_values_written == 20
    assert counters.kv_state_roll_f32_values == 16
    assert counters.kv_state_f32_values_preserved == 44
    assert counters.logical_source_kv_f32_values_read == 4
    assert counters.logical_source_score_f32_values_read == 4


def test_nonoverlap_decode_boundary_pools_state_without_roll() -> None:
    state = _tagged_state(ratio=128, batches=1, head_dim=1, next_pos=127)
    kv = _tensor(1, 1, 1, base=500)
    scores = _tensor(1, 1, 1, base=600)
    ape = _ape(128, 1)
    result = compress_state_update_f32(
        state,
        kv,
        scores,
        ape,
        session_ids=_current_sessions(state, 1),
        start_pos=127,
    )

    expected_kv = (*state.kv_f32_codes[0][:127], kv[0][0])
    expected_scores = (
        *state.score_f32_codes[0][:127],
        _biased(scores[0][0], ape[127]),
    )
    assert result.pool_inputs == CompressionPoolInputs(
        kv_f32_codes=((expected_kv,),),
        score_f32_codes=((expected_scores,),),
    )
    assert result.state.kv_f32_codes[0] == expected_kv
    assert result.state.score_f32_codes[0] == expected_scores
    assert result.counters.logical_kv_state_f32_values_read == 128
    assert result.counters.logical_kv_state_f32_values_written == 1
    assert result.counters.kv_state_roll_f32_values == 0
    assert result.counters.kv_state_f32_values_preserved == 127


def test_overlap_prefill_then_decode_preserves_absolute_phase_boundaries() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    ape = _ape(4, 2)
    prefill_kv = _tensor(1, 6, 2, base=20)
    prefill_scores = _tensor(1, 6, 2, base=40)
    sessions = _sessions(1, "prefill-decode")
    after_prefill = compress_state_update_f32(
        state,
        prefill_kv,
        prefill_scores,
        ape,
        session_ids=sessions,
        start_pos=0,
    ).state

    row6_kv = _tensor(1, 1, 2, base=80)
    row6_score = _tensor(1, 1, 2, base=90)
    after6 = compress_state_update_f32(
        after_prefill,
        row6_kv,
        row6_score,
        ape,
        session_ids=sessions,
        start_pos=6,
    )
    assert not after6.should_compress
    row7_kv = _tensor(1, 1, 2, base=100)
    row7_score = _tensor(1, 1, 2, base=110)
    after7 = compress_state_update_f32(
        after6.state,
        row7_kv,
        row7_score,
        ape,
        session_ids=sessions,
        start_pos=7,
    )

    completed = (*prefill_kv[0][4:6], row6_kv[0][0], row7_kv[0][0])
    assert after7.state.kv_f32_codes[0][:4] == completed
    assert after7.state.kv_f32_codes[0][4:] == completed
    assert after7.pool_inputs is not None
    assert after7.pool_inputs.kv_f32_codes[0][0] == (
        *(row[:1] for row in prefill_kv[0][:4]),
        *(row[1:] for row in completed),
    )


def test_completed_overlap_window_rejects_a_skipped_position_before_stale_reuse() -> (
    None
):
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    sessions = _sessions(1, "skip-after-window")
    ape = _ape(4, 2)
    state = compress_state_update_f32(
        state,
        _tensor(1, 4, 2, base=10),
        _tensor(1, 4, 2, base=20),
        ape,
        session_ids=sessions,
        start_pos=0,
    ).state
    for position in range(4, 8):
        state = compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=30 + position),
            _tensor(1, 1, 2, base=40 + position),
            ape,
            session_ids=sessions,
            start_pos=position,
        ).state

    before = state
    with pytest.raises(
        CompressionStateReferenceError,
        match=r"expected start_pos 8, received 9",
    ):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=90),
            _tensor(1, 1, 2, base=100),
            ape,
            session_ids=sessions,
            start_pos=9,
        )
    assert state == before
    assert state.lanes[0] == CompressionLaneState(sessions[0], 8, 5)


def test_replayed_nonboundary_position_with_different_payload_is_rejected() -> None:
    sessions = _sessions(1, "replay")
    ape = _ape(4, 2)
    state = compress_state_update_f32(
        zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1),
        _tensor(1, 1, 2, base=10),
        _tensor(1, 1, 2, base=20),
        ape,
        session_ids=sessions,
        start_pos=0,
    ).state
    accepted = compress_state_update_f32(
        state,
        _tensor(1, 1, 2, base=30),
        _tensor(1, 1, 2, base=40),
        ape,
        session_ids=sessions,
        start_pos=1,
    ).state

    with pytest.raises(
        CompressionStateReferenceError,
        match=r"expected start_pos 2, received 1",
    ):
        compress_state_update_f32(
            accepted,
            _tensor(1, 1, 2, base=300),
            _tensor(1, 1, 2, base=400),
            ape,
            session_ids=sessions,
            start_pos=1,
        )
    assert accepted.lanes[0] == CompressionLaneState(sessions[0], 2, 2)


def test_decode_rejects_stale_session_identity() -> None:
    state = _tagged_state(ratio=4, batches=1, head_dim=1, next_pos=5)
    before = state
    with pytest.raises(
        CompressionStateReferenceError, match="session ID does not match"
    ):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "stale-session"),
            start_pos=5,
        )
    assert state == before


def test_prefill_rejects_same_session_and_cross_lane_session_reuse() -> None:
    state = _tagged_state(ratio=4, batches=2, head_dim=1)
    row_kv = _tensor(1, 1, 2, base=1)
    row_scores = _tensor(1, 1, 2, base=2)
    ape = _ape(4, 2)

    for reused_session in (
        state.lanes[0].session_id,
        state.lanes[1].session_id,
    ):
        assert reused_session is not None
        with pytest.raises(
            CompressionStateReferenceError,
            match="fresh-session prefill cannot reuse",
        ):
            compress_state_update_f32(
                state,
                row_kv,
                row_scores,
                ape,
                session_ids=(reused_session,),
                start_pos=0,
            )


def test_duplicate_active_session_ids_are_rejected() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1)
    duplicate = _session("duplicate")
    with pytest.raises(CompressionStateReferenceError, match="must be unique"):
        compress_state_update_f32(
            state,
            _tensor(2, 1, 2, base=1),
            _tensor(2, 1, 2, base=2),
            _ape(4, 2),
            session_ids=(duplicate, duplicate),
            start_pos=0,
        )


def test_lane_removed_from_active_prefix_cannot_rejoin_after_missing_a_position() -> (
    None
):
    sessions = _sessions(2, "remove-and-readd")
    ape = _ape(4, 2)
    state = compress_state_update_f32(
        zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1),
        _tensor(2, 1, 2, base=1),
        _tensor(2, 1, 2, base=2),
        ape,
        session_ids=sessions,
        start_pos=0,
    ).state
    state = compress_state_update_f32(
        state,
        _tensor(1, 1, 2, base=10),
        _tensor(1, 1, 2, base=20),
        ape,
        session_ids=sessions[:1],
        start_pos=1,
    ).state
    before = state

    with pytest.raises(
        CompressionStateReferenceError,
        match=r"lane 1 expected start_pos 1, received 2",
    ):
        compress_state_update_f32(
            state,
            _tensor(2, 1, 2, base=30),
            _tensor(2, 1, 2, base=40),
            ape,
            session_ids=sessions,
            start_pos=2,
        )
    assert state == before
    assert state.lanes == (
        CompressionLaneState(sessions[0], 2, 2),
        CompressionLaneState(sessions[1], 1, 1),
    )


def test_lane_versions_are_monotonic_across_decode_and_fresh_prefill() -> None:
    state = _tagged_state(
        ratio=4,
        batches=2,
        head_dim=1,
        next_pos=3,
        version=11,
    )
    inactive = state.lanes[1]
    first_sessions = _sessions(1, "version-first")
    state = compress_state_update_f32(
        state,
        _tensor(1, 2, 2, base=1),
        _tensor(1, 2, 2, base=2),
        _ape(4, 2),
        session_ids=first_sessions,
        start_pos=0,
    ).state
    assert state.lanes == (
        CompressionLaneState(first_sessions[0], 2, 12),
        inactive,
    )

    state = compress_state_update_f32(
        state,
        _tensor(1, 1, 2, base=3),
        _tensor(1, 1, 2, base=4),
        _ape(4, 2),
        session_ids=first_sessions,
        start_pos=2,
    ).state
    assert state.lanes[0] == CompressionLaneState(first_sessions[0], 3, 13)

    second_sessions = _sessions(1, "version-second")
    state = compress_state_update_f32(
        state,
        _tensor(1, 1, 2, base=5),
        _tensor(1, 1, 2, base=6),
        _ape(4, 2),
        session_ids=second_sessions,
        start_pos=0,
    ).state
    assert state.lanes == (
        CompressionLaneState(second_sessions[0], 1, 14),
        inactive,
    )


def test_f32_payload_bits_and_caller_alias_protection() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=2)
    sessions = _sessions(1, "payload-bits")
    state = compress_state_update_f32(
        state,
        _tensor(1, 1, 4, base=10),
        _tensor(1, 1, 4, base=20),
        _ape(4, 4, base=0),
        session_ids=sessions,
        start_pos=0,
    ).state
    kv_lists = [[[0x00000000, 0x80000000, 0x00000001, 0x80000001]]]
    score_lists = [[[0, 0, 0, 0]]]
    ape_lists = _mutable(_ape(4, 4, base=0))
    result = compress_state_update_f32(
        state,
        kv_lists,
        score_lists,
        ape_lists,
        session_ids=sessions,
        start_pos=1,
    )
    expected = result.state
    assert result.state.kv_f32_codes[0][5] == (
        0x00000000,
        0x80000000,
        0x00000001,
        0x80000001,
    )

    kv_lists[0][0][0] = _f32(100)
    score_lists[0][0][0] = _f32(100)
    ape_lists[1][0] = _f32(100)  # type: ignore[index]
    assert result.state == expected
    assert isinstance(result.state.kv_f32_codes, tuple)
    assert isinstance(result.state.kv_f32_codes[0][5], tuple)
    with pytest.raises(FrozenInstanceError):
        result.should_compress = True  # type: ignore[misc]


def _oracle_update(
    state: CompressionState,
    kv: tuple[tuple[tuple[int, ...], ...], ...],
    scores: tuple[tuple[tuple[int, ...], ...], ...],
    ape: tuple[tuple[int, ...], ...],
    *,
    start_pos: int,
) -> tuple[
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[tuple[tuple[int, ...], ...], ...],
    tuple[
        tuple[tuple[tuple[int, ...], ...], ...],
        tuple[tuple[tuple[int, ...], ...], ...],
    ]
    | None,
]:
    ratio = state.ratio
    overlap = ratio == 4
    head_dim = len(state.kv_f32_codes[0][0]) // (2 if overlap else 1)
    out_kv = [[row for row in sequence] for sequence in state.kv_f32_codes]
    out_scores = [[row for row in sequence] for sequence in state.score_f32_codes]
    batch_size = len(kv)
    sequence_length = len(kv[0])
    pool_kv: list[tuple[tuple[int, ...], ...]] = []
    pool_scores: list[tuple[tuple[int, ...], ...]] = []

    if start_pos == 0:
        zero_row = (0,) * len(out_kv[0][0])
        negative_infinity_row = (F32_NEGATIVE_INFINITY,) * len(out_scores[0][0])
        for batch in range(batch_size):
            out_kv[batch] = [zero_row] * len(out_kv[batch])
            out_scores[batch] = [negative_infinity_row] * len(out_scores[batch])

        cutoff = sequence_length - sequence_length % ratio
        remainder = sequence_length - cutoff
        groups = cutoff // ratio
        for batch in range(batch_size):
            if overlap and groups:
                for phase in range(ratio):
                    source = cutoff - ratio + phase
                    out_kv[batch][phase] = kv[batch][source]
                    out_scores[batch][phase] = _biased(
                        scores[batch][source], ape[phase]
                    )
            offset = ratio if overlap else 0
            for phase in range(remainder):
                source = cutoff + phase
                out_kv[batch][offset + phase] = kv[batch][source]
                out_scores[batch][offset + phase] = _biased(
                    scores[batch][source], ape[phase]
                )

            batch_pool_kv = []
            batch_pool_scores = []
            for group in range(groups):
                current = group * ratio
                if overlap:
                    if group == 0:
                        kv_group = [(0,) * head_dim for _ in range(ratio)]
                        score_group = [
                            (F32_NEGATIVE_INFINITY,) * head_dim for _ in range(ratio)
                        ]
                    else:
                        previous = current - ratio
                        kv_group = [
                            kv[batch][previous + phase][:head_dim]
                            for phase in range(ratio)
                        ]
                        score_group = [
                            _biased(scores[batch][previous + phase], ape[phase])[
                                :head_dim
                            ]
                            for phase in range(ratio)
                        ]
                    kv_group.extend(
                        kv[batch][current + phase][head_dim:] for phase in range(ratio)
                    )
                    score_group.extend(
                        _biased(scores[batch][current + phase], ape[phase])[head_dim:]
                        for phase in range(ratio)
                    )
                else:
                    kv_group = [kv[batch][current + phase] for phase in range(ratio)]
                    score_group = [
                        _biased(scores[batch][current + phase], ape[phase])
                        for phase in range(ratio)
                    ]
                batch_pool_kv.append(tuple(kv_group))
                batch_pool_scores.append(tuple(score_group))
            pool_kv.append(tuple(batch_pool_kv))
            pool_scores.append(tuple(batch_pool_scores))
        pool = (tuple(pool_kv), tuple(pool_scores)) if groups else None
    else:
        phase = start_pos % ratio
        boundary = phase == ratio - 1
        destination = ratio + phase if overlap else phase
        for batch in range(batch_size):
            out_kv[batch][destination] = kv[batch][0]
            out_scores[batch][destination] = _biased(scores[batch][0], ape[phase])
        if boundary:
            for batch in range(batch_size):
                if overlap:
                    kv_group = tuple(
                        row[:head_dim] for row in out_kv[batch][:ratio]
                    ) + tuple(row[head_dim:] for row in out_kv[batch][ratio:])
                    score_group = tuple(
                        row[:head_dim] for row in out_scores[batch][:ratio]
                    ) + tuple(row[head_dim:] for row in out_scores[batch][ratio:])
                else:
                    kv_group = tuple(out_kv[batch])
                    score_group = tuple(out_scores[batch])
                pool_kv.append((kv_group,))
                pool_scores.append((score_group,))
            pool = (tuple(pool_kv), tuple(pool_scores))
            if overlap:
                for batch in range(batch_size):
                    out_kv[batch][:ratio] = out_kv[batch][ratio:]
                    out_scores[batch][:ratio] = out_scores[batch][ratio:]
        else:
            pool = None
    return (
        tuple(tuple(sequence) for sequence in out_kv),
        tuple(tuple(sequence) for sequence in out_scores),
        pool,
    )


def test_randomized_causal_traces_match_independent_structural_oracle() -> None:
    rng = random.Random(0x434F_4D50_5354_4154)
    for ratio in (4, 128):
        for case in range(12):
            capacity = rng.randint(1, 3)
            active = rng.randint(1, capacity)
            head_dim = rng.randint(1, 3)
            coefficient = 2 if ratio == 4 else 1
            width = coefficient * head_dim
            state = zero_compression_state_f32(
                ratio=ratio,
                batch_capacity=capacity,
                head_dim=head_dim,
            )
            sequence = rng.choice((1, ratio - 1, ratio, ratio + 1, 2 * ratio + 3))
            kv = _tensor(active, sequence, width, base=300 + case)
            scores = _tensor(active, sequence, width, base=600 + case)
            ape = _ape(ratio, width, base=1)
            sessions = _sessions(active, f"random-{ratio}-{case}-first")
            expected_kv, expected_scores, expected_pool = _oracle_update(
                state,
                kv,
                scores,
                ape,
                start_pos=0,
            )
            result = compress_state_update_f32(
                state,
                kv,
                scores,
                ape,
                session_ids=sessions,
                start_pos=0,
            )
            assert result.state.kv_f32_codes == expected_kv
            assert result.state.score_f32_codes == expected_scores
            if expected_pool is None:
                assert result.pool_inputs is None
            else:
                assert result.pool_inputs == CompressionPoolInputs(*expected_pool)

            state = result.state
            next_pos = sequence
            distance_to_boundary = ratio - (next_pos % ratio)
            if distance_to_boundary == 0:
                distance_to_boundary = ratio
            decode_count = rng.choice((0, 1, min(distance_to_boundary, 3)))
            for decode_index in range(decode_count):
                kv = _tensor(
                    active,
                    1,
                    width,
                    base=900 + case * 10 + decode_index,
                )
                scores = _tensor(
                    active,
                    1,
                    width,
                    base=1200 + case * 10 + decode_index,
                )
                expected_kv, expected_scores, expected_pool = _oracle_update(
                    state,
                    kv,
                    scores,
                    ape,
                    start_pos=next_pos,
                )
                result = compress_state_update_f32(
                    state,
                    kv,
                    scores,
                    ape,
                    session_ids=sessions,
                    start_pos=next_pos,
                )
                assert result.state.kv_f32_codes == expected_kv
                assert result.state.score_f32_codes == expected_scores
                if expected_pool is None:
                    assert result.pool_inputs is None
                else:
                    assert result.pool_inputs == CompressionPoolInputs(*expected_pool)
                state = result.state
                next_pos += 1

            if case % 3 == 0:
                second_sequence = rng.choice((1, ratio - 1, ratio + 1))
                second_kv = _tensor(
                    active,
                    second_sequence,
                    width,
                    base=1500 + case,
                )
                second_scores = _tensor(
                    active,
                    second_sequence,
                    width,
                    base=1800 + case,
                )
                second_sessions = _sessions(
                    active,
                    f"random-{ratio}-{case}-second",
                )
                expected_kv, expected_scores, expected_pool = _oracle_update(
                    state,
                    second_kv,
                    second_scores,
                    ape,
                    start_pos=0,
                )
                result = compress_state_update_f32(
                    state,
                    second_kv,
                    second_scores,
                    ape,
                    session_ids=second_sessions,
                    start_pos=0,
                )
                assert result.state.kv_f32_codes == expected_kv
                assert result.state.score_f32_codes == expected_scores
                if expected_pool is None:
                    assert result.pool_inputs is None
                else:
                    assert result.pool_inputs == CompressionPoolInputs(*expected_pool)


@pytest.mark.parametrize(
    "bad_session",
    [
        "A" * 64,
        "g" * 64,
        "0" * 63,
        "0" * 65,
        b"0" * 64,
        None,
    ],
)
def test_session_ids_require_canonical_lowercase_sha256_hex(
    bad_session: object,
) -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    with pytest.raises(
        CompressionStateReferenceError,
        match="canonical lowercase SHA-256",
    ):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=(bad_session,),
            start_pos=0,
        )


def test_session_id_axis_is_exact_and_matches_active_batch_count() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1)
    with pytest.raises(CompressionStateReferenceError, match="exact list or tuple"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_ListSubclass([_session("axis")]),
            start_pos=0,
        )
    with pytest.raises(CompressionStateReferenceError, match="exactly 1"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(2, "count"),
            start_pos=0,
        )


def test_decode_requires_prefill_initialized_lane() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    before = state
    with pytest.raises(CompressionStateReferenceError, match="lane 0 is uninitialized"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "no-prefill"),
            start_pos=1,
        )
    assert state == before


def test_lane_version_overflow_rejects_decode_and_fresh_prefill_atomically() -> None:
    state = _tagged_state(
        ratio=4,
        batches=1,
        head_dim=1,
        next_pos=1,
        version=STATE_VERSION_MAX,
    )
    before = state
    existing_session = _current_sessions(state, 1)
    with pytest.raises(CompressionStateReferenceError, match="version would overflow"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=existing_session,
            start_pos=1,
        )
    with pytest.raises(CompressionStateReferenceError, match="version would overflow"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=3),
            _tensor(1, 1, 2, base=4),
            _ape(4, 2),
            session_ids=_sessions(1, "overflow-fresh"),
            start_pos=0,
        )
    assert state == before


@pytest.mark.parametrize(
    "bad_start",
    [True, False, 1.0, "1", -1, PINNED_MAX_POSITION],
)
def test_start_position_type_and_range_fail_closed(bad_start: object) -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    with pytest.raises(CompressionStateReferenceError, match="start_pos"):
        compress_state_update_f32(
            state,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "bad-start"),
            start_pos=bad_start,  # type: ignore[arg-type]
        )


def test_decode_shape_and_end_position_are_bounded() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    with pytest.raises(
        CompressionStateReferenceError, match="sequence length exactly 1"
    ):
        compress_state_update_f32(
            state,
            _tensor(1, 2, 2, base=1),
            _tensor(1, 2, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "decode-shape"),
            start_pos=1,
        )
    with pytest.raises(CompressionStateReferenceError, match="end position"):
        compress_state_update_f32(
            state,
            _tensor(1, 2, 2, base=1),
            _tensor(1, 2, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "end-position"),
            start_pos=PINNED_MAX_POSITION - 1,
        )


@pytest.mark.parametrize("ratio", [True, False, 0, 3, 5, 127, 129, 4.0, "4"])
def test_only_released_ratio_profiles_are_admitted(ratio: object) -> None:
    with pytest.raises(CompressionStateReferenceError, match="ratio"):
        zero_compression_state_f32(ratio=ratio)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("arguments", "match"),
    [
        ({"ratio": 4, "batch_capacity": True}, "batch_capacity"),
        ({"ratio": 4, "batch_capacity": 0}, "batch_capacity"),
        ({"ratio": 4, "batch_capacity": 5}, "batch_capacity"),
        ({"ratio": 4, "head_dim": 0}, "head_dim"),
        ({"ratio": 4, "head_dim": 513}, "head_dim"),
    ],
)
def test_state_constructor_bounds_are_type_sensitive(
    arguments: dict[str, object], match: str
) -> None:
    with pytest.raises(CompressionStateReferenceError, match=match):
        zero_compression_state_f32(**arguments)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("lanes", "match"),
    [
        ((), "exactly 1 lane"),
        ((object(),), "exact CompressionLaneState"),
        ((CompressionLaneState(None, 1, 0),), "exact integer zero"),
        ((CompressionLaneState(None, False, 0),), "exact integer zero"),
        ((CompressionLaneState(None, 0, 0.0),), "exact integer zero"),
        ((CompressionLaneState(_session("bad-next"), 0, 1),), "next_pos"),
        ((CompressionLaneState(_session("bad-version"), 1, 0),), "version"),
        (
            (CompressionLaneState(_session("large-version"), 1, 1 << 64),),
            "version",
        ),
        ((CompressionLaneState("A" * 64, 1, 1),), "canonical lowercase"),
    ],
)
def test_malformed_lane_metadata_fails_closed(lanes: object, match: str) -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    with pytest.raises(CompressionStateReferenceError, match=match):
        compression_state_f32(
            state.kv_f32_codes,
            state.score_f32_codes,
            lanes,
            ratio=4,
        )


def test_initialized_session_ids_must_be_unique_across_state_lanes() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1)
    duplicate = _session("duplicate-state-lanes")
    with pytest.raises(CompressionStateReferenceError, match="unique across lanes"):
        compression_state_f32(
            state.kv_f32_codes,
            state.score_f32_codes,
            (
                CompressionLaneState(duplicate, 1, 1),
                CompressionLaneState(duplicate, 1, 1),
            ),
            ratio=4,
        )


@pytest.mark.parametrize(
    ("state", "match"),
    [
        (object(), "exact CompressionState"),
        (CompressionState(3, (), (), ()), "ratio"),
        (CompressionState(4, (), (), ()), "batch extent"),
        (
            CompressionState(
                4,
                (((),) * 8,),
                (((),) * 8,),
                (CompressionLaneState(None, 0, 0),),
            ),
            "at least one value",
        ),
        (
            CompressionState(
                4,
                (((_f32(1),),) * 7,),
                (((_f32(1),),) * 7,),
                (CompressionLaneState(None, 0, 0),),
            ),
            "sequence axis",
        ),
        (
            CompressionState(
                4,
                (((_f32(1), _f32(2), _f32(3)),) * 8,),
                (((_f32(1), _f32(2), _f32(3)),) * 8,),
                (CompressionLaneState(None, 0, 0),),
            ),
            "divisible",
        ),
        (
            CompressionState(
                4,
                (((_f32(1), _f32(2)),) * 8,),
                (((_f32(1), _f32(2)),) * 7,),
                (CompressionLaneState(None, 0, 0),),
            ),
            "sequence axis",
        ),
    ],
)
def test_malformed_state_shapes_fail_closed(state: object, match: str) -> None:
    with pytest.raises(CompressionStateReferenceError, match=match):
        compress_state_update_f32(
            state,  # type: ignore[arg-type]
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "malformed-state"),
            start_pos=1,
        )


def test_exact_state_type_and_exact_sequence_types_are_required() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    subclass = _StateSubclass(
        state.ratio,
        state.kv_f32_codes,
        state.score_f32_codes,
        state.lanes,
    )
    with pytest.raises(CompressionStateReferenceError, match="exact CompressionState"):
        compress_state_update_f32(
            subclass,
            _tensor(1, 1, 2, base=1),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "state-subclass"),
            start_pos=1,
        )
    with pytest.raises(CompressionStateReferenceError, match="exact list or tuple"):
        compress_state_update_f32(
            state,
            _ListSubclass([[[0, 0]]]),
            _tensor(1, 1, 2, base=2),
            _ape(4, 2),
            session_ids=_sessions(1, "sequence-subclass"),
            start_pos=1,
        )


@pytest.mark.parametrize(
    ("kv", "scores", "ape", "match"),
    [
        ((), (((0, 0),),), ((0, 0),) * 4, "batch extent"),
        ((((),),), (((0, 0),),), ((0, 0),) * 4, "value axis"),
        (
            (((0, 0),), ((0, 0),)),
            (((0, 0),),),
            ((0, 0),) * 4,
            "active batches",
        ),
        (
            (((0, 0),),),
            (((0, 0), (0, 0)),),
            ((0, 0),) * 4,
            "sequence axis",
        ),
        (
            (((0,),),),
            (((0, 0),),),
            ((0, 0),) * 4,
            "value axis",
        ),
        (
            (((0, 0),),),
            (((0,),),),
            ((0, 0),) * 4,
            "value axis",
        ),
        (
            (((0, 0),),),
            (((0, 0),),),
            ((0, 0),) * 3,
            "exactly 4 rows",
        ),
        (
            (((0, 0),),),
            (((0, 0),),),
            ((0, 0), (0, 0), (0,), (0, 0)),
            "exactly 2 values",
        ),
    ],
)
def test_malformed_source_and_ape_axes_fail_closed(
    kv: object,
    scores: object,
    ape: object,
    match: str,
) -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    with pytest.raises(CompressionStateReferenceError, match=match):
        compress_state_update_f32(
            state,
            kv,
            scores,
            ape,
            session_ids=_sessions(1, "malformed-input"),
            start_pos=0,
        )


def test_ragged_batches_and_rows_fail_closed_before_commit() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1)
    with pytest.raises(CompressionStateReferenceError, match="rectangular.*sequence"):
        compress_state_update_f32(
            state,
            (((0, 0),), ((0, 0), (0, 0))),
            (((0, 0),), ((0, 0), (0, 0))),
            ((0, 0),) * 4,
            session_ids=_sessions(2, "ragged-sequence"),
            start_pos=0,
        )
    with pytest.raises(CompressionStateReferenceError, match="rectangular.*value"):
        compress_state_update_f32(
            state,
            (((0, 0), (0,)),),
            (((0, 0), (0, 0)),),
            ((0, 0),) * 4,
            session_ids=_sessions(1, "ragged-value"),
            start_pos=0,
        )


@pytest.mark.parametrize(
    ("bad_code", "match"),
    [
        (True, "32-bit binary32"),
        (False, "32-bit binary32"),
        (1.0, "32-bit binary32"),
        (-1, "32-bit binary32"),
        (1 << 32, "32-bit binary32"),
        (0x7F800000, "finite binary32"),
        (0xFF800000, "finite binary32"),
        (0x7FC00001, "finite binary32"),
        (0xFFC00001, "finite binary32"),
    ],
)
@pytest.mark.parametrize("target", ["kv", "scores", "ape"])
def test_invalid_or_nonfinite_transaction_inputs_fail_closed(
    bad_code: object,
    match: str,
    target: str,
) -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    kv: object = [[[0, 0]]]
    scores: object = [[[0, 0]]]
    ape: object = [[0, 0] for _ in range(4)]
    if target == "kv":
        kv = [[[bad_code, 0]]]
    elif target == "scores":
        scores = [[[bad_code, 0]]]
    else:
        ape = [[bad_code, 0], [0, 0], [0, 0], [0, 0]]
    with pytest.raises(CompressionStateReferenceError, match=match):
        compress_state_update_f32(
            state,
            kv,
            scores,
            ape,
            session_ids=_sessions(1, "invalid-f32"),
            start_pos=1,
        )


def test_only_negative_infinity_score_state_sentinel_is_admitted() -> None:
    kv = (((0, 0),) * 8,)
    valid_scores = (((F32_NEGATIVE_INFINITY, F32_NEGATIVE_INFINITY),) * 8,)
    lanes = (CompressionLaneState(_session("score-sentinel"), 1, 1),)
    state = compression_state_f32(kv, valid_scores, lanes, ratio=4)
    assert state.score_f32_codes == valid_scores

    for bad_score in (0x7F800000, 0x7FC00001):
        poisoned = CompressionState(
            4,
            kv,
            (((bad_score, 0),) + ((0, 0),) * 7,),
            lanes,
        )
        with pytest.raises(CompressionStateReferenceError, match="sentinel"):
            compress_state_update_f32(
                poisoned,
                [[[0, 0]]],
                [[[0, 0]]],
                [[0, 0] for _ in range(4)],
                session_ids=(lanes[0].session_id,),
                start_pos=1,
            )


def test_invalid_untouched_state_and_ape_add_overflow_abort_transaction() -> None:
    valid = zero_compression_state_f32(ratio=4, batch_capacity=2, head_dim=1)
    poisoned_kv = [[list(row) for row in sequence] for sequence in valid.kv_f32_codes]
    poisoned_kv[1][0][0] = 0x7F800000
    poisoned = CompressionState(
        4,
        tuple(tuple(tuple(row) for row in sequence) for sequence in poisoned_kv),
        valid.score_f32_codes,
        valid.lanes,
    )
    with pytest.raises(CompressionStateReferenceError, match="finite binary32"):
        compress_state_update_f32(
            poisoned,
            [[[0, 0]]],
            [[[0, 0]]],
            [[0, 0] for _ in range(4)],
            session_ids=_sessions(1, "poisoned-state"),
            start_pos=1,
        )

    sessions = _sessions(1, "overflow-atomicity")
    causal = compression_state_f32(
        valid.kv_f32_codes,
        valid.score_f32_codes,
        (
            CompressionLaneState(sessions[0], 4, 1),
            CompressionLaneState(None, 0, 0),
        ),
        ratio=4,
    )
    before = causal
    max_finite = 0x7F7FFFFF
    with pytest.raises(CompressionStateReferenceError, match="arithmetic failed"):
        compress_state_update_f32(
            causal,
            [[[0, 0]]],
            [[[max_finite, 0]]],
            [[max_finite, 0], [0, 0], [0, 0], [0, 0]],
            session_ids=sessions,
            start_pos=4,
        )
    assert causal == before
    assert causal.lanes[0] == CompressionLaneState(sessions[0], 4, 1)


def test_overlap_prefill_evaluates_ape_on_a_field_later_replaced_by_padding() -> None:
    state = zero_compression_state_f32(ratio=4, batch_capacity=1, head_dim=1)
    before = state
    max_finite = 0x7F7FFFFF
    kv = (((0, 0),) * 8,)
    scores = ((((max_finite, 0),) + ((0, 0),) * 7),)
    ape = ((max_finite, 0), (0, 0), (0, 0), (0, 0))

    # Group zero's first feature half becomes -infinity padding in
    # overlap_transform.  The source nevertheless evaluates score + APE over
    # the complete full-width prefix before that transform.
    with pytest.raises(CompressionStateReferenceError, match="arithmetic failed"):
        compress_state_update_f32(
            state,
            kv,
            scores,
            ape,
            session_ids=_sessions(1, "prefill-poison"),
            start_pos=0,
        )
    assert state == before


def test_result_and_counter_contracts_are_frozen_and_physically_agnostic() -> None:
    assert {field.name for field in fields(CompressionStateUpdateResult)} == {
        "state",
        "mode",
        "start_pos",
        "end_pos",
        "prefill_cutoff",
        "prefill_remainder",
        "decode_phase",
        "should_compress",
        "pool_inputs",
        "counters",
    }
    assert {field.name for field in fields(CompressionPoolInputs)} == {
        "kv_f32_codes",
        "score_f32_codes",
    }
    counter_names = {field.name for field in fields(CompressionStateCounters)}
    assert counter_names == {
        "active_batch_count",
        "state_batch_capacity",
        "sequence_length",
        "ratio",
        "overlap",
        "head_dim",
        "projected_width",
        "complete_group_count",
        "input_kv_f32_values",
        "input_score_f32_values",
        "logical_source_kv_f32_values_read",
        "logical_source_score_f32_values_read",
        "logical_source_kv_read_bytes",
        "logical_source_score_read_bytes",
        "logical_ape_f32_values_read",
        "logical_ape_read_bytes",
        "logical_score_ape_additions",
        "logical_kv_state_f32_values_read",
        "logical_score_state_f32_values_read",
        "logical_kv_state_read_bytes",
        "logical_score_state_read_bytes",
        "logical_kv_state_f32_values_written",
        "logical_score_state_f32_values_written",
        "logical_kv_state_write_bytes",
        "logical_score_state_write_bytes",
        "kv_state_f32_values_preserved",
        "score_state_f32_values_preserved",
        "pool_kv_f32_values",
        "pool_score_f32_values",
        "overlap_pool_zero_f32_values",
        "overlap_pool_negative_infinity_f32_values",
        "kv_state_roll_f32_values",
        "score_state_roll_f32_values",
        "kv_state_reset_f32_values",
        "score_state_reset_f32_values",
        "lane_metadata_records_read",
        "lane_metadata_read_bytes",
        "lane_metadata_records_written",
        "lane_metadata_write_bytes",
        "lane_metadata_records_preserved",
        "logical_ratio_modulo_evaluations",
        "transaction_commits",
    }
    prohibited = (
        "hbm",
        "cycle",
        "latency",
        "bandwidth",
        "burst",
        "energy",
        "area",
        "ppa",
    )
    assert not any(token in name for name in counter_names for token in prohibited)
