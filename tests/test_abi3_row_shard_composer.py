"""Refusals of the row-shard composer, written before its happy path.

Every rule ``tools/abi3_row_shard`` claims is exercised here in the direction
that matters -- a partition that is NOT exact must raise -- because a composer
that silently concatenates a dropped or duplicated row would turn a sharded
run into evidence for a result nobody computed.  The happy-path cases come
last, and one of them is the whole point of the module: eight shards of one
vector concatenate to that vector, byte for byte.
"""

from __future__ import annotations

import pytest

from tools.abi3_row_shard import (
    Composition,
    ShardCompositionError,
    ShardDescriptor,
    argmax_lowest_index,
    compose,
    plan_row_shards,
    plan_row_shards_of_size,
)


OP = "qwen3-8b-rom-single-chip/pc17/desc73"


def words(first: int, count: int) -> list[int]:
    """A distinguishable word per row, so a mis-composition is visible."""

    return [0x3F00 + first + index for index in range(count)]


def shard(first: int, count: int) -> tuple[ShardDescriptor, list[int]]:
    return ShardDescriptor(OP, first, count), words(first, count)


# -- descriptor refusals ---------------------------------------------------
def test_shard_refuses_a_zero_row_count():
    with pytest.raises(ShardCompositionError) as raised:
        ShardDescriptor(OP, 0, 0)
    assert raised.value.reason == "shard_row_count_not_positive"


def test_shard_refuses_a_negative_row_count():
    with pytest.raises(ShardCompositionError) as raised:
        ShardDescriptor(OP, 0, -8)
    assert raised.value.reason == "shard_row_count_not_positive"


def test_shard_refuses_a_negative_first_row():
    with pytest.raises(ShardCompositionError) as raised:
        ShardDescriptor(OP, -1, 8)
    assert raised.value.reason == "shard_first_row_negative"


def test_shard_refuses_a_boolean_row_count():
    with pytest.raises(ShardCompositionError) as raised:
        ShardDescriptor(OP, 0, True)
    assert raised.value.reason == "shard_row_count_not_an_integer"


def test_shard_refuses_an_unnamed_operator():
    with pytest.raises(ShardCompositionError) as raised:
        ShardDescriptor("", 0, 8)
    assert raised.value.reason == "shard_operator_missing"


# -- composition refusals: the three the brief names -----------------------
def test_compose_refuses_a_dropped_row():
    """Eight shards of 128 rows, one of them one row short of its own range.

    The shard still declares 128 rows and hands over 127 words.  That is the
    defect a length-blind concatenation would turn into a 1,023-word answer
    for a 1,024-row operator.
    """

    parts = [shard(index * 128, 128) for index in range(8)]
    descriptor, payload = parts[3]
    parts[3] = (descriptor, payload[:-1])
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "shard_word_count_disagrees_with_row_count"
    assert "row_count=128" in raised.value.detail


def test_compose_refuses_a_dropped_shard():
    """The same row dropped the other way: a whole shard is missing."""

    parts = [shard(index * 128, 128) for index in range(8)]
    del parts[5]
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "shard_gap"
    assert "[640:768)" in raised.value.detail


def test_compose_refuses_a_duplicated_row():
    """Two shards claiming the same rows.

    Their words sum to the declared extent, so a composer that checked only
    the total would admit it and answer with one range twice and another not
    at all.
    """

    parts = [shard(index * 128, 128) for index in range(8)]
    parts[6] = shard(640, 128)
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "shard_overlap"


def test_compose_refuses_a_partial_overlap():
    parts = [shard(0, 512), shard(500, 524)]
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "shard_overlap"


def test_compose_refuses_an_off_by_one_extent_short():
    parts = [shard(0, 512), shard(512, 511)]
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "composed_extent_disagrees_with_declared_extent"
    assert "composed=1023" in raised.value.detail


def test_compose_refuses_an_off_by_one_extent_long():
    parts = [shard(0, 512), shard(512, 513)]
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "composed_extent_disagrees_with_declared_extent"
    assert "composed=1025" in raised.value.detail


def test_compose_refuses_a_partition_that_does_not_start_at_row_zero():
    parts = [shard(1, 512), shard(513, 511)]
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, parts)
    assert raised.value.reason == "shard_gap"
    assert "[0:1)" in raised.value.detail


def test_compose_refuses_shards_of_different_operators():
    first, first_words = shard(0, 512)
    other = ShardDescriptor("qwen3-8b-hbm-single-chip/pc17/desc84", 512, 512)
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, [(first, first_words), (other, words(512, 512))])
    assert raised.value.reason == "shards_of_different_operators"


def test_compose_refuses_an_empty_shard_set():
    with pytest.raises(ShardCompositionError) as raised:
        compose(1024, [])
    assert raised.value.reason == "no_shards"


def test_compose_refuses_a_non_positive_declared_extent():
    with pytest.raises(ShardCompositionError) as raised:
        compose(0, [shard(0, 8)])
    assert raised.value.reason == "declared_extent_not_positive"


# -- reduction refusals ----------------------------------------------------
def test_argmax_refuses_a_bare_word_list():
    with pytest.raises(ShardCompositionError) as raised:
        argmax_lowest_index([0x3F80, 0x4000])
    assert raised.value.reason == (
        "reduction_over_something_that_is_not_a_composition"
    )


def test_argmax_refuses_an_incomplete_composition():
    forged = Composition(
        operator=OP, declared_extent=1024, words=(0x3F80,), shard_count=1
    )
    with pytest.raises(ShardCompositionError) as raised:
        argmax_lowest_index(forged)
    assert raised.value.reason == "reduction_over_an_incomplete_composition"


# -- planner refusals ------------------------------------------------------
def test_planner_refuses_more_shards_than_rows():
    with pytest.raises(ShardCompositionError) as raised:
        plan_row_shards(OP, 8, 9)
    assert raised.value.reason == "shard_count_exceeds_extent"


def test_planner_refuses_a_zero_shard_count():
    with pytest.raises(ShardCompositionError) as raised:
        plan_row_shards(OP, 1024, 0)
    assert raised.value.reason == "shard_count_not_positive"


# -- the happy path, last --------------------------------------------------
def test_eight_shards_concatenate_to_the_whole():
    whole = words(0, 1024)
    parts = [shard(index * 128, 128) for index in range(8)]
    composed = compose(1024, parts)
    assert list(composed.words) == whole
    assert composed.shard_count == 8
    assert composed.partition_proof["sum_of_shard_extents"] == 1024
    assert composed.partition_proof["gaps"] == 0
    assert composed.partition_proof["overlaps"] == 0


def test_composition_is_order_independent():
    forward = compose(1024, [shard(index * 128, 128) for index in range(8)])
    reverse = compose(
        1024, [shard(index * 128, 128) for index in reversed(range(8))]
    )
    assert forward.words == reverse.words
    assert forward.sha256 == reverse.sha256


def test_planner_tiles_an_extent_that_is_not_a_multiple():
    shards = plan_row_shards_of_size(OP, 151_936, 4096)
    assert len(shards) == 38
    assert sum(item.row_count for item in shards) == 151_936
    assert shards[-1].row_count == 151_936 - 37 * 4096
    composed = compose(
        151_936,
        [(item, words(item.first_output_row, item.row_count)) for item in shards],
    )
    assert composed.declared_extent == 151_936
    assert list(composed.words) == words(0, 151_936)


def test_planner_tiles_evenly_when_it_can():
    shards = plan_row_shards(OP, 1024, 8)
    assert [item.row_count for item in shards] == [128] * 8
    assert [item.first_output_row for item in shards] == [
        0, 128, 256, 384, 512, 640, 768, 896
    ]


def test_argmax_is_taken_after_composition_over_every_element():
    # The largest value sits inside the fifth shard; a per-shard argmax
    # merged by shard index would answer 0.
    parts = []
    for index in range(8):
        payload = [0x3F80] * 128
        if index == 4:
            payload[7] = 0x4100
        parts.append((ShardDescriptor(OP, index * 128, 128), payload))
    composed = compose(1024, parts)
    assert argmax_lowest_index(composed) == 4 * 128 + 7
