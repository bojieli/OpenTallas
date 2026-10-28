"""DIE-HEAD-11 compose start-pin slice (START-TREE --start-tree clock binds): a child region's start arrives on ONE
dedicated pin cland_tstart_in of its origin partition, launched from the parent origin's cland_tstart_out or from a
die-level start stage (start_stage_emit.py rs_<region> / pst_<region> nets = die-top ports).  KV DIE-KV-13 crash
KeyError 'start:hg_EN_1->hg_EN_0' (strap_ties looked the start port up as a plan crossing)."""
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError, start_pins
from test_clock_landings import A_BODY, B_BODY
from test_count_straps import strap_vehicle, TOP, pin


def start_vehicle(stage=False, strap=True):
    """strap_vehicle (a root r0 -> b r1, a -> c r2, b/c copies of type B) with the tree on START PORTS: r0 -> r1
    direct; r0 -> r2 direct, or (stage=True) r0 -> die stage st:h0 -> r2"""
    p, t = strap_vehicle(strap_form=strap)
    ca = t["count_aligned"]
    for q in ("P", "Q"):
        ca["ports"][q]["tree"] = False
    sp = {"start:r0->r1": dict(src="r0", dst="r1", launch_part="a", capture_part="b", src_part="a", dst_part="b")}
    if stage:
        ca["regions"]["st:h0"] = dict(parent="r0", tree_port="start:r0->st:h0", edge_fall=False, pad=0)
        sp["start:r0->st:h0"] = dict(src="r0", dst="st:h0", launch_part="a", capture_part=None, src_part="a",
                                     dst_part=None)
        sp["start:st:h0->r2"] = dict(src="st:h0", dst="r2", launch_part=None, capture_part="c", src_part=None,
                                     dst_part="c")
        ca["regions"]["r2"].update(parent="st:h0", tree_port="start:st:h0->r2")
    else:
        sp["start:r0->r2"] = dict(src="r0", dst="r2", launch_part="a", capture_part="c", src_part="a", dst_part="c")
        ca["regions"]["r2"]["tree_port"] = "start:r0->r2"
    ca["regions"]["r1"]["tree_port"] = "start:r0->r1"
    ca["start_tree"], ca["start_ports"] = "clock", sp
    p["partition_types"]["A"]["buses"].append(pin("cland_tstart_out", "out"))
    p["partition_types"]["B"]["buses"].append(pin("cland_tstart_in", "in"))
    return p, t


def test_strap_ties_take_the_start_pin_not_a_crossing():
    p, t = start_vehicle()
    st = CAB.strap_ties(t["count_aligned"], p)
    b = st["types"]["B"]["origin"]
    assert b["form"] == "strap" and b["tree_buses"] == ["cland_tstart_in"] and "tsw" not in b
    assert st["instances"]["c"]["values"]["strap_ca_pad"] == 1 and st["instances"]["c"]["values"]["strap_ca_efall"] == 1


def test_origin_reads_the_start_pin_and_parent_drives_one_out_pin():
    p, t = start_vehicle()
    c = Landings(p, t)
    bb = c.type_rtl("B", B_BODY)
    aa = c.type_rtl("A", A_BODY)
    assert "input wire cland_tstart_in" in bb and ".p_start(cland_tstart_in)" in bb
    assert "ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin (" in bb
    assert "output wire cland_tstart_out" in aa and "assign cland_tstart_out = cland_start;" in aa
    assert "cland_tstart_in" not in aa and "cland_tstart_out" not in bb
    tt = c.top_rtl(TOP)
    assert tt.count(".cland_tstart_out(clock_landing_tstart_a)") == 1
    assert tt.count(".cland_tstart_in(clock_landing_tstart_a)") == 2          # one launch pin, fanned out at the top
    assert "wire clock_landing_tstart_a;" in tt
    assert ".cland_fstart_in_y(" in tt                                         # the ring write-count start stays


def test_parameter_form_child_origin_on_the_start_pin():
    p, t = start_vehicle(strap=False)
    t["count_aligned"]["ports"]["Q"]["K"] = -2          # b and c identical except the origin straps -> same signature
    t["count_aligned"]["regions"]["r2"].update(edge_fall=False, pad=0)
    c = Landings(p, t)
    bb = c.type_rtl("B", B_BODY)
    assert ("ot_dp_landing_origin #(.PAD(0), .EDGE_FALL(0)) u_cland_origin (" in bb
            and ".p_start(cland_tstart_in), .start(cland_start));" in bb)
    assert ".rst_raw_n(cland_reset_y)" in bb               # local timed raw-reset relay (the landed bus's)


def test_stage_ends_are_die_top_ports():
    p, t = start_vehicle(stage=True)
    d = start_pins(p, t["count_aligned"])
    assert [e["port"] for e in d["plan_ports"]] == ["start:r0->r1"]
    assert d["die_inputs"] == [dict(port="start:r0->st:h0", src_part="a", net="rs_r0", stage_region="st:h0")]
    assert d["die_outputs"] == [dict(port="start:st:h0->r2", dst_part="c", net="pst_r2", stage_region="st:h0")]
    c = Landings(p, t)
    c.type_rtl("A", A_BODY); c.type_rtl("B", B_BODY)
    tt = c.top_rtl(TOP)
    assert "input wire pst_r2;" in tt and "output wire rs_r0;" in tt
    assert "assign rs_r0 = clock_landing_tstart_a;" in tt
    assert ".cland_tstart_in(pst_r2)" in tt and ".cland_tstart_in(clock_landing_tstart_a)" in tt


def test_undeclared_start_pin_and_wrong_capture_fail_closed():
    p, t = start_vehicle()
    p["partition_types"]["B"]["buses"] = [b for b in p["partition_types"]["B"]["buses"] if b["name"] != "cland_tstart_in"]
    with pytest.raises(LandingError, match="cland_tstart_in"):
        Landings(p, t)
    p, t = start_vehicle()
    t["count_aligned"]["start_ports"]["start:r0->r1"].update(capture_part="c", dst_part="c")
    with pytest.raises((LandingError, CAB.BindError)):
        Landings(p, t)


def test_annotate_table_carries_start_ports():
    p, t = start_vehicle()
    b = dict(schema="x", period_ps=833.0, root="r0", pad=0, ports={k: dict(v, src=None) for k, v in
             t["count_aligned"]["ports"].items()}, regions=t["count_aligned"]["regions"], start_tree="clock",
             start_ports={k: dict(v, d_ps=1.0) for k, v in t["count_aligned"]["start_ports"].items()})
    tab = dict(ports=[])
    a = CAB.annotate_table(tab, b)["count_aligned"]
    assert a["start_tree"] == "clock" and set(a["start_ports"]) == {"start:r0->r1", "start:r0->r2"}
    assert "d_ps" not in a["start_ports"]["start:r0->r1"] and a["start_ports"]["start:r0->r1"]["dst_part"] == "b"
