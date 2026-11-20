"""UNIFY-TOOLS ROLE-STRAP (FABLE-SUPERSET-0415 10.6, QC slw_stm / slw_fw): origin and relay copies of ONE type.
partition_types[T].landing_role_strap = true: strap_ca_relay picks the copy's count start (origin hardware or the relay rx
flop), the unused start pin of a copy is tied 0 at the parent (bind tie audit: landing_ties), no TYPE_SPLIT."""
import pytest
import count_align_bind as CAB
import landing_tie_children as LTC
import straps as STR
from clock_landings import Landings, LandingError
from test_clock_landings import ca_relay_vehicle, C_BODY

TOP = ("module die_bound_top (rst_n, clk_core);\n input wire rst_n;\n input wire clk_core;\n    a_mod a (\n"
       "        .clk(clk_core)\n    );\n    b_mod b (\n        .clk(clk_core)\n    );\n    c_mod c (\n"
       "        .clk(clk_core)\n    );\n    c_mod d (\n        .clk(clk_core)\n    );\nendmodule\n")


def mixed_vehicle(opt_in=True):
    """c: relay copy of type C (region r1, origin b); d: second copy of C, origin of its own region r2"""
    p, t = ca_relay_vehicle()
    p["partitions"].append(dict(name="d", type="C", origin_um=[20, 0]))
    p["ports"].append(dict(id="S", width=4, kind="data", src=dict(part="a", bus="w"), dst=dict(part="d", bus="z")))
    t["regions"].append(dict(tag="r2", box_um=[20, 0, 30, 10]))
    t["ports"].append(dict(port="S", width=4, src="a", dst="d", src_region="r0", dst_region="r2", lane="LS"))
    ca = t["count_aligned"]
    ca["ports"]["S"] = dict(K=-2, depth=4, sched_lat=2, tree=True)
    ca["regions"]["r2"] = dict(parent="r0", tree_port="S", edge_fall=True, pad=1, origin_part="d")
    ca["parts"]["d"] = dict(region="r2", role="origin", src=None, stages=0)
    ca["strap_form"] = True
    if opt_in:
        p["partition_types"]["C"]["landing_role_strap"] = True
    st = CAB.strap_ties(ca, p)
    for tn, info in st["types"].items():
        p["partition_types"][tn]["count_straps"] = [dict(name=sp, width=w) for sp, w in info["straps"].items()]
    return p, t, st


def test_default_still_splits():
    p, t, st = mixed_vehicle(opt_in=False)
    assert st["types"]["C"]["residual_split"] and "strap_ca_relay" not in st["types"]["C"]["straps"]
    with pytest.raises(LandingError, match="TYPE_SPLIT required"):
        Landings(p, t)


def test_role_strap_one_type_per_copy_values():
    p, t, st = mixed_vehicle()
    tc = st["types"]["C"]
    assert tc["residual_split"] == [] and tc["origin"]["role_strap"] and tc["straps"]["strap_ca_relay"] == 1
    assert st["instances"]["c"]["values"]["strap_ca_relay"] == 1 and st["instances"]["d"]["values"]["strap_ca_relay"] == 0
    # the relay copy's origin straps are unused -> 0; the origin copy keeps its own PAD / EDGE_FALL
    assert st["instances"]["c"]["values"]["strap_ca_pad"] == 0 and st["instances"]["d"]["values"]["strap_ca_pad"] == 1
    assert st["instances"]["d"]["values"]["strap_ca_efall"] == 1
    # types without the key are unchanged
    p0, _t0, st0 = mixed_vehicle(opt_in=False)
    assert st0["types"]["B"] == st["types"]["B"] and st0["instances"]["b"] == st["instances"]["b"]


def test_role_strap_rtl_selects_start_d_and_raw_before_the_flops():
    p, t, _ = mixed_vehicle()
    c = Landings(p, t)
    assert c.ca_type["C"]["role"][0] == "rolestrap"
    cc = c.type_rtl("C", C_BODY)
    assert "input wire cland_rstart_in" in cc and "input wire strap_ca_relay" in cc
    assert "ot_dp_landing_origin_s" in cc and ".start(cland_start_org), .start_d(cland_start_org_d));" in cc
    assert ".d(cland_rstart_in), .q(cland_start_rly));" in cc and "u_cland_rstart_rx" in cc
    assert "assign cland_start = strap_ca_relay ? cland_start_rly : cland_start_org;" in cc
    assert "assign cland_start_d = strap_ca_relay ? cland_rstart_in : cland_start_org_d;" in cc
    assert "assign cland_start_raw = strap_ca_relay ? " in cc
    assert cc.count("assign cland_start =") == 1 and cc.count("assign cland_start_raw =") == 1
    rec = c.reset_placements["C"]["count_origin"]
    assert rec["kind"] == "rolestrap" and rec["relay"]["rx"] == "u_cland_rstart_rx" and rec["origin_kind"] == "strap"


def test_role_strap_top_ties_unused_start_pin_and_audit_accepts_it():
    p, t, st = mixed_vehicle()
    c = Landings(p, t)
    for tn in ("A", "B", "C"):
        body = C_BODY if tn == "C" else None
        if body:
            c.type_rtl(tn, body)
    tt = c.top_rtl(TOP)
    dblock = tt[tt.index("c_mod d ("):]
    dblock = dblock[:dblock.index(");")]
    cblock = tt[tt.index("c_mod c ("):]
    cblock = cblock[:cblock.index(");")]
    assert ".cland_rstart_in(1'b0)" in dblock and ".strap_ca_relay(1'b0)" in dblock
    assert ".cland_rstart_in(clock_landing_rstart_b)" in cblock and ".strap_ca_relay(1'b1)" in cblock
    ties = LTC.landing_ties(p["partition_types"])
    assert ties["C"]["cland_rstart_in"] == "1'b0" and "B" not in ties
    man = dict(types={"C": {sp: dict(width=w) for sp, w in st["types"]["C"]["straps"].items()}}, instances={})
    aud = STR.audit_top_ties(tt, man, {"c_mod": "C", "a_mod": "A", "b_mod": "B"}, landing_ties=ties)
    assert ("d", "cland_rstart_in", "1'b0") in aud["rows"]
    assert not any(r[0].startswith("d.cland_rstart_in") for r in aud["rejected"])


def test_role_strap_rejects_non_boolean():
    p, t, _ = mixed_vehicle()
    p["partition_types"]["C"]["landing_role_strap"] = "yes"
    with pytest.raises((LandingError, CAB.BindError), match="landing_role_strap must be a boolean"):
        Landings(p, t)
