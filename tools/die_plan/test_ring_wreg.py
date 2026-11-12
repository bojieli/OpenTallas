"""WREG-1 (DIE-HEAD-58 TURNB 11-03): clock.landing_ring_wreg on a receiver type -> ot_dp_clk_landing_cas WREG/DSREP
parameters on that bus only, and strap_ties ties K + 1 there (writer start one fclk edge later, landing_writer_start
W=1 rule); every other bus/type is byte-identical."""
import pytest
import count_align_bind as CAB
from clock_landings import Landings, LandingError, ring_write_reg
from test_clock_landings import A_BODY, B_BODY
from test_count_straps import strap_vehicle


def _declare_freg(p, t, bus="y", tn="B"):
    """FREG-DECL-1: a FREG crossing declares its +1 data cycle on the bind sidecar (sched_lat + 1, "freg": 1; logical K
    unchanged, strap_ties applies the physical K + 2), as a die event must (HEAD n4_event convention)."""
    ptype = {q["name"]: q["type"] for q in p["partitions"]}
    for q in p["ports"]:
        if ptype[q["dst"]["part"]] == tn and q["dst"]["bus"] == bus and q["id"] in t["count_aligned"]["ports"]:
            c = t["count_aligned"]["ports"][q["id"]]
            c.update(sched_lat=int(c["sched_lat"]) + 1, freg=1)


def _wreg(p, buses=("y",), dsrep=4):
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = dict(buses=list(buses), dsrep=dsrep)


def test_strap_k_plus_one_only_on_listed_bus():
    p, t = strap_vehicle()
    base = CAB.strap_ties(t["count_aligned"], p)
    _wreg(p)
    st = CAB.strap_ties(t["count_aligned"], p)
    for inst in ("b", "c"):
        k0, k1 = base["instances"][inst]["values"]["strap_ca_k_y"], st["instances"][inst]["values"]["strap_ca_k_y"]
        assert k1 == (k0 + 1) % 64
        assert {k: v for k, v in st["instances"][inst]["values"].items() if k != "strap_ca_k_y"} == \
            {k: v for k, v in base["instances"][inst]["values"].items() if k != "strap_ca_k_y"}
    p2, t2 = strap_vehicle()
    _wreg(p2, buses=("other",))
    assert CAB.strap_ties(t2["count_aligned"], p2)["instances"] == base["instances"]


def test_rtl_parameter_is_the_only_difference():
    p, t = strap_vehicle()
    base = Landings(p, t).type_rtl("B", B_BODY)
    _wreg(p)
    c = Landings(p, t)
    bb = c.type_rtl("B", B_BODY)
    assert "ot_dp_clk_landing_cas #(.W(5), .DEPTH(4), .WREG(1), .DSREP(4)) u_cland_y" in bb
    assert bb.replace(", .WREG(1), .DSREP(4)", "") == base
    assert "WREG" not in c.type_rtl("A", A_BODY)


def test_bad_config_and_parameter_form():
    p, t = strap_vehicle()
    _wreg(p, dsrep=3)
    with pytest.raises(ValueError, match="dsrep"):
        ring_write_reg(p, "B", "y")
    p, t = strap_vehicle(strap_form=False)
    _wreg(p)
    with pytest.raises(LandingError):
        Landings(p, t).type_rtl("B", B_BODY)


def test_freg_face_register_k_plus_two():
    """FREG-1 (DIE-HEAD-58 ruling 11-03): "freg": true -> .FREG(1) and one more K (data + start one more cycle)."""
    p, t = strap_vehicle()
    base = CAB.strap_ties(t["count_aligned"], p)
    rtl0 = Landings(p, t).type_rtl("B", B_BODY)
    _wreg(p)
    p["partition_types"]["B"]["clock"]["landing_ring_wreg"]["freg"] = True
    _declare_freg(p, t)
    st = CAB.strap_ties(t["count_aligned"], p)
    for inst in ("b", "c"):
        assert st["instances"][inst]["values"]["strap_ca_k_y"] == \
            (base["instances"][inst]["values"]["strap_ca_k_y"] + 2) % 64
    bb = Landings(p, t).type_rtl("B", B_BODY)
    assert "ot_dp_clk_landing_cas #(.W(5), .DEPTH(4), .WREG(1), .DSREP(4), .FREG(1)) u_cland_y" in bb
    assert bb.replace(", .WREG(1), .DSREP(4), .FREG(1)", "") == rtl0
    p["partition_types"]["B"]["clock"]["landing_ring_wreg"]["freg"] = 1
    with pytest.raises(ValueError, match="freg"):
        ring_write_reg(p, "B", "y")
