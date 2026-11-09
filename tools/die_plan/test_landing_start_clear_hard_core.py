import pytest
from tools.die_plan.landing_place import (_chain_clear_of_hard_cores, _clear_of_hard_cores,
                                          _reader_start_groups, _writer_start_groups)

CORE = {'inst': 'u', 'origin_um': [50, 50], 'outline_um': [100, 400]}
TYPE = {'outline_um': [300, 600], 'hard_cores': [CORE]}


def test_no_core_or_outside_is_identical():
    r = [10, 10, 14, 14]
    assert _clear_of_hard_cores({'outline_um': [300, 600]}, r) is r
    assert _clear_of_hard_cores(TYPE, r) is r


def test_partial_overlap_keeps_rows_and_is_unchanged():
    r = [48, 100, 52, 104]
    assert _clear_of_hard_cores(TYPE, r) is r


def test_inside_moves_to_nearest_side_clear_of_halo():
    x0, y0, x1, y1 = _clear_of_hard_cores(TYPE, [60, 200, 64.32, 204.32])
    assert (y0, y1) == (200, 204.32)
    assert x1 == pytest.approx(50 - 4.32)
    assert x1 - x0 == pytest.approx(4.32)


def test_neighbour_core_is_respected():
    t = {'outline_um': [300, 600], 'hard_cores': [CORE,
         {'inst': 'v', 'origin_um': [10, 50], 'outline_um': [38, 400]}]}
    x0, _, _, _ = _clear_of_hard_cores(t, [60, 200, 64.32, 204.32])
    assert x0 == pytest.approx(150 + 4.32)


def test_no_room_raises():
    t = {'outline_um': [108, 108], 'hard_cores': [{'origin_um': [0, 0], 'outline_um': [108, 108]}]}
    with pytest.raises(ValueError):
        _clear_of_hard_cores(t, [50, 50, 54, 54])


def test_reader_groups_use_clear_site():
    t = dict(TYPE, clock={'landing_reader_start': {'branches': {'b': {'stages': [{'xy_um': [62, 202]}]}}}})
    (_, rect, tag), = _reader_start_groups(t)
    assert tag == 'reader-start:b' and rect[2] <= 50 - 4.32 + 1e-6


def test_chain_outside_core_is_identical():
    assert _chain_clear_of_hard_cores(TYPE, (5, 5), [{'xy_um': [20, 20]}]) == [[17.84, 17.84, 22.16, 22.16]]


def test_chain_keeps_one_side_when_that_shortens_the_longest_hop():
    # Both stages sit closer to the east wall of a wide core, but the origin is west.
    t = {'outline_um': [600, 600], 'hard_cores': [{'origin_um': [50, 50], 'outline_um': [450, 500]}]}
    (a, b) = _chain_clear_of_hard_cores(t, (20, 300), [{'xy_um': [400, 300]}, {'xy_um': [440, 300]}])
    assert a[2] <= 50 and b[2] <= 50


def test_writer_groups_use_chain():
    t = dict(TYPE, clock={'landing_writer_start': {'branches': {'b': {'stages': [{'xy_um': [62, 202]}]}}}})
    (_, rect, tag), = _writer_start_groups(t)
    assert tag == 'writer-start:b' and rect[2] <= 50 - 4.32 + 1e-6
