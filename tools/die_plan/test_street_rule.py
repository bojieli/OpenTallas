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
                             dict(name="r_b", q="qb", depth=3, role="raw", xy=[200.0, 50.0])]),
        "new": dict(relays=[dict(name="r_a2", q="qa2", depth=2, role="raw", xy=[130.0, 50.0]),
                            dict(name="r_x", q="qx", depth=2, role="raw", xy=[400.0, 50.0]),
                            dict(name="r_b", q="qb", depth=3, role="raw", xy=[205.0, 50.0])]),
    }
    import schema
    import reset_tree
    monkeypatch.setattr(schema, "Plan", lambda raw, path=None: _t.SimpleNamespace(tag=raw["tag"]))
    monkeypatch.setattr(reset_tree, "for_type", lambda PP, tn: trees[PP.tag])
    t = {"reset_start_raw_exports": [dict(port="rst_o", instance="r_a", net="qa", xy_um=[100.0, 50.0])],
         "clock": {"landing_contract": {"pins": [dict(name="rst_o", xy_um=[101.0, 49.0], source_instance="r_a")]},
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
