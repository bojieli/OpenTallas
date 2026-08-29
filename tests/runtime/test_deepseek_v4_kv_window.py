from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import random

import pytest

from runtime.reference.kv_window import (
    BF16_BYTES,
    INFERENCE_CONFIG_SHA256,
    KV_WINDOW_PROFILE,
    MODEL_SOURCE_SHA256,
    PINNED_KV_HEAD_COUNT,
    PINNED_KV_ROW_WIDTH,
    PINNED_KV_VALUE_WIDTH,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    PINNED_QUERY_HEAD_COUNT,
    PINNED_WINDOW_SIZE,
    KVWindowReferenceError,
    KVWindowState,
    KVWindowWriteCounters,
    KVWindowWriteResult,
    KVWindowWriteSegment,
    kv_window_state_bf16,
    kv_window_write_bf16,
    zero_kv_window_state_bf16,
)


class _ListSubclass(list):
    pass


class _StateSubclass(KVWindowState):
    pass


def _row(tag: int, *, heads: int, width: int) -> tuple[tuple[int, ...], ...]:
    return tuple(
        tuple(0x0100 + tag * 64 + head * width + column for column in range(width))
        for head in range(heads)
    )


def _state_values(
    *,
    batches: int,
    window: int,
    heads: int,
    width: int,
    base: int = 1,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return tuple(
        tuple(
            _row(base + batch * window + slot, heads=heads, width=width)
            for slot in range(window)
        )
        for batch in range(batches)
    )


def _input_values(
    *,
    batches: int,
    sequence: int,
    heads: int,
    width: int,
    base: int = 40,
) -> tuple[tuple[tuple[tuple[int, ...], ...], ...], ...]:
    return tuple(
        tuple(
            _row(base + batch * sequence + position, heads=heads, width=width)
            for position in range(sequence)
        )
        for batch in range(batches)
    )


def _mutable(value: object) -> object:
    if isinstance(value, tuple):
        return [_mutable(element) for element in value]
    return value


def test_reference_is_bound_to_pinned_attention_shape_and_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert KV_WINDOW_PROFILE == "opentallas.deepseek_v4_kv_window_write.v1"
    assert PINNED_MAX_BATCH_SIZE == 4
    assert PINNED_MAX_POSITION == 1_048_576
    assert PINNED_WINDOW_SIZE == 128
    assert PINNED_KV_HEAD_COUNT == 1
    assert PINNED_KV_VALUE_WIDTH == 512
    assert PINNED_KV_ROW_WIDTH == 512
    assert PINNED_QUERY_HEAD_COUNT == 64
    assert BF16_BYTES == 2


def test_default_zero_state_has_official_latent_kv_axes_and_is_immutable() -> None:
    state = zero_kv_window_state_bf16()
    assert len(state.bf16_codes) == 4
    assert len(state.bf16_codes[0]) == 128
    assert len(state.bf16_codes[0][0]) == 1
    assert len(state.bf16_codes[0][0][0]) == 512
    assert state.bf16_codes[3][127][0] == (0,) * 512
    assert isinstance(state.bf16_codes, tuple)
    assert isinstance(state.bf16_codes[0], tuple)
    assert isinstance(state.bf16_codes[0][0], tuple)
    assert isinstance(state.bf16_codes[0][0][0], tuple)
    with pytest.raises(FrozenInstanceError):
        state.bf16_codes = ()  # type: ignore[misc]


def test_short_prefill_writes_active_prefix_and_preserves_all_other_state() -> None:
    initial_values = _state_values(batches=3, window=5, heads=2, width=2, base=1)
    state = kv_window_state_bf16(initial_values)
    incoming = _input_values(batches=2, sequence=3, heads=2, width=2, base=40)
    result = kv_window_write_bf16(state, incoming, start_pos=0)

    assert result.mode == "prefill"
    assert result.start_pos == 0
    assert result.end_pos == 3
    assert result.segments == (
        KVWindowWriteSegment(
            source_sequence_start=0,
            source_sequence_stop=3,
            absolute_position_start=0,
            absolute_position_stop=3,
            destination_slot_start=0,
            destination_slot_stop=3,
        ),
    )
    for batch in range(2):
        assert result.state.bf16_codes[batch][:3] == incoming[batch]
        assert result.state.bf16_codes[batch][3:] == initial_values[batch][3:]
    assert result.state.bf16_codes[2] == initial_values[2]
    assert state.bf16_codes == initial_values
    assert result.state is not state
    assert result.counters == KVWindowWriteCounters(
        active_batch_count=2,
        state_batch_capacity=3,
        sequence_length=3,
        window_size=5,
        kv_head_count=2,
        kv_value_width=2,
        input_rows=6,
        input_bf16_values=24,
        committed_positions_per_batch=3,
        uncommitted_positions_per_batch=0,
        logical_source_rows_read=6,
        logical_source_bf16_values_read=24,
        logical_source_read_bytes=48,
        logical_state_rows_read=0,
        logical_state_bf16_values_read=0,
        logical_state_read_bytes=0,
        logical_state_rows_written=6,
        logical_state_bf16_values_written=24,
        logical_state_write_bytes=48,
        state_rows_preserved=9,
        state_bf16_values_preserved=36,
        source_slice_assignments=1,
        nonempty_source_slice_assignments=1,
        logical_slot_modulo_evaluations=0,
        transaction_commits=1,
    )


def test_long_prefill_keeps_only_last_window_and_splits_at_cutoff() -> None:
    state = kv_window_state_bf16(_state_values(batches=2, window=4, heads=1, width=2))
    incoming = _input_values(batches=2, sequence=6, heads=1, width=2, base=30)
    result = kv_window_write_bf16(state, incoming, start_pos=0)

    assert result.segments == (
        KVWindowWriteSegment(2, 4, 2, 4, 2, 4),
        KVWindowWriteSegment(4, 6, 4, 6, 0, 2),
    )
    for batch in range(2):
        assert result.state.bf16_codes[batch] == (
            incoming[batch][4],
            incoming[batch][5],
            incoming[batch][2],
            incoming[batch][3],
        )
    counters = result.counters
    assert counters.input_rows == 12
    assert counters.input_bf16_values == 24
    assert counters.committed_positions_per_batch == 4
    assert counters.uncommitted_positions_per_batch == 2
    assert counters.logical_source_rows_read == 8
    assert counters.logical_source_bf16_values_read == 16
    assert counters.logical_source_read_bytes == 32
    assert counters.logical_state_rows_written == 8
    assert counters.logical_state_write_bytes == 32
    assert counters.state_rows_preserved == 0
    assert counters.source_slice_assignments == 2
    assert counters.nonempty_source_slice_assignments == 2
    assert counters.logical_slot_modulo_evaluations == 1


def test_exact_multiple_long_prefill_retains_one_nonempty_source_slice() -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=4, kv_head_count=1, kv_value_width=1
    )
    incoming = _input_values(batches=1, sequence=8, heads=1, width=1, base=10)
    result = kv_window_write_bf16(state, incoming, start_pos=0)

    assert result.state.bf16_codes[0] == incoming[0][4:8]
    assert result.segments == (KVWindowWriteSegment(4, 8, 4, 8, 0, 4),)
    assert result.counters.source_slice_assignments == 2
    assert result.counters.nonempty_source_slice_assignments == 1
    assert result.counters.logical_slot_modulo_evaluations == 1


def test_sequence_equal_to_window_uses_nonwrapping_prefill_branch() -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=4, kv_head_count=1, kv_value_width=1
    )
    incoming = _input_values(batches=1, sequence=4, heads=1, width=1, base=20)
    result = kv_window_write_bf16(state, incoming, start_pos=0)

    assert result.state.bf16_codes[0] == incoming[0]
    assert result.segments == (KVWindowWriteSegment(0, 4, 0, 4, 0, 4),)
    assert result.counters.source_slice_assignments == 1
    assert result.counters.logical_slot_modulo_evaluations == 0


def test_decode_updates_one_modulo_slot_and_wraps_without_mutating_prior_versions() -> (
    None
):
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=4, kv_head_count=1, kv_value_width=2
    )
    prefill = _input_values(batches=1, sequence=3, heads=1, width=2, base=10)
    version0 = kv_window_write_bf16(state, prefill, start_pos=0).state

    row3 = _input_values(batches=1, sequence=1, heads=1, width=2, base=30)
    write3 = kv_window_write_bf16(version0, row3, start_pos=3)
    assert write3.state.bf16_codes[0] == (*prefill[0], row3[0][0])
    assert write3.segments == (KVWindowWriteSegment(0, 1, 3, 4, 3, 4),)

    row4 = _input_values(batches=1, sequence=1, heads=1, width=2, base=40)
    write4 = kv_window_write_bf16(write3.state, row4, start_pos=4)
    assert write4.state.bf16_codes[0] == (
        row4[0][0],
        prefill[0][1],
        prefill[0][2],
        row3[0][0],
    )
    assert write4.segments == (KVWindowWriteSegment(0, 1, 4, 5, 0, 1),)
    assert write4.counters.logical_slot_modulo_evaluations == 1
    assert write4.counters.logical_state_rows_read == 0

    row5 = _input_values(batches=1, sequence=1, heads=1, width=2, base=50)
    write5 = kv_window_write_bf16(write4.state, row5, start_pos=5)
    assert write5.state.bf16_codes[0][1] == row5[0][0]
    assert version0.bf16_codes[0] == (*prefill[0], ((0, 0),))
    assert write3.state.bf16_codes[0][0] == prefill[0][0]
    assert write4.state.bf16_codes[0][1] == prefill[0][1]


def test_decode_updates_active_batch_prefix_and_preserves_head_value_axes() -> None:
    initial = _state_values(batches=3, window=3, heads=2, width=3, base=1)
    state = kv_window_state_bf16(initial)
    incoming = _input_values(batches=2, sequence=1, heads=2, width=3, base=40)
    result = kv_window_write_bf16(state, incoming, start_pos=7)

    assert result.mode == "decode"
    assert result.end_pos == 8
    for batch in range(2):
        assert result.state.bf16_codes[batch][1] == incoming[batch][0]
        assert result.state.bf16_codes[batch][0] == initial[batch][0]
        assert result.state.bf16_codes[batch][2] == initial[batch][2]
    assert result.state.bf16_codes[2] == initial[2]
    assert result.counters.kv_head_count == 2
    assert result.counters.kv_value_width == 3
    assert result.counters.logical_source_read_bytes == 24
    assert result.counters.logical_state_write_bytes == 24
    assert result.counters.state_rows_preserved == 7
    assert result.counters.state_bf16_values_preserved == 42


def test_window_size_one_always_replaces_the_only_slot() -> None:
    state = kv_window_state_bf16(_state_values(batches=1, window=1, heads=1, width=1))
    prefill = _input_values(batches=1, sequence=5, heads=1, width=1, base=10)
    result = kv_window_write_bf16(state, prefill, start_pos=0)
    assert result.state.bf16_codes[0] == (prefill[0][-1],)
    assert result.segments == (KVWindowWriteSegment(4, 5, 4, 5, 0, 1),)
    assert result.counters.source_slice_assignments == 2
    assert result.counters.nonempty_source_slice_assignments == 1

    decode = _input_values(batches=1, sequence=1, heads=1, width=1, base=30)
    decoded = kv_window_write_bf16(result.state, decode, start_pos=17)
    assert decoded.state.bf16_codes[0] == (decode[0][0],)
    assert decoded.segments == (KVWindowWriteSegment(0, 1, 17, 18, 0, 1),)


def test_signed_zero_and_subnormal_payload_bits_are_preserved() -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=2, kv_head_count=1, kv_value_width=4
    )
    incoming = [[[[0x0000, 0x8000, 0x0001, 0x807F]]]]
    result = kv_window_write_bf16(state, incoming, start_pos=1)
    assert result.state.bf16_codes[0][1][0] == (
        0x0000,
        0x8000,
        0x0001,
        0x807F,
    )


def test_caller_lists_are_frozen_before_commit_and_cannot_alias_result() -> None:
    state_lists = _mutable(_state_values(batches=1, window=2, heads=1, width=2))
    input_lists = _mutable(
        _input_values(batches=1, sequence=1, heads=1, width=2, base=30)
    )
    state = kv_window_state_bf16(state_lists)
    result = kv_window_write_bf16(state, input_lists, start_pos=1)
    expected = result.state.bf16_codes

    state_lists[0][0][0][0] = 0x3F80  # type: ignore[index]
    input_lists[0][0][0][0] = 0x4000  # type: ignore[index]
    assert result.state.bf16_codes == expected
    assert isinstance(result.state.bf16_codes, tuple)
    assert isinstance(result.state.bf16_codes[0][1][0], tuple)
    with pytest.raises(FrozenInstanceError):
        result.mode = "prefill"  # type: ignore[misc]


def test_randomized_transactions_match_independent_absolute_position_oracle() -> None:
    rng = random.Random(0x4B56_5749_4E44_4F57)
    for case in range(128):
        capacity = rng.randint(1, 4)
        active = rng.randint(1, capacity)
        window = rng.randint(1, 8)
        heads = rng.randint(1, 3)
        width = rng.randint(1, 4)
        initial = _state_values(
            batches=capacity,
            window=window,
            heads=heads,
            width=width,
            base=1,
        )
        state = kv_window_state_bf16(initial)
        prefill = rng.choice((True, False))
        if prefill:
            start_pos = 0
            sequence = rng.randint(1, 3 * window + 2)
        else:
            start_pos = rng.randint(1, 1000)
            sequence = 1
        incoming = _input_values(
            batches=active,
            sequence=sequence,
            heads=heads,
            width=width,
            base=40 + case,
        )
        result = kv_window_write_bf16(state, incoming, start_pos=start_pos)

        expected = [[row for row in batch] for batch in initial]
        if start_pos == 0:
            source_positions = range(max(0, sequence - window), sequence)
            absolute_positions = source_positions
        else:
            source_positions = range(1)
            absolute_positions = range(start_pos, start_pos + 1)
        for batch in range(active):
            for source_position, absolute_position in zip(
                source_positions, absolute_positions, strict=True
            ):
                expected[batch][absolute_position % window] = incoming[batch][
                    source_position
                ]
        assert result.state.bf16_codes == tuple(
            tuple(window_rows) for window_rows in expected
        )


@pytest.mark.parametrize(
    "bad_start",
    [True, False, 1.0, "1", -1, PINNED_MAX_POSITION],
)
def test_start_position_type_range_and_decode_shape_fail_closed(
    bad_start: object,
) -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=4, kv_head_count=1, kv_value_width=1
    )
    incoming = _input_values(batches=1, sequence=1, heads=1, width=1)
    with pytest.raises(KVWindowReferenceError, match="start_pos"):
        kv_window_write_bf16(state, incoming, start_pos=bad_start)  # type: ignore[arg-type]


def test_decode_rejects_multi_position_input_and_preserves_prior_state() -> None:
    state = kv_window_state_bf16(_state_values(batches=1, window=4, heads=1, width=2))
    before = state.bf16_codes
    incoming = _input_values(batches=1, sequence=2, heads=1, width=2)
    with pytest.raises(KVWindowReferenceError, match="sequence length exactly 1"):
        kv_window_write_bf16(state, incoming, start_pos=7)
    assert state.bf16_codes == before


@pytest.mark.parametrize(
    "invalid_state, match",
    [
        ((), "KVWindowState"),
        (KVWindowState(()), "at least one batch"),
        (KVWindowState(((),)), "window extent"),
        (KVWindowState(((((),),),)), "value extent"),
        (
            KVWindowState(
                tuple((((0x3F80,),),) for _ in range(PINNED_MAX_BATCH_SIZE + 1))
            ),
            "batch capacity",
        ),
        (
            KVWindowState(
                (tuple(((0x3F80,),) for _ in range(PINNED_WINDOW_SIZE + 1)),)
            ),
            "window extent",
        ),
        (
            KVWindowState(
                ((tuple((0x3F80,) for _ in range(PINNED_KV_ROW_WIDTH + 1)),),)
            ),
            "KV-head extent",
        ),
        (
            KVWindowState(
                (((tuple(0x3F80 for _ in range(PINNED_KV_ROW_WIDTH + 1)),),),)
            ),
            "KV-value extent",
        ),
    ],
)
def test_malformed_state_shapes_fail_closed(
    invalid_state: object,
    match: str,
) -> None:
    incoming = _input_values(batches=1, sequence=1, heads=1, width=1)
    with pytest.raises(KVWindowReferenceError, match=match):
        kv_window_write_bf16(invalid_state, incoming, start_pos=0)  # type: ignore[arg-type]


def test_state_head_value_product_and_exact_state_type_are_enforced() -> None:
    oversized_row = tuple((0x3F80,) * 257 for _ in range(2))
    state = KVWindowState(((oversized_row,),))
    with pytest.raises(KVWindowReferenceError, match="product exceeds"):
        kv_window_write_bf16(state, ((((0x3F80,) * 257,) * 2,),), start_pos=0)

    valid = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=1, kv_head_count=1, kv_value_width=1
    )
    subclass = _StateSubclass(valid.bf16_codes)
    with pytest.raises(KVWindowReferenceError, match="exact KVWindowState"):
        kv_window_write_bf16(subclass, [[[[0x3F80]]]], start_pos=0)


@pytest.mark.parametrize(
    "invalid_input, match",
    [
        ((), "active batch"),
        (((),), "sequence extent"),
        (((((0x3F80,),),), ()), "rectangular.*sequence"),
        (((((0x3F80,),),),) * 3, "active batches"),
        (((((0x3F80,), (0x4000,)),),), "exactly 1 KV heads"),
        (((((0x3F80, 0x4000),),),), "exactly 1 values"),
        (_ListSubclass([[[[0x3F80]]]]), "exact list or tuple"),
        ("not-a-tensor", "exact list or tuple"),
    ],
)
def test_malformed_input_axes_fail_closed(
    invalid_input: object,
    match: str,
) -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=2, window_size=2, kv_head_count=1, kv_value_width=1
    )
    with pytest.raises(KVWindowReferenceError, match=match):
        kv_window_write_bf16(state, invalid_input, start_pos=0)


@pytest.mark.parametrize(
    "invalid_code, match",
    [
        (True, "16-bit BF16"),
        (False, "16-bit BF16"),
        (1.0, "16-bit BF16"),
        (-1, "16-bit BF16"),
        (1 << 16, "16-bit BF16"),
        (0x7F80, "finite BF16"),
        (0x7FC1, "finite BF16"),
        (0xFF80, "finite BF16"),
        (0xFFFF, "finite BF16"),
    ],
)
def test_invalid_or_nonfinite_input_bf16_fails_without_state_change(
    invalid_code: object,
    match: str,
) -> None:
    state = kv_window_state_bf16(_state_values(batches=1, window=2, heads=1, width=1))
    before = state.bf16_codes
    with pytest.raises(KVWindowReferenceError, match=match):
        kv_window_write_bf16(state, [[[[invalid_code]]]], start_pos=1)
    assert state.bf16_codes == before


@pytest.mark.parametrize("invalid_code", [True, 1.0, -1, 65536, 0x7F80, 0x7FC1])
def test_invalid_or_nonfinite_prior_state_is_rejected_even_if_slot_is_untouched(
    invalid_code: object,
) -> None:
    state = KVWindowState(((((invalid_code,),), ((0x3F80,),)),))
    with pytest.raises(KVWindowReferenceError, match="BF16"):
        kv_window_write_bf16(state, [[[[0x4000]]]], start_pos=1)


def test_nonfinite_discarded_prefill_prefix_is_still_transaction_poison() -> None:
    state = zero_kv_window_state_bf16(
        batch_capacity=1, window_size=2, kv_head_count=1, kv_value_width=1
    )
    incoming = [[[[0x7F80]], [[0x3F80]], [[0x4000]]]]
    with pytest.raises(KVWindowReferenceError, match="finite BF16"):
        kv_window_write_bf16(state, incoming, start_pos=0)
    assert state.bf16_codes == (((((0,),), ((0,),))),)


@pytest.mark.parametrize(
    "arguments, match",
    [
        ({"batch_capacity": True}, "batch_capacity"),
        ({"batch_capacity": 0}, "batch_capacity"),
        ({"batch_capacity": 5}, "batch_capacity"),
        ({"window_size": 0}, "window_size"),
        ({"window_size": 129}, "window_size"),
        ({"kv_head_count": 0}, "kv_head_count"),
        ({"kv_value_width": 0}, "kv_value_width"),
        ({"kv_head_count": 2, "kv_value_width": 257}, "exceeds"),
    ],
)
def test_zero_state_constructor_is_bounded_and_type_sensitive(
    arguments: dict[str, object], match: str
) -> None:
    with pytest.raises(KVWindowReferenceError, match=match):
        zero_kv_window_state_bf16(**arguments)  # type: ignore[arg-type]


def test_counter_contract_contains_only_logical_traffic_and_state_counts() -> None:
    names = {field.name for field in fields(KVWindowWriteCounters)}
    assert names == {
        "active_batch_count",
        "state_batch_capacity",
        "sequence_length",
        "window_size",
        "kv_head_count",
        "kv_value_width",
        "input_rows",
        "input_bf16_values",
        "committed_positions_per_batch",
        "uncommitted_positions_per_batch",
        "logical_source_rows_read",
        "logical_source_bf16_values_read",
        "logical_source_read_bytes",
        "logical_state_rows_read",
        "logical_state_bf16_values_read",
        "logical_state_read_bytes",
        "logical_state_rows_written",
        "logical_state_bf16_values_written",
        "logical_state_write_bytes",
        "state_rows_preserved",
        "state_bf16_values_preserved",
        "source_slice_assignments",
        "nonempty_source_slice_assignments",
        "logical_slot_modulo_evaluations",
        "transaction_commits",
    }
    prohibited = ("hbm", "cycle", "latency", "bandwidth", "burst", "transaction")
    assert not any(
        token in name
        for name in names
        for token in prohibited
        if name != "transaction_commits"
    )


def test_result_contract_is_frozen_and_field_complete() -> None:
    assert {field.name for field in fields(KVWindowWriteResult)} == {
        "state",
        "mode",
        "start_pos",
        "end_pos",
        "segments",
        "counters",
    }
    assert {field.name for field in fields(KVWindowWriteSegment)} == {
        "source_sequence_start",
        "source_sequence_stop",
        "absolute_position_start",
        "absolute_position_stop",
        "destination_slot_start",
        "destination_slot_stop",
    }
