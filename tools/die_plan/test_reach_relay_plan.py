"""R-REACH-1 die-level relays: START provider relay stages (count-aligned PAD) and monitor-bundle relays."""
import copy
from types import SimpleNamespace

import pytest

import landing_contract as LC
import reach_relay_plan as RP
import start_provider_plan as SP


def _pv():
    """root b0 (clock node at 0,0) -> child b1 460 um east on a straight trunk; b1 drives partition q's START input"""
    def node(i, x, parent, root):
        return dict(id=i, region=f"st:{i}", rect_um=[x - 5.4, -1.3, x, 1.3], clock_node=i, clock_node_xy_um=[x + 0.5, 0.0],
                    clock_port=f"t_st_{i}__clk", module="ot_dp_landing_origin", flops=3, parent=parent, root=root)
    a, b = node("b0", 0.0, None, True), node("b1", 460.0, "st:b0", False)
    e = dict(max_hop_um=405, source_registered=True, capture_registered=True)
    return dict(form="emitted_start_stage_rows", nodes=[a, b],
                edges=[dict(e, src_stage="b0", dst_stage="b1", src_rect_um=a["rect_um"], dst_rect_um=b["rect_um"]),
                       dict(e, src_stage="b1", part="q", pin="cland_tstart_in", net="pst_b1", src_rect_um=b["rect_um"],
                            dst_rect_um=[470.0, 0.0, 470.0, 0.0])])


def _P():
    pin = dict(name="cland_tstart_in", xy_um=[470.0, 0.0])
    return SimpleNamespace(ptype=lambda n: dict(clock=dict(landing_contract=dict(pins=[pin]))), to_die=lambda n, q: q,
                           clock=dict(landing_network=dict(start_tree=dict(uses=[dict(part="q", pin="cland_tstart_in",
                                                                                     net="pst_b1")]))))


def test_start_relay_inserted_on_trunk_and_padded():
    pv = _pv()
    P = _P()
    assert SP.check(P, pv)["errors"]                       # 460 um parent edge fails the 405 gate
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    rows = RP.start_relays(P, pv, regions)
    r = SP.check(P, pv)
    assert not r["errors"] and r["relays"] == 1 and r["max_hop_um"] <= RP.SITE_MAX
    assert regions["st:b1"]["pad"] == 1 and rows[0]["relays"] == 1        # the bind prices the boot cycle (K)
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rl["clock_node_xy_um"][1] == 0.0 and 0 < rl["clock_node_xy_um"][0] < 460.5   # on the b0 -> b1 trunk
    st = RP.depth_stats(pv)
    assert st["max_depth"] == 3 and st["max_relays_on_path"] == 1
    again = copy.deepcopy(pv)                              # a second pass is a no-op (idempotent)
    assert RP.start_relays(P, again, regions) == [] and again == pv and regions["st:b1"]["pad"] == 1


def test_short_edges_untouched():
    pv = _pv()
    for n in pv["nodes"][1:]:
        n["rect_um"] = [200 - 5.4, -1.3, 200, 1.3]
        n["clock_node_xy_um"] = [200.5, 0.0]
    pv["edges"][0]["dst_rect_um"] = pv["nodes"][1]["rect_um"]
    before = copy.deepcopy(pv)
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    assert RP.start_relays(_P(), pv, regions) == [] and pv == before and regions["st:b1"]["pad"] == 0


def _lc_plan(relays=None, group=True, clk_relay_xy=None):
    pins = {"s": [dict(name="cland_up_ready", dir="out", kind="ctl", epoch=False, layer="M4", xy_um=[0.0, 0.0]),
                  dict(name="fclk_out_cland_up", dir="out", kind="clock", epoch=False, layer="M4", xy_um=[0.0, 2.0])],
            "d": [dict(name="cland_dn_ready_0", dir="in", kind="ctl", epoch=False, layer="M4", xy_um=[0.0, 460.0]),
                  dict(name="fclk_in_cland_dn_0", dir="in", kind="clock", epoch=False, layer="M4", xy_um=[0.0, 462.0])]}
    types = {tn: dict(outline_um=[10.0, 500.0], clock=dict(landing_contract=dict(pins=ps),
                                                            edge_clocks=[dict(port="fclk_in_cland_dn_0")]))
             for tn, ps in pins.items()}
    e = dict(width=1, epoch=False, max_hop_um=405)
    edges = [dict(e, id="cland_mon_ready__s", src=dict(part="s", bus="cland_up_ready"), dst=dict(part="d", bus="cland_dn_ready_0"),
                  kind="ctl", source_registered=True, capture_registered=True),
             dict(e, id="cland_mon_clk__s", src=dict(part="s", bus="fclk_out_cland_up"), dst=dict(part="d", bus="fclk_in_cland_dn_0"),
                  kind="clock", source_registered=False, capture_registered=False)]
    if relays is not None:
        for ed in edges:
            xy = clk_relay_xy if (clk_relay_xy and ed["kind"] == "clock") else relays
            ed["relays"] = [dict(id="rl_s_1", kind="fwd_clock_relay", xy_um=list(xy))]
            if group:
                ed["relay_group"] = "cland_mon__s"
    net = dict(edges=edges, root_observer=dict(part="s", module="m", fault_port="f", ready_port="r"))
    return SimpleNamespace(types=types, parts={"s": dict(type="s"), "d": dict(type="d")}, layers={"M4": {}},
                           clock=dict(landing_network=net), to_die=lambda pn, xy: (xy[0], xy[1]))


def test_monitor_bundle_relay_segments_checked():
    assert any("exceeds405" in e for e in LC.check(_lc_plan())["errors"])
    r = LC.check(_lc_plan(relays=[0.0, 231.0]))
    assert not r["errors"] and r["max_hop_um"] <= 405


@pytest.mark.parametrize("bad", ["no_group", "split_sites", "far_site"])
def test_monitor_relay_mutants_fail(bad):
    P = {"no_group": lambda: _lc_plan(relays=[0.0, 231.0], group=False),
         "split_sites": lambda: _lc_plan(relays=[0.0, 231.0], clk_relay_xy=[0.0, 240.0]),
         "far_site": lambda: _lc_plan(relays=[0.0, 30.0])}[bad]()
    assert LC.check(P)["errors"]


def test_monitor_relay_second_pass_is_noop():
    P = _lc_plan(relays=[0.0, 231.0])
    P.ptype = lambda pn: P.types[P.parts[pn]["type"]]
    before = copy.deepcopy(P.clock)
    assert RP.mon_relays(P, P.clock["landing_network"], [], RP.Grid()) == [] and P.clock == before


def _trunks(region_b0="R0", detour=False, extra_other=False):
    """built clock: b0/b1 sit on built nodes c0 (2, 3) / c1 (455, 3); the built leg c0 -> c1 runs y = 3 in region R0"""
    legs = [dict(a="c0", a_xy_um=[2.0, 3.0], b="c1", b_xy_um=[455.0, 3.0], net="n0", region="R0", region_kind="local",
                 **({"detour_um": 40.0} if detour else {}))]
    if extra_other:     # a nearer leg of another region (y = 0.5) must be rejected
        legs.append(dict(a="x0", a_xy_um=[0.0, 0.5], b="x1", b_xy_um=[460.0, 0.5], net="nx", region="R9", region_kind="feed"))
    return dict(schema="opentallas.qc_trunk_nodes.v1", clock_build="t", plan_sha256="p", legs=legs,
                stages={"b0": dict(clock_node="c0", clock_net="n0", clock_node_xy_um=[2.0, 3.0], region=region_b0,
                                   region_kind="local", old_clock_node="b0"),
                        "b1": dict(clock_node="c1", clock_net="n1", clock_node_xy_um=[455.0, 3.0], region="R0",
                                   region_kind="local", old_clock_node="b1")})


def test_built_trunk_rewrites_provider_and_seats_relays_on_built_legs_of_the_source_region():
    pv, P = _pv(), _P()
    st, segs, meta = RP.load_trunks(_trunks(extra_other=True))
    rw = RP.rewrite_provider(pv, st)
    assert rw["nodes"] == 2 and pv["nodes"][0]["clock_node"] == "c0" and pv["nodes"][0]["clock_region"] == "R0"
    regions = {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}
    rej = set()
    rows = RP.start_relays(P, pv, regions, (segs, meta, RP.by_region(segs, meta)), rej)
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rows[0]["relays"] == 1 and rl["clock_node_xy_um"][1] == 3.0 and rl["site_net"] == "n0"
    assert rl["clock_node"] == "c0" and rl["clock_region"] == "R0" and not SP.check(P, pv)["errors"]
    assert not rej                              # placed on R0 (the nearer R9 leg is never offered)


def test_built_trunk_guards():
    pv = _pv()
    st, *_ = RP.load_trunks(_trunks())
    del st["b1"]
    with pytest.raises(RP.RelayError):          # a provider node without a built node: no fallback
        RP.rewrite_provider(pv, st)
    with pytest.raises(RP.RelayError):
        RP.load_trunks(dict(schema="other", legs=[], stages={}))
    pv = _pv()
    st, segs, meta = RP.load_trunks(_trunks(detour=True))
    assert segs == []                           # detoured legs carry no relay
    RP.rewrite_provider(pv, st)
    with pytest.raises(RP.RelayError):
        RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), set())
    pv = _pv()                                  # only the FED stage's region has a leg: destination-side relay
    st, segs, meta = RP.load_trunks(_trunks(region_b0="R5"))
    RP.rewrite_provider(pv, st)
    RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), set())
    rl = [n for n in pv["nodes"] if n.get("kind") == "relay"][0]
    assert rl["clock_side"] == "dst" and rl["clock_node"] == "c1" and rl["clock_region"] == "R0" and rl["flops"] == 4
    pv = _pv()                                  # a third region only: rejected, no site
    tk = _trunks(region_b0="R5")
    tk["stages"]["b1"]["region"] = "R6"
    st, segs, meta = RP.load_trunks(tk)
    RP.rewrite_provider(pv, st)
    rej = set()
    with pytest.raises(RP.RelayError):
        RP.start_relays(_P(), pv, {"st:b0": dict(pad=0), "st:b1": dict(pad=0)}, (segs, meta, RP.by_region(segs, meta)), rej)
    assert rej and all(r[2] == "R0" for r in rej)


# ---- existing-clock form (S81 J5 die_start_stages: no START provider) + die reset relays (S81-DIE-R4 11-20) ----------
def _mon_plan(dy=900.0, clock=True):
    """a status bundle s -> d dy um apart (straight up x = 0); with clock: a seam bundle (fwd_clock_relay)"""
    P = _lc_plan()
    for t in P.types.values():
        t["outline_um"] = [10.0, 2000.0]
    for tn, y in (("d", dy),):
        for p in P.types[tn]["clock"]["landing_contract"]["pins"]:
            p["xy_um"] = [0.0, y + (2.0 if p["kind"] == "clock" else 0.0)]
    if not clock:
        P.clock["landing_network"]["edges"] = [e for e in P.clock["landing_network"]["edges"] if e["kind"] != "clock"]
        for t in P.types.values():
            lc = t["clock"]["landing_contract"]
            lc["pins"] = [p for p in lc["pins"] if p["kind"] != "clock"]
            t["clock"]["edge_clocks"] = []
    P.ptype = lambda pn: P.types[P.parts[pn]["type"]]
    P.W, P.H, P.budgets = 2000.0, 2000.0, dict(tap_pitch_um=200.0)
    P.clock["spine"] = dict(root_um=[1000.0, 1000.0])
    return P


@pytest.mark.parametrize("clock", [True, False])
def test_monitor_relays_without_provider_keep_segments_and_avoid_hard_boxes(clock):
    P = _mon_plan(clock=clock)
    box = (-50.0, 280.0, 50.0, 340.0)            # a hard core right on the straight path
    taken = RP.Blocked([box])
    rows = RP.mon_relays(P, P.clock["landing_network"], None, taken)
    assert len(rows) == 1 and rows[0]["max_segment_um"] <= RP.SITE_MAX
    assert rows[0]["form"] == ("fwd_clock_relay" if clock else "die_clock_relay")
    for e in P.clock["landing_network"]["edges"]:
        for r in e["relays"]:
            x, y = r["xy_um"]
            assert not (box[0] < x < box[2] and box[1] < y < box[3])
            if not clock:                        # die clock-tree node: the H-tree leaf over the site
                assert r["clock_node"].startswith("htree_") and len(r["clock_node_xy_um"]) == 2
                assert RP.htree_leaf(P, (x, y))[0] == r["clock_node"]
    r = LC.check(P)
    assert not r["errors"] and r["max_hop_um"] <= RP.SITE_MAX + 2.0
    before = copy.deepcopy(P.clock)              # second pass: no-op
    assert RP.mon_relays(P, P.clock["landing_network"], None, RP.Blocked([])) == [] and P.clock == before


def test_monitor_relays_without_provider_add_a_relay_when_targets_are_blocked():
    P = _mon_plan(dy=780.0)
    k0 = max(1, math.ceil(780.0 / RP.TRUNK) - 1)
    walls = [(-200.0, 780.0 * i / (k0 + 1) - 60.0, 200.0, 780.0 * i / (k0 + 1) + 60.0) for i in range(1, k0 + 1)]
    rows = RP.mon_relays(P, P.clock["landing_network"], None, RP.Blocked(walls))
    assert rows and rows[0]["max_segment_um"] <= RP.SITE_MAX


def test_htree_leaf_matches_spine_model():
    import spine
    P = _mon_plan()
    for pt in [(10.0, 20.0), (1500.0, 300.0), (999.0, 1999.0)]:
        name, xy = RP.htree_leaf(P, pt)
        L, legs = spine.htree_path([1000.0, 1000.0], [2000.0, 2000.0], pt, 200.0)
        assert abs(legs[-1] - (abs(pt[0] - xy[0]) + abs(pt[1] - xy[1]))) < 1e-6 and name.startswith("htree_")


import json  # noqa: E402
import math  # noqa: E402
from pathlib import Path  # noqa: E402

import reset_tree as RT  # noqa: E402
import schema  # noqa: E402

TINY = json.loads((Path(__file__).resolve().parent / "examples" / "tiny_plan.json").read_text())


def _tiny(gap=500.0):
    """the tiny die with a gap before its last partition pb: pm2 -> pb is a wavefront hop over the 300-um reset cap"""
    raw = copy.deepcopy(TINY)
    raw.setdefault("reset", {}).update(release="wavefront")
    raw["die"]["outline_um"][0] += gap
    for p in raw["partitions"]:
        if p["name"] == "pb":
            p["origin_um"][0] += gap
    assert schema.validate(raw) == []
    return raw


def test_die_reset_relays_close_long_wavefront_hops_and_price_release():
    raw = _tiny()
    P = schema.Plan(raw)
    W0 = RT.wf_plan(P)
    assert W0["long_hops"] and any("reset wavefront" in e for e in RT.check(P)[0])
    decl, rows = RT.plan_die_relays(P)
    assert decl and all(r["max_segment_um"] <= RT.hop_um(P) - RT.MARGIN_UM + 1e-6 for r in rows)
    raw["reset"]["die_relays"] = decl
    assert schema.validate(raw) == []
    P1 = schema.Plan(raw)
    W1 = RT.wf_plan(P1)
    assert W1["long_hops"] == [] and W1["unreachable"] == [] and W1["max_die_hop_um"] <= RT.hop_um(P1)
    assert not [e for e in RT.check(P1)[0] if "reset wavefront" in e]
    for p, r in W1["parts"].items():           # every relay is one more release cycle for the child and its subtree
        if r["parent"] is None:
            continue
        n = len(decl.get(p, {}).get("sites_um", []))
        assert r.get("die_relays", 0) == n
        assert r["release"] == W1["parts"][r["parent"]]["release"] + n + (W0["parts"][p]["release"] -
                                                                          W0["parts"][r["parent"]]["release"])
    assert all(W1["parts"][p]["release"] == W0["parts"][p]["release"] + len(decl[p]["sites_um"]) for p in decl)
    assert W1["max_release"] >= W0["max_release"] and W1["die_relays"]["relays"] == sum(r["relays"] for r in rows)
    # the die top carries the relays (clocked by the die clock), START rides the same relays
    lines, arst, _outs = RT.wf_die_rtl(P1, clk=lambda p: "clk_core")
    for p in decl:
        n = len(decl[p]["sites_um"])
        assert arst[p] == f"rstw_rl_{p}_{n}" and sum(f"u_rstw_rl_{p}_" in ln for ln in lines) == n
    assert all("(.clk(clk_core)" in ln for ln in lines if "ot_dp_rrelay" in ln)


def test_die_reset_relays_stale_declaration_and_schema():
    raw = _tiny()
    decl, _rows = RT.plan_die_relays(schema.Plan(raw))
    p = sorted(decl)[0]
    raw["reset"]["die_relays"] = {p: dict(decl[p], site=decl[p]["site"] + 7)}
    errs = RT.check(schema.Plan(raw))[0]
    assert any("reset.die_relays" in e and "not the solved" in e for e in errs)
    raw["reset"]["die_relays"] = {p: dict(decl[p], sites_um=[])}
    assert schema.validate(raw)                  # at least one site
    assert len(decl[p]["sites_um"]) > 1
    raw["reset"]["die_relays"] = {p: dict(decl[p], sites_um=[decl[p]["sites_um"][0]])}   # one relay too few: still long
    assert RT.wf_plan(schema.Plan(raw))["long_hops"]


def test_die_reset_relays_simulated_release_matches_offsets():
    """the generated tiny die with die reset relays: every tap releases exactly at W.parts[p].release"""
    import shutil
    import subprocess
    import tempfile
    import gen_rtl
    if not shutil.which("iverilog"):
        pytest.skip("iverilog")
    HERE = Path(__file__).resolve().parent
    raw = _tiny()
    decl, _rows = RT.plan_die_relays(schema.Plan(raw))
    raw["reset"]["die_relays"] = decl
    P = schema.Plan(raw)
    W = RT.wf_plan(P)
    nets, want = [], []
    for part, p in P.parts.items():
        for i in range(len(RT.for_type(P, p["type"])["taps"])):
            nets.append(f"u_top.{gen_rtl.sv_id(part)}.rst_n_t{i}")
            want.append(W["parts"][part]["release"])
    mx = W["max_release"]
    with tempfile.TemporaryDirectory() as d:
        files = [str(f) for f in gen_rtl.write_rtl(copy.deepcopy(raw), d, rtl_root=str(HERE.parent.parent))]
        assert "u_rstw_rl_" in (Path(d) / "tiny_top.sv").read_text()
        chk = "\n".join(f"        if ({n} === 1'b1 && rel[{k}] < 0) rel[{k}] = cyc + 1;" for k, n in enumerate(nets))
        tb = Path(d) / "tb.sv"
        tb.write_text(f"""`timescale 1ns/1ps
module tb;
    reg clk = 0, rst_n = 0;
    always #0.5 clk = ~clk;
    reg [31:0] din = 0;
    wire [31:0] dout;
    tiny_top u_top (.clk(clk), .rst_n(rst_n), .din(din), .dout(dout));
    integer cyc = -{mx + 20}, k;
    integer rel [0:{len(nets) - 1}];
    initial for (k = 0; k < {len(nets)}; k = k + 1) rel[k] = -1;
    always @(posedge clk) begin
        #0.1;
{chk}
        if (cyc == -1) rst_n = 1;
        cyc = cyc + 1;
    end
    initial begin
        repeat ({2 * mx + 40}) @(posedge clk);
        for (k = 0; k < {len(nets)}; k = k + 1) $display("REL %0d %0d", k, rel[k]);
        $finish;
    end
endmodule
""")
        exe = str(Path(d) / "a.out")
        subprocess.run(["iverilog", "-g2012", "-o", exe, str(tb)] + files + [str(HERE / "examples" / "tiny_leaves.sv")],
                       check=True)
        out = subprocess.run(["vvp", "-n", exe], capture_output=True, text=True).stdout
        import re
        assert [int(x) for x in re.findall(r"REL \d+ (-?\d+)", out)] == want, out[-1500:]
