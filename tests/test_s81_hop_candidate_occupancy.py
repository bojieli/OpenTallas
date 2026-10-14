import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import dsrom_s81_fulldie as F


def test_chain_candidate_reserves_stations_and_rolls_back_on_failure():
    occ = F.Occ(B=10)
    existing = (0, 0, 3, 3)
    occ.add(existing)
    before = {key: list(boxes) for key, boxes in occ.g.items()}
    with pytest.raises(RuntimeError):
        with occ.temporary() as reserve:
            first = (7, 7, 16, 16)
            assert occ.free(first)
            reserve(first)
            # The next station crosses several bins of the first. It must
            # reject this position before a candidate can be called clean.
            assert not occ.free((15, 15, 19, 19))
            assert not occ.free(existing)
            raise RuntimeError('candidate did not place its last station')
    assert dict(occ.g) == before
    assert occ.free((15, 15, 19, 19))
    assert not occ.free(existing)


def test_candidate_placement_does_not_reuse_first_station_box():
    planner = F.Placer({'insts': []})
    allowed = [(0, 0, 100, 100)]
    first = planner.near(40, 40, 10, 10, allowed, span=24, rows=2)
    assert first
    with planner.occ.temporary() as reserve:
        reserve((first[0], first[1], first[0] + 10, first[1] + 10))
        second = planner.near(40, 40, 10, 10, allowed, span=24, rows=2)
        assert second and second != first
        assert planner.occ.free((second[0], second[1], second[0] + 10, second[1] + 10), .432)
    assert planner.near(40, 40, 10, 10, allowed, span=24, rows=2) == first
