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
    """LEGACY (street=False): a keepout over the natural merge point: the merge buffer moves to a legal site on its L
    path, the pair is re-balanced (snake ledger), every merge buffer is legal and the model skew stays ~0."""
    ss = [dict(name="a", xy=(0, 0)), dict(name="b", xy=(2000, 0))]
    L = LG.Legality([[700, -50, 1300, 50]])
    R = RG.build(ss, M, (1000, 800), [], objective="nearest", legal=L, street=False)
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
    G, info = TK.compose(spec, M, objective="late_split", street=False)
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
    for c, s in (("TT", 1.0485), ("FF", 1.0552)):
        assert abs(S.wire_ps(2000, c) / F.wire_ps(2000, c) - s) < 1e-9


# ------------------------------------------------------------------ OSS-CLOCK-3: street-aware routing (mscts.street)
from mscts import street as SR  # noqa: E402


def test_street_merge_takes_balanced_detour_point_not_snake():
    """same keepout as the legacy test: the merging segment of a same-row pair is one point, inside the keepout ->
    street mode takes the balanced point just outside it (both routes + h), no snake, no moved merge, skew ~0."""
    ss = [dict(name="a", xy=(0, 0)), dict(name="b", xy=(2000, 0))]
    L = LG.Legality([[700, -50, 1300, 50]])
    R = RG.build(ss, M, (1000, 800), [], objective="nearest", legal=L)
    m = next(nd for nd in R.nodes if nd["kind"] == "merge")
    assert L.ok(m["xy"]) and abs(m["xy"][0] - 1000) < 1.0 and abs(abs(m["xy"][1]) - 50.05) < 1e-6
    assert not R.snakes and not R.moved and len(R.detours) == 1 and abs(R.detours[0]["um"] - 100.1) < 0.2
    R.segs, led = LG.legalize_repeaters(R, L)
    rep, _ = RG.report(R, [], 416.5)
    assert rep["skew_TT_ps"] < 0.5 and led["street"] and led["stages_over_rep"] == 0


def test_router_runs_vertical_wire_in_the_street_column():
    """two tall keepouts (1200 um) with a 50-um street column between them on the path: the router runs the vertical
    wire in the street (Z route, Manhattan length) so every repeater stage is legal and <= reach (an x-first or y-first
    L path has a ~1200 um unrepeatable span over a keepout)."""
    L = LG.Legality([[-100, 200, 100, 1400], [150, 200, 600, 1400]])
    Rt = SR.Router(L, 450.0)
    pts, iv, sc = Rt.route((0, 0), (300, 1600))
    assert sc[0] == 0 and max((b - a for a, b in iv), default=0.0) <= 450.0
    assert abs(SR.plen(pts) - 1900) < 1e-6                              # monotone: no extra wire
    assert any(abs(p[0] - q[0]) < 1e-9 and 100 < p[0] < 150 for p, q in zip(pts, pts[1:]))
    st = SR.place(SR.plen(pts), SR.plen(pts), iv, 450.0)
    assert max(st) <= 450.0 + 1e-6 and all(L.ok(SR.at(pts, s)) for s in __import__("itertools").accumulate(st[:-1]))


def test_place_balanced_stages_no_stub():
    """repeater placement: n = ceil(L / reach) equal stages, a site inside a keepout snaps to the nearer edge without
    a stage over reach and without zero / stub stages; a wire exactly at reach stays one stage."""
    assert SR.place(450.0, 450.0 + 1e-9, [], 450.0) == [450.0 + 1e-9]
    st = SR.place(1000.0, 1000.0, [[300.0, 360.0]], 450.0)
    assert len(st) == 3 and max(st) <= 450.0 and min(st) > 250.0
    st = SR.place(1000.0, 1200.0, [[300.0, 360.0]], 450.0)       # 200 um snake at the child end
    assert abs(sum(st) - 1200.0) < 1e-6 and max(st) <= 450.0


def test_street_trunk_compose_exact_stages_tree_balance():
    """trunk + local trees in street mode: exact stage lengths from build time (no post-hoc rebalance needed), all
    buffers legal, branch-point balancing ('tree') uses no more meander than per-leaf balancing."""
    spec = dict(sinks=_toy4() + [dict(name="s4", xy=(2100, 1600), insertion_ps={"TT": 100.0, "FF": 81.0})],
                crossings=[["s0", "s1"], ["s2", "s3"]],
                trunk=dict(entry=[1000, 750], nodes=[dict(id="t", xy=[1000, 750], parent=None),
                                                     dict(id="lo", xy=[1000, 0], parent="t", rect=[-1, -1, 3000, 700]),
                                                     dict(id="hi", xy=[1000, 1500], parent="t", rect=[-1, 701, 3000, 2000])]))
    L = LG.Legality([[450, -60, 870, 60], [1200, 1440, 1620, 1560]])
    out = {}
    for at in ("leaf", "tree"):
        G, info = TK.compose(spec, M, objective="late_split", legal=L, balance_at=at)
        G.segs, led = LG.legalize_repeaters(G, L)
        reb = LG.rebalance(G, "TT")
        rep, _ = RG.report(G, [tuple(x) for x in spec["crossings"]], 416.5)
        bufs, _ = RG.segments(G)
        assert all(L.ok(xy) for xy, k in bufs.values() if k in ("rep", "merge"))
        assert rep["skew_TT_ps"] < 1.0 and reb < 5.0 and led["max_stage_um"] <= 450.0 + 1e-6
        out[at] = rep["snake_um"]
    assert out["tree"] <= out["leaf"] + 1e-6


def test_place_child_inside_keepout_keeps_repeater_out_of_it():
    """a sink pin inside its own keepout with a snake tail (L > D): the repeater is not put on the pin (route end),
    it snaps back to the keepout edge; every stage stays <= reach."""
    st = SR.place(235.0, 450.5, [[47.0, 235.0]], 450.0)
    assert len(st) == 2 and max(st) <= 450.0 + 1e-6 and st[0] <= 47.0
