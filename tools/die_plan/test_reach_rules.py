"""R-REACH (RULEBOOK 11-13, reach_rules.py): one failing fixture per rule, the fix, idempotency, the shared START trunk
in the generator / placement, and the G0 hook.
    python3 -m pytest -q tools/die_plan/test_reach_rules.py"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_landings as CL  # noqa: E402
import landing_place as LP  # noqa: E402
import reach_rules as RR  # noqa: E402
import schema  # noqa: E402

EX = json.loads((HERE / "examples" / "tiny_plan.json").read_text())


def _band(x, y):
    return dict(rect_um=[x - 20.0, y - 4.0, x + 20.0, y + 4.0], width=8, ring_width=64)


def _start_plan(n_far=6, w=2592.0, h=1728.0):
    """tiny_plan with type 'mid' grown to w x h and a START-tree child origin: pin on the S face, n_far input rings in
    the far NE corner region, 2 near rings, one far FSTART output pin."""
    p = copy.deepcopy(EX)
    t = p["partition_types"]["mid"]
    pins = [dict(name="cland_tstart_in", dir="in", kind="ctl", layer="M7", xy_um=[100.0, 2.0])]
    bands = {}
    for i in range(n_far):
        b = f"f{i}"
        bands[b] = _band(740.0 + 30.0 * (i % 4), 640.0 + 30.0 * (i // 4))
        pins.append(dict(name=f"cland_fstart_in_{b}", dir="in", kind="ctl", layer="M7", xy_um=[862.0, 600.0 + i]))
    for i in range(2):
        b = f"n{i}"
        bands[b] = _band(200.0 + 60.0 * i, 60.0)
        pins.append(dict(name=f"cland_fstart_in_{b}", dir="in", kind="ctl", layer="M7", xy_um=[200.0 + 60 * i, 2.0]))
    pins.append(dict(name="cland_fstart_out_q", dir="out", kind="ctl", layer="M7", xy_um=[862.0, 800.0]))
    t.setdefault("clock", {})["landing_contract"] = dict(pins=pins, bands=bands)
    return p


def _P(p):
    return schema.Plan(copy.deepcopy(p), None)


def test_owners_default_and_shared():
    st = lambda *xs: dict(stages=[dict(xy_um=[x, 0], raw_reset="r") for x in xs])
    cfg = dict(depth=3, branches=dict(a=st(1, 2, 3), b=st(1, 2, 3), c=st(1, 9, 3)))
    assert CL.reader_start_owners(cfg) == dict(a=["a"] * 3, b=["b"] * 3, c=["c"] * 3)        # absent: every bus owns
    cfg["share_trunk"] = True
    # equal prefixes share; the last stage is always the bus's own; a diverging prefix stops sharing
    assert CL.reader_start_owners(cfg) == dict(a=["a", "a", "a"], b=["a", "a", "b"], c=["a", "c", "c"])


def test_rule1_start_far_rings_error_and_fix():
    p = _start_plan()
    t = p["partition_types"]["mid"]
    row, fs = RR.start_findings(t, "mid")
    kinds = {f["kind"] for f in fs}
    assert "start_reach" in kinds and "start_writer_reach" in kinds
    assert row["reader_over"] == 6 and row["reader_worst_hop_um"] > RR.REACH_UM and not row["origin_pinned"]
    rep = RR.fix_start(_P(p), t, "mid")
    assert rep["changed"] == ["landing_reader_start", "landing_writer_start"]
    ck = t["clock"]
    rs = ck["landing_reader_start"]
    assert rs["share_trunk"] is True and set(rs["branches"]) == {f"f{i}" for i in range(6)} | {"n0", "n1"}
    assert all(len(b["stages"]) == rs["depth"] for b in rs["branches"].values())             # uniform depth: one K - R
    assert "origin_rect_um" in rs
    row2, fs2 = RR.start_findings(t, "mid")
    assert fs2 == [] and row2["reader_worst_hop_um"] <= RR.REACH_UM and row2["writer_worst_hop_um"] <= RR.REACH_UM
    # the six far rings ride ONE trunk: the origin drives fewer first relays than rings
    assert row2["origin_loads"] < 8 and row2["origin_pinned"]
    own = CL.reader_start_owners(rs)
    assert len({own[f"f{i}"][0] for i in range(6)}) == 1
    assert schema.validate(p) == []
    # idempotent
    before = json.dumps(t, sort_keys=True)
    assert RR.fix_start(_P(p), t, "mid")["changed"] == [] and json.dumps(t, sort_keys=True) == before


def test_rule1_fanout_over_48():
    p = _start_plan(n_far=0)
    t = p["partition_types"]["mid"]
    lc = t["clock"]["landing_contract"]
    for i in range(60):              # 60 near rings: within reach, but 60 loads on one start register
        b = f"m{i}"
        lc["bands"][b] = _band(120.0 + 4.0 * (i % 20), 40.0 + 12.0 * (i // 20))
        lc["pins"].append(dict(name=f"cland_fstart_in_{b}", dir="in", kind="ctl", layer="M7", xy_um=[150.0, 2.0]))
    row, fs = RR.start_findings(t, "mid")
    assert [f["kind"] for f in fs if f["kind"] == "start_fanout"] and row["origin_loads"] == 62
    RR.fix_start(_P(p), t, "mid")
    row2, fs2 = RR.start_findings(t, "mid")
    assert not [f for f in fs2 if f["kind"] == "start_fanout"] and row2["origin_loads"] <= RR.FANOUT_MAX


def test_rule1_no_start_pin_is_out_of_scope():
    t = copy.deepcopy(EX)["partition_types"]["mid"]
    assert RR.start_findings(t, "mid") == (None, [])


def test_generator_shares_trunk_relays():
    st = lambda *xs: dict(stages=[dict(xy_um=[float(x), 0.0], raw_reset="rst_n_t0") for x in xs])
    cfg = dict(depth=3, share_trunk=True, branches=dict(a=st(1, 2, 3), b=st(1, 2, 4), c=st(1, 9, 5)))
    plan = {"partition_types": {"T": {"clock": {"landing_reader_start": cfg}}}}
    L = CL.Landings.__new__(CL.Landings)
    L.types, L.plan, L.strap = plan["partition_types"], plan, True
    L.reset_placements = {"T": {"a": {}, "b": {}, "c": {}}}
    body = "    ot_dp_rrelay u_r0 (.clk(clk), .d(x), .q(rst_n_t0));\n"
    logic, nets = [], {}
    for bus in ("a", "b", "c"):
        nets[bus], body = L._reader_start_rtl("T", bus, body, logic, head="")
    txt = "\n".join(logic)
    # stage 0 once (owner a), stage 1 twice (a shared by b; c diverges), stage 2 per bus
    assert txt.count("ot_dp_landing_relay u_cland_reader_start_a_0 ") == 1
    assert "u_cland_reader_start_b_0" not in txt and "u_cland_reader_start_c_0" not in txt
    assert "u_cland_reader_start_b_1" not in txt and "ot_dp_landing_relay u_cland_reader_start_c_1 " in txt
    assert ".d(cland_reader_start_a_0), .q(cland_reader_start_c_1)" in txt
    assert ".d(cland_reader_start_a_1), .q(cland_reader_start_b_2)" in txt
    assert nets == dict(a="cland_reader_start_a_2", b="cland_reader_start_b_2", c="cland_reader_start_c_2")
    assert txt.count("ot_dp_landing_relay ") == 6                                           # 9 stages -> 6 relays
    assert L.reset_placements["T"]["b"]["reader_start"]["stages"][0]["shared_trunk_owner"] == "a"
    # absent share_trunk: nine relays, as before
    cfg.pop("share_trunk")
    L2 = CL.Landings.__new__(CL.Landings)
    L2.types, L2.plan, L2.strap = plan["partition_types"], plan, True
    L2.reset_placements = {"T": {"a": {}, "b": {}, "c": {}}}
    logic2 = []
    for bus in ("a", "b", "c"):
        L2._reader_start_rtl("T", bus, body, logic2, head="")
    assert "\n".join(logic2).count("ot_dp_landing_relay ") == 9


def test_placement_groups_once_per_shared_relay():
    st = lambda *xs: dict(stages=[dict(xy_um=[float(x), 50.0], raw_reset="rst_n_t0") for x in xs])
    t = dict(outline_um=[500.0, 500.0],
             clock=dict(landing_reader_start=dict(depth=3, share_trunk=True,
                                                  branches=dict(a=st(10, 20, 30), b=st(10, 20, 40)))))
    names = [g[0] for g in LP._reader_start_groups(t)]
    assert names == ["u_cland_reader_start_a_0", "u_cland_reader_start_a_1", "u_cland_reader_start_a_2",
                     "u_cland_reader_start_b_2"]
    t["clock"]["landing_reader_start"].pop("share_trunk")
    assert len(LP._reader_start_groups(t)) == 6


def _fwd_plan():
    p = copy.deepcopy(EX)
    t = p["partition_types"]["mid"]
    t["outline_um"] = [864.0, 864.0]
    t.setdefault("clock", {})["landing_contract"] = dict(pins=[
        dict(name="fclk_out_a", dir="out", kind="clock", layer="M7", xy_um=[862.0, 820.0], source_clock_port="clk",
             source_clock_tap="clk")], bands={})
    return p


def test_rule4_fwd_source_far_and_repoint():
    p = _fwd_plan()
    P = _P(p)
    g = {n: (x, y) for n, x, y in schema.tap_grid(P, "mid")}
    if len(g) < 2:
        import pytest
        pytest.skip("tiny_plan type has one tap")
    t = P.types["mid"]
    q = t["clock"]["landing_contract"]["pins"][0]
    far = max(g, key=lambda n: RR.man(g[n], q["xy_um"]))
    q["source_clock_port"] = q["source_clock_tap"] = far
    row, fs = RR.fwd_findings(P, t, "mid", reach=100.0)
    assert [f["kind"] for f in fs][:1] == ["fwd_source"] and row["over"] + row["root"] == 1
    rep = RR.fix_fwd(P, t, "mid", reach=100.0)
    near = min((n for n in g if n != "clk"), key=lambda n: (RR.man(g[n], q["xy_um"]), n))
    if RR.man(g[near], q["xy_um"]) <= 100.0:
        assert rep["repoints"][0]["new"] == near and q["source_clock_port"] == near
        assert RR.fwd_findings(P, t, "mid", reach=100.0)[1] == []
    q["source_clock_port"] = "clk_t999"                      # a tap that no longer exists
    assert RR.fwd_findings(P, t, "mid")[0]["dangling"] == 1


def test_rule2_barrier_needs_homes_then_stations():
    p = copy.deepcopy(EX)
    t = p["partition_types"]["mid"]
    t["contents"] = [dict(inst="u_rom", module="rom", status="new", origin_um=[200.0, 100.0],
                          outline_um=[460.0, 660.0])]
    P = _P(p)
    t = P.types["mid"]
    pts = RR._bus_points(P, "mid")
    if len(pts) < 2 or not RR.macro_boxes(t):
        import pytest
        pytest.skip("fixture has no placed macro / face buses")
    row, fs = RR.barrier_findings(P, t, "mid")
    assert row["barrier_um"] >= RR.BARRIER_UM
    if row["sides"] > 1:
        assert [f["kind"] for f in fs] == ["barrier_unanchored"]
    names = sorted(pts)
    t["reach_homes"] = [dict(name="w", rect_um=[20.0, 100.0, 180.0, 760.0], buses=names)]
    row2, fs2 = RR.barrier_findings(P, t, "mid")
    assert not [f for f in fs2 if f["kind"] == "barrier_unanchored"]
    n_hop = len([f for f in fs2 if f["kind"] == "barrier_hop"])
    rep = RR.fix_barrier(P, t, "mid")
    assert len(rep["added"]) == n_hop
    assert not [f for f in RR.barrier_findings(P, t, "mid")[1] if f["kind"] == "barrier_hop"]
    for e in t.get("internal_stations", []):
        if str(e.get("note", "")).startswith("R-REACH-2"):
            ptsx = [e["from_um"]] + e["regs_um"] + [e["to_um"]]
            assert max(RR.man(a, b) for a, b in zip(ptsx, ptsx[1:])) <= RR.REACH_UM + 1e-6


def test_g0_hook_errors_and_budget_modes():
    import check as CK
    p = _start_plan()
    Rd, sd = CK.run(copy.deepcopy(p))       # default: warnings only (existing plans keep their G0 verdict)
    assert sd["r_reach"]["mode"] == "warn" and not [e for e in Rd.errors() if e["check"] == "r_reach"]
    p["budgets"]["r_reach"] = "error"
    R, summ = CK.run(copy.deepcopy(p))
    msgs = [m for c, m, *_ in [(e["check"], e["msg"]) for e in R.errors()] if c == "r_reach"]
    assert any("R-REACH-1 start_reach" in m for m in msgs) and summ["r_reach"]["mode"] == "error"
    p["budgets"]["r_reach"] = "warn"
    R2, _ = CK.run(copy.deepcopy(p))
    assert not [e for e in R2.errors() if e["check"] == "r_reach"]
    p["budgets"]["r_reach"] = "off"
    R3, s3 = CK.run(copy.deepcopy(p))
    assert s3["r_reach"] == dict(mode="off")
    # the base fixture has no R-REACH error
    R0, _ = CK.run(copy.deepcopy(EX))
    assert not [e for e in R0.errors() if e["check"] == "r_reach"]


def test_cli_check_fix_census(tmp_path):
    p = _start_plan()
    f = tmp_path / "plan.json"
    f.write_text(json.dumps(p))
    assert RR.main(["check", str(f), "--json", str(tmp_path / "c.json"), "--rules", "1"]) == 1
    out, rep = tmp_path / "fixed.json", tmp_path / "rep.json"
    assert RR.main(["fix", str(f), "--out-plan", str(out), "--report", str(rep)]) == 0
    assert RR.main(["check", str(out), "--rules", "1"]) == 0
    r = json.loads(rep.read_text())
    assert list(r["types"]) == ["mid"] and r["not_fixed"] == []
    out2, rep2 = tmp_path / "fixed2.json", tmp_path / "rep2.json"
    assert RR.main(["fix", str(out), "--out-plan", str(out2), "--report", str(rep2)]) == 0
    assert json.loads(out2.read_text()) == json.loads(out.read_text())                      # idempotent
    assert RR.main(["census", str(f)]) == 0


def test_rule5_default_even_chain_config():
    import re
    import gen_phys
    cfg = gen_phys.reach_even_cfg()
    assert "set ::ot_chain_min_hop_um 405" in cfg and "set ::ot_chain_skip_sited 1" in cfg
    head, stage = gen_phys.REACH_EVEN_CHAINS[0]
    # the landing bin heads and the lane pad stages of the measured kits (names with the backslashes removed)
    assert re.search(head, "u_bound.u_bin_leafdn_i0/q[5]$_DFF_P_") and not re.search(head, "u_bound.u_lpad_x.q[5]$_DFF_P_")
    for n in ("u_bound.u_lpad_leafdn_i0.q[5]$_DFF_P_", "u_bound.u_lpad_i_ahub_am_EN.r[3][35]$_DFF_P_",
              "u_bound.u_pd4_x_hc1_i_3.r[0]$_DFF_P_"):
        assert re.search(stage, n), n
    assert not re.search(stage, "u_bound.u_bin_leafdn_i0/q[5]$_DFF_P_")
    tcl = (HERE / "chain_even.tcl").read_text()
    for frag in ("::ot_chain_min_hop_um", "::ot_chain_skip_sited", "ot_face_flops.txt", "if {$worst <= $ce_min_hop} { return 0 }"):
        assert frag in tcl
    # opt-in by budget (existing kits unchanged); a type with its own chain_even key keeps it
    assert 'P.budgets.get("r_reach_even", False)' in (HERE / "gen_phys.py").read_text()
    assert schema.SCHEMA["properties"]["budgets"]["properties"]["r_reach_even"] == {"type": "boolean"}


def test_reach_homes_is_a_plan_schema_key_and_g0_reads_it():
    """QC-FORMS-2 11-13 (s29 composed plan: schema 'unknown key reach_homes' on a tree without this branch): the plan
    schema and its JSON dump accept type.reach_homes and budgets.r_reach / r_reach_even, refuse a malformed home, and
    G0 runs clean on a plan that carries homes."""
    import check as CK
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["reach_homes"] = [dict(name="w", rect_um=[20.0, 100.0, 180.0, 760.0], buses=["*"],
                                                      note="soft logic of every face bus")]
    p["budgets"]["r_reach"] = "warn"
    p["budgets"]["r_reach_even"] = True
    assert schema.validate(p) == []
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    tp = on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]
    assert "reach_homes" in tp and "r_reach" in on_disk["properties"]["budgets"]["properties"]
    R, summ = CK.run(copy.deepcopy(p))
    assert not [e for e in R.errors() if e["check"] in ("schema", "r_reach")] and summ["r_reach"]["mode"] == "warn"
    bad = copy.deepcopy(p)
    bad["partition_types"]["mid"]["reach_homes"] = [dict(name="w", rect_um=[20.0, 100.0, 180.0], buses=["*"])]
    assert schema.validate(bad)
    bad["partition_types"]["mid"]["reach_homes"] = [dict(name="w", rect_um=[0, 0, 1, 1], buses=["*"], home=1)]
    assert schema.validate(bad)


def test_rule1_relay_piece_of_a_split_is_scored_and_fixed():
    """DIE-KV-100 11-13 (R-CAP split, KV pv _x1/_x2, hub _s/_n): a non-keep piece takes START on cland_rstart_in
    (rx flop u_cland_rstart_rx); rule 1 scores and fixes it exactly like a cland_tstart_in origin."""
    p = _start_plan()
    t = p["partition_types"]["mid"]
    for q in t["clock"]["landing_contract"]["pins"]:
        if q["name"] == "cland_tstart_in":
            q["name"] = "cland_rstart_in"
    row, fs = RR.start_findings(t, "mid")
    assert row["origin_kind"] == "relay_rx" and {"start_reach", "start_writer_reach"} <= {f["kind"] for f in fs}
    # without the start copy the writer side cannot be planned: the type is reported, nothing is half-written
    import pytest
    before = json.dumps(t, sort_keys=True)
    with pytest.raises(ValueError, match="landing_relay_start_copy"):
        RR.fix_start(_P(p), t, "mid")
    assert json.dumps(t, sort_keys=True) == before
    t["landing_relay_start_copy"] = True
    rep = RR.fix_start(_P(p), t, "mid")
    assert rep["changed"] == ["landing_reader_start", "landing_writer_start"]
    assert RR.start_findings(t, "mid")[1] == [] and "origin_rect_um" in t["clock"]["landing_reader_start"]
    # a relay piece with only far rings (no far FSTART pin) is fixed without the copy key, origin left unpinned
    p2 = _start_plan()
    t2 = p2["partition_types"]["mid"]
    pins = t2["clock"]["landing_contract"]["pins"]
    pins[:] = [q for q in pins if not q["name"].startswith("cland_fstart_out_")]
    for q in pins:
        if q["name"] == "cland_tstart_in":
            q["name"] = "cland_rstart_in"
    rep2 = RR.fix_start(_P(p2), t2, "mid")
    assert rep2["changed"] == ["landing_reader_start"] and "origin_rect_um" not in t2["clock"]["landing_reader_start"]
    assert not [f for f in RR.start_findings(t2, "mid")[1] if f["kind"] == "start_reach"]


class _NoPlan:
    """barrier_findings on a bare type dict: no face buses, no core_conns sidecar."""
    path = None


def _xo_tile():
    """HEAD hd_tile (rp20, COORD ruling 11-13 on HEAD-97 F1c): elemB 285.12 um square (side < BARRIER_UM 405) in the N
    of a 708.48 x 1036.8 tile, 13.3 um under the top edge; x_q registers in the W lobe, u_xo/q in the E lobe."""
    t = dict(outline_um=[708.48, 1036.8],
             contents=[dict(inst="u_eB", module="elemB", status="new", origin_um=[216.0, 734.4],
                            outline_um=[285.12, 285.12])])
    rs = {}
    for k in range(64):
        y = 737.632 + 270.0 * k / 63
        rs[f"x_q[{k}]"] = [130.0 + 60.0 * (k % 2), round(y, 3)]
        rs[f"u_xo/q[{k}]"] = [510.0 + 60.0 * (k % 2), round(y, 3)]
    t["relay_sites"] = rs
    t["reach_pairs"] = [{"name": "x_xo", "from": "x_q", "to": "u_xo/q"}]
    return t


def test_rule2_reg_pair_round_a_small_macro_head97():
    """REACH-TOOL-3 (COORD 11-13): rule 2 fires on the ROUTE length round a macro, not on the macro side: hd_tile's
    x_q -> u_xo registers go round the 285-um elemB (its 13.3-um N band is no corridor), > 405 um, so the check asks
    one station per 405 um (+1 cycle each) and the fix plans them."""
    t = _xo_tile()
    assert max(b[2] - b[0] for b in RR.macro_boxes(t).values()) < RR.BARRIER_UM
    row, fs = RR.barrier_findings(_NoPlan(), t, "hd_tile")
    hop = [f for f in fs if f["kind"] == "reg_hop"]
    assert len(hop) == 1 and row["over"] == 1 and row["barriers"] == 0
    f = hop[0]
    w = RR.pair_route(t, t["reach_pairs"][0])
    assert f["value"] == round(w["L"], 1) > RR.REACH_UM and w["L"] > w["man"] + RR.DETOUR_UM
    assert f["stations"] == __import__("math").ceil(w["L"] / RR.REACH_UM) - 1 >= 1
    # without the declared pair, or with the old macro-side trigger only, rule 2 is silent on this type
    assert RR.barrier_findings(_NoPlan(), dict(t, reach_pairs=[]), "hd_tile") == (None, [])
    # the fix: one chain reg:x_q|reg:u_xo/q, every hop (registers -> first station, station -> station, last station
    # -> registers) <= 405 um round the macros, +k cycles; idempotent
    rep = RR.fix_barrier(_NoPlan(), t, "hd_tile")
    assert [a["conn"] for a in rep["added"]] == ["reg:x_q|reg:u_xo/q"]
    e = t["internal_stations"][0]
    assert e["conn"] == "reg:x_q|reg:u_xo/q" and e["bits"] == 64 and len(e["regs_um"]) == rep["added"][0]["stations"]
    import kv_start_corridor_event as KS
    from start_obstacle_path import length
    obs = KS.corridor_obstacles(t, 4.32, 10.8)
    chain = [tuple(e["from_um"])] + [tuple(r) for r in e["regs_um"]] + [tuple(e["to_um"])]
    assert max(length(KS._route(a, b, obs, 708.48, 1036.8)) for a, b in zip(chain, chain[1:])) <= RR.REACH_UM + 1e-6
    assert rep["added"][0]["worst_end_hop_um"] <= RR.REACH_UM
    for p in RR._group_points(t, "x_q"):
        assert length(KS._route(KS._free_point(p, obs), tuple(e["regs_um"][0]), obs, 708.48, 1036.8)) <= RR.REACH_UM + 1e-6
    assert [f for f in RR.barrier_findings(_NoPlan(), t, "hd_tile")[1] if f["kind"] == "reg_hop"] == []
    before = json.dumps(t, sort_keys=True)
    assert RR.fix_barrier(_NoPlan(), t, "hd_tile")["added"] == []
    assert json.dumps(t, sort_keys=True) == before


def test_rule2_reg_pair_scope():
    """only a route that must go round a macro counts; a missing register group is a warning, never a pass."""
    t = _xo_tile()
    t["contents"][0]["origin_um"] = [216.0, 300.0]           # elemB out of the way: a straight 380-440 um route
    row, fs = RR.barrier_findings(_NoPlan(), t, "hd_tile")
    assert [f for f in fs if f["kind"] == "reg_hop"] == []   # no detour: not this rule (R3 / 12.1e own it)
    t = _xo_tile()
    t["reach_pairs"].append({"name": "gone", "from": "x_q_old", "to": "u_xo/q"})
    fs = RR.barrier_findings(_NoPlan(), t, "hd_tile")[1]
    unk = [f for f in fs if f["kind"] == "reg_pair_unknown"]
    assert len(unk) == 1 and unk[0]["warn"] and unk[0]["pair"] == "gone"
    assert RR._group_points(t, "x_q") and not RR._group_points(t, "x")          # prefix ends at '[', '/' or '.'
    assert len(RR._group_points(t, "u_xo")) == 64                              # 'u_xo/q[k]': '/' after the prefix


def test_rule2_home_corridor_round_a_small_macro(monkeypatch):
    """a declared window -> home corridor now fires without a >= 405 um macro when its route goes round one."""
    t = _xo_tile()
    t.pop("reach_pairs")
    t["buses"] = [dict(name="i", dir="in", width=8, face="W")]
    t["reach_homes"] = [dict(name="e", rect_um=[520.0, 900.0, 600.0, 1000.0], buses=["i"])]
    monkeypatch.setattr(RR, "_bus_points", lambda P, tn: {"i": ("W", (0.0, 990.0))})
    fs = RR.barrier_findings(_NoPlan(), t, "hd_tile")[1]
    assert [f["kind"] for f in fs] == ["barrier_hop"] and fs[0]["value"] > RR.REACH_UM
    t["contents"][0]["origin_um"] = [216.0, 300.0]               # no macro in the way: 520 um straight, not rule 2
    assert RR.barrier_findings(_NoPlan(), t, "hd_tile")[1] == []


def test_reach_pairs_is_a_plan_schema_key():
    p = copy.deepcopy(EX)
    p["partition_types"]["mid"]["reach_pairs"] = [{"name": "x_xo", "from": "x_q", "to": "u_xo/q", "bits": 512,
                                                   "note": "HEAD hd_tile x -> xo round elemB"}]
    assert schema.validate(p) == []
    on_disk = json.loads((HERE / "die_plan.schema.json").read_text())
    assert "reach_pairs" in on_disk["properties"]["partition_types"]["additionalProperties"]["properties"]
    bad = copy.deepcopy(p)
    bad["partition_types"]["mid"]["reach_pairs"] = [{"name": "x_xo", "from": "x_q"}]
    assert schema.validate(bad)
    bad["partition_types"]["mid"]["reach_pairs"] = [{"name": "x_xo", "from": "x_q", "to": "y", "via": 1}]
    assert schema.validate(bad)
