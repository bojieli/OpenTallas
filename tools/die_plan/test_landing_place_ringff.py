"""DIE-HEAD-13: opt-in band_ring="ff" (ring flops only FIRM, bit-major, ring logic to GPL); defaults unchanged."""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import clock_landing_plan as CP  # noqa: E402
import landing_place as LP  # noqa: E402
from test_landing_place_spread import _P  # noqa: E402

TCL = (HERE / "landing_placement.tcl").read_text()


def test_ff_suffix_only_when_band_has_ring_place():
    r = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i"}
    assert "ring:i}" in LP.tcl(_P({"i": dict(r)}), "t")
    assert "ring:i+ff}" in LP.tcl(_P({"i": dict(r, ring_place="ff")}), "t")
    assert "ring:i@1.8037+ff}" in LP.tcl(_P({"i": dict(r, spread=1.8037, ring_place="ff")}), "t")


def test_compose_band_ring_validation():
    with pytest.raises(ValueError):
        CP.compose(dict(), dict(), band_reserve="padded", band_ring="ff")
    with pytest.raises(ValueError):
        CP.compose(dict(), dict(), band_reserve="ring_ff", band_ring="logic")


def test_storage_band_records_ring_place_only_when_ff():
    from test_clock_landing_band_reserve import _type
    try:
        CP.BAND_RESERVE = "ring_ff"
        b = CP._storage_band(_type(), "wide_i", 63, [])
        assert "ring_place" not in b
        CP.BAND_RING = "ff"
        f = CP._storage_band(_type(), "wide_i", 63, [])
        assert f["ring_place"] == "ff"
        assert f["rect_um"] == b["rect_um"] and f["area_reserve_um2"] == b["area_reserve_um2"]
    finally:
        CP.BAND_RESERVE = "padded"; CP.BAND_RING = "all"


def test_default_tags_take_the_unchanged_path():
    # the ff branch only triggers on the +ff suffix; plain/spread ring tags keep the netlist-order first-fit path
    assert "if {[string match {ring:*+ff} $tag]}" in TCL
    assert "proc cland_put {i rect tag {sp {}} {cur 0}}" in TCL
    assert "if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_ffkey_sorts_bit_major():
    proc = re.search(r"proc cland_ffkey \{nm\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[10\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_", "u/u_ring.s_d[2][9]$_DFFE_PP_"]
    body = proc + "set l {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + "} { lappend l [list [cland_ffkey $n] $n] }\n" \
        "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    slots_bits = [tuple(int(v) for v in re.findall(r"\[(\d+)", o)) for o in out]
    assert slots_bits == [(0, 9), (1, 9), (2, 9), (3, 9), (0, 10)]
