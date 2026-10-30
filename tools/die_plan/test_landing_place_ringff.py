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
    assert "if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]}" in TCL
    assert "proc cland_put {i rect tag {sp {}} {cur 0}}" in TCL
    assert "if {$sp eq {}} { set sp 1.0; regexp {^ring:[^@]*@([0-9.]+)$} $tag -> sp }" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_ffkey_sorts_bit_major():
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[10\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_", "u/u_ring.s_d[2][9]$_DFFE_PP_"]
    body = proc + "set l {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + "} { lappend l [list [cland_ffkey $n] $n] }\n" \
        "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    slots_bits = [tuple(int(v) for v in re.findall(r"\[(\d+)", o)) for o in out]
    assert slots_bits == [(0, 9), (1, 9), (2, 9), (3, 9), (0, 10)]


class _PT:
    """a type whose bus i runs lsb_high and whose ft slot fx carries in_order lsb_high / out_order lsb_low."""
    def __init__(self, bands, order="lsb_high"):
        self.types = {"t": {"buses": [{"name": "i", "order": order}],
                            "ft_slots": [{"name": "fx", "in_order": "lsb_high", "out_order": "lsb_low"}],
                            "clock": {"landing_contract": {"monitor": "dataflow", "bands": bands, "pins": []}}}}


def test_lsb_high_bus_gets_reversed_ff_tag_only():
    # DIE-HEAD-32: an lsb_high bus fills its ring_place=ff band in descending bit order (+ffr); lsb_low (default) keeps +ff
    r = {"rect_um": [1, 2, 3, 4], "instance": "u_cland_i"}
    assert "ring:i@1.8037+ffr}" in LP.tcl(_PT({"i": dict(r, spread=1.8037, ring_place="ff")}), "t")
    assert "ring:i@1.8037+ff}" in LP.tcl(_PT({"i": dict(r, spread=1.8037, ring_place="ff")}, "lsb_low"), "t")
    # order only matters for flop-only placement: an "all" band stays the netlist-order tag
    assert "ring:i@1.8037}" in LP.tcl(_PT({"i": dict(r, spread=1.8037)}), "t")
    # ft-slot buses take in_order/out_order; an unknown bus defaults to lsb_low
    assert "ring:fx_i+ffr}" in LP.tcl(_PT({"fx_i": dict(r, ring_place="ff", instance="u_cland_fx_i")}), "t")
    assert "ring:fx_o+ff}" in LP.tcl(_PT({"fx_o": dict(r, ring_place="ff", instance="u_cland_fx_o")}), "t")
    assert "ring:q+ff}" in LP.tcl(_PT({"q": dict(r, ring_place="ff", instance="u_cland_q")}), "t")
    # the placer takes the +ffr tag down the flop-only path
    assert "if {[string match {ring:*+ff} $tag] || [string match {ring:*+ffr} $tag]}" in TCL
    assert "set rev [string match {ring:*+ffr} $tag]" in TCL
    assert "[cland_ffkey [lindex $pr 0] $rev $wch $nbits]" in TCL


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_ffkey_rev_sorts_bits_descending_slots_ascending():
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[10\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[9\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_", "u/u_ring.s_d[2][565]$_DFFE_PP_"]
    def order(rev):
        body = proc + "set l {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + \
            "} { lappend l [list [cland_ffkey $n %d] $n] }\n" % rev + \
            "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
        out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
        return [tuple(int(v) for v in re.findall(r"\[(\d+)", o)) for o in out]
    assert order(0) == [(0, 9), (1, 9), (3, 9), (0, 10), (2, 565)]
    assert order(1) == [(2, 565), (0, 10), (0, 9), (1, 9), (3, 9)]


def _keyed_order(names, rev):
    procs = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0) + \
        re.search(r"proc cland_dsel_wch \{names\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    body = procs + "set ns {" + " ".join("{" + n + "}" for n in names) + "}\nset w [cland_dsel_wch $ns]\nputs W=$w\n" \
        "set l {}\nforeach n $ns { lappend l [list [cland_ffkey $n %d $w] $n] }\n" % rev + \
        "foreach p [lsort -dictionary -index 0 $l] { puts [lindex $p 1] }\n"
    out = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    return out[0], out[1:]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_chunked_read_registers_follow_their_word_bit():
    # FLOW-10 (HEAD st_str r2r 510): dch[c].u_dsel/y[i] = word bit c*WCH+i sits right after that bit's storage slots;
    # the chunk one-hot selects di[k] at the chunk centre.  Before: raw-name keys packed every y register first.
    names = [r"u/u_ring.dch\[1\].u_dsel/y\[0\]$_DFF_P_", r"u/u_ring.s_d\[1\]\[2\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/y\[1\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[1\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/di\[0\]$_DFFE_PP_", r"u/u_ring.s_d\[1\]\[1\]$_DFFE_PP_",
             r"u/u_ring.dch\[0\].u_dsel/y\[0\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[2\]$_DFFE_PP_",
             r"u/u_ring.s_d\[0\]\[0\]$_DFFE_PP_", r"u/u_ring.dch\[1\].u_dsel/y\[1\]$_DFF_P_",
             r"u/u_ring.s_d\[0\]\[3\]$_DFFE_PP_"]
    w, out = _keyed_order(names, 0)
    assert w == "W=2"
    short = [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in out]
    assert short == ["s_d[0][0]", "dch[0].u_dsel/y[0]",
                     "s_d[0][1]", "s_d[1][1]", "dch[0].u_dsel/di[0]", "dch[0].u_dsel/y[1]",
                     "s_d[0][2]", "s_d[1][2]", "dch[1].u_dsel/y[0]",
                     "s_d[0][3]", "dch[1].u_dsel/y[1]"]
    _, rev = _keyed_order(names, 1)
    assert [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in rev][:2] == ["s_d[0][3]", "dch[1].u_dsel/y[1]"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_band_without_chunked_registers_keeps_old_keys():
    names = [r"u/u_ring.s_d\[3\]\[9\]$_DFFE_PP_", r"u/u_ring.rp\[0\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[9\]$_DFFE_PP_"]
    w, out = _keyed_order(names, 0)
    assert w == "W=0"
    old = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    body = old + "foreach n {" + " ".join("{" + n + "}" for n in names) + "} { puts [cland_ffkey $n 0] }\n"
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    assert keys == ["u/u_ring.s_d|000000009|000000003|$_DFFE_PP_", r"u/u_ring.rp\[0\]$_DFF_P_",
                    "u/u_ring.s_d|000000009|000000000|$_DFFE_PP_"]


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_status_bits_above_bus_width_keep_raw_key():
    # HEAD st_str d ring: word bits 512..514 (above the 512-bit d_i bus) feed the plan-sited status stage at the band's
    # low corner; they keep the raw-name key instead of following bit 514 to the band's far end (r2r 537.8)
    proc = re.search(r"proc cland_ffkey \{nm \{rev 0\} \{wch 0\} \{nbits 0\}\} \{\n.*?\n\}\n", TCL, re.S).group(0)
    names = [r"u/u_ring.dch\[8\].u_dsel/y\[2\]$_DFF_P_", r"u/u_ring.dch\[7\].u_dsel/y\[63\]$_DFF_P_"]
    body = proc + "foreach n {" + " ".join("{" + n + "}" for n in names) + "} { puts [cland_ffkey $n 0 64 512] }\n"
    keys = subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split()
    assert keys == [names[0], "u/u_ring.s_d|000000511|999999998|$_DFF_P_"]
    assert "set nbits [expr {max($nbits,$bi+1)}]" in TCL
