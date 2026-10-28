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


def test_sta_fitted_model_is_data_and_balances():
    Mf = MD.load(ROOT / "data" / "asap7_bufx24_sta_fit.json")
    assert Mf.ks["TT"] > 0 and abs(Mf.k["TT"][0] - 21.2438) < 1e-9
    R = RG.build(QC["sinks"], Mf, tuple(QC["entry"]), [tuple(x) for x in QC["crossings"]], objective="late_split")
    rep, _ = RG.report(R, [tuple(x) for x in QC["crossings"]], 416.5)
    assert rep["skew_TT_ps"] < 1.0 and rep["snakes"] == 0
    assert 2900 < rep["insertion_TT_ps"] < 3200          # OpenSTA on the built tree: 3088-3103 ps (OSS-CLOCK run)


# ------------------------------------------------------------------ OSS-CLOCK-2: legality, fixed trunk, spice calibration
from mscts import legal as LG, trunk as TK  # noqa: E402


def _toy4():
    return [dict(name=f"s{i}", xy=xy) for i, xy in enumerate([(0, 0), (2000, 0), (0, 1500), (2000, 1500)])]


def test_legal_merge_moves_off_keepout_and_rebalances():
    """a keepout over the natural merge point: the merge buffer moves to a legal site on its L path, the pair is
    re-balanced (snake ledger), every merge buffer is legal and the model skew stays ~0."""
    ss = [dict(name="a", xy=(0, 0)), dict(name="b", xy=(2000, 0))]
    L = LG.Legality([[700, -50, 1300, 50]])
    R = RG.build(ss, M, (1000, 800), [], objective="nearest", legal=L)
    assert len(R.moved) == 1 and all(L.ok(nd["xy"]) for nd in R.nodes if nd["kind"] == "merge")
    rep, _ = RG.report(R, [], 416.5)
    assert rep["skew_TT_ps"] < 0.5 and rep["snakes"] == 1


def test_repeaters_slide_out_of_keepouts_and_netlist_follows():
    ss = [dict(name="a", xy=(0, 0)), dict(name="b", xy=(3000, 0))]
    R = RG.build(ss, M, (1500, 0), [], objective="nearest")
    L = LG.Legality([[1900, -20, 2300, 20]])
    R.segs, led = LG.legalize_repeaters(R, L)
    bufs, edges = RG.segments(R)
    assert led["repeaters_moved"] >= 1 and all(L.ok(xy) for xy, k in bufs.values() if k == "rep")
    assert abs(sum(w for _, _, w in edges) - sum(sum(v) for v in R.segs.values())) < 1e-6


def test_trunk_compose_balances_leaves_and_keeps_trunk_shared():
    spec = dict(sinks=_toy4() + [dict(name="s4", xy=(2100, 1600), insertion_ps={"TT": 100.0, "FF": 81.0})],
                crossings=[["s0", "s1"], ["s2", "s3"]],
                trunk=dict(entry=[1000, 750], nodes=[dict(id="t", xy=[1000, 750], parent=None),
                                                     dict(id="lo", xy=[1000, 0], parent="t", rect=[-1, -1, 3000, 700]),
                                                     dict(id="hi", xy=[1000, 1500], parent="t", rect=[-1, 701, 3000, 2000])]))
    G, info = TK.compose(spec, M, objective="late_split")
    rep, rows = RG.report(G, [tuple(x) for x in spec["crossings"]], 416.5)
    assert rep["sinks"] == 5 and rep["skew_TT_ps"] < 5.0           # balanced up to one repeater-count step of the snake
    assert set(info["leaves"]) == {"lo", "hi"} and len(info["snakes"]) == 1 and info["snakes"][0]["leaf"] == "lo"
    # the s4 core tap with 100 ps insertion is delivered ~100 ps early (early tap), its latency matches
    arr, _ = RG.arrivals(G, "TT")
    idx = {nd.get("name"): nd["id"] for nd in G.nodes if nd["kind"] == "sink"}
    assert abs((arr[idx["s4"]] + 100.0) - arr[idx["s2"]]) < 5.0          # early tap; snake solve lands on a repeater-count step (<~3 ps)


def test_spice_scale_model_file():
    S = MD.load(str(ROOT / "data" / "asap7_bufx24_spice_cal.json"))
    F = MD.load(str(ROOT / "data" / "asap7_bufx24_sta_fit.json"))
    for c, s in (("TT", 1.0727), ("FF", 1.0731)):
        assert abs(S.wire_ps(2000, c) / F.wire_ps(2000, c) - s) < 1e-9
