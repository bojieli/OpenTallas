"""KV-BAND-C 11-15: opt-in ring band depth floor (BAND_MIN_DEPTH_UM / compose(band_min_depth_um=) /
resize_undersized_bands(min_depth_um=) / CLI --min-depth) and the occupant report of the BAND FAIL message."""
import copy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clock_landing_plan as CP  # noqa: E402
from test_clock_landing_band_resize import GEOM, _plan  # noqa: E402

TCL = (Path(__file__).resolve().parent / "landing_placement.tcl").read_text()


def _depth(r):
    return min(r[2] - r[0], r[3] - r[1])


def _bands(p, tn="a"):
    return p["partition_types"][tn]["clock"]["landing_contract"]["bands"]


@pytest.fixture(autouse=True)
def _restore():
    yield
    CP.BAND_RESERVE = "padded"
    CP.BAND_MIN_DEPTH_UM = 8.64


def _band(min_depth=None, width=1):
    t = dict(outline_um=[400.0, 300.0], hard_cores=[], buses=[], _cland_geom=GEOM)
    if min_depth is not None:
        CP.BAND_MIN_DEPTH_UM = min_depth
    CP.BAND_RESERVE = "ring_ff"
    return CP._storage_band(copy.deepcopy(t), "ft1_i", width, [])


def test_default_floor_is_unchanged():
    assert CP.BAND_MIN_DEPTH_UM == 8.64
    a = _band()
    CP.BAND_MIN_DEPTH_UM = 8.64
    assert a == _band(8.64)


def test_17_28_floor_gives_two_columns():
    CP.BAND_MIN_DEPTH_UM = 8.64
    a = _band()
    b = _band(17.28)
    assert _depth(b["rect_um"]) + 1e-6 >= 17.28
    assert _depth(a["rect_um"]) + 1e-6 >= 8.64


def test_resize_with_min_depth_widens_a_one_column_band_and_default_is_identical():
    p, side = _plan()
    p0 = copy.deepcopy(p)
    old = _bands(p)["ft1_i"]["rect_um"]
    assert _depth(old) < 17.28
    base, rep0 = CP.resize_undersized_bands(p, side, ["a"])
    assert p == p0                                                    # input untouched
    new, rep = CP.resize_undersized_bands(p, side, ["a"], min_depth_um=17.28)
    b = _bands(new)["ft1_i"]
    assert _depth(b["rect_um"]) + 1e-6 >= 17.28
    assert b["resized_from_um"] == old and "KV-BAND-C" in b["resize"]
    assert any(r["bus"] == "ft1_i" for r in rep)
    assert CP.BAND_MIN_DEPTH_UM == 8.64                               # module mode restored
    # other type untouched, default path byte-identical to a call without the kwarg
    assert _bands(new, "b") == _bands(p, "b")
    again, rep1 = CP.resize_undersized_bands(p, side, ["a"], None, None)
    assert again == base and rep1 == rep0


def test_bad_min_depth_rejected():
    p, side = _plan()
    with pytest.raises(ValueError):
        CP.resize_undersized_bands(p, side, ["a"], min_depth_um=4.0)


needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="no tclsh")


def _occ_procs():
    i = TCL.index("proc cland_band_occupants {")
    j = TCL.index("proc cland_put {")
    return TCL[i:j]


MOCK = r"""
set ff_dbu 1000
proc m {op} { switch $op { getName { return DFFHQNx1 } } }
proc inst {n st x0 y0 x1 y1 placed op args} {
  switch $op { getName { return $n } isPlaced { return $placed } getPlacementStatus { return $st } getMaster { return m }
    getBBox { return [list bb $x0 $y0 $x1 $y1] } }
}
proc bb {x0 y0 x1 y1 op} { switch $op { xMin { return $x0 } yMin { return $y0 } xMax { return $x1 } yMax { return $y1 } } }
foreach {n st x0 y0 x1 y1 p} {
  u_ft17/slot_a FIRM 1000 1000 2000 2000 1
  u_reader/start_3 PLACED 3000 1000 4000 2000 1
  far/x FIRM 50000 50000 51000 51000 1
  u_cland_ft20/self FIRM 1000 1000 2000 2000 1
  unplaced/y NONE 1000 1000 2000 2000 0 } {
  interp alias {} i_$n {} inst $n $st $x0 $y0 $x1 $y1 $p
  lappend insts i_$n
  interp alias {} bb_$n {} bb $x0 $y0 $x1 $y1
}
rename inst inst_
proc inst {n st x0 y0 x1 y1 placed op args} {
  if {$op eq "getBBox"} { return bb_$n }
  switch $op { getName { return $n } isPlaced { return $placed } getPlacementStatus { return $st } getMaster { return m } }
}
proc blk {op args} { return $::insts }
set ff_blk blk
puts [cland_band_occupants {{0.5 0.5 3.5 2.5}} u_cland_ft20/self]
"""


@needs_tcl
def test_band_fail_report_names_the_occupants():
    out = subprocess.run(["tclsh"], input="set insts {}\n" + _occ_procs() + MOCK, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    line = out.stdout.strip()
    assert line.startswith("occupants 2:"), line
    assert "u_ft17/slot_a(FIRM,DFFHQNx1)" in line and "u_reader/start_3(PLACED,DFFHQNx1)" in line
    assert "far/x" not in line and "self" not in line and "unplaced" not in line


def test_all_band_fail_sites_carry_the_report():
    n = "OT_CLAND no legal nonoverlapping row/site in reserved band for"
    assert TCL.count("{cland_band_occupants ") == 3
    for line in TCL.splitlines():
        if n in line and line.lstrip().startswith("error "):
            assert "cland_band_occupants" in line, line
