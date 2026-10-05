from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
import inspect

import pytest

import runtime.reference.attention_kv_view as view
import runtime.reference.compressed_kv as compressed
import runtime.reference.kv_window as window


def _sid(value: int) -> str:
    return f"{value:064x}"


def _row(tag: int, width: int) -> tuple[int, ...]:
    return tuple(1 + ((tag * 131 + column * 17) % 0x7E00) for column in range(width))


def _current(
    batches: int,
    sequence: int,
    width: int,
    *,
    base: int,
) -> view.BF16Batch:
    return tuple(
        tuple(_row(base + batch * 1_000 + position, width) for position in range(sequence))
        for batch in range(batches)
    )


def _window_input(value: view.BF16Batch) -> window.BF16InputTensor:
    return tuple(tuple((row,) for row in batch) for batch in value)


def _window_write(
    state: window.KVWindowState,
    current: view.BF16Batch,
    sessions: tuple[str, ...],
    *,
    start_pos: int,
) -> window.KVWindowWriteResult:
    return window.kv_window_write_bf16(
        state,
        _window_input(current),
        active_session_ids=sessions,
        expected_state_versions=state.versions,
        start_pos=start_pos,
    )


def _compressed_rows(value: view.BF16Batch) -> compressed.BF16InputTensor:
    return tuple(tuple((row,) for row in batch) for batch in value)


def _compressed_prefill_view(
    sessions: tuple[str, ...],
    *,
    ratio: int,
    sequence_length: int,
    width: int,
    capacity: int = 8,
    base: int = 700,
) -> tuple[compressed.CompressedKVState, compressed.CompressedKVValidViewResult]:
    state = compressed.zero_compressed_kv_state_bf16(
        ratio=ratio,
        cache_capacity=capacity,
        kv_head_count=1,
        kv_value_width=width,
        batch_capacity=max(2, len(sessions)),
    )
    completed = sequence_length // ratio
    payload = _current(
        len(sessions),
        completed,
        width,
        base=base,
    )
    write = compressed.compressed_kv_write_bf16(
        state,
        _compressed_rows(payload),
        active_session_ids=sessions,
        start_pos=0,
        sequence_length=sequence_length,
    )
    result = compressed.compressed_kv_valid_view_bf16(
        write.state,
        active_session_ids=sessions,
    )
    return write.state, result


def _compressed_decode_view(
    state: compressed.CompressedKVState,
    sessions: tuple[str, ...],
    *,
    start_pos: int,
    width: int,
    base: int = 900,
) -> tuple[compressed.CompressedKVState, compressed.CompressedKVValidViewResult]:
    completed = int((start_pos + 1) % state.ratio == 0)
    payload = _current(
        len(sessions),
        completed,
        width,
        base=base,
    )
    write = compressed.compressed_kv_write_bf16(
        state,
        _compressed_rows(payload),
        active_session_ids=sessions,
        start_pos=start_pos,
        sequence_length=1,
    )
    result = compressed.compressed_kv_valid_view_bf16(
        write.state,
        active_session_ids=sessions,
    )
    return write.state, result


def test_reference_identity_and_claim_boundary_are_explicit() -> None:
    assert view.MODEL_REPOSITORY == "deepseek-ai/DeepSeek-V4-Flash-0731"
    assert view.MODEL_REVISION == "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
    assert view.MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert view.ATTENTION_KV_VIEW_PROFILE == (
        "opentallas.deepseek_v4_attention_kv_view.v1"
    )
    assert view.PINNED_WINDOW_SIZE == 128
    assert view.PINNED_HEAD_DIM == 512
    assert view.PINNED_DSPARK_BLOCK_SIZE == 5
    assert set(view.EXCLUDED_CLAIMS) == {
        "kv_projection_normalization_rope_or_qdq",
        "index_construction_or_sparse_attention_arithmetic",
        "authenticated_producer_origin",
        "atomic_inter_request_compare_and_swap",
        "compiler_service_or_rtl_execution",
        "physical_hbm_sram_cycles_latency_bandwidth_energy_area_routing_ppa",
        "checkpoint_activation_or_end_to_end_model_evidence",
    }


def test_main_prefill_uses_complete_current_kv_not_truncated_window() -> None:
    sessions = (_sid(1), _sid(2))
    current = _current(2, 6, 3, base=10)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=3,
        window_size=4,
        kv_head_count=1,
        kv_value_width=3,
    )
    write = _window_write(zero, current, sessions, start_pos=0)
    result = view.attention_kv_view_bf16(
        current,
        write.state,
        expected_window_state_versions=write.state.versions,
        active_session_ids=sessions,
        start_pos=0,
    )

    assert result.mode == "main_prefill"
    assert result.bf16_codes == current
    assert result.window_region is None
    assert result.current_region == (0, 6)
    assert result.compressed_region is None
    assert result.valid_row_indices == tuple(range(6))
    assert result.window_valid_absolute_start == 2
    assert result.window_valid_row_count == 4
    assert result.window_valid_physical_slots == (0, 1, 2, 3)
    assert result.counters.window_state_rows_reconciled == 8
    assert result.counters.window_state_rows_read == 0
    assert result.counters.output_rows_written == 12
    assert result.counters.invalid_window_capacity_rows_exposed == 0


@pytest.mark.parametrize("ratio", [4, 128])
def test_main_prefill_appends_only_complete_compressed_prefix(ratio: int) -> None:
    sessions = (_sid(10),)
    width = 2
    sequence = ratio + 3
    current = _current(1, sequence, width, base=20)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=width,
    )
    write = _window_write(zero, current, sessions, start_pos=0)
    _, compressed_view = _compressed_prefill_view(
        sessions,
        ratio=ratio,
        sequence_length=sequence,
        width=width,
        capacity=4,
    )
    result = view.attention_kv_view_bf16(
        current,
        write.state,
        expected_window_state_versions=write.state.versions,
        active_session_ids=sessions,
        start_pos=0,
        compression_ratio=ratio,
        compressed_view=compressed_view,
    )

    compressed_flat = tuple(row[0] for row in compressed_view.bf16_codes[0])
    assert result.bf16_codes[0] == current[0] + compressed_flat
    assert result.current_region == (0, sequence)
    assert result.compressed_region == (sequence, sequence + 1)
    assert result.valid_row_indices == tuple(range(sequence + 1))
    assert result.counters.compressed_source_rows_read == 1
    assert result.counters.invalid_window_capacity_rows_exposed == 0


def test_main_decode_preserves_physical_window_slots_and_marks_unused_capacity() -> None:
    sessions = (_sid(20),)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=2,
    )
    prefill = _window_write(zero, _current(1, 2, 2, base=30), sessions, start_pos=0)
    current = _current(1, 1, 2, base=40)
    decoded = _window_write(prefill.state, current, sessions, start_pos=2)
    result = view.attention_kv_view_bf16(
        current,
        decoded.state,
        expected_window_state_versions=decoded.state.versions,
        active_session_ids=sessions,
        start_pos=2,
    )

    physical = tuple(row[0] for row in decoded.state.bf16_codes[0])
    assert result.mode == "main_decode"
    assert result.bf16_codes == (physical,)
    assert result.window_region == (0, 4)
    assert result.current_region is None
    assert result.valid_row_indices == (0, 1, 2)
    assert result.window_valid_physical_slots == (0, 1, 2)
    assert result.counters.window_state_rows_read == 4
    assert result.counters.window_state_rows_reconciled == 1
    assert result.counters.valid_output_rows == 3
    assert result.counters.invalid_window_capacity_rows_exposed == 1


def test_main_decode_appends_valid_compressed_prefix_at_window_offset() -> None:
    sessions = (_sid(30),)
    width = 2
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=width,
    )
    window_prefill = _window_write(
        zero,
        _current(1, 4, width, base=50),
        sessions,
        start_pos=0,
    )
    current = _current(1, 1, width, base=60)
    window_decode = _window_write(
        window_prefill.state,
        current,
        sessions,
        start_pos=4,
    )
    compressed_state, _ = _compressed_prefill_view(
        sessions,
        ratio=4,
        sequence_length=4,
        width=width,
        capacity=4,
    )
    _, compressed_view = _compressed_decode_view(
        compressed_state,
        sessions,
        start_pos=4,
        width=width,
    )
    result = view.attention_kv_view_bf16(
        current,
        window_decode.state,
        expected_window_state_versions=window_decode.state.versions,
        active_session_ids=sessions,
        start_pos=4,
        compression_ratio=4,
        compressed_view=compressed_view,
    )

    physical = tuple(row[0] for row in window_decode.state.bf16_codes[0])
    compressed_flat = tuple(row[0] for row in compressed_view.bf16_codes[0])
    assert result.bf16_codes[0] == physical + compressed_flat
    assert result.window_region == (0, 4)
    assert result.compressed_region == (4, 5)
    assert result.window_valid_absolute_start == 1
    assert result.window_valid_physical_slots == (0, 1, 2, 3)
    assert result.valid_row_indices == (0, 1, 2, 3, 4)
    assert result.counters.compressed_source_rows_read == 1
    assert result.counters.invalid_window_capacity_rows_exposed == 0


def test_dspark_decode_appends_five_draft_rows_not_main_current_row() -> None:
    sessions = (_sid(40),)
    width = 3
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=2,
        window_size=4,
        kv_head_count=1,
        kv_value_width=width,
    )
    prefill = _window_write(
        zero,
        _current(1, 3, width, base=70),
        sessions,
        start_pos=0,
    )
    main_current = _current(1, 1, width, base=80)
    decoded = _window_write(prefill.state, main_current, sessions, start_pos=3)
    draft = _current(1, 5, width, base=90)
    result = view.attention_kv_view_bf16(
        draft,
        decoded.state,
        expected_window_state_versions=decoded.state.versions,
        active_session_ids=sessions,
        start_pos=3,
        dspark=True,
    )

    physical = tuple(row[0] for row in decoded.state.bf16_codes[0])
    assert draft[0][0] != main_current[0][0]
    assert result.mode == "dspark_decode"
    assert result.bf16_codes[0] == physical + draft[0]
    assert result.window_region == (0, 4)
    assert result.current_region == (4, 9)
    assert result.compressed_region is None
    assert result.valid_row_indices == tuple(range(9))
    assert result.counters.window_state_rows_reconciled == 0
    assert result.counters.current_source_rows_read == 5


def test_official_shape_decode_exposes_128_by_512_window() -> None:
    sessions = (_sid(50),)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=128,
        kv_head_count=1,
        kv_value_width=512,
    )
    prefill = _window_write(zero, _current(1, 1, 512, base=100), sessions, start_pos=0)
    current = _current(1, 1, 512, base=101)
    decoded = _window_write(prefill.state, current, sessions, start_pos=1)
    result = view.attention_kv_view_bf16(
        current,
        decoded.state,
        expected_window_state_versions=decoded.state.versions,
        active_session_ids=sessions,
        start_pos=1,
    )
    assert len(result.bf16_codes[0]) == 128
    assert len(result.bf16_codes[0][0]) == 512
    assert result.valid_row_indices == (0, 1)
    assert result.counters.output_bf16_values_written == 128 * 512


def test_stale_window_authority_and_wrong_current_row_poison() -> None:
    sessions = (_sid(60),)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=3,
        kv_head_count=1,
        kv_value_width=2,
    )
    prefill = _window_write(zero, _current(1, 1, 2, base=110), sessions, start_pos=0)
    current = _current(1, 1, 2, base=111)
    decoded = _window_write(prefill.state, current, sessions, start_pos=1)
    with pytest.raises(view.AttentionKVViewReferenceError, match="stale"):
        view.attention_kv_view_bf16(
            current,
            decoded.state,
            expected_window_state_versions=(decoded.state.versions[0] - 1,),
            active_session_ids=sessions,
            start_pos=1,
        )
    with pytest.raises(view.AttentionKVViewReferenceError, match="decode window slot"):
        view.attention_kv_view_bf16(
            _current(1, 1, 2, base=999),
            decoded.state,
            expected_window_state_versions=decoded.state.versions,
            active_session_ids=sessions,
            start_pos=1,
        )


def test_compressed_view_cursor_session_ratio_and_counters_are_rechecked() -> None:
    sessions = (_sid(70),)
    width = 2
    current = _current(1, 4, width, base=120)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=4,
        kv_head_count=1,
        kv_value_width=width,
    )
    window_write = _window_write(zero, current, sessions, start_pos=0)
    _, compressed_view = _compressed_prefill_view(
        sessions,
        ratio=4,
        sequence_length=4,
        width=width,
        capacity=2,
    )
    for forged in (
        replace(compressed_view, next_positions=(5,)),
        replace(compressed_view, session_ids=(_sid(71),)),
        replace(compressed_view, ratio=128),
        replace(
            compressed_view,
            counters=replace(compressed_view.counters, valid_rows_returned=0),
        ),
    ):
        with pytest.raises(view.AttentionKVViewReferenceError):
            view.attention_kv_view_bf16(
                current,
                window_write.state,
                expected_window_state_versions=window_write.state.versions,
                active_session_ids=sessions,
                start_pos=0,
                compression_ratio=4,
                compressed_view=forged,
            )


@pytest.mark.parametrize(
    ("arguments", "match"),
    [
        ({"dspark": True}, "decode-only"),
        ({"dspark": "yes"}, "exact boolean"),
        ({"compression_ratio": 1}, "exactly 0, 4, or 128"),
        ({"compression_ratio": 4}, "exact CompressedKVValidViewResult"),
    ],
)
def test_invalid_mode_and_compression_combinations_fail_closed(
    arguments: dict[str, object],
    match: str,
) -> None:
    sessions = (_sid(80),)
    current = _current(1, 1, 2, base=130)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=2,
    )
    write = _window_write(zero, current, sessions, start_pos=0)
    with pytest.raises(view.AttentionKVViewReferenceError, match=match):
        view.attention_kv_view_bf16(
            current,
            write.state,
            expected_window_state_versions=write.state.versions,
            active_session_ids=sessions,
            start_pos=0,
            **arguments,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("invalid", [True, -1, 0x10000, 0x7F80, 0x7FC0])
def test_nonfinite_or_non_bf16_current_input_poison(invalid: object) -> None:
    sessions = (_sid(90),)
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=1,
    )
    valid = _current(1, 1, 1, base=140)
    write = _window_write(zero, valid, sessions, start_pos=0)
    with pytest.raises(view.AttentionKVViewReferenceError):
        view.attention_kv_view_bf16(
            (((invalid,),),),
            write.state,
            expected_window_state_versions=write.state.versions,
            active_session_ids=sessions,
            start_pos=0,
        )


def test_success_freezes_mutable_inputs_and_public_result_reconstructs_sources() -> None:
    sessions = [_sid(100)]
    current = [[list(_row(150, 2))]]
    zero = window.zero_kv_window_state_bf16(
        batch_capacity=1,
        window_size=2,
        kv_head_count=1,
        kv_value_width=2,
    )
    write = window.kv_window_write_bf16(
        zero,
        ((((tuple(current[0][0]),),)),),
        active_session_ids=tuple(sessions),
        expected_state_versions=zero.versions,
        start_pos=0,
    )
    result = view.attention_kv_view_bf16(
        current,
        write.state,
        expected_window_state_versions=list(write.state.versions),
        active_session_ids=sessions,
        start_pos=0,
    )
    expected = result.bf16_codes
    current[0][0][0] = 0x4000
    sessions[0] = _sid(101)
    assert result.bf16_codes == expected
    assert type(result.current_kv_bf16_codes) is tuple
    assert type(result.expected_window_state_versions) is tuple
    with pytest.raises(FrozenInstanceError):
        result.mode = "main_decode"  # type: ignore[misc]
    with pytest.raises(view.AttentionKVViewReferenceError, match="bf16_codes"):
        replace(result, bf16_codes=(((0, 0),),))
    with pytest.raises(view.AttentionKVViewReferenceError, match="session_ids"):
        replace(result, session_ids=list(result.session_ids))  # type: ignore[arg-type]
    with pytest.raises(view.AttentionKVViewReferenceError):
        replace(result.counters, output_rows_written=0)


def test_counter_contract_has_no_physical_performance_claims() -> None:
    names = {field.name for field in fields(view.AttentionKVViewCounters)}
    assert {
        "current_source_rows_read",
        "window_state_rows_read",
        "compressed_source_rows_read",
        "valid_output_rows",
        "invalid_window_capacity_rows_exposed",
        "transaction_commits",
    }.issubset(names)
    prohibited = ("hbm", "sram", "burst", "cycle", "latency", "bandwidth", "ppa")
    assert not any(token in name for name in names for token in prohibited)


def test_reference_does_not_import_compiler_service_or_attention_oracle() -> None:
    source = inspect.getsource(view)
    assert "compiler." not in source
    assert "service_engine" not in source
    assert "sparse_attention_bf16" not in source


def test_randomized_physical_window_oracle_and_validity_set() -> None:
    for window_size in range(1, 8):
        sessions = (_sid(200 + window_size),)
        state = window.zero_kv_window_state_bf16(
            batch_capacity=1,
            window_size=window_size,
            kv_head_count=1,
            kv_value_width=2,
        )
        prefill_length = min(3, window_size)
        history = list(_current(1, prefill_length, 2, base=300 + window_size)[0])
        prefill = _window_write(
            state,
            (tuple(history),),
            sessions,
            start_pos=0,
        )
        state = prefill.state
        cursor = prefill_length
        for step in range(window_size + 3):
            current = _current(1, 1, 2, base=500 + window_size * 10 + step)
            history.append(current[0][0])
            decoded = _window_write(state, current, sessions, start_pos=cursor)
            result = view.attention_kv_view_bf16(
                current,
                decoded.state,
                expected_window_state_versions=decoded.state.versions,
                active_session_ids=sessions,
                start_pos=cursor,
            )
            physical = tuple(row[0] for row in decoded.state.bf16_codes[0])
            assert result.bf16_codes == (physical,)
            valid_count = min(cursor + 1, window_size)
            expected_slots = tuple(
                sorted(
                    position % window_size
                    for position in range(cursor + 1 - valid_count, cursor + 1)
                )
            )
            assert result.valid_row_indices == expected_slots
            assert result.window_valid_physical_slots == expected_slots
            assert result.counters.invalid_window_capacity_rows_exposed == (
                window_size - valid_count
            )
            state = decoded.state
            cursor += 1
