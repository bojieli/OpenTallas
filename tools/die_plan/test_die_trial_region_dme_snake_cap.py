"""DIE-QC-23: --region-dme-snake-cap opt-in (COORD 10-28 19:26 structural long-snake fix): in early-mode 'merge' regions
the glue taps are built into one DME tree first and each early core sink joins at its root, so the elongation is not
repeated on every low glue subtree; default off = byte-identical trees."""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_region_dme_snake import _arrivals
from test_die_trial_slice_balance import FakeSite, _c_partition


def _mixed():
    """a 1.3 x 2.6 mm partition: 4 x 8 glue grid with two early core taps INSIDE it (c_W2_bn_01 pattern: the spatial
    cut puts each core sink beside glue taps, so the stock merge snakes those glue subtrees)"""
    site = FakeSite(1300.0, 2600.0, [])
    taps = [("p", f"t{i}_{j}", 150.0 + 330.0 * i, 150.0 + 330.0 * j) for i in range(4) for j in range(8)]
    taps += [("p", "c0", 480.0, 1300.0), ("p", "c1", 810.0, 500.0)]
    return site, taps, {("p", "c0"): 300.0, ("p", "c1"): 250.0}


@pytest.fixture
def cap():
    yield
    D.DME_SNAKE_CAP_UM = None


def _run(c):
    D.DME_SNAKE_CAP_UM = c
    site, taps, early = _mixed()
    return D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge", snake=True)


def test_cap_moves_merge_point_up(cap):
    dn0, r0, st0 = _run(None)
    dn, root, st = _run(1200.0)
    a0, a = _arrivals(dn0, r0, 250.0), _arrivals(dn, root, 250.0)
    assert sorted(a) == sorted(a0)                                         # every tap delivered once
    assert st0["snakes"] >= 1 and st0["snake_wire_um"] > 1000.0            # the fixture really snakes glue subtrees
    assert st["snakes"] < st0["snakes"] and st["snake_wire_um"] < st0["snake_wire_um"]
    assert st["snake_legs_over_cap"] == 0 and st["snake_max_leg_um"] <= 1200.0
    assert "snake_legs_over_cap" not in st0                                # stats only with the cap
    assert st["snake_cap_rebuilt"] == 1
    g = [v for k, v in a.items() if not k.startswith("c")]
    assert max(g) - min(g) <= 5.0                                          # glue still zero-skew
    m = sum(g) / len(g)
    assert abs(m - a["c0"] - 300.0) <= 5.0 and abs(m - a["c1"] - 250.0) <= 5.0   # early by construction
    st_, out = [root], []
    while st_:
        i = st_.pop()
        assert len(dn[i]["kids"]) <= 2                                     # binary, no hang
        st_ += dn[i]["kids"]


def test_partition_within_cap_keeps_stock_tree(cap):
    dn0, r0, st0 = _run(None)
    dn, root, st = _run(1e9)                     # no stock snake leg is over the cap -> nothing rebuilt
    assert st["snake_cap_rebuilt"] == 0 and (dn, root) == (dn0, r0)


def test_default_and_non_merge_unchanged(cap):
    site, taps = _c_partition()
    early = {(taps[0][0], taps[0][1]): 60.0}
    D.DME_SNAKE_CAP_UM = None
    ref = [D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, snake=True),
           D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge")]
    D.DME_SNAKE_CAP_UM = 1200.0
    got = [D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, snake=True),          # hang mode
           D.dme_region_tree(site, taps, delay_rep_um=250.0, early=early, early_mode="merge")]   # no snake
    assert got[1] == ref[1]
    assert got[0][0] == ref[0][0] and got[0][1] == ref[0][1]                # same tree; stats gain the cap keys only
    assert {k: v for k, v in got[0][2].items() if not k.startswith("snake_")} == \
        {k: v for k, v in ref[0][2].items() if not k.startswith("snake_")}


def test_flag_is_opt_in():
    assert D.DME_SNAKE_CAP_UM is None
    src = inspect.getsource(D.main)
    assert "--region-dme-snake-cap" in src and "needs --region-dme-snake" in src
