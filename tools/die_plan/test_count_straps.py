"""MESO-STRAP-1 (OWNER 12.15a COUNT STRAPS): strap form of the count-aligned landings (one design per type, strap_ca_*
pins tied at the parent), per-instance tie values (count_align_bind.strap_ties) and the tie-VALUE audit (straps.py, COORD
addition: a wrong / missing tie is a G0 ERROR, mutant = one flipped bit)."""
import copy
import re
import pytest
import count_align_bind as CAB
import straps as STR
from clock_landings import Landings, LandingError
from test_clock_landings import ca_vehicle, A_BODY, B_BODY


def pin(name, direction, width=1):
    return dict(name=name, dir=direction, width=width, face="E", window_um=[1, 2], layers=["M8"])


def strap_vehicle(k_b=-2, k_c=-1, efall_c=True, pad_c=1, strap_form=True):
    """a (root, r0) -> b (r1, K k_b) and a -> c (r2, K k_c, EDGE_FALL/PAD differ): b and c are copies of type B"""
    p, t = ca_vehicle(k=k_b)
    p["partitions"].append(dict(name="c", type="B", origin_um=[20, 0]))
    p["ports"].append(dict(id="Q", width=4, kind="data", src=dict(part="a", bus="x"), dst=dict(part="c", bus="y")))
    t["regions"].append(dict(tag="r2", box_um=[20, 0, 30, 10]))
    t["ports"].append(dict(port="Q", width=4, src="a", dst="c", src_region="r0", dst_region="r2", lane="L2"))
    ca = t["count_aligned"]
    ca["ports"]["Q"] = dict(K=k_c, depth=4, sched_lat=3, tree=True)
    ca["regions"]["r2"] = dict(parent="r0", tree_port="Q", edge_fall=efall_c, pad=pad_c)
    if strap_form:
        ca["strap_form"] = True
        p["partition_types"]["B"]["buses"] += [pin("strap_ca_k_y", "in", 6), pin("strap_ca_pad", "in", 1),
                                               pin("strap_ca_efall", "in", 1)]
    return p, t


TOP = ("module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n"
       "        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\n    b_mod c (\n"
       "        .clk(clk_core)\n    );\nendmodule\n")


def test_strap_ties_values_widths_and_variants():
    p, t = strap_vehicle()
    st = CAB.strap_ties(t["count_aligned"], p)
    b = st["types"]["B"]
    assert b["straps"] == {"strap_ca_k_y": 6, "strap_ca_pad": 1, "strap_ca_efall": 1}
    assert b["buses"] == {"y": dict(depth=4, kw=6)} and b["origin"]["form"] == "strap" and b["variants"] == 2
    assert st["instances"]["b"]["values"] == {"strap_ca_k_y": 62, "strap_ca_pad": 0, "strap_ca_efall": 0}   # -2 mod 64
    assert st["instances"]["c"]["values"] == {"strap_ca_k_y": 63, "strap_ca_pad": 1, "strap_ca_efall": 1}
    assert st["types"]["A"]["origin"]["form"] == "root" and st["types"]["A"]["straps"] == {}
    assert CAB.strap_kw(4) == 6 and CAB.strap_kw(8) == 7 and CAB.strap_bits(-26, 6) == 38


def test_parameter_form_still_type_splits_and_strap_form_does_not():
    p, t = strap_vehicle(strap_form=False)
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)
    p, t = strap_vehicle()
    c = Landings(p, t)                                  # one type B for both K / origin signatures
    bb = c.type_rtl("B", B_BODY)
    assert "ot_dp_clk_landing_cas #(.W(5), .DEPTH(4)) u_cland_y" in bb and ".strap_k(strap_ca_k_y)" in bb
    assert "input wire [5:0] strap_ca_k_y" in bb and "input wire [0:0] strap_ca_pad" in bb
    assert "input wire strap_ca_efall" in bb and ".K(" not in bb
    assert ("ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin (" in bb and ".p_start(cland_fstart_in_y)" in bb
            and ".strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start));" in bb)
    assert c.rows[0]["module"] == "ot_dp_clk_landing_cas"
    c.type_rtl("A", A_BODY)
    tt = c.top_rtl(TOP)
    assert ".strap_ca_k_y(6'b111110)" in tt and ".strap_ca_k_y(6'b111111)" in tt
    assert tt.count(".strap_ca_pad(1'b0)") == 1 and tt.count(".strap_ca_pad(1'b1)") == 1
    assert c.manifest()["count_straps"]["types"]["B"]["variants"] == 2
    assert c.manifest()["count_straps"]["summary"]["lec_variants"] == 3          # + type A (root, no straps)


def test_strap_pins_must_be_declared_with_width():
    p, t = strap_vehicle()
    p["partition_types"]["B"]["buses"] = [b for b in p["partition_types"]["B"]["buses"] if b["name"] != "strap_ca_pad"]
    with pytest.raises(LandingError, match="strap_ca_pad"):
        Landings(p, t)


def test_tie_value_audit_passes_and_catches_one_flipped_bit():
    p, t = strap_vehicle()
    c = Landings(p, t); c.type_rtl("A", A_BODY); c.type_rtl("B", B_BODY)
    tt = c.top_rtl(TOP)
    exp = c.strap_expected()
    assert STR.audit_count_strap_values(tt, exp)["verdict"] == "PASS"
    # MUTANT: flip one tie bit of c's K strap (6'b111111 -> 6'b111101): G0 ERROR naming the pin and the bind value
    bad = tt.replace(".strap_ca_k_y(6'b111111)", ".strap_ca_k_y(6'b111101)")
    assert bad != tt
    r = STR.audit_count_strap_values(bad, exp)
    assert r["verdict"] == "FAIL" and r["severity"] == "G0 ERROR" and "c.strap_ca_k_y" in r["reason"]
    # missing tie, non-literal and wrong width are G0 ERRORs as well
    gone = tt.replace("        .strap_ca_efall(1'b1),\n", "")
    assert gone != tt
    r = STR.audit_count_strap_values(gone, exp)
    assert r["verdict"] == "FAIL" and "missing tie" in r["reason"]
    r = STR.audit_count_strap_values(tt.replace(".strap_ca_pad(1'b1)", ".strap_ca_pad(some_net)"), exp)
    assert r["verdict"] == "FAIL" and "not a literal" in r["reason"]
    r = STR.audit_count_strap_values(tt.replace(".strap_ca_k_y(6'b111110)", ".strap_ca_k_y(5'b11110)"), exp)
    assert r["verdict"] == "FAIL" and "width" in r["reason"]
    # a strap_ca literal the bind does not know is refused too
    r = STR.audit_count_strap_values(tt, {k: v for k, v in exp.items() if k != "c"})
    assert r["verdict"] == "FAIL" and "no bind value" in r["reason"]
    # the netlist tie check takes its values from the bind
    tcl = STR.tie_check_tcl(STR.count_strap_rows(exp))
    assert "ot_strap_tie_check {c} {strap_ca_k_y[1]} 1" in tcl and "ot_strap_tie_check {b} {strap_ca_k_y[0]} 0" in tcl


def nl_vehicle(exp, flip=None, share=False, literal=None):
    """gate-level die netlist: one TIEHI/TIELO per strap bit (die_constant_cells.tcl, max_fanout 1)"""
    cells, insts, k = [], [], 0
    for inst, ports in sorted(exp.items()):
        conns = []
        for port, (w, v) in sorted(ports.items()):
            nets = []
            for b in range(w - 1, -1, -1):
                x = (v >> b) & 1
                if flip == (inst, port, b):
                    x ^= 1
                if literal == (inst, port, b):
                    nets.append("1'b1"); continue
                n = f"tie_n{k}"; k += 1
                if share and nets:
                    n = nets[-1]
                else:
                    cells.append(f"  {'TIEHIx1_ASAP7_75t_R' if x else 'TIELOx1_ASAP7_75t_R'} tie_{k} (.{'H' if x else 'L'}({n}));")
                nets.append(n)
            conns.append(f"    .{port}({{{', '.join(nets)}}})" if w > 1 else f"    .{port}({nets[0]})")
        insts.append(f"  b_mod {inst} (\n    .clk(clk),\n" + ",\n".join(conns) + "\n  );")
    return "module die (clk);\n  input clk;\n" + "\n".join(cells) + "\n" + "\n".join(insts) + "\nendmodule\n"


def test_netlist_tie_value_audit_and_mutants():
    p, t = strap_vehicle()
    exp = Landings(p, t).strap_expected()
    assert STR.audit_netlist_strap_values(nl_vehicle(exp), exp)["verdict"] == "PASS"
    r = STR.audit_netlist_strap_values(nl_vehicle(exp, flip=("c", "strap_ca_k_y", 1)), exp)   # MUTANT: one bit flipped
    assert r["verdict"] == "FAIL" and r["severity"] == "G0 ERROR" and "c.strap_ca_k_y[1]" in r["reason"]
    r = STR.audit_netlist_strap_values(nl_vehicle(exp, share=True), exp)
    assert r["verdict"] == "FAIL" and "shared" in r["reason"]
    r = STR.audit_netlist_strap_values(nl_vehicle(exp, literal=("b", "strap_ca_k_y", 0)), exp)
    assert r["verdict"] == "FAIL" and "literal" in r["reason"]
    gone = nl_vehicle(exp).replace(",\n    .strap_ca_efall(", ",\n    .xx_efall(")
    r = STR.audit_netlist_strap_values(gone, exp)
    assert r["verdict"] == "FAIL" and "missing tie" in r["reason"]


def test_root_and_child_copies_share_one_strap_type():
    """a root copy and a child copy of one type: strap_ca_root selects the root counter (u_cland_root)"""
    p, t = ca_vehicle(k=-2)
    p["partitions"][0]["type"] = "B"
    tb = p["partition_types"]["B"]
    tb["buses"] += [pin("fclk_out_x", "out"), pin("cland_fstart_out_x", "out"), pin("strap_ca_k_y", "in", 7),
                    pin("strap_ca_pad", "in", 1), pin("strap_ca_efall", "in", 1), pin("strap_ca_root", "in", 1)]
    p["ports"].append(dict(id="R", width=4, kind="data", src=dict(part="b", bus="x"), dst=dict(part="a", bus="y")))
    t["ports"].append(dict(port="R", width=4, src="b", dst="a", src_region="r1", dst_region="r0", lane="L3"))
    t["count_aligned"]["ports"]["R"] = dict(K=3, depth=8, sched_lat=4, tree=False)
    t["count_aligned"]["strap_form"] = True
    c = Landings(p, t)
    st = c.strap
    assert st["types"]["B"]["straps"] == {"strap_ca_k_y": 7, "strap_ca_pad": 1, "strap_ca_efall": 1, "strap_ca_root": 1}
    assert st["instances"]["a"]["values"]["strap_ca_root"] == 1 and st["instances"]["b"]["values"]["strap_ca_root"] == 0
    assert st["instances"]["a"]["values"]["strap_ca_k_y"] == 3 and st["instances"]["b"]["values"]["strap_ca_k_y"] == 126
    body = B_BODY.replace("input wire [4:0] y // whole bundle", "input wire [4:0] y, // whole bundle\n output wire [4:0] x")
    bb = c.type_rtl("B", body)
    assert "ot_dp_clk_landing_cas #(.W(5), .DEPTH(8))" in bb and "input wire strap_ca_root" in bb
    assert "ot_dp_landing_root #(.SETTLE(40)) u_cland_root" in bb
    assert "assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;" in bb


def test_relay_role_mix_stays_a_type_split():
    from test_clock_landings import ca_relay_vehicle
    p, t = ca_relay_vehicle()
    # c (relay) and a second copy of C as a region origin: different pin list (cland_rstart_in) -> residual split
    p["partitions"].append(dict(name="d", type="C", origin_um=[20, 0]))
    p["ports"].append(dict(id="S", width=4, kind="data", src=dict(part="a", bus="w"), dst=dict(part="d", bus="z")))
    t["regions"].append(dict(tag="r2", box_um=[20, 0, 30, 10]))
    t["ports"].append(dict(port="S", width=4, src="a", dst="d", src_region="r0", dst_region="r2", lane="LS"))
    ca = t["count_aligned"]
    ca["ports"]["S"] = dict(K=-2, depth=4, sched_lat=2, tree=True)
    ca["regions"]["r2"] = dict(parent="r0", tree_port="S", edge_fall=False, pad=0, origin_part="d")
    ca["parts"]["d"] = dict(region="r2", role="origin", src=None, stages=0)
    ca["strap_form"] = True
    st = CAB.strap_ties(ca, p)
    assert st["types"]["C"]["residual_split"] and st["summary"]["residual_split_types"] == 1
    for tn, info in st["types"].items():
        p["partition_types"][tn]["buses"] += [pin(sp, "in", w) for sp, w in info["straps"].items()]
    with pytest.raises(LandingError, match="TYPE_SPLIT required \\(relay rx/tx pins differ"):
        Landings(p, t)


def test_variant_reference_wrapper_is_the_parameter_form_of_one_copy():
    p, t = strap_vehicle(strap_form=False)
    c = Landings(p, t, ca_variants=True)
    bc = c.type_rtl("B", B_BODY, inst="c")
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(4), .K(-1)) u_cland_y" in bc
    assert "ot_dp_landing_origin #(.PAD(1), .EDGE_FALL(1)) u_cland_origin" in bc
    bb = c.type_rtl("B", B_BODY, inst="b", depth={"y": 8})
    assert "ot_dp_clk_landing_ca #(.W(5), .DEPTH(8), .K(-2)) u_cland_y" in bb


def test_plan_declares_strap_pins_and_kit_sdc_false_path():
    import clock_landing_plan as CP
    p, t = strap_vehicle()
    raw = copy.deepcopy(p)
    for b in list(raw["partition_types"]["B"]["buses"]):
        if b["name"].startswith("strap_ca_"):
            raw["partition_types"]["B"]["buses"].remove(b)
    st = CP._ca_strap_pins(raw, t)
    tb = raw["partition_types"]["B"]
    assert [s["name"] for s in tb["count_straps"]] == ["strap_ca_efall", "strap_ca_k_y", "strap_ca_pad"]
    k = next(b for b in tb["buses"] if b["name"] == "strap_ca_k_y")
    assert k["width"] == 6 and k["dir"] == "in" and abs(k["window_um"][1] - k["window_um"][0] - 6 * .432) < 1e-6
    assert st["summary"]["lec_variants"] == 3
