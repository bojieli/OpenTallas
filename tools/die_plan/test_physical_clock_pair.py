import pytest
from physical_clock_pair import midpoint


def test_midpoint_two_equal_real_wire_legs_all_quadrants():
    a=(500,500)
    for b in [(100,400),(400,100),(900,600),(600,900)]:
        for sign in [-1,1]:
            p=midpoint(a,b,800,sign)
            assert sum(abs(x-y) for x,y in zip(a,p))==pytest.approx(400)
            assert sum(abs(x-y) for x,y in zip(p,b))==pytest.approx(400)
