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
    assert "dict set ::cland_local_chunks {u_cland_link_i} {write 16 read 8}" in _local_chunk_config(typ)  # reach WREG
    typ = dict(clock=dict(landing_ring_wreg=dict(buses=[], reach=False), landing_contract=dict(bands=dict(link_i=band(576)))))
    assert "{u_cland_link_i} {write 0 read 8}" in _local_chunk_config(typ)            # explicit opt-out
    typ = dict(clock=dict(landing_contract=dict(bands=dict(link_i=band(64)))))
    assert _local_chunk_config(typ) == ""                                             # one chunk: no row, as before
    typ = dict(clock=dict(landing_contract=dict(bands=dict(link_i=band(576, hard_core=True)))))
    assert _local_chunk_config(typ) == ""                                             # signed hard child: untouched
    typ = dict(clock=dict(landing_ring_wreg=dict(buses=["link_i"], dsrep=1, write_chunk=8),
                          landing_contract=dict(bands=dict(link_i=band(576)))))
    assert "{u_cland_link_i} {write 8 read 8}" in _local_chunk_config(typ)            # same copies as the ring RTL
    typ = dict(buses=[dict(name="link_i", width=566)],
               clock=dict(landing_contract=dict(bands=dict(link_i=dict(instance="u_cland_link_i")))))
    assert "{u_cland_link_i} {write 16 read 8}" in _local_chunk_config(typ)           # width from the bus declaration


def test_plain_wide_ring_gets_local_write_side():
    # CLAND-RING-LOCALITY (GEN-CLASS-1 11-12): a plain ring wider than one chunk gets LOCAL = 1 (WCHKC slot-index copy per
    # chunk + local reset/on/align copies) next to its DSREP read copies; one-chunk rings and count-aligned rings unchanged
    from test_clock_landings import vehicle
    p, t = vehicle()
    body = _wide(p, t, 63)
    narrow = _ring_line(Landings(p, t).type_rtl("B", body))
    assert narrow.startswith("    ot_dp_clk_landing #(.W(64)") and "LOCAL" not in narrow and "DSREP" not in narrow
    p, t = vehicle()
    body = _wide(p, t, 567)
    lg = Landings(p, t)
    line = _ring_line(lg.type_rtl("B", body))
    assert line == "    ot_dp_clk_landing #(.W(568), .DSREP(8), .LOCAL(1)) u_cland_y (", line
    assert lg.reset_placements["B"]["y"]["ring_local"] == 1
    p, t = ca_vehicle()
    body = _wide(p, t, 567)
    assert "LOCAL" not in _ring_line(Landings(p, t).type_rtl("B", body))


def _wide_band(p, n):
    p["partition_types"]["B"].setdefault("clock", {})["landing_contract"] = dict(bands=dict(y=dict(ring_width=n + 1)))


def test_wide_soft_strap_ring_gets_reach_wreg_and_k_plus_one():
    # CLAND-RING-LOCALITY (COORD-approved family rule): ONE shared rule (ring_wreg_reach) gives RTL and strap K
    p, t = strap_vehicle()
    k0 = CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"]["strap_ca_k_y"]
    body = _wide(p, t, 567)
    _wide_band(p, 567)
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", body)
    line = _ring_line(rtl)
    # WREG (writer) + reach reader START: RSTREP 1 + 9 chunks, PLACEREP copies per chunk
    assert line.endswith(", .WREG(1), .DSREP(8), .WRITE_CHUNK(16), .RSTREP(10), .PLACEREP(1)) u_cland_y ("), line
    assert lg.reset_placements["B"]["y"]["ring_wreg"] == 1 and lg.reset_placements["B"]["y"]["strap_k_delta"] == 1
    rs = lg.reset_placements["B"]["y"]["reader_start"]
    assert rs["reach"] and rs["depth"] == 1 and rs["K_adjustment"] == -1 and rs["ring_reset_copies"] == 10
    assert "ot_dp_landing_relay_rep #(.N(10)) u_cland_reader_start_y_0 (.clk(clk), .rst_raw_n(" in rtl
    assert ".d(cland_start), .q(cland_reader_start_y_0), .qx(cland_reader_start_y_0_x));" in rtl
    assert ".rst_n(cland_reader_start_y_0)" in line or ".rst_n(cland_reader_start_y_0)" in rtl
    k1 = CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"]["strap_ca_k_y"]
    assert k1 == k0 % 64                                            # WREG +1 and reader START -1: net strap K unchanged
    assert CAB.reader_start_depth(p, "B") == 1 and CAB.reader_start_depth(p, "B", strap=False) == 0
    assert ring_write_reg(p, "B", "y") == dict(depth=1, dsrep=8, freg=False, write_chunk=16, reach=True)


def test_reach_wreg_opt_out_narrow_and_non_strap_unchanged():
    p, t = strap_vehicle()
    body = _wide(p, t, 567)
    _wide_band(p, 567)
    p["partition_types"]["B"]["clock"]["landing_ring_wreg"] = dict(buses=[], reach=False)
    p["partition_types"]["B"]["clock"]["landing_reader_start_reach"] = False
    line = _ring_line(Landings(p, t).type_rtl("B", body))
    assert "WREG" not in line and "RSTREP" not in line                              # explicit opt-outs
    assert CAB.reader_start_depth(p, "B") == 0
    p, t = strap_vehicle()
    body = _wide(p, t, 63)
    _wide_band(p, 63)
    assert "WREG" not in _ring_line(Landings(p, t).type_rtl("B", body))            # one chunk
    assert ring_write_reg(p, "B", "y") is None
    p, t = ca_vehicle()
    body = _wide(p, t, 567)
    _wide_band(p, 567)
    line = _ring_line(Landings(p, t).type_rtl("B", body))
    assert "WREG" not in line and line.endswith(", .DSREP(8)) u_cland_y (")      # non-strap: no K carrier, no WREG


def test_explicit_reader_start_chain_gets_per_chunk_copies_no_k_change():
    # CLAND-RING-LOCALITY (COORD whole-family scope): an explicit landing_reader_start chain's LAST stage takes the same
    # per-chunk RSTREP copies (clock_landings.reader_reset_copies) without the die fanout knob; strap K unchanged
    import clock_landings as CL
    p, t = strap_vehicle()
    body = _wide(p, t, 567)
    _wide_band(p, 567)
    p["partition_types"]["B"]["clock"]["landing_reader_start"] = dict(
        depth=2, branches={"y": {"stages": [dict(xy_um=[3., 3.], raw_reset="cland_reset_y"),
                                            dict(xy_um=[6., 3.], raw_reset="cland_reset_y")]}})
    k0 = CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"]["strap_ca_k_y"]
    lg = Landings(p, t)
    rtl = lg.type_rtl("B", body)
    assert "ot_dp_landing_relay_rep #(.N(10)) u_cland_reader_start_y_1 (" in rtl, rtl
    assert "ot_dp_landing_relay u_cland_reader_start_y_0 (" in rtl and ", .RSTREP(10)" in _ring_line(rtl)
    assert lg.reset_placements["B"]["y"]["reader_start"]["ring_reset_copies"] == 10
    assert CAB.reader_start_depth(p, "B") == 2 and not CL.reader_start_reach(p, "B")
    assert CAB.strap_ties(t["count_aligned"], p)["instances"]["b"]["values"]["strap_ca_k_y"] == k0
    assert CL.reader_reset_copies(p, "B", "y", 568) == 10 and CL.reader_reset_copies(p, "B", "y", 64) == 0
    p["partition_types"]["B"]["clock"]["landing_reader_start_reach"] = False       # opt-out
    assert "RSTREP" not in _ring_line(Landings(p, t).type_rtl("B", body))
