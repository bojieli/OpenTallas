from __future__ import annotations

import itertools

import pytest

from runtime.reference.indexing import (
    INT32_MAX,
    MODEL_SOURCE_SHA256,
    IndexReferenceError,
    compressed_dense_indices,
    dspark_window_indices,
    window_indices,
)


def test_reference_is_bound_to_pinned_official_model_source() -> None:
    assert MODEL_SOURCE_SHA256 == (
        "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
    )


def test_window_prefill_known_answer_including_rollover() -> None:
    assert window_indices(4, 2, 6, 0) == (
        (
            (0, -1, -1, -1),
            (0, 1, -1, -1),
            (0, 1, 2, -1),
            (0, 1, 2, 3),
            (1, 2, 3, 4),
            (2, 3, 4, 5),
        ),
        (
            (0, -1, -1, -1),
            (0, 1, -1, -1),
            (0, 1, 2, -1),
            (0, 1, 2, 3),
            (1, 2, 3, 4),
            (2, 3, 4, 5),
        ),
    )


@pytest.mark.parametrize(
    ("start_position", "expected"),
    [
        (1, (0, 1, -1, -1)),
        (2, (0, 1, 2, -1)),
        (3, (0, 1, 2, 3)),
        (4, (1, 2, 3, 0)),
        (5, (2, 3, 0, 1)),
        (8, (1, 2, 3, 0)),
    ],
)
def test_window_decode_known_answers(
    start_position: int, expected: tuple[int, ...]
) -> None:
    assert window_indices(4, 1, 1, start_position) == ((expected,),)


def test_window_size_one_preserves_official_branch_order() -> None:
    # In the pinned source, start_pos >= window_size - 1 wins even for prefill.
    assert window_indices(1, 2, 7, 0) == (((0,),), ((0,),))


def test_compressed_prefill_and_decode_known_answers() -> None:
    assert compressed_dense_indices(4, 1, 10, 0, 128) == (
        (
            (-1, -1),
            (-1, -1),
            (-1, -1),
            (128, -1),
            (128, -1),
            (128, -1),
            (128, -1),
            (128, 129),
            (128, 129),
            (128, 129),
        ),
    )
    assert compressed_dense_indices(4, 3, 1, 7, 128) == (
        ((128, 129),),
        ((128, 129),),
        ((128, 129),),
    )
    assert compressed_dense_indices(4, 1, 1, 1, 128) == (((),),)


def test_dspark_history_and_draft_regions_are_disjoint() -> None:
    assert dspark_window_indices(4, 2, 3, 2) == (
        (
            (0, 1, 2, 4, 5, 6),
            (0, 1, 2, 4, 5, 6),
            (0, 1, 2, 4, 5, 6),
        ),
        (
            (0, 1, 2, 4, 5, 6),
            (0, 1, 2, 4, 5, 6),
            (0, 1, 2, 4, 5, 6),
        ),
    )
    saturated = dspark_window_indices(4, 1, 2, 99)
    assert saturated == (((0, 1, 2, 3, 4, 5), (0, 1, 2, 3, 4, 5)),)


def test_window_prefill_matches_causal_last_window_invariant_exhaustively() -> None:
    for window_size, sequence_length in itertools.product(range(2, 10), range(1, 14)):
        (matrix,) = window_indices(window_size, 1, sequence_length, 0)
        width = min(window_size, sequence_length)
        assert len(matrix) == sequence_length
        assert all(len(row) == width for row in matrix)
        for query_position, row in enumerate(matrix):
            valid = tuple(index for index in row if index >= 0)
            expected_start = max(0, query_position - window_size + 1)
            assert valid == tuple(range(expected_start, query_position + 1))
            assert row[len(valid) :] == (-1,) * (width - len(valid))


def test_compressed_indices_match_complete_group_invariant_exhaustively() -> None:
    for ratio, sequence_length, offset in itertools.product(
        range(1, 8), range(1, 20), (0, 3, 128)
    ):
        (matrix,) = compressed_dense_indices(
            ratio, 1, sequence_length, 0, offset
        )
        width = sequence_length // ratio
        for query_position, row in enumerate(matrix):
            complete = (query_position + 1) // ratio
            assert row[:complete] == tuple(offset + i for i in range(complete))
            assert row[complete:] == (-1,) * (width - complete)


@pytest.mark.parametrize(
    ("function", "arguments", "match"),
    [
        (window_indices, (0, 1, 1, 0), "window_size"),
        (window_indices, (4, True, 1, 0), "batch_size"),
        (window_indices, (4, 1, 0, 0), "sequence_length"),
        (window_indices, (4, 1, 1, -1), "start_position"),
        (compressed_dense_indices, (0, 1, 1, 0, 0), "ratio"),
        (compressed_dense_indices, (4, 1, 1, 0, -1), "offset"),
        (dspark_window_indices, (4, 1, 5, 0), "start_position"),
        (dspark_window_indices, (4, 1, 0, 1), "block_size"),
    ],
)
def test_invalid_structural_requests_fail_closed(
    function, arguments: tuple[int, ...], match: str
) -> None:
    with pytest.raises(IndexReferenceError, match=match):
        function(*arguments)


def test_int32_output_overflow_fails_instead_of_wrapping() -> None:
    with pytest.raises(IndexReferenceError, match="signed int32"):
        window_indices(INT32_MAX + 2, 1, 1, 0)
    with pytest.raises(IndexReferenceError, match="signed int32"):
        compressed_dense_indices(1, 1, 1, 1, INT32_MAX)
    with pytest.raises(IndexReferenceError, match="signed int32"):
        dspark_window_indices(INT32_MAX, 1, 2, 1)
