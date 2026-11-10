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
    assert out == dict(buses=["y"], dsrep=2, write_chunk=32) and cfg == dict(buses=["y"], dsrep=1)
    # never loosens an explicit tighter choice
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 32}, dict(buses=[], dsrep=4, write_chunk=8)) == \
        dict(buses=[], dsrep=4, write_chunk=8)
    # a bounded read_chunk type keeps its own dsrep (SREP must divide its chunk width)
    assert ring_fanout_wreg_cfg({"landing_ring_fanout_max": 16}, dict(buses=[], dsrep=1, read_chunk=48)) == \
        dict(buses=[], dsrep=1, read_chunk=48, write_chunk=16)


@pytest.mark.parametrize("bad", [3, 48, 128, -1, True, "32", 32.0])
def test_bad_bound(bad):
    with pytest.raises(ValueError):
        ring_fanout_max({"landing_ring_fanout_max": bad})


def test_ring_rtl_and_same_k():
    p, t = strap_vehicle()
    _wreg(p)
    base_rtl, base_k = Landings(p, t).type_rtl("B", B_BODY), CAB.strap_ties(t["count_aligned"], p)
    assert ".WREG(1), .DSREP(1)) u_cland_y" in base_rtl
    p2, t2 = strap_vehicle()
    _wreg(p2)
    p2.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    rtl = Landings(p2, t2).type_rtl("B", B_BODY)
    assert ".WREG(1), .DSREP(2), .WRITE_CHUNK(32)) u_cland_y" in rtl
    assert rtl.replace(".DSREP(2), .WRITE_CHUNK(32))", ".DSREP(1))") == base_rtl     # only the two parameters
    assert CAB.strap_ties(t2["count_aligned"], p2) == base_k                        # register copies: no K change
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
    assert "{write 32 read 32}" in _local_chunk_config(typ, {"landing_ring_fanout_max": 32})


def test_sdc_line_gated_and_linted(monkeypatch):
    import test_sdc_lint as T
    txt0, ctx0 = _landing_kit()
    assert "set_max_fanout" not in txt0                                        # default: byte-same
    raw = copy.deepcopy(T.TINY)
    raw.setdefault("clock", {})["landing_ring_fanout_max"] = 32
    monkeypatch.setattr(T, "TINY", raw)
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
    raw.setdefault("clock", {}).update(landing_ring_fanout_max=32, landing_ring_status_reg=True)
    schema.validate(raw) if hasattr(schema, "validate") else schema.Plan(raw)
