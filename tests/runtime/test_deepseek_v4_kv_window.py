from __future__ import annotations

import copy
from dataclasses import FrozenInstanceError, fields, replace
import hashlib
import json
from pathlib import Path
import random
import re

import pytest

import runtime.reference.kv_window as kv


class _ListSubclass(list):
    pass


class _StateSubclass(kv.KVWindowState):
    pass


def _sid(value: int) -> str:
    return f"{value:064x}"


def _row(tag: int, *, heads: int = 1, width: int = 2) -> kv.BF16HeadRow:
    return tuple(
        tuple(
            1 + ((tag * 131 + head * width * 17 + column * 17) % 0x7E00)
            for column in range(width)
        )
        for head in range(heads)
    )


def _input_values(
    *,
    batches: int,
    sequence: int,
    heads: int = 1,
    width: int = 2,
    base: int = 10,
) -> kv.BF16InputTensor:
    return tuple(
        tuple(
            _row(base + batch * 1_000 + position, heads=heads, width=width)
            for position in range(sequence)
        )
        for batch in range(batches)
    )


def _mutable(value: object) -> object:
    if isinstance(value, tuple):
        return [_mutable(element) for element in value]
    return value


def _write_prefill(
    state: kv.KVWindowState,
    session_ids: tuple[str, ...],
    *,
    sequence: int,
    base: int = 10,
) -> tuple[kv.KVWindowWriteResult, kv.BF16InputTensor]:
    heads = len(state.bf16_codes[0][0])
    width = len(state.bf16_codes[0][0][0])
    incoming = _input_values(
        batches=len(session_ids),
        sequence=sequence,
        heads=heads,
        width=width,
        base=base,
    )
    return (
        kv.kv_window_write_bf16(
            state,
            incoming,
            active_session_ids=session_ids,
            expected_state_versions=state.versions,
            start_pos=0,
        ),
        incoming,
    )


def _write_decode(
    state: kv.KVWindowState,
    session_ids: tuple[str, ...],
    *,
    start_pos: int,
    base: int,
) -> tuple[kv.KVWindowWriteResult, kv.BF16InputTensor]:
    heads = len(state.bf16_codes[0][0])
    width = len(state.bf16_codes[0][0][0])
    incoming = _input_values(
        batches=len(session_ids),
        sequence=1,
        heads=heads,
        width=width,
        base=base,
    )
    return (
        kv.kv_window_write_bf16(
            state,
            incoming,
            active_session_ids=session_ids,
            expected_state_versions=state.versions,
            start_pos=start_pos,
        ),
        incoming,
    )


def _assert_window_reconciliation(result: kv.KVWindowWriteResult) -> None:
    counters = result.counters
    assert (
        counters.valid_window_rows_before
        - counters.valid_window_rows_invalidated
        + counters.logical_state_rows_written
        == counters.valid_window_rows_after
    )


def _compact_source(value: str) -> str:
    return re.sub(r"[\s()]", "", value)


def test_reference_is_bound_to_the_frozen_official_release() -> None:
    assert kv.MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert kv.MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert kv.MODEL_CONFIG_PATH == "config.json"
    assert kv.MODEL_CONFIG_SHA256 == (
        "6c8f3d2d3b48707541b88f32f22ef3f0f8a6b57d8523281e2b8d3cdb0ae9a023"
    )
    assert kv.MODEL_CONFIG_MAX_POSITION_FIELD == "max_position_embeddings"
    assert kv.MODEL_CONFIG_MAX_POSITION_EMBEDDINGS == 1_048_576
    assert kv.MODEL_CONFIG_MAX_POSITION_ANCHOR == (
        "config.json",
        kv.MODEL_CONFIG_SHA256,
        "max_position_embeddings",
        1_048_576,
    )
    assert kv.MODEL_SOURCE_PATH == "inference/model.py"
    assert kv.MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert kv.INFERENCE_CONFIG_PATH == "inference/config.json"
    assert kv.INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert kv.KV_WINDOW_PROFILE == "opentallas.deepseek_v4_kv_window_write.v2"
    assert kv.KV_WINDOW_VALID_VIEW_PROFILE == (
        "opentallas.deepseek_v4_kv_window_valid_view.v1"
    )
    assert kv.PINNED_MAX_BATCH_SIZE == 4
    assert kv.PINNED_MAX_POSITION == kv.MODEL_CONFIG_MAX_POSITION_EMBEDDINGS
    assert kv.PINNED_WINDOW_SIZE == 128
    assert kv.PINNED_KV_HEAD_COUNT == 1
    assert kv.PINNED_KV_VALUE_WIDTH == 512
    assert kv.PINNED_KV_ROW_WIDTH == 512
    assert kv.PINNED_QUERY_HEAD_COUNT == 64
    assert kv.BF16_BYTES == 2


def test_cached_official_config_inference_config_and_source_when_available() -> None:
    snapshot = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731"
        / "snapshots"
        / kv.MODEL_REVISION
    )
    cached_config = snapshot / kv.MODEL_CONFIG_PATH
    cached_inference_config = snapshot / kv.INFERENCE_CONFIG_PATH
    cached_source = snapshot / kv.MODEL_SOURCE_PATH
    if not all(
        path.is_file()
        for path in (cached_config, cached_inference_config, cached_source)
    ):
        pytest.skip("pinned official release files are not all in the local HF cache")

    config_bytes = cached_config.read_bytes()
    assert hashlib.sha256(config_bytes).hexdigest() == kv.MODEL_CONFIG_SHA256
    config = json.loads(config_bytes)
    assert config[kv.MODEL_CONFIG_MAX_POSITION_FIELD] == (
        kv.MODEL_CONFIG_MAX_POSITION_EMBEDDINGS
    )
    assert kv.PINNED_MAX_POSITION == config["max_position_embeddings"]

    inference_config_bytes = cached_inference_config.read_bytes()
    assert (
        hashlib.sha256(inference_config_bytes).hexdigest() == kv.INFERENCE_CONFIG_SHA256
    )
    source_bytes = cached_source.read_bytes()
    assert hashlib.sha256(source_bytes).hexdigest() == kv.MODEL_SOURCE_SHA256
    compact_source = _compact_source(source_bytes.decode("utf-8"))
    for assignment in kv.SOURCE_ASSIGNMENTS:
        assert _compact_source(assignment) in compact_source


def test_synthetic_small_cases_have_explicitly_structural_claim_limits() -> None:
    assert set(kv.EXCLUDED_CLAIMS) == {
        "kv_projection_normalization_rope_or_qdq",
        "sparse_attention_or_attention_kv_composition",
        "checkpoint_numeric_output_evidence",
        "compiler_lowering",
        "service_or_rtl_execution",
        "atomic_service_compare_and_swap",
        "cryptographic_or_authenticated_transition_origin",
        "physical_hbm_sram_cycles_latency_bandwidth_energy_area_routing_ppa",
        "end_to_end_model_execution",
    }
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=2,
        kv_value_width=3,
    )
    result, _ = _write_prefill(state, (_sid(1),), sequence=1)
    assert result.counters.kv_head_count * result.counters.kv_value_width == 6
    assert result.counters.kv_head_count * result.counters.kv_value_width < 512


def test_default_zero_state_has_official_axes_and_zero_metadata() -> None:
    state = kv.zero_kv_window_state_bf16()
    assert len(state.bf16_codes) == 4
    assert len(state.bf16_codes[0]) == 128
    assert len(state.bf16_codes[0][0]) == 1
    assert len(state.bf16_codes[0][0][0]) == 512
    assert state.bf16_codes[3][127][0] == (0,) * 512
    assert state.session_ids == (None,) * 4
    assert state.lane_active == (False,) * 4
    assert state.next_positions == (0,) * 4
    assert state.versions == (0,) * 4
    assert isinstance(state.bf16_codes, tuple)
    assert isinstance(state.bf16_codes[0][0][0], tuple)
    with pytest.raises(FrozenInstanceError):
        state.bf16_codes = ()  # type: ignore[misc]


def test_zero_state_view_exposes_no_capacity_rows() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=5,
        kv_head_count=1,
        kv_value_width=1,
    )
    view = kv.kv_window_valid_view_bf16(
        state,
        expected_state_versions=state.versions,
        active_session_ids=(),
    )
    assert view.profile == kv.KV_WINDOW_VALID_VIEW_PROFILE
    assert view.bf16_codes == ()
    assert view.session_ids == ()
    assert view.absolute_position_starts == ()
    assert view.next_positions == ()
    assert view.versions == ()
    assert view.counters.valid_rows_returned == 0
    assert view.counters.inactive_capacity_rows_excluded == 15
    assert view.counters.total_state_rows_not_exposed == 15
    assert view.counters.transaction_commits == 0


def test_short_prefill_commits_sessions_and_excludes_stale_slots_from_view() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=5,
        kv_head_count=2,
        kv_value_width=2,
    )
    old_sessions = (_sid(1), _sid(2), _sid(3))
    stale_prefill, stale_payload = _write_prefill(
        zero,
        old_sessions,
        sequence=5,
        base=100,
    )
    retired = kv.kv_window_retire_bf16(
        stale_prefill.state,
        expected_state_versions=stale_prefill.state.versions,
        expected_active_session_ids=old_sessions,
        retired_session_ids=old_sessions,
    )
    assert retired.state.bf16_codes == stale_payload
    assert retired.state.lane_active == (False, False, False)
    assert retired.state.versions == (2, 2, 2)

    sessions = (_sid(10), _sid(11))
    result, incoming = _write_prefill(
        retired.state,
        sessions,
        sequence=3,
        base=20,
    )

    assert result.mode == "prefill"
    assert result.start_pos == 0
    assert result.end_pos == 3
    assert result.active_session_ids == sessions
    assert result.segments == (kv.KVWindowWriteSegment(0, 3, 0, 3, 0, 3),)
    assert result.state.session_ids == (_sid(10), _sid(11), _sid(3))
    assert result.state.lane_active == (True, True, False)
    assert result.state.next_positions == (3, 3, 0)
    assert result.state.versions == (3, 3, 2)
    for batch in range(2):
        assert result.state.bf16_codes[batch][:3] == incoming[batch]
        assert result.state.bf16_codes[batch][3:] == stale_payload[batch][3:]
    assert result.state.bf16_codes[2] == stale_payload[2]

    view = kv.kv_window_valid_view_bf16(
        result.state,
        expected_state_versions=result.state.versions,
        active_session_ids=sessions,
    )
    assert view.bf16_codes == incoming
    assert view.absolute_position_starts == (0, 0)
    assert view.next_positions == (3, 3)
    assert view.versions == (3, 3)
    assert view.counters.active_capacity_rows_excluded == 4
    assert view.counters.inactive_capacity_rows_excluded == 5
    _assert_window_reconciliation(result)


@pytest.mark.parametrize("sequence", [4, 8])
def test_exact_window_and_exact_multiple_prefill_mapping(sequence: int) -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    result, incoming = _write_prefill(state, (_sid(1),), sequence=sequence)
    assert result.state.bf16_codes[0] == incoming[0][-4:]
    view = kv.kv_window_valid_view_bf16(
        result.state,
        expected_state_versions=result.state.versions,
        active_session_ids=(_sid(1),),
    )
    assert view.bf16_codes[0] == incoming[0][-4:]
    assert view.absolute_position_starts == (sequence - 4,)
    if sequence == 4:
        assert result.segments == (kv.KVWindowWriteSegment(0, 4, 0, 4, 0, 4),)
        assert result.counters.source_slice_assignments == 1
        assert result.counters.logical_slot_modulo_evaluations == 0
    else:
        assert result.segments == (kv.KVWindowWriteSegment(4, 8, 4, 8, 0, 4),)
        assert result.counters.source_slice_assignments == 2
        assert result.counters.nonempty_source_slice_assignments == 1
        assert result.counters.logical_slot_modulo_evaluations == 1
    _assert_window_reconciliation(result)


def test_long_prefill_preserves_official_physical_split_and_chronological_view() -> (
    None
):
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    sessions = (_sid(1), _sid(2))
    result, incoming = _write_prefill(state, sessions, sequence=6, base=30)
    assert result.segments == (
        kv.KVWindowWriteSegment(2, 4, 2, 4, 2, 4),
        kv.KVWindowWriteSegment(4, 6, 4, 6, 0, 2),
    )
    for batch in range(2):
        assert result.state.bf16_codes[batch] == (
            incoming[batch][4],
            incoming[batch][5],
            incoming[batch][2],
            incoming[batch][3],
        )
    view = kv.kv_window_valid_view_bf16(
        result.state,
        expected_state_versions=result.state.versions,
        active_session_ids=sessions,
    )
    assert view.bf16_codes == tuple(sequence[-4:] for sequence in incoming)
    assert view.absolute_position_starts == (2, 2)
    assert view.next_positions == (6, 6)
    assert result.counters.input_rows == 12
    assert result.counters.logical_source_rows_read == 8
    assert result.counters.uncommitted_positions_per_batch == 2
    _assert_window_reconciliation(result)


def test_window_size_one_prefill_and_decode_are_exact() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=1,
        kv_head_count=1,
        kv_value_width=1,
    )
    session = (_sid(1),)
    prefill, incoming = _write_prefill(state, session, sequence=3, base=40)
    assert prefill.state.bf16_codes[0] == (incoming[0][-1],)
    assert prefill.counters.valid_window_rows_invalidated == 0

    decoded, decode_input = _write_decode(
        prefill.state,
        session,
        start_pos=3,
        base=90,
    )
    assert decoded.state.bf16_codes[0] == (decode_input[0][0],)
    assert decoded.counters.valid_window_rows_before == 1
    assert decoded.counters.valid_window_rows_invalidated == 1
    assert decoded.counters.valid_window_rows_after == 1
    view = kv.kv_window_valid_view_bf16(
        decoded.state,
        expected_state_versions=decoded.state.versions,
        active_session_ids=session,
    )
    assert view.bf16_codes == ((decode_input[0][0],),)
    assert view.absolute_position_starts == (3,)
    assert view.next_positions == (4,)
    _assert_window_reconciliation(decoded)


def test_signed_zero_and_subnormal_bf16_encodings_are_preserved_bit_exactly() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=6,
    )
    encodings = (0x0000, 0x8000, 0x0001, 0x007F, 0x8001, 0x807F)
    incoming = (((encodings,),),)
    result = kv.kv_window_write_bf16(
        state,
        incoming,
        active_session_ids=(_sid(1),),
        expected_state_versions=state.versions,
        start_pos=0,
    )
    assert result.state.bf16_codes[0][0][0] == encodings
    view = kv.kv_window_valid_view_bf16(
        result.state,
        expected_state_versions=result.state.versions,
        active_session_ids=(_sid(1),),
    )
    assert view.bf16_codes[0][0][0] == encodings


def test_decode_requires_exact_cursor_and_produces_chronological_wrap_view() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    session = (_sid(1),)
    prefill, prefill_input = _write_prefill(state, session, sequence=3, base=10)
    current = prefill.state
    history = list(prefill_input[0])

    for start_pos, base in ((3, 30), (4, 40), (5, 50)):
        decoded, incoming = _write_decode(
            current,
            session,
            start_pos=start_pos,
            base=base,
        )
        assert decoded.mode == "decode"
        assert decoded.start_pos == start_pos
        assert decoded.end_pos == start_pos + 1
        assert decoded.segments == (
            kv.KVWindowWriteSegment(
                0,
                1,
                start_pos,
                start_pos + 1,
                start_pos % 4,
                start_pos % 4 + 1,
            ),
        )
        history.append(incoming[0][0])
        view = kv.kv_window_valid_view_bf16(
            decoded.state,
            expected_state_versions=decoded.state.versions,
            active_session_ids=session,
        )
        assert view.bf16_codes[0] == tuple(history[-4:])
        assert view.absolute_position_starts == (start_pos + 1 - 4,)
        assert view.next_positions == (start_pos + 1,)
        assert view.versions == (start_pos - 1,)
        _assert_window_reconciliation(decoded)
        current = decoded.state


@pytest.mark.parametrize(
    ("start_pos", "session", "message"),
    [
        (2, _sid(1), "expected next_pos 3"),
        (4, _sid(1), "expected next_pos 3"),
        (3, _sid(2), "session identity mismatch"),
    ],
)
def test_decode_rejects_replay_skip_and_session_mismatch(
    start_pos: int,
    session: str,
    message: str,
) -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    prefill, _ = _write_prefill(state, (_sid(1),), sequence=3)
    incoming = _input_values(batches=1, sequence=1, width=1)
    with pytest.raises(kv.KVWindowReferenceError, match=message):
        kv.kv_window_write_bf16(
            prefill.state,
            incoming,
            active_session_ids=(session,),
            expected_state_versions=prefill.state.versions,
            start_pos=start_pos,
        )


def test_decode_rejects_multirow_input_even_at_the_exact_cursor() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    prefill, _ = _write_prefill(state, (_sid(1),), sequence=2)
    incoming = _input_values(batches=1, sequence=2, width=1)
    with pytest.raises(kv.KVWindowReferenceError, match="sequence length exactly 1"):
        kv.kv_window_write_bf16(
            prefill.state,
            incoming,
            active_session_ids=(_sid(1),),
            expected_state_versions=prefill.state.versions,
            start_pos=2,
        )


def test_trailing_lane_retirement_keeps_tombstone_and_invalidates_its_view() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2), _sid(3))
    prefill, _ = _write_prefill(state, sessions, sequence=2)
    retired_payload = prefill.state.bf16_codes[2]
    decoded, _ = _write_decode(
        prefill.state,
        sessions[:2],
        start_pos=2,
        base=50,
    )

    assert decoded.state.session_ids == sessions
    assert decoded.state.lane_active == (True, True, False)
    assert decoded.state.next_positions == (3, 3, 0)
    assert decoded.state.versions == (2, 2, 2)
    assert decoded.state.bf16_codes[2] == retired_payload
    assert decoded.counters.previous_active_batch_count == 3
    assert decoded.counters.removed_batch_count == 1
    assert decoded.counters.valid_window_rows_invalidated == 2
    view = kv.kv_window_valid_view_bf16(
        decoded.state,
        expected_state_versions=decoded.state.versions,
        active_session_ids=sessions[:2],
    )
    assert len(view.bf16_codes) == 2
    assert view.counters.inactive_capacity_rows_excluded == 4
    _assert_window_reconciliation(decoded)

    with pytest.raises(kv.KVWindowReferenceError, match="cannot reactivate"):
        kv.kv_window_write_bf16(
            decoded.state,
            _input_values(batches=3, sequence=1, width=1),
            active_session_ids=sessions,
            expected_state_versions=decoded.state.versions,
            start_pos=3,
        )


def test_reactivation_requires_fresh_prefill_and_entirely_new_identities() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    old_sessions = (_sid(1), _sid(2), _sid(3))
    prefill, _ = _write_prefill(state, old_sessions, sequence=2)
    shrunk, _ = _write_decode(
        prefill.state,
        old_sessions[:2],
        start_pos=2,
        base=20,
    )

    with pytest.raises(kv.KVWindowReferenceError, match="new identity"):
        _write_prefill(
            shrunk.state,
            (_sid(10), _sid(11), old_sessions[2]),
            sequence=1,
        )

    new_sessions = (_sid(10), _sid(11), _sid(12))
    restarted, incoming = _write_prefill(
        shrunk.state,
        new_sessions,
        sequence=1,
        base=70,
    )
    assert restarted.state.session_ids == new_sessions
    assert restarted.state.lane_active == (True, True, True)
    assert restarted.state.next_positions == (1, 1, 1)
    assert restarted.state.versions == (3, 3, 3)
    view = kv.kv_window_valid_view_bf16(
        restarted.state,
        expected_state_versions=restarted.state.versions,
        active_session_ids=new_sessions,
    )
    assert view.bf16_codes == incoming


def test_explicit_suffix_retirement_preserves_payload_and_tombstones() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=4,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    sessions = (_sid(1), _sid(2), _sid(3))
    prefill, _ = _write_prefill(state, sessions, sequence=3)
    payload_before = prefill.state.bf16_codes

    retired = kv.kv_window_retire_bf16(
        prefill.state,
        expected_state_versions=prefill.state.versions,
        expected_active_session_ids=list(sessions),
        retired_session_ids=list(sessions[1:]),
    )
    assert retired.profile == kv.KV_WINDOW_RETIRE_PROFILE
    assert retired.previous_active_session_ids == sessions
    assert retired.active_session_ids == sessions[:1]
    assert retired.retired_session_ids == sessions[1:]
    assert retired.retired_next_positions == (3, 3)
    assert retired.retired_previous_versions == (1, 1)
    assert retired.state.profile == kv.KV_WINDOW_PROFILE
    assert retired.state.bf16_codes == payload_before
    assert retired.state.session_ids == sessions + (None,)
    assert retired.state.lane_active == (True, False, False, False)
    assert retired.state.next_positions == (3, 0, 0, 0)
    assert retired.state.versions == (1, 2, 2, 0)

    counters = retired.counters
    assert counters.previous_active_batch_count == 3
    assert counters.active_batch_count == 1
    assert counters.retired_batch_count == 2
    assert counters.logical_state_rows_read == 0
    assert counters.logical_state_rows_written == 0
    assert counters.state_rows_preserved == 16
    assert counters.state_bf16_values_preserved == 32
    assert counters.valid_window_rows_before == 9
    assert counters.valid_window_rows_invalidated == 6
    assert counters.valid_window_rows_after == 3
    assert counters.logical_session_ids_read == 3
    assert counters.logical_lane_active_flags_read == 4
    assert counters.logical_lane_active_flags_written == 2
    assert counters.logical_next_positions_read == 3
    assert counters.logical_next_positions_written == 2
    assert counters.logical_versions_read == 2
    assert counters.logical_versions_written == 2
    assert counters.logical_metadata_fields_read == 12
    assert counters.logical_metadata_fields_written == 6
    assert counters.transaction_commits == 1


def test_explicit_retirement_can_reach_zero_active_lanes() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=4)
    retired = kv.kv_window_retire_bf16(
        prefill.state,
        expected_state_versions=prefill.state.versions,
        expected_active_session_ids=sessions,
        retired_session_ids=sessions,
    )
    assert retired.active_session_ids == ()
    assert retired.state.session_ids == sessions
    assert retired.state.lane_active == (False, False)
    assert retired.state.next_positions == (0, 0)
    assert retired.state.versions == (2, 2)
    assert retired.counters.valid_window_rows_before == 6
    assert retired.counters.valid_window_rows_invalidated == 6
    assert retired.counters.valid_window_rows_after == 0
    view = kv.kv_window_valid_view_bf16(
        retired.state,
        expected_state_versions=retired.state.versions,
        active_session_ids=(),
    )
    assert view.bf16_codes == ()
    assert view.counters.inactive_capacity_rows_excluded == 6

    new_sessions = (_sid(10), _sid(11))
    restarted, restarted_input = _write_prefill(
        retired.state,
        new_sessions,
        sequence=2,
        base=70,
    )
    assert restarted.state.session_ids == new_sessions
    assert restarted.state.lane_active == (True, True)
    assert restarted.state.next_positions == (2, 2)
    assert restarted.state.versions == (3, 3)
    restarted_view = kv.kv_window_valid_view_bf16(
        restarted.state,
        expected_state_versions=restarted.state.versions,
        active_session_ids=new_sessions,
    )
    assert restarted_view.bf16_codes == restarted_input
    decoded, _ = _write_decode(
        restarted.state,
        new_sessions,
        start_pos=2,
        base=90,
    )
    assert decoded.state.next_positions == (3, 3)
    assert decoded.state.versions == (4, 4)


@pytest.mark.parametrize(
    ("expected", "retired", "message"),
    [
        ((_sid(1), _sid(2), _sid(3)), (_sid(2),), "trailing suffix"),
        ((_sid(1), _sid(2), _sid(3)), (_sid(4),), "trailing suffix"),
        ((_sid(1), _sid(9), _sid(3)), (_sid(3),), "do not match"),
        ((_sid(1), _sid(2)), (_sid(2),), "identify every"),
        ((_sid(1), _sid(2), _sid(3)), (), "extent"),
    ],
)
def test_explicit_retirement_rejects_middle_nonmatching_and_incomplete_authority(
    expected: tuple[str, ...],
    retired: tuple[str, ...],
    message: str,
) -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2), _sid(3))
    prefill, _ = _write_prefill(state, sessions, sequence=1)
    with pytest.raises(kv.KVWindowReferenceError, match=message):
        kv.kv_window_retire_bf16(
            prefill.state,
            expected_state_versions=prefill.state.versions,
            expected_active_session_ids=expected,
            retired_session_ids=retired,
        )


def test_retirement_version_overflow_poisons_without_mutation() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=1)
    overflow = replace(
        prefill.state,
        versions=(1, kv.MAX_STATE_VERSION),
    )
    snapshot = copy.deepcopy(overflow)
    with pytest.raises(kv.KVWindowReferenceError, match="version overflow for lane 1"):
        kv.kv_window_retire_bf16(
            overflow,
            expected_state_versions=overflow.versions,
            expected_active_session_ids=sessions,
            retired_session_ids=sessions[1:],
        )
    assert overflow == snapshot


def test_retirement_rejects_an_already_inactive_state() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    with pytest.raises(kv.KVWindowReferenceError, match="inactive state"):
        kv.kv_window_retire_bf16(
            state,
            expected_state_versions=state.versions,
            expected_active_session_ids=(_sid(1),),
            retired_session_ids=(_sid(1),),
        )


def test_valid_view_requires_the_exact_active_identity_prefix() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=1)
    for supplied in ((), sessions[:1], (sessions[0], _sid(3))):
        with pytest.raises(kv.KVWindowReferenceError):
            kv.kv_window_valid_view_bf16(
                prefill.state,
                expected_state_versions=prefill.state.versions,
                active_session_ids=supplied,
            )


def test_fresh_prefill_metadata_and_payload_counters_reconcile_exactly() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    result, _ = _write_prefill(state, (_sid(1), _sid(2)), sequence=2)
    assert result.counters == kv.KVWindowWriteCounters(
        active_batch_count=2,
        previous_active_batch_count=0,
        removed_batch_count=0,
        state_batch_capacity=3,
        sequence_length=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
        input_rows=4,
        input_bf16_values=8,
        committed_positions_per_batch=2,
        uncommitted_positions_per_batch=0,
        logical_source_rows_read=4,
        logical_source_bf16_values_read=8,
        logical_source_read_bytes=16,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=4,
        logical_state_bf16_values_written=8,
        logical_state_write_bytes=16,
        state_rows_preserved=8,
        state_bf16_values_preserved=16,
        valid_window_rows_before=0,
        valid_window_rows_invalidated=0,
        valid_window_rows_after=4,
        source_slice_assignments=1,
        nonempty_source_slice_assignments=1,
        logical_slot_modulo_evaluations=0,
        logical_session_ids_read=3,
        logical_session_ids_written=2,
        logical_lane_active_flags_read=3,
        logical_lane_active_flags_written=2,
        logical_next_positions_read=0,
        logical_next_positions_written=2,
        logical_versions_read=2,
        logical_versions_written=2,
        logical_metadata_fields_read=8,
        logical_metadata_fields_written=8,
        transaction_commits=1,
    )
    _assert_window_reconciliation(result)


def test_full_window_decode_counts_overwrite_and_retirement_invalidation() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=3)
    decoded, _ = _write_decode(
        prefill.state,
        sessions[:1],
        start_pos=3,
        base=70,
    )
    counters = decoded.counters
    assert counters.valid_window_rows_before == 6
    assert counters.valid_window_rows_invalidated == 4
    assert counters.valid_window_rows_after == 3
    assert counters.logical_state_rows_written == 1
    assert counters.logical_session_ids_read == 1
    assert counters.logical_lane_active_flags_read == 2
    assert counters.logical_next_positions_read == 2
    assert counters.logical_versions_read == 2
    assert counters.logical_metadata_fields_read == 7
    assert counters.logical_session_ids_written == 0
    assert counters.logical_lane_active_flags_written == 1
    assert counters.logical_next_positions_written == 2
    assert counters.logical_versions_written == 2
    assert counters.logical_metadata_fields_written == 5
    _assert_window_reconciliation(decoded)


def test_valid_view_counters_reconcile_payload_and_excluded_capacity() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=2,
        kv_value_width=3,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=2)
    view = kv.kv_window_valid_view_bf16(
        prefill.state,
        expected_state_versions=prefill.state.versions,
        active_session_ids=sessions,
    )
    counters = view.counters
    assert counters.logical_session_ids_read == 2
    assert counters.logical_lane_active_flags_read == 3
    assert counters.logical_next_positions_read == 2
    assert counters.logical_versions_read == 2
    assert counters.logical_metadata_fields_read == 9
    assert counters.logical_state_rows_read == 4
    assert counters.logical_state_bf16_values_read == 24
    assert counters.logical_state_read_bytes == 48
    assert counters.logical_slot_modulo_evaluations == 4
    assert counters.valid_rows_returned == 4
    assert counters.active_capacity_rows_excluded == 4
    assert counters.inactive_capacity_rows_excluded == 4
    assert counters.total_state_rows_not_exposed == 8
    assert counters.view_evaluations == 1
    assert counters.transaction_commits == 0


def test_version_overflow_poisons_active_write_and_trailing_retirement() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=1)

    active_overflow = replace(
        prefill.state,
        versions=(kv.MAX_STATE_VERSION, 1),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="version overflow for lane 0"):
        _write_decode(active_overflow, sessions, start_pos=1, base=30)

    retirement_overflow = replace(
        prefill.state,
        versions=(1, kv.MAX_STATE_VERSION),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="version overflow for lane 1"):
        _write_decode(retirement_overflow, sessions[:1], start_pos=1, base=30)


def test_version_overflow_poisons_reactivation_of_a_retired_lane() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    retired = kv.KVWindowState(
        profile=kv.KV_WINDOW_PROFILE,
        bf16_codes=zero.bf16_codes,
        session_ids=(_sid(1),),
        lane_active=(False,),
        next_positions=(0,),
        versions=(kv.MAX_STATE_VERSION,),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="version overflow for lane 0"):
        _write_prefill(retired, (_sid(2),), sequence=1)


def test_cursor_maximum_allows_final_position_then_poisons_further_decode() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    state = kv.kv_window_state_bf16(
        kv.KVWindowState(
            profile=kv.KV_WINDOW_PROFILE,
            bf16_codes=zero.bf16_codes,
            session_ids=(_sid(1),),
            lane_active=(True,),
            next_positions=(kv.PINNED_MAX_POSITION - 1,),
            versions=(1,),
        )
    )
    final, _ = _write_decode(
        state,
        (_sid(1),),
        start_pos=kv.PINNED_MAX_POSITION - 1,
        base=90,
    )
    assert final.state.next_positions == (kv.PINNED_MAX_POSITION,)
    with pytest.raises(kv.KVWindowReferenceError, match="start_pos"):
        _write_decode(
            final.state,
            (_sid(1),),
            start_pos=kv.PINNED_MAX_POSITION,
            base=91,
        )


def test_end_position_overflow_poisons_before_decode_commit() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    state = kv.KVWindowState(
        profile=kv.KV_WINDOW_PROFILE,
        bf16_codes=zero.bf16_codes,
        session_ids=(_sid(1),),
        lane_active=(True,),
        next_positions=(kv.PINNED_MAX_POSITION - 1,),
        versions=(1,),
    )
    incoming = _input_values(batches=1, sequence=2, width=1)
    with pytest.raises(kv.KVWindowReferenceError, match="end position exceeds"):
        kv.kv_window_write_bf16(
            state,
            incoming,
            active_session_ids=(_sid(1),),
            expected_state_versions=state.versions,
            start_pos=kv.PINNED_MAX_POSITION - 1,
        )


def test_state_validator_deeply_freezes_exact_state_and_rejects_raw_payload() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    mutable_payload = _mutable(zero.bf16_codes)
    mutable_state = kv.KVWindowState(
        profile=kv.KV_WINDOW_PROFILE,
        bf16_codes=mutable_payload,  # type: ignore[arg-type]
        session_ids=[None],  # type: ignore[arg-type]
        lane_active=[False],  # type: ignore[arg-type]
        next_positions=[0],  # type: ignore[arg-type]
        versions=[0],  # type: ignore[arg-type]
    )
    frozen = kv.kv_window_state_bf16(mutable_state)
    assert frozen == zero
    assert isinstance(frozen.bf16_codes, tuple)
    assert isinstance(frozen.session_ids, tuple)
    mutable_payload[0][0][0][0] = 0x3F80  # type: ignore[index]
    assert frozen.bf16_codes[0][0][0][0] == 0

    with pytest.raises(kv.KVWindowReferenceError, match="exact KVWindowState"):
        kv.kv_window_state_bf16(zero.bf16_codes)
    with pytest.raises(kv.KVWindowReferenceError, match="exact KVWindowState"):
        _StateSubclass(**zero.__dict__)


def test_public_state_rejects_unsynchronized_active_lane_cursors() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    prefill, _ = _write_prefill(state, (_sid(1), _sid(2)), sequence=2)
    with pytest.raises(kv.KVWindowReferenceError, match="synchronized next position"):
        replace(prefill.state, next_positions=(2, 3))


@pytest.mark.parametrize("profile", [True, 0, "wrong.profile"])
def test_state_and_write_result_require_the_exact_semantic_profile(
    profile: object,
) -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    result, _ = _write_prefill(state, (_sid(1),), sequence=1)
    assert result.profile == kv.KV_WINDOW_PROFILE
    assert result.state.profile == kv.KV_WINDOW_PROFILE
    with pytest.raises(kv.KVWindowReferenceError, match="profile"):
        replace(state, profile=profile)
    with pytest.raises(kv.KVWindowReferenceError, match="profile"):
        replace(result, profile=profile)


def test_public_write_segment_constructor_rejects_bool_and_forged_extents() -> None:
    segment = kv.KVWindowWriteSegment(0, 1, 0, 1, 0, 1)
    with pytest.raises(kv.KVWindowReferenceError, match="source_sequence_start"):
        replace(segment, source_sequence_start=True)
    with pytest.raises(kv.KVWindowReferenceError, match="extents"):
        replace(segment, destination_slot_stop=2)
    with pytest.raises(kv.KVWindowReferenceError, match="source_sequence_stop"):
        replace(segment, source_sequence_stop=0)


def test_public_write_counter_constructor_rejects_bool_and_drift() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    result, _ = _write_prefill(state, (_sid(1),), sequence=1)
    with pytest.raises(kv.KVWindowReferenceError, match="nonnegative integer"):
        replace(result.counters, input_rows=True)
    with pytest.raises(kv.KVWindowReferenceError, match="does not reconcile"):
        replace(result.counters, logical_state_rows_written=2)
    with pytest.raises(kv.KVWindowReferenceError, match="exactly one commit"):
        replace(result.counters, transaction_commits=0)


def test_public_write_counters_require_a_reachable_synchronized_mode_pattern() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    first, _ = _write_prefill(state, (_sid(1), _sid(2)), sequence=2)
    restarted, _ = _write_prefill(
        first.state,
        (_sid(3), _sid(4)),
        sequence=1,
    )

    with pytest.raises(kv.KVWindowReferenceError, match="cursor-synchronized"):
        replace(
            restarted.counters,
            valid_window_rows_before=3,
            valid_window_rows_invalidated=3,
        )
    with pytest.raises(kv.KVWindowReferenceError, match="reachable synchronized"):
        replace(
            restarted.counters,
            logical_session_ids_read=1,
            logical_lane_active_flags_read=3,
        )


def test_public_write_result_constructor_freezes_aliases_and_rejects_forgery() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    result, _ = _write_prefill(state, (_sid(1),), sequence=2)
    session_alias = list(result.active_session_ids)
    segment_alias = list(result.segments)
    rebuilt = kv.KVWindowWriteResult(
        profile=result.profile,
        prior_state=result.prior_state,
        input_bf16_codes=result.input_bf16_codes,
        state=result.state,
        mode=result.mode,
        start_pos=result.start_pos,
        end_pos=result.end_pos,
        active_session_ids=session_alias,  # type: ignore[arg-type]
        segments=segment_alias,  # type: ignore[arg-type]
        counters=result.counters,
    )
    session_alias[0] = _sid(9)
    segment_alias.clear()
    assert rebuilt.active_session_ids == (_sid(1),)
    assert rebuilt.segments == result.segments
    assert isinstance(rebuilt.active_session_ids, tuple)
    assert isinstance(rebuilt.segments, tuple)

    with pytest.raises(kv.KVWindowReferenceError, match="mode"):
        replace(result, mode="decode")
    with pytest.raises(kv.KVWindowReferenceError, match="start_pos"):
        replace(result, start_pos=True)
    with pytest.raises(kv.KVWindowReferenceError, match="segments"):
        replace(result, segments=())
    forged_state = replace(result.state, next_positions=(1,))
    with pytest.raises(kv.KVWindowReferenceError, match="exactly reconstruct"):
        replace(result, state=forged_state)


def test_public_write_result_reconciles_prior_cursor_and_removed_tombstones() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    prefill, _ = _write_prefill(state, sessions, sequence=3)
    decoded, _ = _write_decode(
        prefill.state,
        sessions[:1],
        start_pos=3,
        base=50,
    )

    alternate_cursor_counters = replace(
        decoded.counters,
        valid_window_rows_before=4,
        valid_window_rows_invalidated=2,
        valid_window_rows_after=3,
    )
    with pytest.raises(kv.KVWindowReferenceError, match="valid rows before"):
        replace(decoded, counters=alternate_cursor_counters)

    wrong_tombstone_state = replace(
        decoded.state,
        session_ids=(sessions[0], _sid(9)),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="exactly reconstruct"):
        replace(decoded, state=wrong_tombstone_state)

    insufficient_version_state = replace(decoded.state, versions=(1, 2))
    with pytest.raises(kv.KVWindowReferenceError, match="exactly reconstruct"):
        replace(decoded, state=insufficient_version_state)


def test_public_valid_view_evidence_freezes_aliases_and_rejects_forgery() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    write, _ = _write_prefill(state, (_sid(1),), sequence=2)
    view = kv.kv_window_valid_view_bf16(
        write.state,
        expected_state_versions=write.state.versions,
        active_session_ids=(_sid(1),),
    )
    payload_alias = _mutable(view.bf16_codes)
    session_alias = list(view.session_ids)
    start_alias = list(view.absolute_position_starts)
    next_alias = list(view.next_positions)
    version_alias = list(view.versions)
    rebuilt = kv.KVWindowValidViewResult(
        profile=view.profile,
        state=view.state,
        bf16_codes=payload_alias,  # type: ignore[arg-type]
        session_ids=session_alias,  # type: ignore[arg-type]
        absolute_position_starts=start_alias,  # type: ignore[arg-type]
        next_positions=next_alias,  # type: ignore[arg-type]
        versions=version_alias,  # type: ignore[arg-type]
        counters=view.counters,
    )
    payload_alias[0][0][0][0] = 0x4000  # type: ignore[index]
    session_alias[0] = _sid(2)
    start_alias[0] = 1
    next_alias[0] = 1
    version_alias[0] = 9
    assert rebuilt == view
    assert isinstance(rebuilt.bf16_codes, tuple)
    assert isinstance(rebuilt.bf16_codes[0][0][0], tuple)

    with pytest.raises(kv.KVWindowReferenceError, match="profile"):
        replace(view, profile=True)
    with pytest.raises(kv.KVWindowReferenceError, match="nonnegative integer"):
        replace(view.counters, valid_rows_returned=True)
    with pytest.raises(kv.KVWindowReferenceError, match="absolute bounds"):
        replace(view, absolute_position_starts=(1,))
    with pytest.raises(kv.KVWindowReferenceError, match="payload length"):
        replace(view, bf16_codes=(view.bf16_codes[0][:1],))


def test_public_valid_view_evidence_requires_synchronized_lane_windows() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    write, _ = _write_prefill(state, (_sid(1), _sid(2)), sequence=3)
    view = kv.kv_window_valid_view_bf16(
        write.state,
        expected_state_versions=write.state.versions,
        active_session_ids=(_sid(1), _sid(2)),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="cursor-synchronized"):
        replace(view.counters, valid_rows_returned=5)

    mixed_windows = (
        view.bf16_codes[0][:2],
        view.bf16_codes[1] + (view.bf16_codes[1][-1],),
    )
    with pytest.raises(kv.KVWindowReferenceError, match="exactly reconstruct"):
        replace(
            view,
            bf16_codes=mixed_windows,
            absolute_position_starts=(0, 0),
            next_positions=(2, 4),
        )


def test_public_retirement_evidence_freezes_aliases_and_rejects_forgery() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2))
    write, _ = _write_prefill(state, sessions, sequence=1)
    result = kv.kv_window_retire_bf16(
        write.state,
        expected_state_versions=write.state.versions,
        expected_active_session_ids=sessions,
        retired_session_ids=sessions[1:],
    )
    previous_alias = list(result.previous_active_session_ids)
    active_alias = list(result.active_session_ids)
    retired_alias = list(result.retired_session_ids)
    position_alias = list(result.retired_next_positions)
    version_alias = list(result.retired_previous_versions)
    rebuilt = kv.KVWindowRetireResult(
        profile=result.profile,
        prior_state=result.prior_state,
        state=result.state,
        previous_active_session_ids=previous_alias,  # type: ignore[arg-type]
        active_session_ids=active_alias,  # type: ignore[arg-type]
        retired_session_ids=retired_alias,  # type: ignore[arg-type]
        retired_next_positions=position_alias,  # type: ignore[arg-type]
        retired_previous_versions=version_alias,  # type: ignore[arg-type]
        counters=result.counters,
    )
    previous_alias.clear()
    active_alias.clear()
    retired_alias.clear()
    position_alias[0] = 2
    version_alias[0] = 2
    assert rebuilt == result

    with pytest.raises(kv.KVWindowReferenceError, match="profile"):
        replace(result, profile=False)
    with pytest.raises(kv.KVWindowReferenceError, match="nonnegative integer"):
        replace(result.counters, retired_batch_count=True)
    with pytest.raises(kv.KVWindowReferenceError, match="prior metadata"):
        replace(result, retired_next_positions=())
    with pytest.raises(kv.KVWindowReferenceError, match="versions"):
        replace(result, retired_previous_versions=(2,))


def test_public_retirement_evidence_reconciles_the_shared_prior_cursor() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=1,
        kv_value_width=1,
    )
    sessions = (_sid(1), _sid(2), _sid(3))
    write, _ = _write_prefill(state, sessions, sequence=3)
    result = kv.kv_window_retire_bf16(
        write.state,
        expected_state_versions=write.state.versions,
        expected_active_session_ids=sessions,
        retired_session_ids=sessions[1:],
    )

    with pytest.raises(kv.KVWindowReferenceError, match="cursor-synchronized"):
        replace(
            result.counters,
            valid_window_rows_before=8,
            valid_window_rows_invalidated=5,
        )
    alternate_cursor_counters = replace(
        result.counters,
        valid_window_rows_before=6,
        valid_window_rows_invalidated=4,
        valid_window_rows_after=2,
    )
    with pytest.raises(kv.KVWindowReferenceError, match="valid_window_rows_before"):
        replace(result, counters=alternate_cursor_counters)
    with pytest.raises(kv.KVWindowReferenceError, match="synchronized"):
        replace(result, retired_next_positions=(3, 2))
    with pytest.raises(kv.KVWindowReferenceError, match="retained prior state"):
        replace(result, retired_next_positions=(2, 2))


def test_state_validator_rejects_malformed_metadata_atomically() -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    malformed_changes = (
        {"session_ids": (None,)},
        {
            "session_ids": (_sid(1), _sid(2)),
            "lane_active": (False, True),
            "next_positions": (0, 1),
            "versions": (1, 1),
        },
        {"session_ids": (_sid(1), _sid(1)), "versions": (1, 1)},
        {
            "lane_active": (True, False),
            "next_positions": (1, 0),
            "versions": (1, 0),
        },
        {
            "session_ids": (_sid(1), None),
            "lane_active": (True, False),
            "next_positions": (0, 0),
            "versions": (1, 0),
        },
        {
            "session_ids": (_sid(1), None),
            "lane_active": (True, False),
            "next_positions": (1, 0),
            "versions": (0, 0),
        },
        {
            "session_ids": (_sid(1), None),
            "next_positions": (1, 0),
            "versions": (1, 0),
        },
        {"versions": (1, 0)},
        {"session_ids": (_sid(1), None), "versions": (0, 0)},
        {"next_positions": (False, 0)},
    )
    for changes in malformed_changes:
        with pytest.raises(kv.KVWindowReferenceError):
            replace(zero, **changes)


@pytest.mark.parametrize("invalid_code", [-1, 0x10000, True, 0x7F80, 0x7FC0])
def test_state_and_input_reject_non_bf16_or_nonfinite_codes(
    invalid_code: object,
) -> None:
    zero = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=1,
        kv_head_count=1,
        kv_value_width=1,
    )
    with pytest.raises(kv.KVWindowReferenceError):
        replace(zero, bf16_codes=((((invalid_code,),),),))
    with pytest.raises(kv.KVWindowReferenceError):
        kv.kv_window_write_bf16(
            zero,
            ((((invalid_code,),),),),
            active_session_ids=(_sid(1),),
            expected_state_versions=zero.versions,
            start_pos=0,
        )


@pytest.mark.parametrize(
    "active_session_ids",
    [
        (_sid(10).upper(),),
        ("0" * 63,),
        ("g" * 64,),
        (1,),
        _ListSubclass([_sid(1)]),
    ],
)
def test_write_rejects_noncanonical_session_identity_containers(
    active_session_ids: object,
) -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    with pytest.raises(kv.KVWindowReferenceError):
        kv.kv_window_write_bf16(
            state,
            _input_values(batches=1, sequence=1, width=1),
            active_session_ids=active_session_ids,
            expected_state_versions=state.versions,
            start_pos=0,
        )


def test_write_rejects_empty_duplicate_and_batch_mismatched_sessions() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    cases = (
        ((), _input_values(batches=0, sequence=1, width=1)),
        ((_sid(1), _sid(1)), _input_values(batches=2, sequence=1, width=1)),
        ((_sid(1),), _input_values(batches=2, sequence=1, width=1)),
    )
    for sessions, incoming in cases:
        with pytest.raises(kv.KVWindowReferenceError):
            kv.kv_window_write_bf16(
                state,
                incoming,
                active_session_ids=sessions,
                expected_state_versions=state.versions,
                start_pos=0,
            )


def test_write_rejects_ragged_or_wrong_rank_input_and_bool_position() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=2,
        kv_head_count=1,
        kv_value_width=2,
    )
    malformed_inputs = (
        (_input_values(batches=1, sequence=1, width=2)[0],),
        (
            _input_values(batches=1, sequence=1, width=2)[0],
            _input_values(batches=1, sequence=2, width=2)[0],
        ),
        (((_row(1, heads=2, width=2)),),),
        (((((0x3F80,),)),),),
    )
    for malformed in malformed_inputs:
        with pytest.raises(kv.KVWindowReferenceError):
            kv.kv_window_write_bf16(
                state,
                malformed,
                active_session_ids=(_sid(1), _sid(2)),
                expected_state_versions=state.versions,
                start_pos=0,
            )
    with pytest.raises(kv.KVWindowReferenceError, match="start_pos"):
        kv.kv_window_write_bf16(
            state,
            _input_values(batches=2, sequence=1, width=2),
            active_session_ids=(_sid(1), _sid(2)),
            expected_state_versions=state.versions,
            start_pos=False,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {"batch_capacity": 0},
        {"batch_capacity": 5},
        {"window_size": 0},
        {"window_size": 129},
        {"kv_head_count": 0},
        {"kv_value_width": 0},
        {"kv_head_count": 257, "kv_value_width": 2},
        {"batch_capacity": True},
    ],
)
def test_zero_state_rejects_out_of_profile_shapes(arguments: dict[str, object]) -> None:
    with pytest.raises(kv.KVWindowReferenceError):
        kv.zero_kv_window_state_bf16(**arguments)  # type: ignore[arg-type]


def test_success_deeply_freezes_inputs_results_segments_and_counters() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    mutable_input = _mutable(_input_values(batches=1, sequence=1, width=1))
    mutable_sessions = [_sid(1)]
    result = kv.kv_window_write_bf16(
        state,
        mutable_input,
        active_session_ids=mutable_sessions,
        expected_state_versions=state.versions,
        start_pos=0,
    )
    expected = result.state.bf16_codes[0][0][0][0]
    mutable_input[0][0][0][0] = 0x4000  # type: ignore[index]
    mutable_sessions[0] = _sid(2)
    assert result.state.bf16_codes[0][0][0][0] == expected
    assert result.active_session_ids == (_sid(1),)
    assert isinstance(result.segments, tuple)
    assert all(
        type(getattr(result.counters, field.name)) is int
        for field in fields(result.counters)
    )
    with pytest.raises(FrozenInstanceError):
        result.start_pos = 1  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.counters.transaction_commits = 2  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.segments[0].destination_slot_start = 1  # type: ignore[misc]


def test_failed_transaction_preserves_state_and_all_caller_inputs() -> None:
    state = kv.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=3,
        kv_head_count=1,
        kv_value_width=1,
    )
    prefill, _ = _write_prefill(state, (_sid(1),), sequence=2)
    original_state = copy.deepcopy(prefill.state)
    incoming = _mutable(_input_values(batches=1, sequence=1, width=1, base=50))
    original_input = copy.deepcopy(incoming)
    sessions = [_sid(1)]
    original_sessions = list(sessions)

    with pytest.raises(kv.KVWindowReferenceError, match="expected next_pos"):
        kv.kv_window_write_bf16(
            prefill.state,
            incoming,
            active_session_ids=sessions,
            expected_state_versions=prefill.state.versions,
            start_pos=3,
        )
    assert prefill.state == original_state
    assert incoming == original_input
    assert sessions == original_sessions


def test_randomized_structural_oracle_matches_physical_and_causal_windows() -> None:
    for seed in range(40):
        rng = random.Random(seed)
        capacity = rng.randint(1, kv.PINNED_MAX_BATCH_SIZE)
        window = rng.randint(1, 8)
        heads = rng.randint(1, 2)
        width = rng.randint(1, 3)
        active_count = rng.randint(1, capacity)
        sequence = rng.randint(1, 2 * window + 3)
        sessions = tuple(_sid(seed * 100 + lane + 1) for lane in range(active_count))
        state = kv.zero_kv_window_state_bf16(
            batch_capacity=capacity,
            window_size=window,
            kv_head_count=heads,
            kv_value_width=width,
        )
        physical = [list(batch) for batch in state.bf16_codes]
        histories: list[list[kv.BF16HeadRow]] = [list() for _ in range(capacity)]
        versions = [0] * capacity

        incoming = _input_values(
            batches=active_count,
            sequence=sequence,
            heads=heads,
            width=width,
            base=seed * 200 + 10,
        )
        result = kv.kv_window_write_bf16(
            state,
            incoming,
            active_session_ids=sessions,
            expected_state_versions=state.versions,
            start_pos=0,
        )
        for batch in range(active_count):
            for position, row in enumerate(incoming[batch]):
                physical[batch][position % window] = row
            histories[batch].extend(incoming[batch])
            versions[batch] += 1
        assert result.state.bf16_codes == tuple(tuple(batch) for batch in physical)
        assert result.state.versions == tuple(versions)
        _assert_window_reconciliation(result)
        state = result.state
        cursor = sequence

        for step in range(4):
            previous_active = active_count
            active_count = rng.randint(1, previous_active)
            incoming = _input_values(
                batches=active_count,
                sequence=1,
                heads=heads,
                width=width,
                base=seed * 1_000 + step * 20 + 500,
            )
            result = kv.kv_window_write_bf16(
                state,
                incoming,
                active_session_ids=sessions[:active_count],
                expected_state_versions=state.versions,
                start_pos=cursor,
            )
            for batch in range(active_count):
                physical[batch][cursor % window] = incoming[batch][0]
                histories[batch].append(incoming[batch][0])
            for batch in range(previous_active):
                versions[batch] += 1
            assert result.state.bf16_codes == tuple(tuple(batch) for batch in physical)
            assert result.state.versions == tuple(versions)
            assert result.state.lane_active == (
                (True,) * active_count + (False,) * (capacity - active_count)
            )
            assert result.state.next_positions == (
                (cursor + 1,) * active_count + (0,) * (capacity - active_count)
            )
            view = kv.kv_window_valid_view_bf16(
                result.state,
                expected_state_versions=result.state.versions,
                active_session_ids=sessions[:active_count],
            )
            assert view.bf16_codes == tuple(
                tuple(histories[batch][-window:]) for batch in range(active_count)
            )
            expected_start = cursor + 1 - min(cursor + 1, window)
            assert view.absolute_position_starts == (expected_start,) * active_count
            assert view.next_positions == (cursor + 1,) * active_count
            assert view.versions == tuple(versions[:active_count])
            _assert_window_reconciliation(result)
            state = result.state
            cursor += 1
