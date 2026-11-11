"""DIE-QC-97 CLAND-RING-FO (COORD 11-10): die-level clock.landing_ring_fanout_max bounds every WREG count-aligned ring's
write-enable / read-select register fanout (existing same-D kept copies: 0 cycles, no K change), the kit SDC carries
set_max_fanout F, and clock.landing_ring_status_reg turns STATUS_REG on die-wide.  Default (absent / 0): byte-same.
    python3 -m pytest -q tools/die_plan/test_cland_ring_fanout.py"""
import copy

import pytest

import count_align_bind as CAB
import gen_phys
import schema
import sdc_lint
from clock_landings import Landings, ring_fanout_max, ring_fanout_wreg_cfg, ring_write_reg
from landing_place import _local_chunk_config
from test_clock_landings import B_BODY
from test_count_straps import strap_vehicle
from test_sdc_lint import _errs, _landing_kit, _kit


def _wreg(p, **kw):
    cfg = dict(buses=["y"], dsrep=1, freg=False)
    cfg.update(kw)
    p["partition_types"]["B"].setdefault("clock", {})["landing_ring_wreg"] = cfg


def test_helper_bounds():
    assert ring_fanout_max({}) == 0 and ring_fanout_max(None) == 0
    cfg = dict(buses=["y"], dsrep=1)
    assert ring_fanout_wreg_cfg({}, cfg) is cfg                       # legacy: the cfg itself
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 0}, cfg) is cfg
    out = ring_fanout_wreg_cfg({"landing_ring_fanout_max": 32}, cfg)
    assert out == dict(buses=["y"], dsrep=2) and cfg == dict(buses=["y"], dsrep=1)      # write chunk stays 64
    # the write chunk bound is its own opt-in (pilot 1: start -> enable T/2 on wide rings)
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 32, "landing_ring_write_chunk": 32}, cfg) == \
        dict(buses=["y"], dsrep=2, write_chunk=32)
    assert ring_fanout_wreg_cfg({"landing_ring_write_chunk": 32}, cfg) == dict(buses=["y"], dsrep=1, write_chunk=32)
    assert ring_fanout_wreg_cfg({"landing_ring_write_chunk": 64}, cfg) is cfg
    # never loosens an explicit tighter choice
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 32, "landing_ring_write_chunk": 32},
                                dict(buses=[], dsrep=4, write_chunk=8)) == dict(buses=[], dsrep=4, write_chunk=8)
    # a bounded read_chunk type keeps its own dsrep (SREP must divide its chunk width)
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 16, "landing_ring_write_chunk": 16},
                                dict(buses=[], dsrep=1, read_chunk=48)) == dict(buses=[], dsrep=1, read_chunk=48, write_chunk=16)


@pytest.mark.parametrize("bad", [3, 48, 128, -1, True, "32", 32.0])
def test_bad_bound(bad):
    from clock_landings import ring_write_chunk_max
    with pytest.raises(ValueError):
        ring_fanout_max({"landing_ring_fanout_max": bad})
    with pytest.raises(ValueError):
        ring_write_chunk_max({"landing_ring_write_chunk": bad})


def test_ring_rtl_and_same_k():
    p, t = strap_vehicle()
    _wreg(p)
    base_rtl, base_k = Landings(p, t).type_rtl("B", B_BODY), CAB.strap_ties(t["count_aligned"], p)
    assert ".WREG(1), .DSREP(1)) u_cland_y" in base_rtl
    p2, t2 = strap_vehicle()
    _wreg(p2)
    p2.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    rtl = Landings(p2, t2).type_rtl("B", B_BODY)
    assert ".WREG(1), .DSREP(2)) u_cland_y" in rtl and "WRITE_CHUNK" not in rtl
    assert rtl.replace(".DSREP(2))", ".DSREP(1))") == base_rtl                       # only the read-select copies
    assert CAB.strap_ties(t2["count_aligned"], p2) == base_k                        # register copies: no K change
    assert "write_chunk" not in ring_write_reg(p2, "B", "y")
    p2["clock"]["landing_ring_write_chunk"] = 32                                    # the separate opt-in
    rtl32 = Landings(p2, t2).type_rtl("B", B_BODY)
    assert ".WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u_cland_y" in rtl32
    assert ring_write_reg(p2, "B", "y")["write_chunk"] == 32


def test_status_reg_die_wide():
    p, t = strap_vehicle()
    _wreg(p)
    base = Landings(p, t).type_rtl("B", B_BODY)
    p2, t2 = strap_vehicle()
    _wreg(p2)
    p2.setdefault("clock", {})["landing_ring_status_reg"] = True
    lg = Landings(p2, t2)
    rtl = lg.type_rtl("B", B_BODY)
    assert ", .STATUS_REG(1), .WREG(1)" in rtl and rtl.replace(", .STATUS_REG(1)", "") == base
    assert lg.reset_placements["B"]["y"]["status_reg_added_fault_cycles"] == 1
    assert CAB.strap_ties(t2["count_aligned"], p2) == CAB.strap_ties(t["count_aligned"], p)
    p3, _ = strap_vehicle()
    p3.setdefault("clock", {})["landing_ring_status_reg"] = 1
    with pytest.raises(ValueError):
        Landings(p3, strap_vehicle()[1]).type_rtl("B", B_BODY)


def test_placement_chunks_follow_the_bound():
    p, _ = strap_vehicle()
    _wreg(p)
    typ = p["partition_types"]["B"]
    assert _local_chunk_config(typ) == "" and _local_chunk_config(typ, {}) == ""
    assert _local_chunk_config(typ, {"landing_ring_fanout_max": 32}) == ""        # write chunk 64: no rows
    assert "{write 32 read 32}" in _local_chunk_config(typ, {"landing_ring_fanout_max": 32, "landing_ring_write_chunk": 32})


def test_sdc_line_gated_and_linted(monkeypatch):
    import test_sdc_lint as T
    txt0, ctx0 = _landing_kit()
    assert "set_max_fanout" not in txt0                                        # default: byte-same
    raw = copy.deepcopy(T.TINY)
    raw.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    monkeypatch.setattr(T, "TINY", raw)
    assert "set_max_fanout" not in _landing_kit()[0]                           # the bound alone: no SDC line
    raw["clock"]["landing_ring_sdc_max_fanout"] = True                          # its own opt-in
    txt, ctx = _landing_kit()
    assert txt.endswith("set_max_fanout 32 [current_design]\n") or "set_max_fanout 32 [current_design]\n" in txt
    assert txt.replace(next(ln for ln in txt.splitlines(True) if ln.startswith(gen_phys.RING_FANOUT_TAG)), "") \
        .replace("set_max_fanout 32 [current_design]\n", "") == txt0
    assert _errs(txt, ctx) == []
    for bad, msg in [(txt.replace("set_max_fanout 32 [current_design]", "set_max_fanout 48 [current_design]"), "power of two"),
                     (txt.replace("set_max_fanout 32 [current_design]", "set_max_fanout 32 [get_nets *]"), "only 'set_max_fanout"),
                     (txt + "set_max_fanout 32 [current_design]\n", "twice")]:
        errs = _errs(bad, ctx)
        assert any(msg in e for e in errs), errs
    # no landed ring: no line even with the die bound, and a hand-added line fails closed
    t2, c2 = _kit(raw)
    assert "set_max_fanout" not in t2
    assert any("ring_fanout" in e for e in _errs(t2 + "set_max_fanout 32 [current_design]\n", c2))


def test_schema_accepts_the_knobs():
    import test_sdc_lint as T
    raw = copy.deepcopy(T.TINY)
    raw.setdefault("clock", {}).update(landing_ring_fanout_max=32, landing_ring_status_reg=True,
                                       landing_ring_write_chunk=32, landing_ring_sdc_max_fanout=True)
    schema.validate(raw) if hasattr(schema, "validate") else schema.Plan(raw)


# ---- part (d) RSTREP-1: same-D copies of the last reader-START stage, ring reset loads split ----
from clock_landings import ring_reset_copies


def _reader_start(p):
    p["partition_types"]["B"]["clock"]["landing_reader_start"] = dict(
        depth=2, branches={"y": {"stages": [dict(xy_um=[3., 3.], raw_reset="cland_reset_y"),
                                            dict(xy_um=[6., 3.], raw_reset="cland_reset_y")]}})


def test_reset_copies_count():
    assert ring_reset_copies({}, 549, 4, 2) == 0 and ring_reset_copies(None, 549, 4, 2) == 0
    c = {"landing_ring_fanout_max": 32}
    assert ring_reset_copies(c, 549, 4, 2) == 4      # 9 chunks x 8 select flops: 3 groups of <= 4 chunks + oh
    assert ring_reset_copies(c, 64, 4, 2) == 2
    assert ring_reset_copies(c, 549, 8, 2) == 6      # 16 flops / chunk: groups of 2
    assert ring_reset_copies(c, 549, 4, 2, read_chunk=48) == 1 + 3     # 12 chunks of 48 bits
    assert ring_reset_copies({"landing_ring_fanout_max": 4}, 64, 4, 2) == 2    # over-wide chunk: one per group


def test_reader_start_copies_rtl():
    p, t = strap_vehicle()
    _wreg(p)
    _reader_start(p)
    base = Landings(p, t).type_rtl("B", B_BODY)
    assert "ot_dp_landing_relay_rep" not in base and "rst_xn" not in base and "RSTREP" not in base   # legacy
    p2, t2 = strap_vehicle()
    _wreg(p2)
    _reader_start(p2)
    p2.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    lg = Landings(p2, t2)
    rtl = lg.type_rtl("B", B_BODY)
    assert ".RSTREP(" in rtl and ", .rst_xn(cland_reader_start_y_1_x)" in rtl
    k = int(rtl.split(".RSTREP(")[1].split(")")[0])
    assert k >= 2
    assert f"wire [{k - 1}:0] cland_reader_start_y_1_x;" in rtl
    assert (f'(* keep = "true" *) ot_dp_landing_relay_rep #(.N({k})) u_cland_reader_start_y_1 (.clk(clk), '
            f'.rst_raw_n(cland_reset_y), .d(cland_reader_start_y_0), .q(cland_reader_start_y_1), '
            f'.qx(cland_reader_start_y_1_x));') in rtl
    # the first stage, the ring's rst_n and the strap K are unchanged
    assert "ot_dp_landing_relay u_cland_reader_start_y_0 (" in rtl and ".rst_n(cland_reader_start_y_1)" in rtl
    assert CAB.strap_ties(t2["count_aligned"], p2) == CAB.strap_ties(t["count_aligned"], p)
    r = lg.reset_placements["B"]["y"]["reader_start"]
    assert r["ring_reset_copies"] == k and r["ring_reset_copies_added_cycles"] == 0
    # same placement group (the copies sit inside the stage's kept instance)
    import landing_place as LP
    assert [g[0] for g in LP._reader_start_groups(p2["partition_types"]["B"])] == \
        ["u_cland_reader_start_y_0", "u_cland_reader_start_y_1"]


def test_no_reader_start_no_copies():
    p, t = strap_vehicle()
    _wreg(p)
    p.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    rtl = Landings(p, t).type_rtl("B", B_BODY)
    assert "RSTREP" not in rtl and "ot_dp_landing_relay_rep" not in rtl


def test_rtl_module_has_rstrep():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2] / "rtl/common/ot_dp_clk_landing_ca.sv").read_text()
    assert "module ot_dp_landing_relay_rep" in src and "parameter int RSTREP = 0" in src and "rst_xn" in src


def test_place_copies_helper():
    """PLACEREP-1: needs a die fanout bound and more than one read chunk (64-bit chunks, or the wreg READ_CHUNK)."""
    from clock_landings import ring_place_copies
    c = {"landing_ring_fanout_max": 32}
    assert not ring_place_copies({}, 549) and not ring_place_copies(None, 549)
    assert not ring_place_copies({"landing_ring_fanout_max": 0}, 549)
    assert ring_place_copies(c, 549) and ring_place_copies(c, 65)          # 9 / 2 chunks
    assert not ring_place_copies(c, 64) and not ring_place_copies(c, 5)    # one chunk
    assert ring_place_copies(c, 64, read_chunk=32) and not ring_place_copies(c, 64, read_chunk=64)


def test_place_copies_follow_the_bound(monkeypatch):
    """Under landing_ring_fanout_max a wide strap-form ring is instantiated with .PLACEREP(1), 0 added cycles; a one-chunk ring
    and an absent / 0 bound keep byte-same RTL."""
    import clock_landings
    p, t = strap_vehicle()
    _wreg(p)
    base = Landings(p, t).type_rtl("B", B_BODY)
    assert "PLACEREP" not in base
    p0, t0 = strap_vehicle()
    _wreg(p0)
    p0.setdefault("clock", {})["landing_ring_fanout_max"] = 0
    assert Landings(p0, t0).type_rtl("B", B_BODY) == base
    p1, t1 = strap_vehicle()                      # 5-bit bundle: one read chunk, no copy
    _wreg(p1)
    p1.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    assert "PLACEREP" not in Landings(p1, t1).type_rtl("B", B_BODY)
    monkeypatch.setattr(clock_landings, "ring_place_copies", lambda *a, **k: True)   # as a wide ring
    p2, t2 = strap_vehicle()
    _wreg(p2)
    p2.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    lg = Landings(p2, t2)
    rtl = lg.type_rtl("B", B_BODY)
    assert ".PLACEREP(1)) u_cland_y" in rtl and rtl.count(".PLACEREP(1)") == rtl.count("ot_dp_clk_landing_cas #(")
    r = lg.reset_placements["B"]["y"]
    assert r["ring_place_copies"] is True and r["ring_place_copies_added_cycles"] == 0
    assert CAB.strap_ties(t2["count_aligned"], p2) == CAB.strap_ties(t["count_aligned"], p)


def test_rtl_module_has_placerep():
    import pathlib
    src = (pathlib.Path(__file__).resolve().parents[2] / "rtl/common/ot_dp_clk_landing_ca.sv").read_text()
    assert "module ot_meso_place_rep" in src and "parameter bit PLACEREP = 0" in src
    assert src.count(".PLACEREP(PLACEREP)") == 1 and ".place(pl_c)" in src and ".place(RP0[AW-1:0])" not in src
