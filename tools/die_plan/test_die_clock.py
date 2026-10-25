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
