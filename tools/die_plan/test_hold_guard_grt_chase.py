"""QC-HOLD-CHASE 11-25: the GRT hold guard chases to the margin by default; OT_HOLD_CHASE_MARGIN=0 restores the early stops."""
import shutil
import subprocess
from pathlib import Path

import pytest

T = (Path(__file__).resolve().parent / "hold_guard_grt.tcl").read_text()


def test_defaults_chase_margin():
    assert "OT_HOLD_CHASE_MARGIN" in T
    assert 'set ::ot_hg_stop_dflt 0; set ::ot_hg_stall_dflt "margin"' in T
    assert "OT_HOLD_DONE_STOP $::ot_hg_stop_dflt" in T
    assert "OT_HOLD_ZERO_VIOL_STOP $::ot_hg_stop_dflt" in T
    assert "$hm : $::ot_hg_stall_dflt" in T


def test_window_stall_and_budget_stops_kept():
    assert "OT_HOLD_STALL NEEDS_RTL stage=grt" in T
    assert "total buffer budget $tot % used, stop" in T
    assert "OT_HOLD_SETUP_GUARD stop" in T


@pytest.mark.skipif(not shutil.which("tclsh"), reason="no tclsh")
def test_tcl_syntax_balanced():
    r = subprocess.run(["tclsh"], input="set f [open " + str(Path(__file__).resolve().parent / "hold_guard_grt.tcl") + "]; set s [read $f]; puts [info complete $s]", capture_output=True, text=True)
    assert r.stdout.strip() == "1", r.stderr
