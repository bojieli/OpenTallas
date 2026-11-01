"""DIE-S81-47 11-01: multi-rect landing bands (rects_um) for ring buses with no legal single band (S81 "landing band
absent": 17 bands in 11 types).  Planner (clock_landing_plan._storage_rects / fill_failed_bands), emission
(landing_place.band_rects: one cland_groups entry per rect, same tag), packer (landing_placement.tcl: cland_put moves
to the next rect, cland_band_fit sums the rects) and single-rect bands unchanged."""
import copy
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import clock_landing_plan as CL
import landing_place as LP

TCL = (Path(__file__).resolve().parent / "landing_placement.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")

# 400 x 400 type, bus pin at (200, 0) on the S face; the only free space is two strips beside the pin
# (x 150-190 and 210-260, y 17.28-25.92): ~756 um2 together, neither holds the 676.5 um2 padded reserve of W=100.
OBST = [[0, 25.92, 400, 400], [0, 0, 150, 25.92], [190, 0, 210, 25.92], [260, 0, 400, 25.92]]


def _type():
    return {"outline_um": [400, 400],
            "buses": [{"name": "b", "dir": "in", "face": "S", "window_um": [190, 210], "width": 100}],
            "clock": {"landing_contract": {"bands": {
                "b": {"placement": "FAIL", "rect_um": None, "instance": "u_cland_b"},
                "c": {"rect_um": [0, 0, 1, 1], "width": 1, "ring_place": "ff", "placement": "PROPOSED"}}}}}


@pytest.fixture
def blocked(monkeypatch):
    monkeypatch.setattr(CL.RT, "blockages", lambda t, *a, **k: [list(o) for o in OBST])


def test_single_band_impossible_multi_rect_fills_two_strips(blocked):
    t = _type()
    with pytest.raises(ValueError):
        CL._storage_band(t, "b", 100, [])
    b = CL._storage_rects(t, "b", 100, [])
    rs = b["rects_um"]
    assert len(rs) == 2 and b["rect_um"] == rs[0]
    assert sum((r[2] - r[0]) * (r[3] - r[1]) for r in rs) + 1e-6 >= b["area_reserve_um2"]
    for r in rs:                                         # same legality as one band
        assert r[0] >= 17.28 - 1e-6 and r[1] >= 17.28 - 1e-6 and r[2] <= 400 - 17.28 + 1e-6
        assert CL._hop(r, 200, 0) <= 405 - 2.16
        assert not any(CL._rect_overlap(r, o) for o in OBST)
    assert not CL._rect_overlap(rs[0], rs[1])
    assert CL._hop(rs[0], 200, 0) <= CL._hop(rs[1], 200, 0)   # nearest the pin first
    assert b["max_pin_to_band_hop_um"] == round(max(CL._hop(r, 200, 0) for r in rs), 3)


def test_not_enough_free_area_still_fails(blocked):
    with pytest.raises(ValueError, match="no multi-rect"):
        CL._storage_rects(_type(), "b", 160, [])          # W=160 reserve 878 um2 > the ~756 um2 free


def test_fill_failed_bands_fills_only_fail_bands(blocked):
    t = _type()
    plan = {"partition_types": {"T": t, "U": copy.deepcopy(t)}}
    side = {"collector": {"types": {"T": {"bus_geometry": {}, "tree": None}}}}
    out, rep = CL.fill_failed_bands(plan, side, ["T"])
    nb = out["partition_types"]["T"]["clock"]["landing_contract"]["bands"]["b"]
    assert nb["instance"] == "u_cland_b" and nb["ring_place"] == "ff" and len(nb["rects_um"]) == 2
    assert out["partition_types"]["T"]["clock"]["landing_contract"]["bands"]["c"] == t["clock"]["landing_contract"]["bands"]["c"]
    assert out["partition_types"]["U"] == plan["partition_types"]["U"]   # unnamed types untouched
    assert plan["partition_types"]["T"]["clock"]["landing_contract"]["bands"]["b"]["placement"] == "FAIL"  # input kept
    assert len(rep) == 1 and rep[0]["bus"] == "b"


def test_band_rects_emission_and_validation():
    one = {"rect_um": [1, 2, 3, 4]}
    assert LP.band_rects("T", "b", one) == [[1, 2, 3, 4]]
    multi = {"rect_um": [20, 20, 30, 30], "rects_um": [[20, 20, 30, 30], [40, 20, 50, 30]]}
    assert LP.band_rects("T", "b", multi, {"outline_um": [100, 100]}) == multi["rects_um"]
    for bad in ({"rect_um": [20, 20, 30, 30], "rects_um": [[20, 20, 30, 30]]},
                {"rect_um": [20, 20, 30, 30], "rects_um": [[20, 20, 30, 30], [25, 25, 35, 35]]},
                {"rect_um": [40, 20, 50, 30], "rects_um": [[20, 20, 30, 30], [40, 20, 50, 30]]},
                {"rect_um": [20, 20, 30, 30], "rects_um": [[20, 20, 30, 30], [90, 20, 110, 30]]},
                {"rect_um": [20, 20, 30, 30], "rects_um": [[20, 20, 30, 30], [40, 20, 50, 30]], "fill_axis": "x",
                 "ring_place": "ff"},
                {"placement": "FAIL", "rect_um": None}):
        with pytest.raises(ValueError):
            LP.band_rects("T", "b", bad, {"outline_um": [100, 100]})
    t = {"outline_um": [100, 100], "buses": [{"name": "b", "order": "lsb_low"}]}
    c = {"monitor": "dataflow", "bands": {"b": dict(multi, ring_place="ff")}}
    txt = LP._dataflow_tcl("T", c, t)
    groups = re.findall(r"^  \{(u_cland_b) \{([^}]*)\} (\S+)\}$", txt, re.M)
    assert [g[2] for g in groups] == ["ring:b+ff", "ring:b+ff"]
    assert [list(map(float, g[1].split())) for g in groups] == multi["rects_um"]


# packer mock: 1 row band rects of 2000 dbu x 4 rows, site 54, row 270 (as test_landing_band_fit)
def _procs():
    put = re.search(r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    occ = re.search(r"proc cland_occupy \{x y w h\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    fit = re.search(r"proc cland_band_fit \{prefix rect tag\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    return occ + put + fit


MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 6000; set ff_y1 1080; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create 0 R0 270 MX 540 R0 810 MX]; set cland_done {}; set cland_n 0; set cland_cursor {}
set cland_fh [open /dev/null w]
set cland_occ [dict create]
%(MULTI)s
proc mst {k op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return BUFx2 } } }
proc ins {k op args} { switch $op { getName { return u_cland_g/c$k } getMaster { return m$k } getPlacementStatus { return PLACED }
  setLocation { dict set ::loc $k $args } default {} } }
proc mk {k} { interp alias {} m$k {} mst $k; interp alias {} i$k {} ins $k; return i$k }
set insts {}; set loc {}
for {set k 0} {$k < %(N)d} {incr k} { lappend insts [mk $k] }
proc blk {op args} { return $::insts }
set ff_blk blk
set fit [catch {cland_band_fit u_cland_g {0 0 1.0 1.08} ring:g} fe]
set n 0
set put [catch { foreach i $insts { cland_put $i {0 0 1.0 1.08} ring:g; incr n } } pe]
puts "FIT $fit PUT $put N $n"
foreach {k xy} $loc { puts "LOC $k $xy" }
"""


def _pack(n, multi):
    m = "set cland_multi [dict create ring:g {{0.00000 0.00000 1.00000 1.08000} {3.00000 0.00000 4.00000 1.08000}}]" \
        if multi else ""
    out = subprocess.run(["tclsh"], input=_procs() + MOCK % dict(N=n, MULTI=m), capture_output=True, text=True,
                         check=True).stdout
    f, p, k = map(int, re.search(r"FIT (\d) PUT (\d) N (\d+)", out).groups())
    return f, p, k, [tuple(map(int, l.split()[2:4])) for l in out.splitlines() if l.startswith("LOC ")]


@needs_tcl
def test_packer_fills_rects_in_order():
    # 108-wide cells reserve 270: 4 per 1000-dbu row (last body fits), 16 per rect
    f, p, n, locs = _pack(16, False)
    assert (f, p, n) == (0, 0, 16)                     # one rect holds 16
    f, p, n, locs = _pack(20, False)
    assert f == 1 and p == 1                           # single rect: fails closed (bound and first fit)
    f, p, n, locs = _pack(30, True)
    assert (f, p, n) == (0, 0, 30)
    first = [xy for xy in locs if xy[0] < 1000]
    second = [xy for xy in locs if 3000 <= xy[0] < 4000]
    assert len(first) == 16 and len(second) == 14 and len(set(locs)) == 30
    f, p, n, locs = _pack(40, True)
    assert f == 1 and p == 1 and n == 32               # over both rects: same fail-closed error
