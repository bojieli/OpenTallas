"""The candidate-mask reference semantics, and the vectors built from them.

These tests pin the parts of ``select_candidate_mask`` a campaign cannot argue
about later: the polarity, the pinned-last-block rule, the -inf padded tail, the
set behaviour of the ids, and the refusals.  The RTL correlation itself is
``results/rtl/a3_v41_candidate_mask_campaign.json``
(``tools/run_a3_v41_candidate_mask_rtl_campaign.py``).
"""

from __future__ import annotations

import pytest

from runtime.reference.candidate_pool import (
    CANDIDATE_MASK_ABSENT_ID,
    CandidateMaskError,
    select_candidate_mask,
)
from tools.build_a3_v41_candidate_mask_vectors import GEOMETRIES, build_cases, evaluate


def test_polarity_is_admission_not_exclusion():
    #: One block of eight chosen out of a 64-position axis admits eight
    #: positions.  Were a set bit an exclusion, the population would be 56.
    result = select_candidate_mask([0], width=64, block=8, pin_last_block=False)
    assert result["polarity"] == "set_bit_admits_position"
    assert result["population"] == 8
    assert result["words"] == (0x000000FF, 0x00000000)


def test_v41_pool_population_is_the_declared_bound():
    #: 2,048 blocks of 8 is 16,384 admitted positions -- the bound the plan's
    #: candidate_pool_bound checker states, which is what fixes the polarity.
    result = select_candidate_mask(list(range(2048)), width=16384, block=8)
    assert result["population"] == 16384
    assert result["admitted_block_count"] == 2048
    assert all(word == 0xFFFFFFFF for word in result["words"])


def test_pinned_last_block_is_admitted_without_any_id():
    pinned = select_candidate_mask([], width=100, block=8)
    assert pinned["pinned_block"] == 12
    assert pinned["blocks"] == (12,)
    #: The last block of a 100-position axis holds four positions, not eight.
    assert pinned["population"] == 4
    unpinned = select_candidate_mask([], width=100, block=8, pin_last_block=False)
    assert unpinned["population"] == 0
    assert unpinned["words"] == (0, 0, 0, 0)


def test_the_pin_is_counted_once_when_an_id_names_it():
    both = select_candidate_mask([7], width=64, block=8)
    assert both["blocks"] == (7,)
    assert both["population"] == 8


def test_tail_beyond_width_is_never_admitted():
    result = select_candidate_mask([0], width=5, block=8)
    assert result["block_count"] == 1
    assert result["population"] == 5
    assert result["words"] == (0b11111,)
    assert result["tail_bits"] == 5


def test_ids_are_a_set_and_order_free():
    a = select_candidate_mask([11, 2, 0], width=100, block=8)
    b = select_candidate_mask([0, 2, 11, 2, 0, 11], width=100, block=8)
    assert a["words"] == b["words"]
    assert a["population"] == b["population"] == 28


def test_absent_slots_admit_nothing():
    absent = [CANDIDATE_MASK_ABSENT_ID] * 4
    assert (select_candidate_mask(absent + [5], width=4096, block=8)["words"]
            == select_candidate_mask([5], width=4096, block=8)["words"])


def test_block_size_that_is_not_a_power_of_two():
    result = select_candidate_mask([0, 2], width=10, block=3)
    assert result["block_count"] == 4
    assert result["blocks"] == (0, 2, 3)
    #: blocks 0 and 2 are three positions each, the pinned block 3 is one.
    assert result["population"] == 7
    assert result["words"] == (0b1111000111,)


def test_id_outside_the_block_count_is_a_fault():
    with pytest.raises(CandidateMaskError, match="outside the 8 blocks"):
        select_candidate_mask([8], width=64, block=8)


def test_population_bound_refuses_rather_than_truncates():
    with pytest.raises(CandidateMaskError, match="above the declared bound"):
        select_candidate_mask([0, 1], width=64, block=8, max_population=8)


def test_degenerate_geometry_is_refused():
    with pytest.raises(CandidateMaskError):
        select_candidate_mask([], width=0, block=8)
    with pytest.raises(CandidateMaskError):
        select_candidate_mask([], width=8, block=0)


def test_campaign_cases_are_internally_consistent():
    cases = build_cases()
    assert len(cases) >= 30
    for entry in cases:
        evaluate(entry)
        geom = GEOMETRIES[entry["geom"]]
        if entry["expect_code"] == 0:
            assert len(entry["words"]) == (entry["width"] + 31) // 32
            assert entry["population"] <= entry["width"]
        if entry["max_pop"] and entry["expect_code"] == 0:
            assert entry["population"] <= entry["max_pop"]
        assert geom["block"] >= 1
    #: Every geometry the top elaborates is exercised by at least one case, and
    #: both polarities of the pinned-last-block rule appear.
    assert {c["geom"] for c in cases} == {g["geom"] for g in GEOMETRIES}
    assert {GEOMETRIES[c["geom"]]["pin"] for c in cases} == {0, 1}
