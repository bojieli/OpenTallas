"""UNIFY-TOOLS class_merge: a class of types becomes ONE type; monitor children tieable and re-indexed by site."""
import collections, copy, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import class_merge as CM  # noqa: E402
import landing_tie_children as LTC  # noqa: E402


def _child(i, xy):
    return dict(index=i, xy_um=list(xy), seam=True, node=f"n{i}", part=None,
                ready=f"cland_dn_ready_{i}", fault=f"cland_dn_fault_{i}")


def _pins(children):
    out = [dict(name="cland_up_ready", dir="out", kind="ctl", layer="M5", xy_um=[600.0, 0.0]),
           dict(name="d_in", dir="in", kind="data", layer="M5", xy_um=[0.024, 300.0])]
    for i, (x, y) in children:
        out += [dict(name=f"cland_dn_ready_{i}", dir="in", kind="ctl", layer="M5", xy_um=[x, y]),
                dict(name=f"cland_dn_fault_{i}", dir="in", kind="ctl", layer="M5", xy_um=[x, y + 0.48]),
                dict(name=f"fclk_in_cland_dn_{i}", dir="in", kind="clk", layer="M5", xy_um=[x, y + 0.96])]
    return out


def _type(name, children, pad=None):
    t = dict(module=name, outline_um=[1226.88, 1339.2], buses=[dict(name="d_in", width=8)], ft_slots=[],
             hard_cores=[dict(name=f"core_{name}")],
             clock=dict(landing_contract=dict(pins=_pins(children),
                                              collector_children=[_child(i, xy) for i, xy in children])))
    if pad is not None:
        t["r8_strap_pad_max"] = pad
    return t


A, B, C = (8.16, 502.176), (153.376, 1330.592), (460.064, 1330.592)


def _plan():
    types = {"ctl__rep": _type("ctl__rep", [(0, A), (1, B), (2, C)]),
             "ctl__m1": _type("ctl__m1", [(0, C)], pad=31),           # its child 0 is the rep's child 2
             "ctl__m2": _type("ctl__m2", []),
             "other": _type("other", [])}
    parts = [dict(name="p0", type="ctl__rep"), dict(name="p1", type="ctl__m1"), dict(name="p2", type="ctl__m2"),
             dict(name="kid", type="other")]
    edges = [dict(id=f"cland_mon_{k}__kid", src=dict(part="kid", bus="cland_up_ready"),
                  dst=dict(part="p1", bus=f"{pin}_0"))
             for k, pin in (("ready", "cland_dn_ready"), ("fault", "cland_dn_fault"), ("clk", "fclk_in_cland_dn"))]
    plan = dict(partition_types=types, partitions=parts, clock=dict(
        landing_network=dict(edges=edges),
        tap_window=dict(per_type_ps={"ctl__rep": 90, "ctl__m1": 60, "ctl__m2": 70, "other": 10})),
        reset=dict(in_sites={k: [1.0, 2.0] for k in types}))
    side = dict(count_aligned=dict(parts={p: dict(role="origin") for p in ("p0", "p1", "p2")}),
                collector=dict(parts={p["name"]: dict(type=p["type"]) for p in parts},
                               types={k: dict(base_type=k) for k in types},
                               edges=[dict(src="kid", dst="p1", dst_index=0)],
                               boot_budget=dict(local_registered_depths={"p0": 10, "p1": 9, "p2": 10})))
    return plan, side


def test_merge_one_type_reindexed_tieable():
    plan, side = _plan()
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__rep", "ctl__m1", "ctl__m2"])
    assert rep["refused"] == []
    assert {p["type"] for p in plan["partitions"] if p["name"] != "kid"} == {"ctl__rep"}
    assert set(plan["partition_types"]) == {"ctl__rep", "other"}
    lc = plan["partition_types"]["ctl__rep"]["clock"]["landing_contract"]
    assert lc["tieable_children"] == [dict(index=i, seam=True) for i in range(3)]
    names = {p["name"] for p in lc["pins"]}
    assert {"strap_cland_use_0", "strap_cland_use_1", "strap_cland_use_2"} <= names
    # p1's only child (site C) is the representative's child 2
    assert {e["dst"]["bus"] for e in plan["clock"]["landing_network"]["edges"]} == \
        {"cland_dn_ready_2", "cland_dn_fault_2", "fclk_in_cland_dn_2"}
    assert side["collector"]["edges"][0]["dst_index"] == 2
    assert plan["partition_types"]["ctl__rep"]["r8_strap_pad_max"] == 31
    assert set(plan["clock"]["tap_window"]["per_type_ps"]) == {"ctl__rep", "other"}
    assert set(plan["reset"]["in_sites"]) == {"ctl__rep", "other"}
    assert set(side["collector"]["types"]) == {"ctl__rep", "other"}
    assert side["collector"]["boot_budget"]["local_registered_depths"]["p1"] == 10
    # per-instance use straps come from the real edges: p1 uses child 2 only, p0 none, p2 none
    use = LTC.instance_use(plan)
    assert use["p1"] == {"strap_cland_use_0": (1, 0), "strap_cland_use_1": (1, 0), "strap_cland_use_2": (1, 1)}
    assert use["p2"] == {f"strap_cland_use_{i}": (1, 0) for i in range(3)}


def test_refuses_child_site_not_on_representative():
    plan, side = _plan()
    plan["partition_types"]["ctl__m2"] = _type("ctl__m2", [(0, (1217.76, 1171.808))])
    before = copy.deepcopy(plan)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"])
    assert any("not a representative child site" in r for r in rep["refused"])
    assert plan == before


def test_refuses_outline_and_role_difference():
    plan, side = _plan()
    plan["partition_types"]["ctl__m2"]["outline_um"] = [1226.88, 1400.0]
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"])
    assert any("outline_um differs" in r for r in rep["refused"])
    assert any("landing role differs" in r for r in rep["refused"])


def test_types_outside_the_class_unchanged(tmp_path):
    plan, side = _plan()
    other = json.dumps(plan["partition_types"]["other"], sort_keys=True)
    pp, sp = tmp_path / "p.json", tmp_path / "s.json"
    pp.write_text(json.dumps(plan)); sp.write_text(json.dumps(side))
    rc = CM.main([str(pp), str(sp), str(tmp_path / "op.json"), str(tmp_path / "os.json"), "--rep", "ctl__rep",
                  "--stem", "ctl", "--report", str(tmp_path / "r.json")])
    assert rc == 0
    out = json.loads((tmp_path / "op.json").read_text())
    assert json.dumps(out["partition_types"]["other"], sort_keys=True) == other
    assert json.loads((tmp_path / "r.json").read_text())["instances"] == 3


def test_role_strap_union_of_start_pins_and_straps():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    rx = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="M5", xy_um=[700.0, 0.0])
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(rx)
    plan["partition_types"]["ctl__rep"]["count_straps"] = [dict(name="strap_ca_pad", width=2),
                                                           dict(name="strap_ca_efall", width=1)]
    plan["partition_types"]["ctl__m1"]["count_straps"] = [dict(name="strap_ca_pad", width=3)]
    assert CM.merge(copy.deepcopy(plan), copy.deepcopy(side), "ctl__rep", ["ctl__m1", "ctl__m2"])["refused"]
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert rep["refused"] == [] and rep["role_strap"]["pins_added"] == ["cland_rstart_in"]
    t = plan["partition_types"]["ctl__rep"]
    assert t["landing_role_strap"] is True
    assert {c["name"]: c["width"] for c in t["count_straps"]} == {"strap_ca_pad": 3, "strap_ca_efall": 1,
                                                                  "strap_ca_relay": 1}
    assert rx in t["clock"]["landing_contract"]["pins"]


def test_role_strap_moves_a_colliding_start_pin_to_a_free_track():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    taken = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="M5", xy_um=[0.024, 300.0])   # d_in's site
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(taken)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert rep["refused"] == []
    old, new = rep["role_pins_moved"]["cland_rstart_in"]
    assert old == [0.024, 300.0] and new[1] == 300.0 and new[0] >= 1.0      # M5 is vertical: moved in x, on a track
    assert abs(round((new[0] - 0.024) / 0.048) * 0.048 + 0.024 - new[0]) < 1e-6


def test_role_strap_refuses_unknown_layer_collision():
    plan, side = _plan()
    side["count_aligned"]["parts"]["p2"]["role"] = "relay"
    plan["partition_types"]["ctl__rep"]["clock"]["landing_contract"]["pins"][1]["layer"] = "MX"
    taken = dict(name="cland_rstart_in", dir="in", kind="ctl", layer="MX", xy_um=[0.024, 300.0])
    plan["partition_types"]["ctl__m2"]["clock"]["landing_contract"]["pins"].append(taken)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], role_strap=True)
    assert any("no free site" in r for r in rep["refused"])


def _lane_plan(rep_regs, mem_regs, fixed, core_out=0):
    """p0 (rep) and p1 (member) each source lane d_out -> kid.d_in; the member's OUT chain is shorter"""
    plan, side = _plan()
    P = plan["partition_types"]
    for tn, regs in (("ctl__rep", rep_regs), ("ctl__m1", mem_regs), ("ctl__m2", rep_regs)):
        P[tn]["buses"] = [dict(name="d_in", width=8), dict(name="d_out", width=8, dir="out")]
        P[tn]["internal_stations"] = [dict(conn="bus:d_out", regs_um=[[1.0, 1.0]] * regs)] if regs else []
        if core_out and tn == "ctl__rep":
            P[tn]["hard_cores"][0]["core_latency"] = dict(out=dict(d_out=core_out))
    plan["ports"], plan["lanes"], plan["latency"] = [], [], dict(lanes={})
    for p in ("p0", "p1", "p2"):
        plan["ports"].append(dict(id=f"pt_{p}", src=dict(part=p, bus="d_out"), dst=dict(part="kid", bus=f"d_in_{p}")))
        plan["lanes"].append(dict(id=f"ln_{p}", ports=[f"pt_{p}"], fixed_cycles=fixed[p]))
        plan["latency"]["lanes"][f"ln_{p}"] = dict(cycles=4 + fixed[p], stations=0, boundary=2, fixed=fixed[p],
                                                  clock_landing=2, natural=4 + fixed[p], pad=0)
    return plan, side


def test_prices_representative_out_kit_stations_on_moved_lanes():
    # rep chain 3 regs + 1 declared core cycle = 4; member m1 chain 2 = 2 (+0, its core declares none)
    plan, side = _lane_plan(3, 2, dict(p0=4, p1=2, p2=4), core_out=1)
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__rep", "ctl__m1", "ctl__m2"])
    assert rep["refused"] == []
    # p1: member chain 2 cut from its pad, class chain 4 not cut (fixed 2 < 4) -> late 4; p2 (member 3, fixed 4):
    # the class chain is cut from its receiver pad 1 -> on time, unchanged
    assert rep["kit_priced"] == [dict(lane="ln_p1", part="p1", bus="d_out", member=2, rep=4, add=2, late=4)]
    assert plan["latency"]["lanes"]["ln_p2"]["cycles"] == 8
    row = plan["latency"]["lanes"]["ln_p1"]
    assert (row["fixed"], row["cycles"], row["natural"], row["pad"]) == (4, 8, 8, 0)
    assert next(x for x in plan["lanes"] if x["id"] == "ln_p1")["fixed_cycles"] == 4
    assert plan["latency"]["lanes"]["ln_p0"]["cycles"] == 8      # the representative's own lane is unchanged


def test_kit_pricing_skips_lane_that_never_priced_its_chain_and_reprice_cli(tmp_path):
    plan, side = _lane_plan(3, 2, dict(p0=3, p1=0, p2=3))
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__rep", "ctl__m1", "ctl__m2"])
    assert rep["kit_priced"] == []                      # p1 fixed 0 < member chain 2: not kit-priced before either
    assert CM.late_by_kit(dict(cycles=14, boundary=2, stations=6, clock_landing=3), 3, 3, 1) == 1   # zero pad: IN chain
    # --reprice-from on an already merged plan: same rule, instance types from the pre-merge plan
    plan2, side2 = _lane_plan(3, 2, dict(p0=3, p1=2, p2=3))
    pre = copy.deepcopy(plan2)
    for p in plan2["partitions"]:
        if p["type"] in ("ctl__m1", "ctl__m2"):
            p["type"] = "ctl__rep"
    for name, d in (("plan.json", plan2), ("side.json", side2), ("pre.json", pre)):
        (tmp_path / name).write_text(json.dumps(d))
    assert CM.main([str(tmp_path / "plan.json"), str(tmp_path / "side.json"), str(tmp_path / "o.json"),
                    str(tmp_path / "os.json"), "--reprice-from", str(tmp_path / "pre.json")]) == 0
    out = json.loads((tmp_path / "o.json").read_text())
    assert out["latency"]["lanes"]["ln_p1"]["cycles"] == 7 and out["latency"]["lanes"]["ln_p2"]["cycles"] == 7


def _ft(name, face_y, stations=2, in_face="W", out_face="E"):
    return dict(name=name, in_face=in_face, out_face=out_face, width=4, stations=stations,
                in_window_um=[face_y, face_y + 6.0], out_window_um=[face_y, face_y + 6.0], layers=["M5"])


def _ft_plan():
    """rep has slot a; m1 has a's pins under another name (dup) plus its own x; m2 has its own y.  Ports bind p1.dup,
    p1.x and p2.y; p0 binds a."""
    plan, side = _plan()
    T = plan["partition_types"]
    T["ctl__rep"]["ft_slots"] = [_ft("a", 100.0)]
    T["ctl__m1"]["ft_slots"] = [_ft("xft__ctl__m1__dup", 100.0), _ft("xft__ctl__m1__x", 200.0)]
    T["ctl__m2"]["ft_slots"] = [_ft("xft__ctl__m2__y", 300.0)]
    T["ctl__m1"]["clock"]["landing_contract"]["collector_children"] = []
    T["ctl__m1"]["clock"]["landing_contract"]["pins"] = _pins([])
    plan["clock"]["landing_network"]["edges"] = []
    side["collector"]["edges"] = []
    pr = lambda i, sp, sb, dp, db: dict(id=f"pt{i}", src=dict(part=sp, bus=sb), dst=dict(part=dp, bus=db), width=4)
    plan["ports"] = [pr(0, "kid", "o0", "p0", "a_i"), pr(1, "p0", "a_o", "kid", "i0"),
                     pr(2, "kid", "o1", "p1", "xft__ctl__m1__dup_i"), pr(3, "p1", "xft__ctl__m1__dup_o", "kid", "i1"),
                     pr(4, "kid", "o2", "p1", "xft__ctl__m1__x_i"), pr(5, "p1", "xft__ctl__m1__x_o", "kid", "i2"),
                     pr(6, "kid", "o3", "p2", "xft__ctl__m2__y_i"), pr(7, "p2", "xft__ctl__m2__y_o", "kid", "i3")]
    return plan, side


def test_ft_superset_union_keeps_stable_names_and_declares_spares():
    """UNIFY-TOOLS-R3 (COORD): the class row carries the union of the members' ft slots under their own names"""
    plan, side = _ft_plan()
    assert any("ft_slots differs" in r for r in CM.merge(*_ft_plan(), "ctl__rep", ["ctl__m1", "ctl__m2"])["refused"])
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], ft_superset=True)
    assert rep["refused"] == []
    R = plan["partition_types"]["ctl__rep"]
    assert R["superset"] is True
    assert [s["name"] for s in R["ft_slots"]] == ["a", "xft__ctl__m1__x", "xft__ctl__m2__y"]
    fs = rep["ft_superset"]
    assert fs["added"] == ["xft__ctl__m1__x", "xft__ctl__m2__y"] and fs["overlaps"] == []
    assert fs["collapsed"] == {"ctl__m1": {"xft__ctl__m1__dup": "a"}} and fs["repointed_port_ends"] == 2
    buses = {(e["part"], e["bus"]) for p in plan["ports"] for e in (p["src"], p["dst"])}
    assert ("p1", "a_i") in buses and ("p1", "a_o") in buses and ("p1", "xft__ctl__m1__x_i") in buses
    sp = {p["name"]: p.get("spare_ends") for p in plan["partitions"]}
    assert sp == {"p0": ["xft__ctl__m1__x", "xft__ctl__m2__y"], "p1": ["xft__ctl__m2__y"],
                  "p2": ["a", "xft__ctl__m1__x"], "kid": None}
    # a spare end is bound by no port (schema.spare_end_errors rule)
    use = collections.defaultdict(list)
    for p in plan["ports"]:
        for e in (p["src"], p["dst"]):
            use[(e["part"], e["bus"])].append(p["id"])
    assert all(not use[(pn, n + sfx)] for pn, ns in sp.items() for n in (ns or []) for sfx in ("_i", "_o"))


def test_ft_superset_refuses_station_mismatch_reports_overlaps(tmp_path):
    plan, side = _ft_plan()
    plan, side = _ft_plan()
    plan["partition_types"]["ctl__m1"]["ft_slots"][0]["stations"] = 3               # a's pins, one more station
    plan["lanes"] = [dict(id="L1", ports=["pt2", "pt3"]), dict(id="L0", ports=["pt0", "pt1"])]
    plan["latency"] = dict(lanes={k: dict(cycles=10, natural=10, stations=4, pad=0) for k in ("L0", "L1")})
    r = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], ft_superset=True)
    assert r["refused"] == [] and plan["partition_types"]["ctl__rep"]["ft_slots"][0]["stations"] == 3
    # the rep's own copy (p0, 2 stations) is the shallower one: its lane L0 gets +1; p1's L1 already had 3
    assert r["ft_stations_raised"] == [dict(lane="L0", part="p0", slot="a", add=1)]
    assert plan["latency"]["lanes"]["L0"]["cycles"] == 11 and plan["latency"]["lanes"]["L1"]["cycles"] == 10
    # overlap report + CLI flag
    plan, side = _ft_plan()
    plan["partition_types"]["ctl__m2"]["ft_slots"] = [_ft("xft__ctl__m2__y", 103.0)]
    pp, sp_, op, os_, rp = (tmp_path / n for n in ("p.json", "s.json", "o.json", "os.json", "r.json"))
    pp.write_text(json.dumps(plan)); sp_.write_text(json.dumps(side))
    assert CM.main([str(pp), str(sp_), str(op), str(os_), "--rep", "ctl__rep", "--members", "ctl__m1,ctl__m2",
                    "--ft-superset", "--report", str(rp)]) == 0
    ov = json.loads(rp.read_text())["ft_superset"]["overlaps"]
    assert ["a", "xft__ctl__m2__y", "W"] in ov and ["a", "xft__ctl__m2__y", "E"] in ov


def test_ft_superset_clashing_local_names_get_stable_class_names():
    """S81 leaf types name their slots ft0..ftN per type: a member ft0 with other pins than the rep's ft0 becomes
    ft0_c<pinhash>, its per-slot landing pins and landing edges follow, the class row gains those pins"""
    plan, side = _ft_plan()
    T = plan["partition_types"]
    T["ctl__rep"]["ft_slots"] = [_ft("ft0", 100.0)]
    T["ctl__m2"]["ft_slots"] = [_ft("ft0", 300.0)]
    T["ctl__m2"]["clock"]["landing_contract"]["pins"] += [
        dict(name="fclk_in_ft0_i", dir="in", kind="clk", layer="M5", xy_um=[0.024, 301.0]),
        dict(name="cland_fstart_out_ft0_o", dir="out", kind="ctl", layer="M5", xy_um=[1226.8, 301.0])]
    plan["clock"]["landing_network"]["edges"] = [dict(id="fe", src=dict(part="kid", bus="x"),
                                                      dst=dict(part="p2", bus="fclk_in_ft0_i"))]
    for p in plan["ports"]:
        for e in (p["src"], p["dst"]):
            if e["part"] == "p0":
                e["bus"] = e["bus"].replace("a_", "ft0_")
            if e["part"] == "p2":
                e["bus"] = e["bus"].replace("xft__ctl__m2__y_", "ft0_")
    T["ctl__m1"]["ft_slots"] = [_ft("xft__ctl__m1__dup", 100.0), _ft("xft__ctl__m1__x", 200.0)]
    key = CM.ft_pin_key(_ft("ft0", 300.0))
    cn = CM.ft_class_name("ft0", key)
    assert cn.startswith("ft0_c") and cn == CM.ft_class_name("ft0", key)
    two = copy.deepcopy((plan, side))
    rep = CM.merge(plan, side, "ctl__rep", ["ctl__m1", "ctl__m2"], ft_superset=True)
    assert rep["refused"] == []
    names = [s["name"] for s in plan["partition_types"]["ctl__rep"]["ft_slots"]]
    assert names == ["ft0", cn, "xft__ctl__m1__x"]
    assert {(e["part"], e["bus"]) for p in plan["ports"] for e in (p["src"], p["dst"]) if e["part"] == "p2"} == \
        {("p2", cn + "_i"), ("p2", cn + "_o")}
    pins = {q["name"] for q in plan["partition_types"]["ctl__rep"]["clock"]["landing_contract"]["pins"]}
    assert {f"fclk_in_{cn}_i", f"cland_fstart_out_{cn}_o"} <= pins
    assert plan["clock"]["landing_network"]["edges"][0]["dst"]["bus"] == f"fclk_in_{cn}_i"
    assert rep["ft_superset"]["landing_edges_repointed"] == 1
    # stable: member order does not change the class names
    rep2 = CM.merge(*two, "ctl__rep", ["ctl__m2", "ctl__m1"], ft_superset=True)
    assert [s["name"] for s in two[0]["partition_types"]["ctl__rep"]["ft_slots"]] == names and rep2["refused"] == []
