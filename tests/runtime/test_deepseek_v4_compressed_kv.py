from __future__ import annotations

from copy import deepcopy
from dataclasses import FrozenInstanceError, fields

import pytest

from runtime.reference.compressed_kv import (
    BF16_BYTES,
    COMPRESSED_KV_PROFILE,
    INFERENCE_CONFIG_SHA256,
    MODEL_SOURCE_SHA256,
    PINNED_COMPRESSION_RATIOS,
    PINNED_INDEX_HEAD_DIM,
    PINNED_MAIN_HEAD_DIM,
    PINNED_MAX_BATCH_SIZE,
    PINNED_MAX_POSITION,
    CompressedKVReferenceError,
    CompressedKVState,
    CompressedKVWriteCounters,
    CompressedKVWriteResult,
    compressed_kv_state_bf16,
    compressed_kv_write_bf16,
    zero_compressed_kv_state_bf16,
)
from runtime.reference.formats import binary32_bits_to_bf16_rne, encode_binary32_rne


class _ListSubclass(list):
    pass


class _StateSubclass(CompressedKVState):
    pass


def _bf16(value: int) -> int:
    return binary32_bits_to_bf16_rne(encode_binary32_rne(value)).code


def _rows(*rows: tuple[int, ...]) -> tuple:
    return (tuple(((tuple(_bf16(value) for value in row),)) for row in rows),)


def _tagged_state(
    *,
    ratio: int = 4,
    batches: int = 2,
    capacity: int = 4,
    width: int = 2,
    valid_prefixes: tuple[int, ...] = (3, 1),
) -> CompressedKVState:
    payload = tuple(
        tuple(
            (tuple(_bf16(100 * batch + 10 * slot + column + 1) for column in range(width)),)
            for slot in range(capacity)
        )
        for batch in range(batches)
    )
    valid = tuple(
        tuple(slot < valid_prefixes[batch] for slot in range(capacity))
        for batch in range(batches)
    )
    return compressed_kv_state_bf16(
        CompressedKVState(ratio=ratio, bf16_codes=payload, valid=valid)
    )


def test_contract_is_bound_to_pinned_source_profiles_and_bytes() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )
    assert INFERENCE_CONFIG_SHA256 == (
        "c90861f3d10a9e4ef5954f8f1a34c529d480da1c5799f84660028f4e38e14e71"
    )
    assert COMPRESSED_KV_PROFILE == "opentallas.deepseek_v4_compressed_kv_write.v1"
    assert PINNED_COMPRESSION_RATIOS == (4, 128)
    assert PINNED_MAIN_HEAD_DIM == 512
    assert PINNED_INDEX_HEAD_DIM == 128
    assert PINNED_MAX_BATCH_SIZE == 4
    assert PINNED_MAX_POSITION == 1_048_576
    assert BF16_BYTES == 2


def test_zero_state_has_explicit_axes_validity_and_immutability() -> None:
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
    assert state.valid == ((False, False, False),) * 2
    with pytest.raises(FrozenInstanceError):
        state.ratio = 128  # type: ignore[misc]


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
def test_ratio_four_prefill_commits_only_complete_groups(
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
    source = _rows(*(tuple((10 * row + 1, 10 * row + 2)) for row in range(expected_rows)))
    result = compressed_kv_write_bf16(
        state,
        source,
        start_pos=0,
        sequence_length=sequence_length,
    )
    assert result.mode == "prefill"
    assert result.cache_slots == slots
    assert result.state.valid == (
        tuple(slot < expected_rows for slot in range(4)),
    )
    assert result.state.bf16_codes[0][:expected_rows] == source[0]
    assert result.counters.completed_rows_per_batch == expected_rows
    assert result.counters.logical_source_rows_read == expected_rows
    assert result.counters.logical_state_rows_written == expected_rows
    assert result.counters.logical_source_read_bytes == expected_rows * 2 * BF16_BYTES
    assert result.counters.logical_state_write_bytes == expected_rows * 2 * BF16_BYTES


def test_prefill_invalidates_stale_prefix_but_preserves_unwritten_payload_bits() -> None:
    state = _tagged_state()
    before = deepcopy(state)
    source = _rows((1, 2), (3, 4))
    result = compressed_kv_write_bf16(
        state,
        source,
        start_pos=0,
        sequence_length=10,
    )

    assert state == before
    assert result.state.valid == (
        (True, True, False, False),
        before.valid[1],
    )
    assert result.state.bf16_codes[0][:2] == source[0]
    assert result.state.bf16_codes[0][2:] == before.bf16_codes[0][2:]
    assert result.state.bf16_codes[1] == before.bf16_codes[1]
    assert result.counters == CompressedKVWriteCounters(
        active_batch_count=1,
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
        valid_rows_invalidated=3,
        validity_bits_written=6,
        valid_rows_after=3,
        transaction_commits=1,
    )


def test_ratio_128_prefill_slot_mapping_is_floor_division() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=128,
        cache_capacity=3,
        kv_value_width=1,
        batch_capacity=1,
    )
    result = compressed_kv_write_bf16(
        state,
        _rows((1,), (2,)),
        start_pos=0,
        sequence_length=300,
    )
    assert result.cache_slots == (0, 1)
    assert result.state.valid == ((True, True, False),)
    assert result.end_pos == 300


def test_decode_nonboundary_is_an_explicit_noop_then_boundary_commits() -> None:
    initial = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=4,
        kv_value_width=2,
        batch_capacity=1,
    )
    prefill = compressed_kv_write_bf16(
        initial,
        _rows((1, 2),),
        start_pos=0,
        sequence_length=5,
    )
    current = prefill.state
    for start_pos in (5, 6):
        result = compressed_kv_write_bf16(
            current,
            ((),),
            start_pos=start_pos,
            sequence_length=1,
        )
        assert result.mode == "decode"
        assert result.cache_slots == ()
        assert result.state == current
        assert result.counters.completed_rows_per_batch == 0
        assert result.counters.logical_source_read_bytes == 0
        assert result.counters.logical_state_write_bytes == 0
        current = result.state

    boundary = compressed_kv_write_bf16(
        current,
        _rows((7, 8),),
        start_pos=7,
        sequence_length=1,
    )
    assert boundary.cache_slots == (1,)
    assert boundary.state.valid == ((True, True, False, False),)
    assert boundary.state.bf16_codes[0][1] == ((_bf16(7), _bf16(8)),)


def test_decode_rejects_a_forged_or_wrong_generation_prefix_atomically() -> None:
    forged = _tagged_state(
        batches=1,
        capacity=4,
        valid_prefixes=(2,),
    )
    before = deepcopy(forged)
    with pytest.raises(CompressedKVReferenceError, match="is 2, expected 1"):
        compressed_kv_write_bf16(
            forged,
            _rows((9, 10),),
            start_pos=7,
            sequence_length=1,
        )
    assert forged == before


def test_multiple_active_batches_write_the_prefix_and_preserve_inactive_batches() -> None:
    state = zero_compressed_kv_state_bf16(
        ratio=4,
        cache_capacity=2,
        kv_value_width=1,
        batch_capacity=3,
    )
    source = (
        (((_bf16(1),),),),
        (((_bf16(2),),),),
    )
    result = compressed_kv_write_bf16(
        state,
        source,
        start_pos=0,
        sequence_length=4,
    )
    assert result.state.bf16_codes[0][0] == ((_bf16(1),),)
    assert result.state.bf16_codes[1][0] == ((_bf16(2),),)
    assert result.state.bf16_codes[2] == state.bf16_codes[2]
    assert result.state.valid == (
        (True, False),
        (True, False),
        (False, False),
    )


def test_result_dataclasses_and_counter_fields_are_explicit() -> None:
    assert [field.name for field in fields(CompressedKVWriteResult)] == [
        "state",
        "mode",
        "cache_slots",
        "start_pos",
        "end_pos",
        "counters",
    ]
    assert len(fields(CompressedKVWriteCounters)) == 24


@pytest.mark.parametrize(
    ("operation", "match"),
    [
        (
            lambda: zero_compressed_kv_state_bf16(
                ratio=8, cache_capacity=1, kv_value_width=1
            ),
            "ratio must be exactly",
        ),
        (
            lambda: compressed_kv_state_bf16(object()),
            "exact CompressedKVState",
        ),
        (
            lambda: compressed_kv_state_bf16(
                _StateSubclass(4, ((((0,),),),), ((False,),))
            ),
            "exact CompressedKVState",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(4, (), ())
            ),
            "batch capacity",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(4, ((((0,),),),), ((True, False),))
            ),
            "cache extents",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(
                    4,
                    ((((0,),),) * 3,),
                    ((True, False, True),),
                )
            ),
            "contiguous prefix",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(4, ((((0x7F80,),),),), ((False,),))
            ),
            "finite BF16",
        ),
        (
            lambda: compressed_kv_state_bf16(
                CompressedKVState(4, _ListSubclass([(((0,),),)]), ((False,),))
            ),
            "exact list or tuple",
        ),
        (
            lambda: compressed_kv_write_bf16(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=2,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                _rows((1,),),
                start_pos=0,
                sequence_length=3,
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
                _rows((1,), (2,)),
                start_pos=5,
                sequence_length=2,
            ),
            "sequence length exactly 1",
        ),
        (
            lambda: compressed_kv_write_bf16(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=1,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                _rows((1,),),
                start_pos=7,
                sequence_length=1,
            ),
            "exceeds cache capacity",
        ),
        (
            lambda: compressed_kv_write_bf16(
                zero_compressed_kv_state_bf16(
                    ratio=4,
                    cache_capacity=2,
                    kv_value_width=1,
                    batch_capacity=1,
                ),
                ((((True,),),),),
                start_pos=0,
                sequence_length=4,
            ),
            "16-bit BF16",
        ),
    ],
)
def test_malformed_nonfinite_out_of_order_and_overflow_inputs_fail_closed(
    operation,
    match: str,
) -> None:
    with pytest.raises(CompressedKVReferenceError, match=match):
        operation()
