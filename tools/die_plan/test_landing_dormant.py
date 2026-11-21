"""UNIFY-TOOLS-R3 DORMANT landing (S81 leaf classes, COORD 11-21): copies of ONE superset class type land different
ft-slot buses.  A copy that declares a landed class slot spare (partitions[].spare_ends) keeps the type's ring for it,
dormant: strap_ca_k_<b> = 0 and strap_ca_off_<b> = 1 at the parent, ring ready / fault masked to 1 / 0 inside the type,
fclk_in_<b> / cland_fstart_in_<b> tied 0 at the parent.  No landing-mask TYPE_SPLIT."""
import pytest
import count_align_bind as CAB
import landing_tie_children as LTC
import straps as STR
from clock_landings import Landings, LandingError
from test_role_strap import mixed_vehicle, TOP
from test_clock_landings import C_BODY

CF_BODY = C_BODY.replace(" input wire [4:0] z // whole bundle\n", " input wire [4:0] z, // whole bundle\n input wire [4:0] f_i\n")


def _pin(name, direction):
    return dict(name=name, dir=direction, width=1, face="E", window_um=[1, 2], layers=["M8"])


def dormant_vehicle(spare=True):
    """type C (role strap): c = relay copy landing z only, d = origin copy landing z (tree) and slot f (port R from a)"""
    p, t, _ = mixed_vehicle()
    C = p["partition_types"]["C"]
    C["superset"] = True
    C["ft_slots"] = [dict(name="f", in_face="E", out_face="W", width=4, stations=1)]
    C["buses"] += [_pin("f_i", "in"), _pin("fclk_in_f_i", "in"), _pin("landing_ready_f_i", "out"),
                   _pin("landing_fault_f_i", "out"), _pin("cland_fstart_in_f_i", "in")]
    p["partition_types"]["A"]["buses"] += [_pin("w2", "out"), _pin("fclk_out_w2", "out"), _pin("cland_fstart_out_w2", "out")]
    p["ports"].append(dict(id="R", width=4, kind="data", src=dict(part="a", bus="w2"), dst=dict(part="d", bus="f_i")))
    t["ports"].append(dict(port="R", width=4, src="a", dst="d", src_region="r0", dst_region="r2", lane="LR"))
    t["count_aligned"]["ports"]["R"] = dict(K=-3, depth=4, sched_lat=2, tree=False)
    if spare:
        next(x for x in p["partitions"] if x["name"] == "c")["spare_ends"] = ["f"]
    st = CAB.strap_ties(t["count_aligned"], p) if spare else None
    if st:
        for tn, info in st["types"].items():
            p["partition_types"][tn]["count_straps"] = [dict(name=sp, width=w) for sp, w in info["straps"].items()]
    return p, t, st


def test_without_spare_the_copies_still_need_a_split():
    p, t, _ = dormant_vehicle(spare=False)
    with pytest.raises(CAB.BindError, match="land different buses"):
        CAB.strap_ties(t["count_aligned"], p)


def test_dormant_strap_values():
    p, t, st = dormant_vehicle()
    tc = st["types"]["C"]
    assert tc["dormant_buses"] == ["f_i"] and tc["straps"]["strap_ca_off_f_i"] == 1 and "strap_ca_k_f_i" in tc["straps"]
    c, d = st["instances"]["c"], st["instances"]["d"]
    assert c["values"]["strap_ca_off_f_i"] == 1 and c["values"]["strap_ca_k_f_i"] == 0 and c["dormant"] == ["f_i"]
    assert d["values"]["strap_ca_off_f_i"] == 0 and "dormant" not in d and d["K"]["f_i"] == -3
    assert "f_i" not in c["K"]


def test_dormant_ring_is_type_hardware_masked_by_its_strap():
    p, t, _ = dormant_vehicle()
    c = Landings(p, t)
    assert c.dormant_ins["c"] == {"f_i"} and not c.dormant_ins["d"]
    cc = c.type_rtl("C", CF_BODY)
    assert "input wire [0:0] strap_ca_off_f_i" in cc and "u_cland_f_i" in cc
    assert ".ready(landing_ready_raw_f_i), .fault(landing_fault_raw_f_i));" in cc
    assert "assign landing_ready_f_i = landing_ready_raw_f_i | strap_ca_off_f_i[0];" in cc
    assert "assign landing_fault_f_i = landing_fault_raw_f_i & ~strap_ca_off_f_i[0];" in cc
    # the always-landed ring z keeps its direct status
    assert ".ready(landing_ready_z), .fault(landing_fault_z));" in cc


def test_dormant_copy_ties_clock_start_and_straps_at_the_parent():
    p, t, st = dormant_vehicle()
    c = Landings(p, t)
    c.type_rtl("C", CF_BODY)
    tt = c.top_rtl(TOP)
    cblock = tt[tt.index("c_mod c ("):]; cblock = cblock[:cblock.index(");")]
    dblock = tt[tt.index("c_mod d ("):]; dblock = dblock[:dblock.index(");")]
    assert ".fclk_in_f_i(1'b0)" in cblock and ".cland_fstart_in_f_i(1'b0)" in cblock
    assert ".strap_ca_off_f_i(1'b1)" in cblock and ".strap_ca_off_f_i(1'b0)" in dblock
    assert ".fclk_in_f_i(clock_landing_fwd_a__w2)" in dblock
    ties = LTC.landing_ties(p["partition_types"])
    man = dict(types={"C": {sp: dict(width=w) for sp, w in st["types"]["C"]["straps"].items()}}, instances={})
    aud = STR.audit_top_ties(tt, man, {"c_mod": "C", "a_mod": "A", "b_mod": "B"}, landing_ties=ties)
    assert ties["C"]["fclk_in_f_i"] == "1'b0" and ties["C"]["cland_fstart_in_f_i"] == "1'b0"
    assert ("c", "fclk_in_f_i", "1'b0") in aud["rows"] and ("c", "cland_fstart_in_f_i", "1'b0") in aud["rows"]
    assert not any(r[0].startswith(("c.fclk_in_f_i", "c.cland_fstart_in_f_i")) for r in aud["rejected"]), aud["rejected"]


def test_dormant_needs_the_strap_form():
    p, t, _ = dormant_vehicle()
    t["count_aligned"]["strap_form"] = False
    with pytest.raises(LandingError, match="TYPE_SPLIT"):
        Landings(p, t)
