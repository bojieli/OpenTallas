"""Density clock taps (OWNER decision 5, 10-24; clock.tap_mode "density").   python3 -m pytest -q tools/die_plan/test_density_taps.py"""
import copy
import json
import random
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schema  # noqa: E402
import taps  # noqa: E402
from test_g2 import PAIR  # noqa: E402

CORES = [dict(inst="u_a", origin_um=[17.28, 8.64], outline_um=[317.672, 317.672]),
         dict(inst="u_b", origin_um=[371.52, 8.64], outline_um=[317.672, 317.672]),
         dict(inst="u_e", origin_um=[216.0, 734.4], outline_um=[277.652, 277.652])]


def _plan(sites, cores=CORES, **ck):
    """a fake plan of one 708.48 x 1036.8 type (the S81 hd_tile outline) with no pins: sinks = sink_sites_um only."""
    c = dict(tap_mode="density", tap_um=[354.24, 518.4])
    c.update(ck)
    c["sink_sites_um"] = sites
    t = dict(outline_um=[708.48, 1036.8], hard_cores=cores, clock=c)
    return SimpleNamespace(types={"hd": t}, clock=dict(insertion_ps=250))


def _sites(seed=1):
    """S81-head-like inventory: a dense top band around the elemB core (y > 700) and a sparse cross channel."""
    r = random.Random(seed)
    out = []
    for _ in range(9000):
        x, y = r.uniform(20, 690), r.uniform(705, 1030)
        if not (216 < x < 494 and 734 < y < 1012):
            out.append([round(x, 3), round(y, 3)])
    for _ in range(1500):
        out.append([round(r.uniform(337, 369), 3), round(r.uniform(10, 700), 3)])
    for _ in range(600):
        out.append([round(r.uniform(20, 690), 3), round(r.uniform(328, 378), 3)])
    return out


def _no_pins(monkeypatch):
    monkeypatch.setattr(taps, "planned_sinks", lambda P, tn: [])
    taps._CACHE.clear()


def _in_core(x, y, cores=CORES, clear=schema.TAP_CLEAR_UM):
    return any(c["origin_um"][0] - clear < x < c["origin_um"][0] + c["outline_um"][0] + clear and
               c["origin_um"][1] - clear < y < c["origin_um"][1] + c["outline_um"][1] + clear for c in cores)


def test_density_respects_cap_radius_and_keep_clear(monkeypatch):
    _no_pins(monkeypatch)
    P = _plan(_sites(), tap_max_sinks=1500, tap_radius_um=200.0)
    tl = taps.density_taps(P, "hd")
    n = sum(t[3] for t in tl)
    assert n == len(P.types["hd"]["clock"]["sink_sites_um"])               # every sink in exactly one cluster
    assert all(0 < t[3] <= 1200 for t in tl)                                # default target 0.8 x cap, no empty tap
    assert [t[0] for t in tl] == ["clk"] + [f"clk_t{i}" for i in range(1, len(tl))]
    assert not any(_in_core(x, y) for _, x, y, _, _ in tl)                  # no tap on (or next to) a hard core
    assert all(schema.TAP_CLEAR_UM <= x <= 708.48 - schema.TAP_CLEAR_UM and
               schema.TAP_CLEAR_UM <= y <= 1036.8 - schema.TAP_CLEAR_UM for _, x, y, _, _ in tl)
    xy = [(x, y) for _, x, y, _, _ in tl]
    assert all(max(abs(a[0] - b[0]), abs(a[1] - b[1])) >= schema.TAP_CLEAR_UM
               for i, a in enumerate(xy) for b in xy[i + 1:])                   # distinct spine drops
    # density follows the sinks: most taps sit in the dense top band, none in the empty core areas
    assert sum(1 for _, _, y, _, _ in tl if y > 700) >= 0.6 * len(tl)
    # the kit's nearest + capacity split of the same sinks keeps every tap under the hard cap
    sinks = [(x, y, 1.0) for x, y in P.types["hd"]["clock"]["sink_sites_um"]]
    load, far, _ = taps.assign(tl, sinks, 1500, 200.0)
    assert max(load) <= 1500 and min(load) > 0


def test_density_weighted_bins_and_single_heavy_site(monkeypatch):
    _no_pins(monkeypatch)
    P = _plan([[100, 760, 900], [110, 770, 900], [600, 760, 300], [354, 350, 50]], tap_max_sinks=1000,
              tap_target_sinks=1000)
    tl = taps.density_taps(P, "hd")
    assert sorted(t[3] for t in tl) == [50, 300, 900, 900]                  # two 900 bins never share a 1000 tap
    P2 = _plan([[100, 760, 2500]], tap_max_sinks=1500)                       # one site above the target: one tap
    assert [t[3] for t in taps.density_taps(P2, "hd")] == [2500]


def test_density_deterministic(monkeypatch):
    _no_pins(monkeypatch)
    a = taps.density_taps(_plan(_sites(3)), "hd")
    taps._CACHE.clear()
    s = _sites(3)
    b = taps.density_taps(_plan(s), "hd")
    assert a == b
    sinks = [(x, y, 1.0) for x, y in s]
    assert taps.assign(a, sinks, 1500, 200.0) == taps.assign(b, list(sinks), 1500, 200.0)
    # input order does not matter
    taps._CACHE.clear()
    c = taps.density_taps(_plan(list(reversed(s))), "hd")
    assert [(t[1], t[2], t[3]) for t in c] == [(t[1], t[2], t[3]) for t in a]


def test_assign_distance_then_load():
    tl = [("clk", 100.0, 100.0), ("clk_t1", 300.0, 100.0), ("clk_t2", 900.0, 100.0)]
    sinks = [(110.0 + i * 0.01, 100.0, 1.0) for i in range(30)]               # all nearest clk
    load, far, asg = taps.assign(tl, sinks, 20, 250.0)
    assert load == [20, 10, 0]                                              # overflow to the next-nearest with room
    assert set(asg[:20]) == {0} or load[0] == 20
    load, _, _ = taps.assign(tl, sinks, 20, 100.0)                          # too far to move: stays over (WARN)
    assert load == [30, 0, 0]


def test_tap_clear_default_unchanged():
    t = dict(outline_um=[400.0, 400.0])
    assert schema.tap_clear(t, 1.0, 1.0, [(1.0, 2.0)]) == (1.0, 1.0)        # no cores: untouched (grid kits)
    x, y = schema.tap_clear(t, 1.0, 1.0, [(1.0, 2.0)], strict=True)
    assert x >= schema.TAP_CLEAR_UM and y >= schema.TAP_CLEAR_UM


def test_density_kit_config_and_defaults_unchanged():
    import gen_phys
    P0 = schema.Plan(copy.deepcopy(PAIR))
    raw = copy.deepcopy(PAIR)
    w, h = raw["partition_types"]["fa"]["outline_um"]
    raw["partition_types"]["fa"].setdefault("clock", {}).update(
        tap_mode="density", tap_radius_um=150.0, tap_max_sinks=40,
        sink_sites_um=[[w * 0.25, h * 0.25, 30], [w * 0.75, h * 0.75, 30]])
    P = schema.Plan(raw)
    tl = schema.tap_grid(P, "fa")
    st = taps.density_taps(P, "fa")
    assert [(n, x, y) for n, x, y, _, _ in st] == tl and all(t[3] > 0 for t in st)
    with tempfile.TemporaryDirectory() as d:
        gen_phys.write_type_kit(P, "fa", d, [])
        cfg = (Path(d) / "fa" / "config.mk").read_text()
        assert "OT_TAP_MAX_SINKS = 40" in cfg and "OT_TAP_REASSIGN_UM = 150" in cfg
        # FLOW 10-25: POST_GLOBAL_ROUTE is the grt_post.tcl chain, which sources tap_balance_grt.tcl on OT_TAP_GRT_MODE
        assert "POST_GLOBAL_ROUTE_TCL = /work/grt_post.tcl" in cfg and "OT_TAP_GRT_MODE = grt_report" in cfg
        assert (Path(d) / "fa" / "tap_balance_grt.tcl").is_file()
        bud = json.loads((Path(d) / "fa" / "budget.json").read_text())["clock"]
        assert bud["tap_mode"] == "density" and bud["grid_taps"] == 0
        assert {t["kind"] for t in bud["taps"]} == {"density"} and len(bud["sink_taps"]) == len(tl)
    with tempfile.TemporaryDirectory() as d:                                # default kit: none of it
        gen_phys.write_type_kit(P0, "fa", d, [])
        cfg = (Path(d) / "fa" / "config.mk").read_text()
        assert "OT_TAP_MAX_SINKS = 3000" in cfg
        assert "OT_TAP_REASSIGN_UM" not in cfg and "OT_TAP_GRT_MODE" not in cfg
        assert not (Path(d) / "fa" / "tap_balance_grt.tcl").exists()


def test_tap_balance_grt_hook_text():
    s = (HERE / "tap_balance.tcl").read_text()
    assert "global_route -start_incremental" in s and "estimate_parasitics -global_routing" in s
    assert "${n}_tb${tb_tag}${it}_tree" in s                                # GRT pass cells never clash with CTS ones
    g = (HERE / "tap_balance_grt.tcl").read_text()
    assert "write_guides $::env(RESULTS_DIR)/route.guide" in g and "OT_TAP_EST) grt" in g


def test_sparse_control_bank_keeps_its_own_tap(monkeypatch):
    _no_pins(monkeypatch)
    # Data bank at the left, a single reset-control flop 550 um away.
    # The minimum sink preference must not pull that control onto the band.
    P = _plan([[100+i*.1, 600] for i in range(200)] + [[650, 600]], cores=[],
              tap_max_sinks=1250, tap_target_sinks=1000,
              tap_radius_um=175, tap_min_sinks=50)
    tl=taps.density_taps(P,'hd')
    assert len(tl)==2
    assert sorted(t[3] for t in tl)==[1,200]
    assert max(t[4] for t in tl)<=175


def test_sparse_nearby_group_may_merge_without_long_clock_arm():
    leaves=[(100,100,200,5,[(95,100,100),(105,100,100)]),
            (110,100,1,0,[(110,100,1)]),
            (650,100,1,0,[(650,100,1)])]
    result=taps._absorb(leaves,1000,50,175)
    assert sorted(q[2] for q in result)==[1,201]
    assert max(q[3] for q in result)<=175


def test_face_legalisation_cannot_silently_extend_radius(monkeypatch):
    _no_pins(monkeypatch)
    # Median y=2 is clamped to the interior; the former 160 um radius then
    # becomes 175.28 um and needs another legal tap, rather than a false bound.
    P=_plan([[100,2,200],[260,2,1]],cores=[],tap_max_sinks=1250,
            tap_target_sinks=1000,tap_radius_um=175,tap_min_sinks=50)
    tl=taps.density_taps(P,'hd')
    assert len(tl)==2
    assert max(t[4] for t in tl)<=175


def test_capacity_move_cannot_break_absolute_density_radius():
    tl=[('clk',100,100),('clk_t1',300,100)]
    sinks=[(100+i*.01,100,1) for i in range(30)]
    load,far,_=taps.assign(tl,sinks,20,250,max_distance_um=175)
    assert load==[30,0]
    assert max(far)<1
