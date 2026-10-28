"""opentools.mscts region-mode tests (pure python, < 2 s)."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))
sys.path.insert(0, str(ROOT.parent / "clkplan"))
from clkplan import model as MD  # noqa: E402
from mscts import netlist as NL, region as RG  # noqa: E402

M = MD.load()
QC = json.loads((ROOT / "examples" / "qc_slice.json").read_text())


def _build(obj, spec=QC):
    return RG.build(spec["sinks"], M, tuple(spec["entry"]), [tuple(x) for x in spec["crossings"]], objective=obj)


def test_zero_skew_merge_balances_model_arrivals():
    R = _build("nearest")
    rep, _ = RG.report(R, [], 416.5)
    assert rep["sinks"] == 192 and rep["skew_TT_ps"] < 10.0 and rep["snakes"] == 0


def test_late_split_cuts_unshared_on_listed_pairs():
    xs = [tuple(x) for x in QC["crossings"]]
    a, _ = RG.report(_build("nearest"), xs, 416.5)
    b, _ = RG.report(_build("late_split"), xs, 416.5)
    assert b["TT"]["max_unshared_ps"] < 0.2 * a["TT"]["max_unshared_ps"]
    assert b["TT"]["worst_margin_ps"] > a["TT"]["worst_margin_ps"]
    assert abs(b["insertion_TT_ps"] - a["insertion_TT_ps"]) < 0.05 * a["insertion_TT_ps"]   # same depth class


def test_snake_when_children_unbalanced():
    sinks = [dict(name="a", xy=(0, 0)), dict(name="b", xy=(100, 0))]
    R = RG.RegionTree(M)
    i = R.add(xy=(0, 0), kind="sink", kids=[], t_ps=0.0, name="a")
    j = R.add(xy=(100, 0), kind="sink", kids=[], t_ps=500.0, name="b")
    R.merge(i, j)
    assert R.snakes and R.snakes[0]["um"] > 1000
    del sinks


def test_netlist_views_agree():
    R = _build("late_split")
    bufs, edges = RG.segments(R)
    names = list(bufs)
    sinks = [f"s_{nd['name']}" for nd in R.nodes if nd["kind"] == "sink"]
    v = NL.verilog(names, edges, f"r{R.root}", sinks)
    sp = NL.spef(names, edges, sinks)
    deck = NL.spice(names, edges, f"r{R.root}", sinks, "TT", "/w/lib", "/w/osdi/x.osdi")
    assert v.count(NL.CFG["cell"] + " x_") == len(names)
    assert deck.count(" " + NL.CFG["cell"]) == len(names) + 2
    wl = sum(w for _, _, w in edges)
    tot = sum(float(m.group(1)) for m in re.finditer(r"^\*D_NET \S+ ([0-9.]+)", sp, re.M))
    assert abs(tot - wl * NL.CFG["c_ff_um"]) < 1e-3 * tot
    # every SPEF internal node is net:<int>
    assert not re.search(r"^\d+ o_\S+:\d+_\d+ ", sp, re.M)
