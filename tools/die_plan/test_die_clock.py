"""tests for die_clock.py: the structured die clock is balanced by construction (identical electrical path to every
tap), legal (no die buffer on a keep-out), and its STA on the exact RC shows ~0 tap skew."""
import argparse
import json
import shutil
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import die_clock as DC  # noqa: E402
import schema as S  # noqa: E402

PLANS = [HERE / "examples" / "tiny_plan.json", HERE / "examples" / "s81_pair" / "s81_pair_plan.json"]


def signature(T, tree):
    """per tap: the electrical sequence (padded length, layer, driver fan-out) from the root to the tap port."""
    into = {}
    for n in T.nets:
        for L, layer, load, _ in n["branches"]:
            into[load] = (round(L, 6), layer, len(n["branches"]))
    out = {}
    for t in tree["taps"]:
        out[t["port"]] = tuple(into[c] for c in t["path"] if c in into) + (into["port:" + t["port"]],)
    return out


@pytest.mark.parametrize("plan", PLANS, ids=lambda p: p.stem)
@pytest.mark.parametrize("leaf", [300.0, 1000.0])
def test_balanced_by_construction(plan, leaf):
    P = S.Plan(json.loads(plan.read_text()))
    T, tree = DC.build(P, leaf_um=leaf, rep_um=450.0, keep=[], pad="level")
    taps = DC.plan_taps(P)
    assert len(tree["taps"]) == len(taps)
    sig = signature(T, tree)
    assert len(set(sig.values())) == 1, "every root -> tap path must be electrically identical"
    # every node drives the same load: fan-out per level identical
    fo = {}
    for n in T.nets:
        c = T.cells.get(n["drv"])
        if c and c["kind"] == "node":
            fo.setdefault(c["level"], set()).add(len(n["branches"]))
    assert all(len(v) == 1 for v in fo.values())


def test_keepout_legalisation_keeps_balance():
    P = S.Plan(json.loads(PLANS[1].read_text()))
    T0, tree0 = DC.build(P, leaf_um=300.0, keep=[], pad="level")
    # a keep-out over a third of the die's H-tree nodes / repeaters
    cells = [c for c in T0.cells.values() if c["kind"] in ("node", "rep")]
    keep = [(c["x"] - 30.0, c["y"] - 30.0, c["x"] + 30.0, c["y"] + 30.0, f"k{i}") for i, c in enumerate(cells[1::3])]
    T, tree = DC.build(P, leaf_um=300.0, keep=keep, pad="level")
    K = DC.KeepIndex(keep)
    assert tree["meta"]["cells_on_keepout"] == 0
    assert not [n for n, c in T.cells.items() if c["kind"] in ("node", "rep") and K.hit(c["x"], c["y"])]
    assert len(set(signature(T, tree).values())) == 1
    assert tree["meta"]["geometry_over_standard_um"] <= 1e-6


def test_split_keeps_related_taps_together():
    """a split candidate on a partition edge that cuts less pair weight wins over the midpoint."""
    coords = {0: 10.0, 1: 40.0, 2: 60.0, 3: 90.0}
    pairs = [(1, 2, 100), (0, 1, 1), (2, 3, 1)]
    s, w = DC.choose_split(0.0, 100.0, 0, coords, pairs, edges=[45.0, 70.0], window=0.25)
    assert s == 70.0 and w == 1
    s, w = DC.choose_split(0.0, 100.0, 0, coords, pairs, edges=[], window=0.25)
    assert s == 50.0 and w == 100


@pytest.mark.skipif(not (shutil.which("sta") or Path("~/.local/opentallas-tools/bin/sta").expanduser().is_file()),
                    reason="OpenSTA not installed")
@pytest.mark.parametrize("pad", ["level", "sta"])
def test_sta_skew_and_spine(tmp_path, pad):
    try:
        libdir = DC.find_libdir()
    except SystemExit:
        pytest.skip("no ASAP7 libs")
    plan = PLANS[1]
    a = argparse.Namespace(plan=str(plan), out=str(tmp_path), leaf_um=300.0, rep_um=450.0, core_early="off",
                           window=DC.SPLIT_WINDOW, aware_levels=DC.AWARE_LEVELS, corner=["TT", "FF"], libdir=libdir,
                           iters=0 if pad == "level" else 10, stop_ps=2.0, pad=pad)
    lim = 0.5 if pad == "level" else DC.TARGET_PS
    assert DC.cmd_run(a) == 0
    rep = json.loads((tmp_path / "clock_report.json").read_text())
    for c in ("TT", "FF"):
        cr = rep["corners"][c]
        assert cr["tap_skew_ps"] < lim
        assert cr["tap_slew_max_ps"] < 320
        assert rep["verdict"][c]["gate"] == "PASS"
        sp = json.loads((tmp_path / f"spine_{c}.json").read_text())
        assert sum(len(p["taps"]) for p in sp["parts"].values()) == cr["taps"]
        assert max(t["offset_ps"] for p in sp["parts"].values() for t in p["taps"].values()) < lim


def test_long_hop_repeater_keeps_netlist_consistent(tmp_path):
    """macros over every other repeater site: far slides get a local repeater; every net has one name and driver,
    every tap port is driven, the netlist links."""
    P = S.Plan(json.loads(PLANS[1].read_text()))
    T0, _ = DC.build(P, leaf_um=300.0, keep=[])
    cells = [c for c in T0.cells.values() if c["kind"] in ("rep", "chain")]
    keep = [(c["x"] - 300, c["y"] - 300, c["x"] + 300, c["y"] + 300, "k") for c in cells[::2]]
    T, tree = DC.build(P, leaf_um=300.0, keep=keep)
    assert tree["meta"]["long_hop_repeaters"] > 0
    names = [n["name"] for n in T.nets]
    assert len(names) == len(set(names))
    loads = {ld for n in T.nets for _, _, ld, _ in n["branches"]}
    assert all("port:" + t["port"] in loads for t in tree["taps"])
    assert all(n["name"] == ld[5:] for n in T.nets for _, _, ld, _ in n["branches"] if ld.startswith("port:"))


def test_slide_escapes_wide_macro():
    """a macro wider than the leg and SIDE_MAX_UM: the buffer goes to the nearest legal macro edge, never back
    onto the macro (codex legalisation patch 10-24)."""
    K = DC.KeepIndex([(0.0, 400.0, 10000.0, 3000.0)], die=(10000.0, 5000.0))
    x, y, side = DC._slide((5000.0, 1500.0), (4000.0, 1500.0), (6000.0, 1500.0), K)
    assert not K.hit(x, y)
    assert abs(x - 5000.0) + abs(y - 1500.0) <= 1501.0 + 1e-6


def test_delay_stage_pads_keep_netlist_consistent():
    """a balance pad far beyond the segment cap becomes BUF + SNAKE_UM stages; every cell keeps one input and
    one output net, the port net keeps its name, the electrical length is conserved."""
    T = DC.Tree()
    T.ports = [("input", "root"), ("output", "t_a__clk")]
    T.cell("n0_0", 0.0, 0.0, "node", 0)
    T.cell("c_a", 100.0, 0.0, "chain", 1)
    T.nets = [dict(name="root", drv="port:root", branches=[(10.0, "M8", "n0_0", 10.0)]),
              dict(name="w_n0_0", drv="n0_0", branches=[(100.0, "M8", "c_a", 100.0)]),
              dict(name="t_a__clk", drv="c_a", branches=[(200.0, "M8", "port:t_a__clk", 200.0)])]
    pads = {("w_n0_0", 0): 1500.0, ("t_a__clk", 0): 1000.0}
    E, st = DC.expand_pads(T, pads)
    assert st == int((1600 - 440) // DC.SNAKE_UM) + int((1200 - 440) // DC.SNAKE_UM)
    names = [n["name"] for n in E.nets]
    assert len(names) == len(set(names)) and "t_a__clk" in names
    drv = [n["drv"] for n in E.nets]
    assert len(drv) == len(set(drv))
    loads = [b[2] for n in E.nets for b in n["branches"]]
    assert sorted(set(loads)) == sorted(loads)
    assert set(c for c in E.cells) == set(d for d in drv if not d.startswith("port:"))
    tot = sum(b[0] for n in E.nets for b in n["branches"])
    assert abs(tot - (10 + 100 + 200 + 1500 + 1000)) < 1e-6


def test_ndr_4w_everywhere():
    """--ndr 4w: every die-tree segment gets the 4W RC (R/4, C*1.3), not only hops > WIDE_UM; default unchanged."""
    old = DC.NDR_MODE
    try:
        DC.NDR_MODE = "2w"
        r2, c2 = DC.layer_rc("M8", 400.0)
        assert DC.layer_rc("M8", DC.WIDE_UM + 1) == pytest.approx((DC.LAYER_RC["M8"][0] * 0.25, DC.LAYER_RC["M8"][1] * 1.3))
        DC.NDR_MODE = "4w"
        r4, c4 = DC.layer_rc("M8", 400.0)
        assert r4 == pytest.approx(r2 / 2) and c4 > c2
        P = S.Plan(json.loads(PLANS[1].read_text()))
        T, tree = DC.build(P, leaf_um=1000.0, rep_um=450.0, keep=[], pad="level")
        assert tree["meta"]["ndr"].startswith("4W")
    finally:
        DC.NDR_MODE = old


def test_cmd_build_sets_ndr(tmp_path):
    old = DC.NDR_MODE
    try:
        rc = DC.main(["build", str(PLANS[0]), "--out", str(tmp_path / "b"), "--ndr", "4w"])
        assert rc == 0
        meta = json.loads((tmp_path / "b" / "tree.json").read_text())["meta"]
        assert meta["ndr"].startswith("4W")
    finally:
        DC.NDR_MODE = old


def test_wide_levels_only_top_legs():
    """--wide-levels N: trunk + legs 1..N on 8W (R/8); deeper legs and the default (0) unchanged."""
    old = DC.WIDE_LEVELS
    try:
        P = S.Plan(json.loads(PLANS[1].read_text()))
        T, tree = DC.build(P, leaf_um=300.0, rep_um=450.0, keep=[], pad="level")
        lv = {n["name"]: DC.net_leg_level(T, n) for n in T.nets}
        assert 0 in lv.values() and 1 in lv.values() and max(lv.values()) > 2
        DC.WIDE_LEVELS = 0
        assert DC.layer_rc("M9", 100.0, 0) == DC.layer_rc("M9", 100.0)
        DC.WIDE_LEVELS = 2
        r0, _ = DC.layer_rc("M9", 100.0, 1)
        r9, _ = DC.layer_rc("M9", 100.0, 3)
        assert r0 == pytest.approx(DC.LAYER_RC["M9"][0] / 8) and r9 == pytest.approx(DC.LAYER_RC["M9"][0] * DC.NDR_R)
    finally:
        DC.WIDE_LEVELS = old
