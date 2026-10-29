"""DIE-QC-3: clock_legal_dme (1x stage model, legal-site DME) + die_trial --clock-rc / --legal-dme opt-ins."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import clock_legal_dme as C   # noqa: E402
import die_trial as D          # noqa: E402
from test_die_trial_slice_spine import FakeSite   # noqa: E402


def test_1x_rc_is_the_platform_setrc_and_twice_the_ndr_r():
    r, c = C.RC_1X
    assert abs(r - 2 * D.WIRE_R) < 1e-12 and abs(c * 1.1 - D.WIRE_C) < 1e-12


def test_1x_stage_model_runs_slower_than_ndr_per_mm():
    # a regular 250-um repeated line: 1x ~ 283 ps/mm TT (spice-scaled), NDR fit 213 ps/mm (both OpenSTA ladders)
    ps_mm = C.stage_ps(250.0, 250.0, "TT") / 0.25
    assert 270 < ps_mm < 300
    assert C.stage_ps(250.0, 250.0, "FF") < C.stage_ps(250.0, 250.0, "TT")


def test_place_reps_never_lands_in_a_blocked_interval_when_a_legal_one_is_near():
    site = FakeSite(2000.0, 2000.0, [(300.0, 0.0, 700.0, 2000.0)])     # vertical core band x 300-700
    fs = C.FastSite(site)
    reps, bad = C.place_reps(fs, (100.0, 1000.0), (1100.0, 1000.0), 250.0)
    assert len(reps) == 3 and bad == 0
    assert all(site.legal(q) for q in reps)
    assert all(abs(q[1] - 1000.0) < 1e-6 for q in reps)                # stays on the route (no sideways jog)


def test_legal_dme_balances_a_slid_merge_point():
    # parent at the middle of two kids, but the middle is blocked: the stock site pass slid it toward one kid
    site = FakeSite(3000.0, 1000.0, [(1300.0, 0.0, 1700.0, 600.0)])
    nodes = {
        0: dict(id=0, x=1500.0, y=900.0, parent=None, kids=[1], taps=[], fixed=True),
        1: dict(id=1, x=1290.0, y=500.0, parent=0, kids=[2, 3], taps=[], req_xy=[1500.0, 500.0]),   # slid
        2: dict(id=2, x=700.0, y=500.0, parent=1, kids=[], taps=[("a", "t", 690.0, 500.0), ("a", "u", 710.0, 500.0)]),
        3: dict(id=3, x=2300.0, y=500.0, parent=1, kids=[], taps=[("b", "t", 2290.0, 500.0), ("b", "u", 2310.0, 500.0)]),
    }
    before = C._sub(C.FastSite(site), (1290.0, 500.0), [((700.0, 500.0), *C._sub(C.FastSite(site), (700.0, 500.0), [], [(690.0, 500.0), (710.0, 500.0)], 250.0, "TT")),
                                                          ((2300.0, 500.0), *C._sub(C.FastSite(site), (2300.0, 500.0), [], [(2290.0, 500.0), (2310.0, 500.0)], 250.0, "TT"))],
                    [], 250.0, "TT")
    st = C.legal_dme(nodes, site, 250.0)
    lo, hi = nodes[1]["dme"]
    assert site.legal((nodes[1]["x"], nodes[1]["y"]))
    assert hi - lo < 10.0 < before[1] - before[0]          # slid: ~2 x 210 um of imbalance; DME: <10 ps
    assert (nodes[0]["x"], nodes[0]["y"]) == (1500.0, 900.0) and st["moved"] >= 1   # fixed node stays


def test_column_node_slides_along_the_column_to_balance_unequal_strips():
    site = FakeSite(2000.0, 4000.0, [])
    heavy = [("h", f"t{i}", 1800.0, 3000.0) for i in range(4)]     # far strip (long leaf legs)
    light = [("l", "t", 1010.0, 1000.0)]
    nodes = {
        0: dict(id=0, x=1000.0, y=3900.0, parent=None, kids=[1], taps=[], fixed=True),
        1: dict(id=1, x=1000.0, y=2000.0, parent=0, kids=[2, 3], taps=[], fixed=True, spine="column"),
        2: dict(id=2, x=1000.0, y=3000.0, parent=1, kids=[], taps=heavy, fixed=True, spine="column"),
        3: dict(id=3, x=1000.0, y=1000.0, parent=1, kids=[], taps=light, fixed=True, spine="column"),
    }
    st = C.legal_dme(nodes, site, 250.0)
    lo, hi = nodes[1]["dme"]
    assert nodes[1]["x"] == 1000.0 and 2000.0 < nodes[1]["y"] < 3000.0     # moved toward the slow (heavy) strip
    assert hi - lo < 10.0 and st["column_moves"] == 1
    st = C.legal_dme(nodes, site, 250.0, column_slide=False)


def test_place_reps_drops_a_repeater_rather_than_put_it_on_a_core():
    site = FakeSite(3000.0, 3000.0, [(0.0, 1000.0, 3000.0, 2200.0)])      # 1200-um core band across the route
    reps, bad = C.place_reps(C.FastSite(site), (500.0, 900.0), (500.0, 2300.0), 250.0)
    assert bad >= 1 and all(site.legal(q) for q in reps)


def test_opt_ins_default_off():
    sig = inspect.signature(D.clock_kit).parameters
    assert sig["clock_rc"].default == "ndr" and sig["legal_dme"].default is False
    sig = inspect.signature(D.write_kit).parameters
    assert sig["clock_rc"].default == "ndr" and sig["legal_dme"].default is False


if __name__ == "__main__":
    n = 0
    for k, f in sorted(dict(globals()).items()):
        if k.startswith("test_"):
            f()
            n += 1
    print(n, "passed")
