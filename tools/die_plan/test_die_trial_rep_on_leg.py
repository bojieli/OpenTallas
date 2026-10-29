"""DIE-QC-24 (COORD 10-28 21:00): repeater leg-slide rules, opt-in.
Root cause (trial15): a region-DME leg route that crosses a hard core (+halo) on a blocked run < route_um is accepted; the
evenly spaced repeater inside the core is moved by site.nearest() to the closest core EDGE, which can be sideways (28
repeaters 146.8 um off-leg).  --rep-on-leg slides it ALONG its own leg; --rep-off-leg-max UM fails the kit when a repeater
sits more than UM off its planned leg.  Both default off = byte-identical."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import die_trial as D
from test_die_trial_slid_root import _P, _nodes


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(D, "lef_top_layer", lambda _: None)
    yield
    D.REP_ON_LEG = False
    D.REP_OFF_LEG_MAX_UM = None


def _route_leg(y=650.0, x0=1000.0, x1=2000.0):
    """a routed DME leg (nd['route']) along y through the 800 x 400 core of _P (x 1100-1900, y 300-700), 52 um below
    the core's top halo edge (702.16): the short way out of the core is sideways, as in trial15 c_E0_tf_00"""
    n = _nodes(x0, x1, y)
    n[1]["route"] = [[x0, y], [x1, y]]
    return n


def _reps(place):
    return [(x, y) for i, x, y in place if i.startswith("r")]


def test_stock_placement_slides_sideways_and_guard_fails():
    site = D.SiteMap(_P())
    n = _route_leg()
    _, place, *_ = D.tree_netlist(n, [], rep_um=250.0, site=site)
    leg = [(1000.0, 650.0), (2000.0, 650.0)]
    offs = sorted(D.off_leg_um(c, leg) for c in _reps(place))
    assert len(offs) == 3 and offs[-1] > 50.0                  # the root cause: sideways to the top halo edge
    D.REP_OFF_LEG_MAX_UM = 50.0
    with pytest.raises(ValueError, match="rep-off-leg-max 50: 3 leg repeaters"):
        D.tree_netlist(_route_leg(), [], rep_um=250.0, site=D.SiteMap(_P()))


def test_rep_on_leg_keeps_repeaters_on_the_leg_and_passes_guard():
    D.REP_ON_LEG = True
    D.REP_OFF_LEG_MAX_UM = 50.0
    site = D.SiteMap(_P())
    n = _route_leg()
    _, place, *_ = D.tree_netlist(n, [], rep_um=250.0, site=site)
    reps = _reps(place)
    assert len(reps) == 3
    assert all(site.legal(c) for c in reps)
    assert all(abs(c[1] - 650.0) < 1e-6 for c in reps)        # on the leg, no sideways spur
    xs = [c[0] for c in reps]
    assert xs == sorted(xs) and len(set(xs)) == 3              # order along the leg kept, no two at one point
    assert xs[0] < 1100.0 and xs[1] > 1900.0                   # slid to the core's halo edges along the leg


def test_defaults_and_clean_legs_are_byte_identical():
    a = D.tree_netlist(_route_leg(y=850.0), [], rep_um=250.0, site=D.SiteMap(_P()))   # y 850: leg clear of the core
    D.REP_ON_LEG = True
    D.REP_OFF_LEG_MAX_UM = 50.0
    b = D.tree_netlist(_route_leg(y=850.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    assert a[0] == b[0] and a[1] == b[1]
    # the slid-root detour fixture (DIE-KV-2) is unchanged by the flags
    D.REP_ON_LEG = False
    D.REP_OFF_LEG_MAX_UM = None
    c = D.tree_netlist(_nodes(1902.2, 900.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    D.REP_ON_LEG = True
    D.REP_OFF_LEG_MAX_UM = 50.0
    d = D.tree_netlist(_nodes(1902.2, 900.0), [], rep_um=250.0, site=D.SiteMap(_P()))
    assert c[0] == d[0] and c[1] == d[1]


def test_off_leg_um():
    assert D.off_leg_um((5.0, 3.0), [(0, 0), (10, 0)]) == 3.0
    assert D.off_leg_um((12.0, 0.0), [(0, 0), (10, 0), (10, 10)]) == 2.0
    assert D.off_leg_um((5.0, 5.0), [(0, 0), (10, 10)]) == 0.0          # straight leg: any L route in its bbox


def test_cli_flags_parse():
    src = Path(D.__file__).read_text()
    assert '"--rep-on-leg"' in src and '"--rep-off-leg-max"' in src
