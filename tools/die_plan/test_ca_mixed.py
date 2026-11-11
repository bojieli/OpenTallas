"""CA-MIXED-1 (TOK-VERIFY-1 11-11): count-aligned / ring choice per landing (count_aligned.mixed).

Vehicle: a (r0) -> b (r1) on P (count-aligned, start-tree port) and a -> c (r2) on Q (ring).  Checks the mixed
emission, pricing, fail-closed cases, and the two identity anchors: a mixed table whose bind covers every crossing
emits exactly the whole-network count-aligned RTL, and a mixed table with no count-aligned crossing emits exactly
today's all-ring RTL."""
import copy
import json

import pytest

import clock_landing_plan as CP
import count_align_bind as CAB
from clock_landings import Landings, LandingError, ca_port, network_lane_cycles, requirements


def pin(name, direction):
    return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])


def base_vehicle():
    """a.x -> b.y (P, lane L) and a.w -> c.z (Q, lane LQ); a in r0, b in r1, c in r2"""
    p = dict(partitions=[dict(name="a", type="A", origin_um=[0, 0]),
                         dict(name="b", type="B", origin_um=[10, 0]),
                         dict(name="c", type="C", origin_um=[20, 0])],
             partition_types={
                 "A": dict(module="a_mod", outline_um=[10, 10], buses=[pin("fclk_out_x", "out"), pin("fclk_out_w", "out")]),
                 "B": dict(module="b_mod", outline_um=[10, 10], buses=[pin("y", "in"), pin("fclk_in_y", "in"),
                           pin("landing_ready_y", "out"), pin("landing_fault_y", "out")]),
                 "C": dict(module="c_mod", outline_um=[10, 10], buses=[pin("z", "in"), pin("fclk_in_z", "in"),
                           pin("landing_ready_z", "out"), pin("landing_fault_z", "out")])},
             ports=[dict(id="P", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="b", bus="y")),
                    dict(id="Q", width=4, kind="data", src=dict(part="a", bus="w"), dst=dict(part="c", bus="z"))])
    t = dict(regions=[dict(tag="r0", box_um=[0, 0, 10, 10]), dict(tag="r1", box_um=[10, 0, 20, 10]),
                      dict(tag="r2", box_um=[20, 0, 30, 10])],
             ports=[dict(port="P", width=4, src="a", dst="b", src_region="r0", dst_region="r1", lane="L"),
                    dict(port="Q", width=4, src="a", dst="c", src_region="r0", dst_region="r2", lane="LQ")])
    return p, t


CA_P = dict(K=-2, depth=4, sched_lat=2, tree=True)
CA_Q = dict(K=-1, depth=8, sched_lat=3, tree=True)


def ca_block(ports, regions):
    return dict(schema="opentallas.count_align_bind.v1", period_ps=833.0, root="r0", pad=0, root_settle_cycles=40,
                ports=ports, regions=regions)


def add_ca_pins(p, x=True, w=True):
    if x:
        p["partition_types"]["A"]["buses"].append(pin("cland_fstart_out_x", "out"))
        p["partition_types"]["B"]["buses"].append(pin("cland_fstart_in_y", "in"))
    if w:
        p["partition_types"]["A"]["buses"].append(pin("cland_fstart_out_w", "out"))
        p["partition_types"]["C"]["buses"].append(pin("cland_fstart_in_z", "in"))


R0 = dict(parent=None, tree_port=None, edge_fall=False, pad=0)
R1 = dict(parent="r0", tree_port="P", edge_fall=False, pad=0)
R2 = dict(parent="r0", tree_port="Q", edge_fall=False, pad=0)


def mixed_vehicle(ring_cycles=None):
    """P count-aligned, Q a ring (measured count ring_cycles or nominal 3)"""
    p, t = base_vehicle()
    add_ca_pins(p, x=True, w=False)
    t["count_aligned"] = ca_block({"P": dict(CA_P)}, {"r0": dict(R0), "r1": dict(R1)})
    t["count_aligned"]["mixed"] = True
    if ring_cycles is not None:
        t["count_aligned"]["ring_cycles"] = {"Q": ring_cycles}
    return p, t


A_BODY = ("module a_mod (\n input wire clk,\n output wire [4:0] x,\n output wire [4:0] w\n);\n wire rr_parent, rst_n_t0;\n"
          " ot_dp_rrelay u_rrl_0 (.clk(clk), .d(rr_parent), .q(rst_n_t0));\n assign x = 0;\n assign w = 0;\nendmodule\n")
B_BODY = ("module b_mod (\n input wire clk,\n input wire [4:0] y // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
          " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] y_q;\n assign y_q = y;\nendmodule\n")
C_BODY = ("module c_mod (\n input wire clk,\n input wire [4:0] z // whole bundle\n);\n wire rst_n, rst_n_t0, rr_parent, run;\n"
          " ot_dp_rgate u_rrl_0 (.clk(clk), .d(rr_parent), .run(run), .q(rst_n_t0));\n wire [4:0] z_q;\n assign z_q = z;\nendmodule\n")
TOP = ("module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n"
       "        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\n    c_mod c (\n"
       "        .clk(clk_core)\n    );\nendmodule\n")


def emit(p, t):
    c = Landings(p, t)
    return c, dict(A=c.type_rtl("A", A_BODY), B=c.type_rtl("B", B_BODY), C=c.type_rtl("C", C_BODY), top=c.top_rtl(TOP))


def test_mixed_emits_ca_on_bind_crossings_and_ring_on_the_rest():
    p, t = mixed_vehicle()
    c, r = emit(p, t)
    # sender: one forwarded start, beside the count-aligned bus only
    assert "output wire cland_fstart_out_x" in r["A"] and "cland_fstart_out_w" not in r["A"]
    assert "u_cland_origin" in r["A"]                                   # a holds the root origin (CA sender)
    # count-aligned receiver
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-2)) u_cland_y" in r["B"]
    assert ".t_rst_n(cland_fstart_in_y)" in r["B"] and "u_cland_origin" in r["B"]
    # ring receiver: today's ring on its tap reset, no start pin, no count origin
    assert "ot_dp_clk_landing #(.W(5)) u_cland_z" in r["C"] and ".rst_n(cland_reset_z)" in r["C"]
    assert "cland_fstart" not in r["C"] and "u_cland_origin" not in r["C"] and "cland_start" not in r["C"]
    tt = r["top"]
    assert ".cland_fstart_out_x(clock_landing_start_a__x)" in tt and ".cland_fstart_in_y(clock_landing_start_a__x)" in tt
    assert "clock_landing_start_a__w" not in tt and ".fclk_in_z(clock_landing_fwd_a__w)" in tt
    m = c.manifest()
    assert m["lane_added_cycles"] == {"L": 2, "LQ": 3}
    assert m["count_aligned_mixed"]["count_aligned"] == 1 and m["count_aligned_mixed"]["ring"] == 1
    assert {x["port"]: x["landing_form"] for x in m["ports"]} == {"P": "count_aligned", "Q": "ring"}
    assert sorted(c.ca_type) == ["A", "B"]                                # c is not in any count frame
    assert c.land_slots("C") is None and "cland_fstart_in_y" in c.land_slots("B")["buses"]
    req = requirements(p, t)
    assert req["lane_added_cycles"] == {"L": 2, "LQ": 3}
    forms = {x["port"]: (x["form"], "required_src_start_pin" in x) for x in req["ports"]}
    assert forms == {"P": ("count_aligned", True), "Q": ("ring", False)}


def test_mixed_ring_landing_priced_at_measured_count():
    p, t = mixed_vehicle(ring_cycles=2)
    c = Landings(p, t)
    assert c.manifest()["lane_added_cycles"] == {"L": 2, "LQ": 2}
    assert requirements(p, t)["lane_added_cycles"] == {"L": 2, "LQ": 2}
    for bad in (0, -1, True, 2.5, "2"):
        p, t = mixed_vehicle(ring_cycles=bad)
        with pytest.raises(LandingError, match="ring_cycles"):
            Landings(p, t)


def test_mixed_identity_all_ca_equals_whole_network_form():
    p, t = base_vehicle(); add_ca_pins(p)
    t["count_aligned"] = ca_block({"P": dict(CA_P), "Q": dict(CA_Q)}, {"r0": R0, "r1": R1, "r2": R2})
    c0, whole = emit(copy.deepcopy(p), copy.deepcopy(t))
    t["count_aligned"]["mixed"] = True
    c1, mixed = emit(p, t)
    assert whole == mixed                                                 # byte-identical RTL, every type + top
    m0, m1 = c0.manifest(), c1.manifest()
    assert m0["lane_added_cycles"] == m1["lane_added_cycles"] == {"L": 2, "LQ": 3}
    assert c0.ca_type == c1.ca_type and c0.by_type == c1.by_type


def test_mixed_identity_no_ca_equals_all_ring():
    p, t = base_vehicle()
    c0, ring = emit(copy.deepcopy(p), copy.deepcopy(t))
    t["count_aligned"] = ca_block({}, {"r0": R0})
    t["count_aligned"]["mixed"] = True
    c1, mixed = emit(p, t)
    assert ring == mixed
    assert c0.manifest()["lane_added_cycles"] == c1.manifest()["lane_added_cycles"] == {"L": 3, "LQ": 3}
    assert c1.ca_type == {}


def test_whole_network_form_still_requires_every_crossing_in_the_bind():
    p, t = mixed_vehicle()
    del t["count_aligned"]["mixed"]
    p["partition_types"]["A"]["buses"].append(pin("cland_fstart_out_w", "out"))
    p["partition_types"]["C"]["buses"].append(pin("cland_fstart_in_z", "in"))
    with pytest.raises(LandingError, match="no K/DEPTH/latency"):
        Landings(p, t)


def test_mixed_fails_closed():
    # a bind crossing that is not a landed row
    p, t = mixed_vehicle(); t["count_aligned"]["ports"]["R"] = dict(CA_Q)
    with pytest.raises(LandingError, match="not landed rows"):
        Landings(p, t)
    # a count-aligned crossing still needs its start pins
    p, t = mixed_vehicle(); p["partition_types"]["B"]["buses"].pop()
    with pytest.raises(LandingError, match="cland_fstart_in_y"):
        Landings(p, t)
    # a ring landing whose receiver type also has a count-aligned copy -> TYPE_SPLIT, never a silent first copy
    p, t = mixed_vehicle()
    p["partitions"][2]["type"] = "B"
    p["ports"][1]["dst"]["bus"] = "y"
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)
    # legacy input FREG stays legal on a ring landing of a mixed table, illegal on its count-aligned landing
    p, t = mixed_vehicle(); p["partition_types"]["C"]["clock"] = dict(landing_input_freg=["z"])
    c = Landings(p, t)
    assert c.manifest()["lane_added_cycles"] == {"L": 2, "LQ": 4}
    p, t = mixed_vehicle(); p["partition_types"]["B"]["clock"] = dict(landing_input_freg=["y"])
    with pytest.raises(LandingError, match="FREG"):
        Landings(p, t)


def test_mixed_network_prices_per_landing():
    p, _ = base_vehicle()
    p["lanes"] = [dict(id="L", ports=["P"]), dict(id="LQ", ports=["Q"])]
    edges = [dict(id="cland_clk__P", kind="clock", src=dict(part="a", bus="fclk_out_x"), dst=dict(part="b", bus="fclk_in_y")),
             dict(id="cland_clk__Q", kind="clock", src=dict(part="a", bus="fclk_out_w"), dst=dict(part="c", bus="fclk_in_z"))]
    p["clock"] = dict(landing_network=dict(data_cycles_per_crossing="count_aligned", count_aligned_cycles={"P": 4},
                                           count_aligned_mixed=True, ring_cycles={"Q": 2}, edges=edges))
    assert network_lane_cycles(p) == {"L": 4, "LQ": 2}
    del p["clock"]["landing_network"]["ring_cycles"]
    assert network_lane_cycles(p) == {"L": 4, "LQ": 3}
    p["clock"]["landing_network"]["count_aligned_cycles"]["X"] = 4      # a CA latency with no landing edge
    with pytest.raises(LandingError, match="no landing edge"):
        network_lane_cycles(p)
    del p["clock"]["landing_network"]["count_aligned_mixed"]           # whole network: Q must be priced too
    del p["clock"]["landing_network"]["count_aligned_cycles"]["X"]
    with pytest.raises(LandingError, match="no planned latency"):
        network_lane_cycles(p)


def test_compose_helpers_add_start_pins_and_ports_per_landing():
    p, t = mixed_vehicle()
    pports = {x["id"]: x for x in p["ports"]}
    assert CP._ca_out_buses(t, pports) == {("a", "x")}
    ins = {"a": {}, "b": {"y": dict(port="P")}, "c": {"z": dict(port="Q")}}
    outs = {"a": {"x", "w"}, "b": set(), "c": set()}
    assert CP._ca_mask(t, pports, "a", ins, outs) == dict(ca_inputs=[], ca_outputs=["x"])
    assert CP._ca_mask(t, pports, "c", ins, outs) == dict(ca_inputs=[], ca_outputs=[])
    del t["count_aligned"]["mixed"]                                        # whole network: every landed bus
    assert CP._ca_out_buses(t, pports) == {("a", "x"), ("a", "w")}
    assert ca_port(t["count_aligned"], "Q") and not ca_port(None, "P")


def bind_doc():
    return dict(schema="opentallas.count_align_bind.v2", period_ps=833.0, root="r0", pad=0,
                ports={"P": dict(src="r0", dst="r1", **CA_P)},
                regions={"r0": dict(parent=None, tree_port=None, edge_fall=False, pad=0),
                         "r1": dict(parent="r0", tree_port="P", edge_fall=False, pad=0)})


def test_annotate_table_mixed():
    _, t = base_vehicle()
    with pytest.raises(CAB.BindError, match="missing from the bind"):     # whole network (unchanged)
        CAB.annotate_table(t, bind_doc())
    out = CAB.annotate_table(t, bind_doc(), mixed=dict(ring_cycles={"Q": 2}))
    ca = out["count_aligned"]
    assert ca["mixed"] is True and sorted(ca["ports"]) == ["P"] and ca["ring_cycles"] == {"Q": 2}
    assert {r["port"]: r["added_cycles"] for r in out["ports"]} == {"P": 2, "Q": 2}
    with pytest.raises(CAB.BindError, match="count-aligned crossings"):
        CAB.annotate_table(t, bind_doc(), mixed=dict(ring_cycles={"P": 3}))
    b = bind_doc(); b["ports"]["R"] = dict(b["ports"]["P"])
    with pytest.raises(CAB.BindError, match="not table crossings"):
        CAB.annotate_table(t, b, mixed={})


def test_select_file_and_plan_filter(tmp_path):
    sel = dict(landings_detail=[dict(port="P", decision="CA", new_cycles=4), dict(port="Q", decision="LAG", new_cycles=2),
                                dict(port="T", decision="LEAD", new_cycles=3)])
    f = tmp_path / "ca_select.json"; f.write_text(json.dumps(sel))
    s = CAB.load_select(str(f))
    assert s == dict(ca={"P"}, ring={"Q": 2, "T": 3})
    g = tmp_path / "changeset.json"; g.write_text(json.dumps(dict(landings=sel["landings_detail"])))
    assert CAB.load_select(str(g)) == s                                     # a change set's landings list reads the same
    plan = dict(summary={}, regions=[dict(region="r0", start_from=None), dict(region="r2", start_from=dict(port="T"))],
                crossings=[dict(port=x) for x in ("P", "Q", "T")])
    assert [o["port"] for o in CAB.select_plan(plan, s["ca"])["crossings"]] == ["P", "T"]   # tree port T stays CA
    sel["landings_detail"].append(dict(port="U", decision="?", new_cycles=3)); f.write_text(json.dumps(sel))
    with pytest.raises(CAB.BindError, match="CA/LEAD/LAG"):
        CAB.load_select(str(f))
