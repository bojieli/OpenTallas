"""S81-PLAN-1: the rank-tree leg is compiled from the bound tl / ca / cb depths; +-1 moves it, missing lanes fail."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lower_bk as LB


def bind(tl=58, ca=59, cb=58):
    mk = lambda lane, n: dict(lane=lane, bound_stages=n, plan_cycles=n)
    return dict(buses=[mk(LB.TREE_LANES['tl'], tl), mk(LB.TREE_LANES['ca'], ca), mk(LB.TREE_LANES['cb'], cb)])


def test_c72370_legs():
    assert LB.tree_legs_from_bind(bind()) == {2: 846, 3: 845}
    assert LB.tree_leg_bound(bind()) == 846


def test_shift_and_fail_closed():
    for d in (1, -1):
        assert LB.tree_leg_bound(bind(tl=58 + d)) == 846 + d
    b = bind()
    b['buses'][0]['plan_cycles'] = 0
    with pytest.raises(ValueError):
        LB.tree_leg_bound(b)
    with pytest.raises(ValueError):
        LB.tree_leg_bound(dict(buses=bind()['buses'][1:]))
