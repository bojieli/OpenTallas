"""CLAND-BIN 11-15 (FABLE-GENBUG G6): ft station hops over reach + 5 % are counted, attributed to a slot and a cause."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

TCL = (Path(__file__).resolve().parent / "face_flops.tcl").read_text()
pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def _procs(*names):
    out = ""
    for n in names:
        m = re.search(r"^proc %s \{[^\n]*\n(?:.*?\n)??\}\n|^proc %s \{[^\n]*\}\n" % (n, n), TCL, re.S | re.M)
        assert m, n
        out += m.group(0)
    return out


def _run(body):
    return subprocess.run(["tclsh"], input=body, capture_output=True, text=True, check=True).stdout.split("\n")


PRE = "set ff_dbu 1000; set ff_lane_max 0.0; set ff_lane_n405 0\nset ff_lane_n_gate 0; set ff_lane_slotmax {}; set ff_lane_cur s1; set ff_lane_disp_n 0; set ff_lane_disp_max 0.0; set ff_lane_over_disp 0\n"


def test_gate_counts_over_reach_plus_five_percent_and_attributes_cause():
    body = PRE + _procs("ff_lane_init", "ff_lane_reach", "ff_lane_disp", "ff_lane_hop") + \
        "ff_lane_disp {0 0} {0 100000}\nff_lane_hop {0 0} {410000 0}\nff_lane_hop {0 0} {430000 0}\n" \
        "puts \"$ff_lane_n405 $ff_lane_n_gate $ff_lane_over_disp $ff_lane_disp_n [dict get $ff_lane_slotmax s1]\"\n"
    assert _run(body)[0] == "2 1 1 1 430.0"   # 410 > 405 counted, only 430 > 425.25 gated; its station was displaced 100 um


def test_reach_is_configurable():
    body = PRE + "set ::env(OT_FT_REACH) 300\n" + _procs("ff_lane_init", "ff_lane_reach", "ff_lane_disp", "ff_lane_hop") + \
        "ff_lane_hop {0 0} {320000 0}\nputs $ff_lane_n_gate\n"
    assert _run(body)[0] == "1"


def test_gate_is_advisory_unless_asked():
    assert 'eq "1"} { error "OT_FT_LANE_GATE:' in TCL
    assert "OT_FT_LANE_GATE $ff_lane_verdict:" in TCL
    assert TCL.count("ff_lane_disp $xy $got") == 2          # landed and unlanded paths both measured
