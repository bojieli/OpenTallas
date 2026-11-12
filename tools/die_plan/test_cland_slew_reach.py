"""CLAND-SLEW-1 (GEN-CLASS-1 11-12): reach-based read-select copies on every soft landing ring.

HEAD hd_spn_wshim_rx (pf_wshim, plan g5p) was NOT SIGNED on drv: 265 A1 pins of u_cland_link_i/u_ring.dch[2].u_dsel at
TT 418-433 ps vs the 320 ps limit.  They are the chunk's one-hot SELECT nets: the 4 select flops of every 64-bit read
chunk are packed at the ring START bit (y 866) while dch[2]'s 64 AND-OR loads sit at their bits (y 911-942), and
repair_design saw 0 violations at place and GRT.  A ring with more than one read chunk now carries 8 kept select copies
per chunk (ot_meso_dsel SREP / DSREP 8: <= 8 loads per copy, 0 cycles) and the band keys each copy at its own 8-bit
group (landing_place cland_local_chunks read 8).
    python3 -m pytest -q tools/die_plan/test_cland_slew_reach.py"""
import pytest

import count_align_bind as CAB
from clock_landings import Landings, ring_reach_select_copies, ring_write_reg
from landing_place import _local_chunk_config
from test_clock_landings import B_BODY, ca_vehicle
from test_count_straps import strap_vehicle


def _wide(p, t, n):
    """the vehicle's x -> y crossings at n + 1 bound bits (n = planned width)"""
    for x in p["ports"] + t["ports"]:
        x["width"] = n
    return B_BODY.replace("[4:0] y", f"[{n}:0] y")


def _ring_line(rtl):
    return next(ln for ln in rtl.splitlines() if "u_cland_y (" in ln)


def test_rule():
    assert [ring_reach_select_copies(w) for w in (1, 5, 63, 64)] == [1, 1, 1, 1]       # one read chunk: unchanged
    assert [ring_reach_select_copies(w) for w in (65, 128, 568, 2049)] == [8, 8, 8, 8]  # >= 2 chunks: <= 8 loads/copy
    assert ring_reach_select_copies(568, read_chunk=48) == 1                          # bounded chunks keep their own


@pytest.mark.parametrize("mk,mod", [(strap_vehicle, "ot_dp_clk_landing_cas"), (ca_vehicle, "ot_dp_clk_landing_ca")])
def test_narrow_ring_byte_same_wide_ring_gets_copies(mk, mod):
    p, t = mk()
    base = Landings(p, t).type_rtl("B", B_BODY)
    assert "DSREP" not in base                                                        # 5-bit ring: unchanged
    p, t = mk()
    body = _wide(p, t, 63)
    lg = Landings(p, t)
    narrow = lg.type_rtl("B", body)                                        # W 64: one chunk
    assert "DSREP" not in _ring_line(narrow) and "ring_dsrep_reach" not in lg.reset_placements["B"]["y"]
    p, t = mk()
    body = _wide(p, t, 567)
    k0 = CAB.strap_ties(t["count_aligned"], p) if mk is strap_vehicle else None
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", body)                                          # the wshim_rx link_i width
    line = _ring_line(rtl)
    assert line.startswith(f"    {mod} #(.W(568)") and line.endswith(", .DSREP(8)) u_cland_y (")
    assert lg.reset_placements["B"]["y"]["ring_dsrep_reach"] == 8
    assert lg.reset_placements["B"]["y"]["ring_dsrep"] == 8 and lg.reset_placements["B"]["y"]["ring_dsrep_added_cycles"] == 0
    p2, t2 = mk()
    body2 = _wide(p2, t2, 567)
    ref = Landings(p2, t2).type_rtl("B", body2)
    assert rtl == ref and rtl.replace(", .DSREP(8))", ")").count("DSREP") == 0        # deterministic; only DSREP
    if k0 is not None:
        assert CAB.strap_ties(t["count_aligned"], p) == k0                            # no K / cycle change


def test_wreg_ring_raised_never_lowered():
    p, t = strap_vehicle()
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = dict(buses=["y"], dsrep=1, freg=False)
    body = _wide(p, t, 199)
    assert ".WREG(1), .DSREP(8)) u_cland_y" in Landings(p, t).type_rtl("B", body)
    assert ring_write_reg(p, "B", "y")["dsrep"] == 1                                  # plan metadata unchanged
    p, t = strap_vehicle()
    p["partition_types"]["B"]["clock"] = dict(landing_ring_wreg=dict(buses=["y"], dsrep=16, freg=False))
    body = _wide(p, t, 199)
    assert ".WREG(1), .DSREP(16)) u_cland_y" in Landings(p, t).type_rtl("B", body)
    p, t = strap_vehicle()
    p["partition_types"]["B"]["clock"] = dict(landing_ring_wreg=dict(buses=["y"], dsrep=1, freg=False, read_chunk=40))
    body = _wide(p, t, 199)
    assert ".DSREP(1), .READ_CHUNK(40)) u_cland_y" in Landings(p, t).type_rtl("B", body)


def test_placement_keys_copies_at_their_group():
    band = lambda w, **kw: dict(instance="u_cland_link_i", ring_width=w, **kw)          # noqa: E731
    typ = dict(clock=dict(landing_contract=dict(bands=dict(link_i=band(576)))))
    assert "dict set ::cland_local_chunks {u_cland_link_i} {write 0 read 8}" in _local_chunk_config(typ)
    typ = dict(clock=dict(landing_contract=dict(bands=dict(link_i=band(64)))))
    assert _local_chunk_config(typ) == ""                                             # one chunk: no row, as before
    typ = dict(clock=dict(landing_contract=dict(bands=dict(link_i=band(576, hard_core=True)))))
    assert _local_chunk_config(typ) == ""                                             # signed hard child: untouched
    typ = dict(clock=dict(landing_ring_wreg=dict(buses=["link_i"], dsrep=1, write_chunk=8),
                          landing_contract=dict(bands=dict(link_i=band(576)))))
    assert "{u_cland_link_i} {write 8 read 8}" in _local_chunk_config(typ)            # same copies as the ring RTL
    typ = dict(buses=[dict(name="link_i", width=566)],
               clock=dict(landing_contract=dict(bands=dict(link_i=dict(instance="u_cland_link_i")))))
    assert "{u_cland_link_i} {write 0 read 8}" in _local_chunk_config(typ)            # width from the bus declaration
