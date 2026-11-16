"""KIT-OPS-6 lever 7: known-answer tests for the pure hold-guard procs of tools/orfs_hold_mm.tcl (ot_hm_buffers, ot_hm_decide, ot_pin_class) run in
tclsh (no OpenROAD needed: the procs are extracted from the real file, so a change to them is what the test sees)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SRC = (Path(__file__).resolve().parents[2] / "orfs_hold_mm.tcl").read_text()
needs_tcl = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def proc(name):
    m = re.search(r"^proc %s \{.*?(?=^proc |^# |\Z)" % re.escape(name), SRC, re.S | re.M)
    assert m, name
    return m.group(0)


def tcl(body):
    code = proc("ot_hm_buffers") + proc("ot_hm_decide") + proc("ot_pin_class") + body
    return subprocess.run(["tclsh"], input=code, capture_output=True, text=True, check=True).stdout.strip()


@needs_tcl
def test_projected_buffers_one_per_buf_ps_of_deficit_per_endpoint():
    # margin 10, buffer 10 ps: slack -5 -> 2 buffers, 0 -> 1, 10 and 20 -> 0
    assert tcl("puts [ot_hm_buffers {-5 0 10 20} 10 10]") == "3"
    assert tcl("puts [ot_hm_buffers {} 10 10]") == "0"


@needs_tcl
def test_decide_keeps_the_margin_within_limits_and_drops_it_over_limits():
    # (hm worst n_in buffers core_um2 buf_area max_ep max_pts floor)
    assert tcl("puts [lindex [ot_hm_decide 50 -3 100 100 100000 0.1 10000 8 10] 2]") == "within limits"
    assert tcl("puts [lindex [ot_hm_decide 50 -3 100 100 100000 0.1 10000 8 10] 0]") == "50"
    # 20,000 endpoints in the margin > 10,000: new margin = max(floor, |worst| + floor) = 13
    assert tcl("puts [lindex [ot_hm_decide 50 -3 20000 100 100000 0.1 10000 8 10] 0]") == "13.0"
    # a margin already at the floor is never reduced
    assert tcl("puts [lindex [ot_hm_decide 10 -3 20000 100 100000 0.1 10000 8 10] 0]") == "10"
    # utilisation points over the limit: 100000 buffers x 0.1 um2 over 100000 um2 = 10 points > 8
    assert "util points" in tcl("puts [lindex [ot_hm_decide 50 0 10 100000 100000 0.1 10000 8 10] 2]")


@needs_tcl
def test_pin_class_splits_ports_from_register_pins():
    assert tcl("puts [ot_pin_class d_in]") == "port" and tcl("puts [ot_pin_class u_r/ff/D]") == "reg"
