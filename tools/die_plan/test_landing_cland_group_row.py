"""CLAND-RING-GROUP (SONNET-FIX-QC 11-19, lever 6): opt-in OT_CLAND_GROUP_ROW=1 keeps a bit's ring cells on one row."""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = (HERE / "landing_placement.tcl").read_text()


def test_default_off_and_call_sites():
    assert 'if {![info exists ::env(OT_CLAND_GROUP_ROW)] || $::env(OT_CLAND_GROUP_ROW) ne "1"} return' in TCL
    assert TCL.count("cland_group_prepare $ordered") == 1
    assert "dict exists $::cland_grp $name" in TCL
    assert "set ::cland_fill_dry 1; set ::cland_grp_busy 1" in TCL


def _proc():
    return re.search(r"proc cland_group_prepare \{ordered\} \{\n.*?\n\}\n", TCL, re.S).group(0)


@pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")
def test_group_prepare_marks_first_cell_of_each_bit_group(tmp_path):
    keys = []
    for bit in (0, 1):
        for slot in range(4):
            keys.append(("b|%09d|%09d|x" % (bit, slot), "c%d_%d" % (bit, slot)))
        keys.append(("b|%09d|999999998|y" % bit, "y%d" % bit))
    keys.append(("rawname", "raw0"))
    names = " ".join(n for _, n in keys)
    ordered = " ".join("{{%s} %s}" % (k, n) for k, n in keys)
    body = _proc() + "foreach n {" + names + "} { proc $n {m} \"return $n\" }\n"
    body += "set ::env(OT_CLAND_GROUP_ROW) 1\ncland_group_prepare {" + ordered + "}\n"
    body += "puts [llength [dict get $::cland_grp c0_0]]\nputs [llength [dict get $::cland_grp c1_0]]\n"
    body += "puts [dict size $::cland_grp]\nputs [dict exists $::cland_grp c0_1]\n"
    body += "set ::env(OT_CLAND_GROUP_ROW) 0\ncland_group_prepare {" + ordered + "}\nputs [info exists ::cland_grp]\n"
    f = tmp_path / "t.tcl"
    f.write_text(body)
    out = subprocess.run(["tclsh", str(f)], capture_output=True, text=True, check=True).stdout.split()
    assert out == ["5", "5", "2", "0", "0"]
