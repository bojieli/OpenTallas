"""STREET-RULE-1: street-or-abut rule (pure geometry), the compactor / expander on a synthetic type, die estimate."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import street_rule as SR  # noqa: E402

CFG = dict(SR.DEFAULTS)


def core(inst, x, y, w, h, pins=None, partners=None, has_conns=True):
    return dict(inst=inst, x=x, y=y, w=w, h=h, pins=pins or {}, partners=partners or {}, has_conns=has_conns)


def face(n, lo, hi, bus="d"):
    step = (hi - lo) / max(n, 1)
    return [(lo + step * (k + 0.5), bus) for k in range(n)]


def test_need_calibration():
    assert SR.need_um(0, CFG) == 43.2                       # minimum street
    assert SR.need_um(320, CFG) == 43.2                     # LANE-PAIR: 160 + 160 pins at 43.2
    assert SR.need_um(1620, CFG) == 43.2                    # 1,620 facing pins fill 43.2
    assert SR.need_um(3349, CFG) == 90.72                   # lepe_nh_mus_LP 3,349 pins (15 um slot) -> 90.72
    assert abs(SR.need_um(1700, CFG) / SR.G - round(SR.need_um(1700, CFG) / SR.G)) < 1e-9   # on the 4.32 lattice


def test_pair_kinds():
    a = core("a", 0, 0, 100, 100, {"E": face(500, 0, 100)})
    b = core("b", 115, 0, 100, 100, {"W": face(100, 0, 100)})
    r = SR.pair_rule(a, b, CFG)
    assert r["kind"] == "street" and r["axis"] == "x" and r["pins"] == [500, 100] and r["need"] == 43.2
    b["x"] = 100 + 43.2
    assert SR.pair_rule(a, b, CFG)["kind"] == "ok"
    b["x"] = 100.0                                           # abutted, small faces: legal
    assert SR.pair_rule(a, b, CFG)["kind"] == "abut"
    a["pins"]["E"] = face(1600, 0, 100)                     # > 1500-pin face abutting a pin face: WALL
    assert SR.pair_rule(a, b, CFG)["kind"] == "wall"
    b["pins"] = {}                                           # pinless facing face: abutment allowed
    assert SR.pair_rule(a, b, CFG)["kind"] == "abut"
    c = core("c", 300, 300, 10, 10)                          # diagonal / not facing: no rule
    assert SR.pair_rule(a, c, CFG) is None


def test_straight_across_and_sliver():
    a = core("a", 0, 0, 100, 100, {"E": face(400, 0, 100, "x")}, {"x": {"b"}})
    b = core("b", 115, 0, 100, 100, {})
    r = SR.pair_rule(a, b, CFG)
    assert r["pins"] == [0, 0] and r["kind"] == "sliver"     # pins go straight across: no street demand, WARN only
    # types without core_conns: aligned pins on both faces cross the seam (native split, t51)
    a2 = core("a", 0, 0, 100, 100, {"E": face(200, 0, 100)}, has_conns=False)
    b2 = core("b", 117.28, 0, 100, 100, {"W": face(200, 0, 100)}, has_conns=False)
    b3 = core("b", 117.28, 0, 100, 100, {"W": face(100, 0, 100)}, has_conns=False)
    assert SR.pair_rule(a2, b3, CFG)["pins"] == [100, 0]   # one-to-one: 100 of 200 pair up
    assert SR.pair_rule(a2, b2, CFG)["kind"] == "sliver"


def test_outline_rule_windows_and_margin():
    c = core("a", 8.64, 50, 100, 100, {"W": face(300, 0, 100)})
    v = SR.outline_rule(c, 1000, 1000, CFG)
    assert [x["face"] for x in v] == ["W"] and v[0]["kind"] == "street"
    # the same pins inside a type bus window on the W face go straight out
    assert SR.outline_rule(c, 1000, 1000, CFG, {"W": [(40, 160)]}) == []
    c2 = core("b", 8.64, 50, 100, 100)                      # pinless at the 8.64 edge margin: legal
    assert SR.outline_rule(c2, 1000, 1000, CFG) == []


def test_analyze_tap_street():
    # one cluster boxed in on all sides by 8.64 gaps, no outline face: tap_street WARN
    cs = [core("m", 100, 100, 50, 50), core("w", 41.36, 80, 50, 90), core("e", 158.64, 80, 50, 90),
          core("s", 90, 41.36, 70, 50), core("n", 90, 158.64, 70, 50)]
    V, cnt = SR.analyze(400, 400, cs, [[0], [1], [2], [3], [4]], CFG)
    assert any(v["kind"] == "tap_street" and v["a"] == "m" for v in V)


def test_die_growth_push():
    P = {"die": {"outline_um": [1000.0, 500.0]},
         "partition_types": {"A": {"outline_um": [400.0, 500.0]}, "B": {"outline_um": [600.0, 500.0]}},
         "partitions": [{"name": "a", "type": "A", "origin_um": [0, 0]}, {"name": "b", "type": "B", "origin_um": [400, 0]}]}
    d = SR.die_growth(P, {"A": (443.2, 500.0)})
    assert d["dW"] == 43.2 and d["dH"] == 0.0 and abs(d["area_pct"] - 4.32) < 1e-6


def test_eq_struct():
    t0 = {"outline_um": [10, 10], "hard_cores": [{"inst": "a", "origin_um": [1, 1], "outline_um": [2, 2]}],
          "buses": [{"name": "x", "face": "N"}]}
    t1 = json.loads(json.dumps(t0))
    t1["outline_um"] = [14.32, 10]
    t1["hard_cores"][0]["origin_um"] = [5.32, 1]
    assert SR.eq_struct(t0, t1) == []
    t1["hard_cores"][0]["outline_um"] = [3, 2]
    assert SR.eq_struct(t0, t1)                              # a core shape change is never allowed
    t2 = json.loads(json.dumps(t0))
    t2["buses"][0]["face"] = "S"
    assert SR.eq_struct(t0, t2)


def _toy_plan(tmp_path, gap=15.12):
    """two 100x100 cores, 400 pins facing each other across a 15.12-um slot, an ft register in the slot row."""
    pins = tmp_path / "pins"
    pins.mkdir()
    pa = [{"name": "o[%d]" % k, "x": 100.0, "y": 0.25 * k + 0.1} for k in range(400)]
    pb = [{"name": "i[%d]" % k, "x": 0.0, "y": 0.25 * k + 0.1} for k in range(400)]
    (pins / "a.json").write_text(json.dumps({"pins": pa}))
    (pins / "b.json").write_text(json.dumps({"pins": pb}))
    x_b = 60.48 + 100 + gap
    t = {"outline_um": [604.8, 302.4], "module": "toy",
         "hard_cores": [{"inst": "u_a", "module": "A", "origin_um": [60.48, 86.4], "outline_um": [100.0, 100.0],
                         "orient": "R0", "pins_file": "pins/a.json"},
                        {"inst": "u_b", "module": "B", "origin_um": [x_b, 86.4], "outline_um": [100.0, 100.0],
                         "orient": "R0", "pins_file": "pins/b.json"}],
         "ft_slots": [{"name": "ft0", "in_face": "W", "out_face": "E", "width": 4, "in_window_um": [130, 140],
                       "out_window_um": [130, 140], "regs_um": [[400.0, 135.0]]}],
         "clock": {"tap_um": [480.0, 250.0]}}
    P = {"die": {"name": "toy", "outline_um": [604.8, 302.4]}, "partition_types": {"toy": t},
         "partitions": [{"name": "p0", "type": "toy", "origin_um": [0, 0]}]}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(P))
    # core_conns: the two faces talk to the type faces, not to each other (so their pins run along the slot)
    (tmp_path / "core_conns.json").write_text(json.dumps({"toy": {"u_a": {"o": ["face:E"]}, "u_b": {"i": ["face:W"]}}}))
    return plan, P


def test_legalize_opens_street(tmp_path):
    plan, P = _toy_plan(tmp_path)
    out = tmp_path / "new.json"
    ev = tmp_path / "ev.json"
    rc = SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
                  "--event", str(ev), "--rs-halving", "off"])
    assert rc == 0
    E = json.loads(ev.read_text())
    row = E["rows"][0]
    assert row["violations_before"].get("street") == 1
    assert row["applied"], row["reason"]
    Q = json.loads(out.read_text())
    t = Q["partition_types"]["toy"]
    a, b = t["hard_cores"]
    gap = b["origin_um"][0] - (a["origin_um"][0] + 100.0)
    assert gap >= SR.need_um(800, SR.DEFAULTS) - 1e-6       # 400 + 400 facing pins -> street
    assert a["outline_um"] == [100.0, 100.0] and b["outline_um"] == [100.0, 100.0]   # never a core shape change
    # displacements on the 4.32 lattice; relative order kept
    for h0, h1 in zip(P["partition_types"]["toy"]["hard_cores"], t["hard_cores"]):
        d = h1["origin_um"][0] - h0["origin_um"][0]
        assert abs(d / SR.G - round(d / SR.G)) < 1e-6
    assert a["origin_um"][0] < b["origin_um"][0]
    assert t["outline_um"] == P["partition_types"]["toy"]["outline_um"]   # free area absorbed it: no growth
    # the ft register in the slot row is never under a core
    assert SR.points_under_cores(t) == []
    # the rule check on the new plan is clean
    ck = tmp_path / "ck.json"
    SR.main(["check", str(out), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck)])
    assert json.loads(ck.read_text())["types_with_violations"] == 0


def test_legalize_grows_outline_when_full(tmp_path):
    plan, P = _toy_plan(tmp_path)
    t = P["partition_types"]["toy"]
    t["outline_um"] = [8.64 + 100 + 15.12 + 100 + 8.64, 302.4]   # no free width: the street needs growth
    t["hard_cores"][0]["origin_um"] = [8.64, 86.4]
    t["hard_cores"][1]["origin_um"] = [8.64 + 100 + 15.12, 86.4]
    t["ft_slots"] = []
    t["clock"] = {}
    P["die"]["outline_um"] = list(t["outline_um"])
    plan.write_text(json.dumps(P))
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
             "--event", str(ev), "--rs-halving", "off"])
    row = json.loads(ev.read_text())["rows"][0]
    assert row["applied"], row["reason"]
    W0, W1 = row["outline_before"][0], row["outline_after"][0]
    assert W1 > W0 and abs((W1 - W0) / 8.64 - round((W1 - W0) / 8.64)) < 1e-6
    assert json.loads(ev.read_text())["die_estimate"]["dW"] == round(W1 - W0, 2)


def test_g0_hook(tmp_path):
    import check as CK
    plan, P = _toy_plan(tmp_path)
    R = CK.Report()
    summ = SR.g0_check(P, R, tmp_path, "error", repo=tmp_path)
    assert summ["types_with_errors"] == 1 and summ["counts"]["street"] == 1
    errs = [i for i in R.items if i["level"] == "ERROR" and i["check"] == "street_gap"]
    assert len(errs) == 1 and "u_a|u_b" in errs[0]["msg"]
    R2 = CK.Report()
    SR.g0_check(P, R2, tmp_path, "warn", repo=tmp_path)
    assert not R2.errors() and any(i["check"] == "street_gap" for i in R2.items)


def test_hub_repack_escape_boxed_in_terminates():
    # a station end inside a core that is flush with the outline and boxed in by a neighbour: escape() used to
    # recurse forever (q_b102__physical_v1); it now returns a lattice point
    import hub_repack as HR
    R = HR.Raster(200.0, 100.0, [(0.0, 0.0, 100.0, 100.0), (104.0, 0.0, 200.0, 100.0)])
    q = HR.escape(R, (50.0, 50.0))
    assert len(q) == 2


def test_locked_axis_never_grows(tmp_path):
    # die at the reticle: grow_axes=y keeps W; the street that needs W stays residual, nothing crosses the outline
    plan, P = _toy_plan(tmp_path)
    t = P["partition_types"]["toy"]
    t["outline_um"] = [8.64 + 100 + 15.12 + 100 + 8.64, 302.4]
    t["hard_cores"][0]["origin_um"] = [8.64, 86.4]
    t["hard_cores"][1]["origin_um"] = [8.64 + 100 + 15.12, 86.4]
    t["ft_slots"] = []
    t["clock"] = {}
    plan.write_text(json.dumps(P))
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
             "--event", str(ev), "--rs-halving", "off", "--set", "grow_axes=y"])
    row = json.loads(ev.read_text())["rows"][0]
    assert abs(row["outline_after"][0] - row["outline_before"][0]) < 1e-6
    Q = json.loads(out.read_text())["partition_types"]["toy"]
    for h in Q["hard_cores"]:
        assert h["origin_um"][0] + 100.0 <= Q["outline_um"][0] + 1e-6


def test_reticle_fit_reverts_growth():
    P = {"die": {"outline_um": [32990.0, 1000.0]},
         "partition_types": {"A": {"outline_um": [400.0, 1000.0]}, "B": {"outline_um": [600.0, 1000.0]}},
         "partitions": [{"name": "a", "type": "A", "origin_um": [0, 0]}, {"name": "b", "type": "B", "origin_um": [400, 0]}]}
    import copy
    Q = copy.deepcopy(P)
    Q["partition_types"]["A"]["outline_um"] = [443.2, 1000.0]
    rows = [{"type": "A", "applied": True, "outline_before": [400.0, 1000.0], "outline_after": [443.2, 1000.0],
             "violations_before": {"street": 1}, "violations_after": {}}]
    d, rev = SR.reticle_fit(P, Q, rows, log=lambda s: None)
    assert rev == ["A"] and not rows[0]["applied"] and Q["partition_types"]["A"]["outline_um"] == [400.0, 1000.0]


class _FakeM:
    def __init__(self, W, H, rects):
        import numpy as np
        self.W, self.H, self.n = W, H, len(rects)
        self._o = [(x, y) for x, y, _, _ in rects]
        self.dim = np.array([[w, h] for _, _, w, h in rects], float)

    def core_origin(self, i):
        return self._o[i]


def test_add_ft_regs_inserts_stage_on_overlong_hop():
    import copy
    f = {"name": "ft0", "in_face": "W", "out_face": "E", "in_window_um": [130, 140], "out_window_um": [130, 140],
         "stations": 1, "regs_um": [[300.0, 135.0]],
         "bit_sites_um": [[[300.0, 134.73], [300.0, 135.27]]]}
    t0 = {"outline_um": [604.8, 302.4], "ft_slots": [f]}
    t1 = copy.deepcopy(t0)
    t1["outline_um"] = [829.44, 302.4]
    t1["ft_slots"][0]["regs_um"] = [[440.64, 135.0]]          # the street push stretched hop 0 to ~440 um
    t1["ft_slots"][0]["bit_sites_um"] = [[[440.64, 134.73], [440.64, 135.27]]]
    M = _FakeM(829.44, 302.4, [(100.0, 200.0, 50.0, 50.0)])
    assert SR.ft_hop_check(t0, t1, 405.0)
    add = SR.add_ft_regs(M, t0, t1, 405.0, 1)
    assert add and add[0]["added"] == 1
    f1 = t1["ft_slots"][0]
    assert len(f1["regs_um"]) == 2 and f1["stations"] == 2 and len(f1["bit_sites_um"]) == 2
    assert not SR.ft_hop_check_added(t0, t1, 405.0)
    # the new stage's bit sites are the neighbour's pattern, translated
    (x, y), sites = f1["regs_um"][0][:2], f1["bit_sites_um"][0]
    assert sites == [[round(x, 4), round(y - 0.27, 4)], [round(x, 4), round(y + 0.27, 4)]]


def test_pass2_levers_reorder_and_xfeed():
    cfg = dict(SR.DEFAULTS, pin_reorder=1)
    a = core("a", 0, 0, 100, 100, {"E": face(20, 0, 100)}, has_conns=False)
    b = core("b", 117.28, 0, 100, 100, {"W": face(20, 2.5, 102.5)}, has_conns=False)
    assert SR.pair_rule(a, b, CFG)["kind"] == "street"          # misaligned pins: a street
    r = SR.pair_rule(a, b, cfg)
    assert r["pins"] == [0, 0] and r["pin_reorder"] == 20 and r["kind"] == "sliver"   # (b) reordered straight across
    cfg2 = dict(SR.DEFAULTS, x_pin_factor=0.5)
    a2 = core("a", 0, 0, 100, 100, {"E": face(1800, 0, 100)})
    b2 = core("b", 140, 0, 100, 100, {"W": face(1800, 0, 100)})
    assert SR.pair_rule(a2, b2, CFG)["need"] > SR.pair_rule(a2, b2, cfg2)["need"]   # (d) 2:1 x feed halves the need
    assert SR.pair_rule(a2, b2, cfg2)["pins"] == [900, 900]


def test_legalize_moves_sinks_with_cores(tmp_path):
    """COORD 11-12 (HEAD-94 hd_lep0N): every off-core coordinate follows the moved cores -- sink sites, sink bins,
    keepouts -- the sink total is unchanged and no sink ends inside a core."""
    plan, P = _toy_plan(tmp_path)
    t0 = P["partition_types"]["toy"]
    x_b = t0["hard_cores"][1]["origin_um"][0]
    # sites: in the old slot, just E of core b (b moves E onto it), on core a (rides with a)
    t0["clock"]["sink_sites_um"] = [[60.48 + 100 + 7.0, 136.0, 2], [x_b + 104.0, 136.0, 3], [100.0, 120.0, 5]]
    t0["clock"]["keepouts_um"] = [[x_b + 102.0, 90.0, x_b + 110.0, 180.0]]
    # islands: inside core b, straddling b's W edge (centre on b), free in the slot row above the cores
    isl = [[x_b + 10.0, 100.0, x_b + 30.0, 120.0], [x_b - 4.0, 140.0, x_b + 12.0, 150.0], [300.0, 250.0, 340.0, 270.0]]
    t0["clock"]["die_islands_um"] = [list(r) for r in isl]
    bins = [[x_b + 105.3, 135.0, 7], [x_b + 106.0, 140.0, 1], [100.0, 120.0, 11], [20.0, 20.0, 4], [500.0, 280.0, 6]]
    bf = Path("physical/die_plan/toy/bins/toy.json")
    (tmp_path / bf).parent.mkdir(parents=True)
    (tmp_path / bf).write_text(json.dumps({"bin_um": 10.8, "bins": bins}))
    t0["clock"]["sink_bins_file"] = str(bf)
    plan.write_text(json.dumps(P))
    _, tot0 = SR.sink_points(t0, tmp_path)
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    assert SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
                    "--event", str(ev), "--rs-halving", "off"]) == 0
    row = json.loads(ev.read_text())["rows"][0]
    assert row["applied"], row["reason"]
    t = json.loads(out.read_text())["partition_types"]["toy"]
    b1 = t["hard_cores"][1]["origin_um"][0]
    assert b1 > x_b + 1.0                                         # core b moved E (the street opened)
    pts, tot1 = SR.sink_points(t, tmp_path)
    assert tot1 == tot0                                           # sink total preserved (sites + merged bins)
    # nothing new inside a core: only the sinks that sat on core a in the base (and ride with it) are on a core
    assert sorted(SR.sinks_under_cores(t, tmp_path)) == sorted(SR.sinks_under_cores(t0, tmp_path)) == [[100.0, 120.0]] * 2
    assert t["clock"]["sink_bins_file"] != str(bf)                # a new bins file, the base one untouched
    assert json.loads((tmp_path / bf).read_text())["bins"] == bins
    s = t["clock"]["sink_sites_um"]
    assert s[1][0] >= b1 + 100.0 and s[1][2] == 3                 # E of b stays E of b, weight kept
    assert s[2] == [100.0, 120.0, 5]                              # on core a (not moved): unchanged
    k = t["clock"]["keepouts_um"][0]
    assert k[0] >= b1 + 100.0 - 1e-6                              # the keepout E of b followed it
    # COORD 11-12 (HEAD-94 hd_lep0N): rects move as whole boxes; islands on a moved core move with it
    dx = b1 - x_b
    i1 = t["clock"]["die_islands_um"]
    assert [round(v, 3) for v in i1[0]] == [round(v, 3) for v in (isl[0][0] + dx, 100.0, isl[0][2] + dx, 120.0)]
    assert [round(v, 3) for v in i1[1]] == [round(v, 3) for v in (isl[1][0] + dx, 140.0, isl[1][2] + dx, 150.0)]
    assert abs((i1[2][2] - i1[2][0]) - 40.0) < 1e-6 and abs((i1[2][3] - i1[2][1]) - 20.0) < 1e-6

    def rects(o, key=None):
        if isinstance(o, dict):
            for k_, v in o.items():
                yield from rects(v, k_)
        elif isinstance(o, list):
            if len(o) == 4 and all(isinstance(v, (int, float)) for v in o) and key and (
                    "rect" in key or key in ("keepouts_um", "die_islands_um")):
                yield o
            else:
                for v in o:
                    yield from rects(v, key)
    for r in rects(t):
        assert r[0] <= r[2] and r[1] <= r[3], r                   # every rect stays valid


def test_reset_resel_follows_resolved_tree(monkeypatch, tmp_path):
    """COORD 11-12 (HEAD-94 hd_lep0N): raw reset exports / landing pin sources / stage raw refs are re-selected on the
    re-solved reset tree of a legalized type (mesh_resel rule)."""
    import types as _t
    trees = {
        "base": dict(relays=[dict(name="r_a", q="qa", depth=2, role="raw", xy=[100.0, 50.0]),
                             dict(name="r_b", q="qb", depth=3, role="raw", xy=[200.0, 50.0]),
                             dict(name="s1", q="s1", d="qa", depth=3, xy=[100.0, 90.0])]),
        "new": dict(relays=[dict(name="r_a2", q="qa2", depth=2, role="raw", xy=[130.0, 50.0]),
                            dict(name="r_x", q="qx", depth=2, role="raw", xy=[400.0, 50.0]),
                            dict(name="r_b", q="qb", depth=3, role="raw", xy=[205.0, 50.0]),
                            dict(name="s1n", q="s1n", d="qa2", depth=3, xy=[130.0, 92.0]),
                            dict(name="s1x", q="s1x", d="qx", depth=3, xy=[100.0, 90.0])]),
    }
    import schema
    import reset_tree
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: _t.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])
    t = {"reset_start_raw_exports": [dict(port="rst_o", instance="r_a", net="qa", xy_um=[100.0, 50.0])],
         "clock": {"landing_contract": {"pins": [dict(name="rst_o", xy_um=[101.0, 49.0], source_instance="r_a")],
                                        "collector_tree": json.loads(json.dumps(trees["base"]))},
                   "landing_raw_branches": [dict(name="o", base="qa", stages=[dict(original="s1", xy_um=[100.0, 90.0])],
                                                 consumers=["origin"])],
                   "landing_local_resets": [dict(raw="qa", xy_um=[100.0, 50.0]), dict(raw="qb", xy_um=[200.0, 50.0])]}}
    P = {"tag": "base", "partition_types": {"x": json.loads(json.dumps(t))}}
    Q = {"tag": "new", "partition_types": {"x": t}}
    rec = SR.reset_resel(P, Q, ["x"], tmp_path / "plan.json")["x"]
    assert "error" not in rec, rec
    e = t["reset_start_raw_exports"][0]
    assert (e["instance"], e["net"], e["xy_um"]) == ("r_a2", "qa2", [130.0, 50.0])     # same role+depth, nearest
    pn = t["clock"]["landing_contract"]["pins"][0]
    assert pn["source_instance"] == "r_a2" and pn["xy_um"] == [131.0, 49.0]           # pin offset kept
    lr = t["clock"]["landing_local_resets"]
    assert lr[0]["raw"] == "qa2" and lr[1]["raw"] == "qb"     # gone -> nearest same depth; surviving Q kept
    # the published collector_tree is the re-solved one; raw branches follow it as a D-chain (not nearest-by-xy:
    # s1x sits exactly at the old stage xy but hangs off another base)
    assert t["clock"]["landing_contract"]["collector_tree"] == trees["new"] and rec["tree_republished"] == [3, 5]
    br = t["clock"]["landing_raw_branches"][0]
    assert br["base"] == "qa2" and br["stages"][0]["original"] == "s1n"


def test_reset_resel_keeps_role_hd_st_n3_transit_u2_i(monkeypatch, tmp_path):
    """COORD 11-12 (HEAD-94 hd_st_n3_transit.u2_i): a reader-START stage raw_reset names a REGISTERED raw relay; the
    nearest same-depth relay of the re-solved tree is the gated consumer tap rst_n_t1 (reset AND run), which fails
    gen-phys's reader-START check.  The re-select keeps the role: the nearest same-depth RAW relay (a plain rst_rl_*
    or the raw copy rr_t<i> of a gated tap), never a gated one."""
    import types as _t
    import re as _re
    R = lambda q, d, xy, dd: dict(name="u_" + q, q=q, d=dd, depth=d, kind="tap" if q.startswith("rst_n_t") else "relay",
                                  xy=xy, tap=None)  # noqa: E731
    trees = {
        "base": dict(start=True, relays=[R("rst_rl_25", 3, [300.0, 400.0], "rst_rl_20"),
                                         R("rst_n_t10", 3, [600.0, 400.0], "rst_rl_20"),
                                         R("rst_n_t1", 3, [900.0, 900.0], "rst_rl_20")]),
        # cores moved: rst_rl_25 gone, the gated tap rst_n_t1 now sits closest to the u2_i stage, rst_rl_26 farther
        "new": dict(start=True, relays=[R("rst_n_t1", 3, [305.0, 402.0], "rst_rl_20"),
                                        R("rst_rl_26", 3, [360.0, 470.0], "rst_rl_20"),
                                        R("rst_n_t11", 3, [640.0, 420.0], "rst_rl_20")]),
    }
    import schema
    import reset_tree

    def start_relays(T):     # mission type: consumer taps gated, plain relays raw (reset_tree.start_relays roles)
        return [dict(r, role="gated" if _re.match(r"rst_n_t\d+$", r["q"]) else "raw") for r in T["relays"]]
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: _t.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])
    monkeypatch.setattr(reset_tree, "start_relays", start_relays)
    st = [dict(xy_um=[300.0, 400.0], raw_reset="rst_rl_25"), dict(xy_um=[600.0, 400.0], raw_reset="rr_t10"),
          dict(xy_um=[900.0, 900.0], raw_reset="rst_n_t1")]
    t = {"clock": {"landing_reader_start": {"branches": {"u2_i": {"stages": st}}}}}
    P = {"tag": "base", "partition_types": {"hd_st_n3_transit": json.loads(json.dumps(t))}}
    Q = {"tag": "new", "partition_types": {"hd_st_n3_transit": t}}
    rec = SR.reset_resel(P, Q, ["hd_st_n3_transit"], tmp_path / "plan.json")["hd_st_n3_transit"]
    assert "error" not in rec, rec
    got = [x["raw_reset"] for x in st]
    assert got[0] == "rst_rl_26"          # not the closer gated rst_n_t1
    assert got[1] == "rr_t11"             # a raw copy stays a raw copy (of the nearest gated tap), never rst_n_t11
    assert got[2] == "rst_n_t11"          # a gated reference stays gated (nearest gated tap to its stage)
    roles = SR._q_roles(trees["new"])
    assert all(roles[q]["role"] == SR._q_roles(trees["base"])[o]["role"]
               for q, o in zip(got, ["rst_rl_25", "rr_t10", "rst_n_t1"]))


def test_add_ft_regs_keeps_site_rows_aligned():
    """the usual ft form: station 0 at the in pin has no bit-site row (bit_sites_um = stations 1..k-1). An added stage
    gets its own row, so taps.planned_sinks' bit_sites_um[j - 1][bit] for j < stations stays in range (COORD 11-12)."""
    import copy
    f = {"name": "ft0", "in_face": "W", "out_face": "E", "in_window_um": [130, 140], "out_window_um": [130, 140],
         "width": 2, "stations": 2, "regs_um": [[2.0, 135.0], [300.0, 135.0]],
         "bit_sites_um": [[[300.0, 134.73], [300.0, 135.27]]]}
    t0 = {"outline_um": [604.8, 302.4], "ft_slots": [f]}
    t1 = copy.deepcopy(t0)
    t1["outline_um"] = [829.44, 302.4]
    t1["ft_slots"][0]["regs_um"][1] = [440.64, 135.0]
    t1["ft_slots"][0]["bit_sites_um"] = [[[440.64, 134.73], [440.64, 135.27]]]
    M = _FakeM(829.44, 302.4, [(100.0, 200.0, 50.0, 50.0)])
    add = SR.add_ft_regs(M, t0, t1, 405.0, 1)
    assert add and add[0]["added"] == 1
    f1 = t1["ft_slots"][0]
    assert f1["stations"] == 3 and len(f1["regs_um"]) == 3 and len(f1["bit_sites_um"]) == 2
    for j in range(1, f1["stations"]):
        for bit in range(2):
            f1["bit_sites_um"][j - 1][bit]                                  # taps.planned_sinks indexing
    (x, y), sites = f1["regs_um"][1][:2], f1["bit_sites_um"][0]
    assert sites == [[round(x, 4), round(y - 0.27, 4)], [round(x, 4), round(y + 0.27, 4)]]


def test_sliver_rule_makes_slivers_streets(tmp_path):
    """COORD 11-12: with sliver_rule=1 a sub-street gap between facing cores is an error whatever its pin count, and
    legalize opens it to a full street (or keeps an abutment); the default keeps the WARN class."""
    a = core("a", 0, 0, 100, 100, {})
    b = core("b", 108.64, 0, 100, 100, {})                   # 8.64-um slot, no pins: the S81 leaf sliver
    assert SR.pair_rule(a, b, CFG)["kind"] == "sliver"
    on = dict(CFG, sliver_rule=1)
    r = SR.pair_rule(a, b, on)
    assert r["kind"] == "street" and r["need"] == 43.2 and r.get("sliver")
    b["x"] = 100.0                                           # abutted: legal under the rule
    assert SR.pair_rule(a, b, on)["kind"] == "abut"
    b["x"] = 143.2                                           # a full street: legal
    assert SR.pair_rule(a, b, on)["kind"] == "ok"
    b["x"] = 108.64
    V, c = SR.analyze(400.0, 200.0, [a, b], [[0], [1]], on)
    assert c.get("street", 0) == 1 and "sliver" not in c
    V, c = SR.analyze(400.0, 200.0, [a, b], [[0], [1]], CFG)
    assert c.get("sliver", 0) == 1 and "street" not in c


def test_legalize_face_anchor_west_growth_fixed_east(tmp_path):
    """FIXED-FACE (GEN-CLASS-1, HEAD-95): the type grows WEST; its E face abuts a FIXED partition and keeps die-x of
    its N / S windows, ... here: the N face abuts a FIXED partition, the S face a moved one.  The instance origin moves
    by -dW, the N window keeps its die x (local +dW), the S window keeps its local x; legacy (no anchor) unchanged."""
    plan, P = _toy_plan(tmp_path)
    t = P["partition_types"]["toy"]
    t["outline_um"] = [8.64 + 100 + 15.12 + 100 + 8.64, 302.4]
    t["hard_cores"][0]["origin_um"] = [8.64, 86.4]
    t["hard_cores"][1]["origin_um"] = [8.64 + 100 + 15.12, 86.4]
    t["ft_slots"] = []
    t["clock"] = {"landing_contract": {"pins": [{"name": "fclk_in_n", "xy_um": [50.0, 300.0]},
                                                {"name": "fclk_in_s", "xy_um": [50.0, 2.0]}],
                                       "bands": {"n_i": {"rect_um": [40.0, 280.0, 60.0, 300.0]}}}}
    t["buses"] = [{"name": "n_i", "face": "N", "window_um": [40.0, 60.0], "width": 8},
                  {"name": "s_i", "face": "S", "window_um": [40.0, 60.0], "width": 8}]
    P["die"]["outline_um"] = [2000.0, 302.4]
    P["partitions"][0]["origin_um"] = [1000.0, 0.0]
    plan.write_text(json.dumps(P))
    fa = tmp_path / "fa.json"
    fa.write_text(json.dumps({"toy": {"grow": {"x": "W"}, "fixed_faces": ["N"]}}))
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
             "--event", str(ev), "--rs-halving", "off", "--face-anchor", str(fa)])
    row = json.loads(ev.read_text())["rows"][0]
    assert row["applied"], row["reason"]
    dW = row["outline_after"][0] - row["outline_before"][0]
    assert dW > 0
    assert row["face_anchor"]["origin_shift_um"] == [round(-dW, 4), 0.0]
    Q = json.loads(out.read_text())
    q = Q["partition_types"]["toy"]
    ox = Q["partitions"][0]["origin_um"][0]
    assert abs(ox - (1000.0 - dW)) < 1e-6
    bn = {b["name"]: b for b in q["buses"]}
    # N (fixed neighbour): die x kept
    assert abs(ox + bn["n_i"]["window_um"][0] - 1040.0) < 1e-6 and abs(ox + bn["n_i"]["window_um"][1] - 1060.0) < 1e-6
    # S (moved neighbour): local x kept
    assert bn["s_i"]["window_um"] == [40.0, 60.0]
    lc = q["clock"]["landing_contract"]
    assert abs(ox + lc["pins"][0]["xy_um"][0] - 1050.0) < 1e-6
    assert abs(ox + lc["bands"]["n_i"]["rect_um"][0] - 1040.0) < 1e-6
    # E edge keeps its die position
    assert abs(ox + q["outline_um"][0] - (1000.0 + row["outline_before"][0])) < 1e-6


def test_face_anchor_cfg_rejects_bad():
    import pytest
    assert SR.face_anchor_cfg(None, "x") is None
    assert SR.face_anchor_cfg({}, "x") == dict(grow=dict(x="E", y="N"), origin_shift_um=[0.0, 0.0], fixed_faces=[])
    for bad in ({"grow": {"x": "N"}}, {"fixed_faces": ["Q"]}, {"origin_shift_um": [1]}, {"other": 1}):
        with pytest.raises(ValueError):
            SR.face_anchor_cfg(bad, "x")


# ---------------------------------------------------------------------------------------------- R-STREET (11-13)
def box(inst, x, y, w, h, movable=True, face_pins=None):
    return dict(inst=inst, x=x, y=y, w=w, h=h, movable=movable, face_pins=face_pins or {})


def test_face_windows_and_span_pins():
    t = {"buses": [{"name": "a", "face": "S", "window_um": [0, 100], "width": 500, "kind": "data"}],
         "ft_slots": [{"name": "ft0", "in_face": "N", "out_face": "S", "width": 200,
                       "in_window_um": [10, 50], "out_window_um": [200, 300]}]}
    w = SR.type_face_windows(t)
    assert w["S"] == [(0.0, 100.0, 500, "a"), (200.0, 300.0, 200, "ft0_o")] and w["N"] == [(10.0, 50.0, 200, "ft0_i")]
    assert SR.span_pins(w["S"], 0, 50) == 250 and SR.span_pins(w["S"], 50, 250) == 350 and SR.span_pins(w["S"], 100, 200) == 0


def test_face_street_need_by_pins_and_ends():
    W, H = 1440.0, 1200.0
    wins = {"S": [(0.0, 1250.0, 6750, "s")]}                  # 5.4 pins / um (leaf t28 S face)
    # one macro 300 um wide, both ends open: 1,620 pins / (37.5 x 2) = 21.6 -> the 43.2 minimum
    v = SR.face_shadow_rule(W, H, [box("m", 400, 34.56, 300, 300)], wins, CFG)
    assert len(v) == 1 and v[0]["kind"] == "face_street" and v[0]["need"] == 43.2 and v[0]["ends"] == 2
    assert v[0]["pins"][0] == 1620 and v[0]["face"] == "S" and v[0]["free_spans"][0] == (0.0, 400.0)
    assert SR.face_shadow_rule(W, H, [box("m", 400, 43.2, 300, 300)], wins, CFG) == []
    # a 1,030-um wall of four macros (8.64 seams), W end closed by the corner: 5,562 pins one-ended -> the 129.6 cap
    row = [box("a", 30, 34.56, 250, 100), box("b", 288.64, 34.56, 250, 100), box("c", 547.28, 34.56, 250, 100),
           box("d", 805.92, 34.56, 254.08, 100)]
    v = SR.face_shadow_rule(W, H, row, wins, CFG)
    assert len(v) == 4 and {x["ends"] for x in v} == {1} and {x["need"] for x in v} == {129.6}
    # the same wall with a 43.2 street in the middle and off the corner: two walls, two-ended each
    row2 = [box("a", 43.2, 34.56, 250, 100), box("b", 301.84, 34.56, 250, 100), box("c", 595.04, 34.56, 250, 100),
            box("d", 853.68, 34.56, 250, 100)]
    v = SR.face_shadow_rule(W, H, row2, wins, CFG)
    assert {x["ends"] for x in v} == {2} and {x["need"] for x in v} == {43.2} and {x["pins"][0] for x in v} == {2747}
    # a sparse wall (< 3 pins / um): only the 17.28 tap-legal floor, so the 34.56 edge margin is legal
    sp = {"S": [(0.0, 1250.0, 2500, "s")]}                    # 2 pins / um
    assert SR.face_shadow_rule(W, H, [box("m", 400, 34.56, 300, 300)], sp, CFG) == []
    v = SR.face_shadow_rule(W, H, [box("m", 400, 8.64, 300, 300)], sp, CFG)
    assert len(v) == 1 and v[0]["need"] == 17.28 and not v[0]["dense"]
    # a notch: a 30-um macro under the dense face is no wall (pins jog <= 21.6 um to open area)
    assert SR.face_shadow_rule(W, H, [box("m", 400, 8.64, 30, 300)], wins, CFG) == []
    # deeper than face_depth_um: not a wall of this face; a face without pins: no rule
    assert SR.face_shadow_rule(W, H, [box("m", 400, 129.6, 300, 300)], wins, CFG) == []
    assert SR.face_shadow_rule(W, H, [box("m", 400, 8.64, 300, 300)], {"S": [(0.0, 100.0, 10, "s")]}, CFG) == []
    # E face: gap measured from the E outline
    v = SR.face_shadow_rule(W, H, [box("m", W - 30 - 200, 100, 200, 400)], {"E": [(0.0, 600.0, 2600, "e")]}, CFG)
    assert len(v) == 1 and v[0]["face"] == "E" and v[0]["gap"] == 30.0 and v[0]["pins"][0] == 1733


def test_face_street_abutted():
    W, H = 1000.0, 1000.0
    wins = {"S": [(0.0, 1000.0, 4000, "s")]}
    # abutted, the 800 pins of its span go straight into its own 800 S pins: legal
    assert SR.face_shadow_rule(W, H, [box("m", 400, 0, 200, 300, face_pins={"S": 800})], wins, CFG) == []
    # abutted over foreign pins: the pins move out of the span (free spans given) or the macro lifts to a street
    v = SR.face_shadow_rule(W, H, [box("m", 400, 0, 200, 300)], wins, CFG)
    assert len(v) == 1 and v[0]["abutted"] and v[0]["need"] == 43.2 and v[0]["free_spans"] == [(0.0, 400.0), (600.0, 1000.0)]
    # an abutted macro closes the end of the wall next to it (20 um opening): one-ended, 800 pins -> 43.2 > 34.56
    v = SR.face_shadow_rule(W, H, [box("m", 400, 0, 200, 300, face_pins={"S": 800}), box("n", 620, 34.56, 200, 100)],
                            wins, CFG)
    assert [x["a"] for x in v] == ["n"] and v[0]["ends"] == 1


def test_face_needs_and_fixed_content():
    cfg = dict(CFG, _fwins={"S": [(0.0, 1000.0, 4000, "s")]}, _xboxes=[box("sram", 700, 20, 100, 50, movable=False)])
    cs = [core("m", 100, 34.56, 300, 300)]
    V, cnt = SR.analyze(1000, 1000, cs, [[0]], cfg)
    assert cnt.get("face_street") == 2                       # the hard core and the fixed LEF content macro
    assert SR.face_needs(1000, 1000, cs, cfg) == {("m", "S"): 43.2}          # only the movable core is lifted
    assert "face_street" not in SR.analyze(1000, 1000, cs, [[0]], dict(cfg, face_rule=0))[1]
    assert set(SR.HARD) >= {"face_street", "station_alley"}


def test_station_alley():
    t = {"outline_um": [1000.0, 1000.0],
         "hard_cores": [{"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [200.0, 200.0]},
                        {"inst": "b", "origin_um": [320.0, 100.0], "outline_um": [200.0, 200.0]},
                        {"inst": "c", "origin_um": [600.0, 25.0], "outline_um": [200.0, 200.0]}],
         "internal_stations": [{"regs_um": [[310.0, 150.0]], "bits": 640},     # in the 20-um a|b slot (200 long)
                               {"regs_um": [[310.0, 250.0]], "bits": 4},       # same slot: 652 bits = 3.3 / um, dense
                               {"regs_um": [[700.0, 12.0]], "bits": 32},       # under c, 25 um off S: sparse, legal
                               {"regs_um": [[560.0, 150.0]], "bits": 100},     # 80-um b|c street: legal
                               {"regs_um": [[150.0, 150.0]], "bits": 500},     # on core a: rides with it
                               {"regs_um": [[900.0, 900.0]], "bits": 500}],    # open area
         "ft_slots": [{"name": "f", "width": 8, "regs_um": [[310.0, 120.0]]}]}
    V = SR.station_alleys(t, CFG)
    got = {(v["a"], v["b"]): (v["pins"][0], v["gap"]) for v in V}
    assert got == {("a", "b"): (652, 20.0)} and V[0]["need"] == 43.2 and V[0]["dense"]
    # a sparse slot (>= 16 bits, < 3 bits / um) only needs the 17.28 tap-legal width: c moved to 12 um off S fails
    t["hard_cores"][2]["origin_um"] = [600.0, 16.0]
    V = SR.station_alleys(t, CFG)
    got = {(v["a"], v["b"]): (v["pins"][0], v["gap"], v["need"]) for v in V}
    assert got == {("a", "b"): (652, 20.0, 43.2), ("outline:S", "c"): (32, 16.0, 17.28)}
    pairs, faces = SR.alley_force(V)
    assert pairs == {frozenset(("a", "b")): 43.2} and faces == {("c", "S"): 43.2}
    # legalize: the forced pair is a street although no core pin faces the slot
    a = core("a", 100, 100, 200, 200)
    b = core("b", 320, 100, 200, 200)
    assert SR.pair_rule(a, b, CFG)["kind"] == "sliver"
    assert SR.pair_rule(a, b, dict(CFG, _alley=pairs))["kind"] == "street"
    # a notch: the same dense stations between two cores that face each other over only 30 um are legal
    t2 = json.loads(json.dumps(t))
    t2["hard_cores"][1]["origin_um"] = [320.0, 270.0]        # a|b overlap y 270..300
    t2["internal_stations"] = [{"regs_um": [[310.0, 285.0]], "bits": 640}]
    t2["ft_slots"] = []
    assert SR.station_alleys(t2, CFG) == []
    # fewer than pinface_min bits: a single relay in a slot is legal
    t["internal_stations"] = [{"regs_um": [[310.0, 150.0]], "bits": 8}]
    t["ft_slots"] = []
    assert SR.station_alleys(t, CFG) == []
    assert SR.station_alleys(t, dict(CFG, face_rule=0)) == []


def _face_plan(tmp_path):
    """toy plan with the two cores 21.6 um above a 2,000-pin S bus window of the type (4 pins / um)."""
    plan, P = _toy_plan(tmp_path, gap=86.4)
    t = P["partition_types"]["toy"]
    for h in t["hard_cores"]:
        h["origin_um"][1] = 21.6
    t["buses"] = [{"name": "s_i", "dir": "in", "width": 2000, "kind": "data", "face": "S", "window_um": [50.0, 550.0]}]
    t["ft_slots"] = []
    plan.write_text(json.dumps(P))
    return plan, P


def test_face_street_check_and_legalize(tmp_path):
    plan, P = _face_plan(tmp_path)
    ck = tmp_path / "ck.json"
    SR.main(["check", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck)])
    row = json.loads(ck.read_text())["rows"][0]
    assert row["counts"].get("face_street") == 2 and {v["a"] for v in row["face"]} == {"u_a", "u_b"}
    assert json.loads(ck.read_text())["types_with_violations"] == 1
    # face_rule=0 restores the STREET-RULE-1 result
    SR.main(["check", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck), "--set", "face_rule=0"])
    assert "face_street" not in json.loads(ck.read_text())["rows"][0]["counts"]
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    rc = SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
                  "--event", str(ev), "--rs-halving", "off"])
    assert rc == 0
    row = json.loads(ev.read_text())["rows"][0]
    assert row["applied"], row["reason"]
    t = json.loads(out.read_text())["partition_types"]["toy"]
    for h0, h1 in zip(P["partition_types"]["toy"]["hard_cores"], t["hard_cores"]):
        assert h1["origin_um"][1] >= 43.2 - 1e-6                        # lifted to a street off the S pin face
        assert h1["outline_um"] == h0["outline_um"]                     # never a core shape change
        assert abs((h1["origin_um"][1] - h0["origin_um"][1]) / SR.G - round((h1["origin_um"][1] - h0["origin_um"][1]) / SR.G)) < 1e-6
    assert t["outline_um"] == P["partition_types"]["toy"]["outline_um"]
    SR.main(["check", str(out), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck)])
    assert json.loads(ck.read_text())["types_with_violations"] == 0


def test_face_street_g0_error(tmp_path):
    import check as CK
    plan, P = _face_plan(tmp_path)
    R = CK.Report()
    summ = SR.g0_check(P, R, tmp_path, "error", repo=tmp_path)
    assert summ["counts"]["face_street"] == 2 and summ["types_with_errors"] == 1
    errs = [i for i in R.items if i["level"] == "ERROR" and i["check"] == "street_gap"]
    assert len(errs) == 1 and "face_street" in errs[0]["msg"] and "face:S" in errs[0]["msg"]


def test_legalize_refuses_core_on_content_macro(tmp_path):
    plan, P = _face_plan(tmp_path)
    t = P["partition_types"]["toy"]
    # a fixed LEF content macro right above u_a: lifting u_a would land on it -> not applied, the base stays
    t["contents"] = [{"inst": "u_mem", "module": "M", "lef": "m.lef", "origin_um": [60.48, 125.0],
                      "outline_um": [100.0, 40.0], "orient": "R0"}]
    plan.write_text(json.dumps(P))
    out, ev = tmp_path / "new.json", tmp_path / "ev.json"
    SR.main(["legalize", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out-plan", str(out),
             "--event", str(ev), "--rs-halving", "off"])
    row = json.loads(ev.read_text())["rows"][0]
    assert not row["applied"] and "LEF content" in row["reason"]


def test_plan_face_windows_fallback(tmp_path, monkeypatch):
    # a type whose buses carry no face / window (qwen_kvsys form): the windows come from the plan's port pins
    import types as _types
    fake = _types.SimpleNamespace(DIE_PART="@die", OPP=SR.OPP)

    class Plan:
        def __init__(self, raw, path=None):
            self.parts = {"p0": {"type": "toy"}, "p1": {"type": "toy"}}
            self.ports = {"L0": {"src": {"part": "p0", "bus": "o"}, "dst": {"part": "x", "bus": "i"}, "face": "S"},
                          "L1": {"src": {"part": "x", "bus": "o"}, "dst": {"part": "p0", "bus": "j"}, "face": "W"},
                          "L2": {"src": {"part": "p1", "bus": "o"}, "dst": {"part": "x", "bus": "i"}, "face": "S"}}

        def type_face(self, part, f):
            return f

        @staticmethod
        def rect(P, part):
            return (1000.0, 2000.0, 1600.0, 2300.0)

        def port_pins(self, pid):
            if pid == "L1":
                return [(k, "M4", 2100.0 + 0.1 * k) for k in range(40)]
            return [(k, "M5", 1050.0 + 0.25 * k) for k in range(2000)] + [(2000 + k, "M5", 1580.0 + k) for k in range(3)]

        def to_type(self, part, pt):
            return pt[0] - 1000.0, pt[1] - 2000.0
    fake.Plan = Plan
    monkeypatch.setitem(sys.modules, "schema", fake)
    raw = {"partition_types": {"toy": {"hard_cores": [{"inst": "u_a"}], "buses": [{"name": "o", "width": 2003}]},
                               "soft": {"buses": []}}}
    w = SR.plan_face_windows(raw)
    assert set(w) == {"toy"} and [x[2] for x in w["toy"]["S"]] == [2000, 3]       # two runs of bus o (gap > 8.64)
    assert w["toy"]["S"][0][:2] == (50.0, 549.75)
    e = w["toy"]["E"]                                         # the dst side of a W port sits on the type's E face
    assert len(e) == 1 and e[0][0] == 100.0 and abs(e[0][1] - 103.9) < 1e-6 and e[0][2:] == (40, "j")
    cfg = SR.type_cfg(dict(CFG, _planwins=w), raw["partition_types"]["toy"], "toy")
    assert SR.span_pins(cfg["_fwins"]["S"], 50, 300) == 1001          # 2,000 pins over 499.75 um
    # a type that carries its own windows never takes the fallback
    raw["partition_types"]["toy"]["buses"] = [{"name": "o", "face": "N", "window_um": [0, 10], "width": 5}]
    assert SR.plan_face_windows(raw) == {}


def test_content_only_type_checked(tmp_path):
    # a type with no hard core: its SRAM 20 um above a dense S pin window is a face_street (check and G0)
    import check as CK
    t = {"outline_um": [600.0, 300.0], "module": "soft",
         "buses": [{"name": "s_i", "dir": "in", "width": 2000, "kind": "data", "face": "S", "window_um": [50.0, 550.0]}],
         "contents": [{"inst": "u_mem", "module": "M", "lef": "m.lef", "origin_um": [100.0, 20.0],
                       "outline_um": [200.0, 80.0], "orient": "R0"}]}
    P = {"die": {"name": "toy", "outline_um": [600.0, 300.0]}, "partition_types": {"soft": t},
         "partitions": [{"name": "p0", "type": "soft", "origin_um": [0, 0]}]}
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps(P))
    ck = tmp_path / "ck.json"
    SR.main(["check", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck)])
    rec = json.loads(ck.read_text())
    assert rec["types_with_violations"] == 1 and rec["rows"][0]["cores"] == 0
    v = rec["rows"][0]["face"][0]
    assert v["kind"] == "face_street" and v["a"] == "u_mem" and not v["movable"] and v["need"] == 43.2
    R = CK.Report()
    summ = SR.g0_check(P, R, tmp_path, "error", repo=tmp_path)
    assert summ["counts"] == {"face_street": 1} and summ["types_with_errors"] == 1 and len(R.errors()) == 1
    t["contents"][0]["origin_um"] = [100.0, 43.2]
    plan.write_text(json.dumps(P))
    SR.main(["check", str(plan), "--die", "toy", "--repo", str(tmp_path), "--out", str(ck)])
    assert json.loads(ck.read_text())["types_with_violations"] == 0


def test_transit_street():
    # two macros 43.2 um above the S outline; an ft chain of 2,208 bits runs along that strip (hops along x at y = 12)
    t = {"outline_um": [1000.0, 600.0],
         "hard_cores": [{"inst": "a", "origin_um": [100.0, 43.2], "outline_um": [300.0, 200.0]},
                        {"inst": "b", "origin_um": [500.0, 43.2], "outline_um": [300.0, 200.0]}],
         "ft_slots": [{"name": "f4", "width": 1104, "regs_um": [[900.0, 0.0], [700.0, 12.0], [400.0, 12.0], [60.0, 12.0]]},
                      {"name": "f5", "width": 1104, "regs_um": [[950.0, 0.0], [720.0, 14.0], [420.0, 14.0], [80.0, 14.0]]}]}
    assert len(SR.station_hops(t)) == 6
    V = SR.transit_streets(t, CFG)
    got = {(v["a"], v["b"]): (v["pins"][0], v["gap"], v["need"]) for v in V}
    assert got == {("outline:S", "a"): (2208, 43.2, 60.48), ("outline:S", "b"): (2208, 43.2, 60.48)}
    assert all(v["kind"] == "transit_street" and v["axis"] == "y" for v in V)
    pairs, faces = SR.alley_force(V)
    assert faces == {("a", "S"): 60.48, ("b", "S"): 60.48} and pairs == {}
    # the same chain in a 60.48-um strip is legal; one 1,104-bit slot alone fits 43.2 (29.4 -> 30.24)
    for h in t["hard_cores"]:
        h["origin_um"][1] = 60.48
    assert SR.transit_streets(t, CFG) == []
    for h in t["hard_cores"]:
        h["origin_um"][1] = 43.2
    t["ft_slots"] = t["ft_slots"][:1]
    assert SR.transit_streets(t, CFG) == []
    # a chain between two cores: the pair becomes a street of the transit width in legalize
    t2 = {"outline_um": [1000.0, 600.0],
          "hard_cores": [{"inst": "a", "origin_um": [100.0, 100.0], "outline_um": [200.0, 400.0]},
                         {"inst": "b", "origin_um": [343.2, 100.0], "outline_um": [200.0, 400.0]}],
          "internal_stations": [{"from_um": [320.0, 520.0], "regs_um": [[320.0, 300.0]], "to_um": [320.0, 80.0], "bits": 3000}]}
    V = SR.transit_streets(t2, CFG)
    assert [(v["a"], v["b"], v["axis"], v["pins"][0], v["need"]) for v in V] == [("a", "b", "x", 3000, 82.08)]
    pairs, _ = SR.alley_force(V)
    a = core("a", 100, 100, 200, 400)
    b = core("b", 343.2, 100, 200, 400)
    r = SR.pair_rule(a, b, dict(CFG, _alley=pairs))
    assert r["kind"] == "street" and r["need"] == 82.08
    assert "transit_street" in SR.HARD
