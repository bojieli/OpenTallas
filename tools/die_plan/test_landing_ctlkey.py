"""DIE-HEAD-43 c3 (FLOW-11 shared): ring control/status registers keyed next to the bus bit nearest the START pin."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs(*names):
    out = ""
    for n in names:
        m = re.search(r"^proc %s \{[^\n]*\n(?:.*?\n)??\}\n|^proc %s \{[^\n]*\}\n" % (n, n), TCL, re.S | re.M)
        out += m.group(0)
    return out


def _run(body):
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")


def test_nearest_bit_to_start_pin():
    body = _procs("cland_nearest_bit") + "puts [cland_nearest_bit {100 0} {{0 0 0} {1 90 5} {2 200 0}}]\n"
    assert _run(body)[0] == "1 15"


def _order(names, nbb, kb, rev=0):
    body = _procs("cland_kbit", "cland_ffkey", "cland_ctl_rekey") + \
        "set ffs {}\nforeach n {" + " ".join("{" + n + "}" for n in names) + "} { lappend ffs [list [cland_ffkey $n %d] $n] }\n" % rev + \
        "lassign [cland_ctl_rekey $ffs u/u_ring.s_d %d %d %d] nc ffs\nputs NC=$nc\n" % (kb, nbb, rev) + \
        "foreach p [lsort -dictionary -index 0 $ffs] { puts [lindex $p 1] }\n"
    out = [o for o in _run(body) if o]
    return out[0], [re.sub(r"\\|u/u_ring\.|\$_DFF\w*", "", o) for o in out[1:]]


def test_control_registers_follow_the_start_bit():
    names = [r"u/u_ring.arm_cnt\[0\]$_DFF_P_", r"u/u_ring.s_d\[0\]\[0\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[1\]$_DFFE_PP_",
             r"u/u_ring.s_d\[1\]\[1\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[2\]$_DFFE_PP_", r"u/u_ring.rp\[0\]$_DFF_P_",
             r"u/u_ring.s_d\[0\]\[5\]$_DFFE_PP_"]
    # bus width 3 (bits 0..2): bit 5 is a status bit above the bus -> moves with the controls; START nearest bit 1
    nc, order = _order(names, nbb=3, kb=1)
    assert nc == "NC=3"
    assert order == ["s_d[0][0]", "s_d[0][1]", "s_d[1][1]", "s_d[0][5]", "arm_cnt[0]", "rp[0]", "s_d[0][2]"]


def test_lsb_high_bus_reverses_bit_keys():
    names = [r"u/u_ring.ctl$_DFF_P_", r"u/u_ring.s_d\[0\]\[0\]$_DFFE_PP_", r"u/u_ring.s_d\[0\]\[1\]$_DFFE_PP_",
             r"u/u_ring.s_d\[0\]\[2\]$_DFFE_PP_"]
    nc, order = _order(names, nbb=3, kb=999999999 - 2, rev=1)
    assert nc == "NC=1" and order == ["s_d[0][2]", "ctl", "s_d[0][1]", "s_d[0][0]"]


def test_only_bands_with_a_start_pin_and_storage_are_rekeyed():
    assert 'if {$bn eq "cland_fstart_in_$cbus"} { set sx [list $cx $cy] }' in TCL
    assert "if {[llength $sx] && [llength $bxy] && $base ne {}} {" in TCL
    i = TCL.index(" set ffs [lmap pr $ffs {list [cland_ffkey [lindex $pr 0] $rev $wch $nbits] [lindex $pr 1]}]")
    assert i < TCL.index("lassign [cland_ctl_rekey $ffs $base $kb $nbb $rev] nc ffs") < TCL.index("set ordered [lsort -dictionary -index 0 $ffs]")
