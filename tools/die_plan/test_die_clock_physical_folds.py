import math
import pytest
from die_clock import folded_leg


def length(a, points):
    total=0
    for p in points:
        total+=abs(p[0]-a[0])+abs(p[1]-a[1]);a=p
    return total


def test_folds_realize_equal_length_with_equal_stage_count():
    a=(1000,1000)
    for target in (400,750,1000,1250,1600):
        points=folded_leg(a,(target,1000),0,700,2,die=(3000,3000))
        assert len(points)==4
        assert points[-1]==(target,1000)
        assert math.isclose(length(a,points),700)
        prev=a
        for p in points:
            assert abs(prev[0]-p[0])+abs(prev[1]-p[1])<=350
            prev=p


def test_edge_fold_chooses_inward_and_refuses_hidden_shortfall():
    points=folded_leg((100,100),(150,100),0,400,1,die=(1000,1000))
    assert length((100,100),points)==400
    assert all(x>=1 for x,y in points)
    with pytest.raises(ValueError):folded_leg((100,100),(500,100),0,200,1)
