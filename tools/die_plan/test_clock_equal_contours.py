import pytest
from clock_equal_contours import points


def test_every_candidate_has_equal_individual_physical_legs():
    for a,b,r in [((0,0),(100,0),75),((0,0),(100,100),125),((100,150),(75,80),75),((100,100),(100,100),50)]:
        candidates=points(a,b,r)
        assert candidates
        for p in candidates:
            assert abs(a[0]-p[0])+abs(a[1]-p[1])==pytest.approx(r)
            assert abs(b[0]-p[0])+abs(b[1]-p[1])==pytest.approx(r)
    assert points((0,0),(100,100),99)==[]
