"""STA2204-1: the PRE_RESIZE hook (gp_noconverge_gate.tcl) must run under OpenSTA object semantics.

OpenSTA's [current_design] returns the top cell NAME (a string), not an object handle; get_full_name / get_property
on that string raises "[ERROR STA-2204] get_property <top> is not an object." and resize.tcl stops at 3_4 (make
Error 1).  The PLACE-FANOUT log line of KW-FIX-45 did exactly that in S81 wave src 590cbd5fd0 (fixed on main by
HEAD-94 be3be89cde88); every kit with OT_PLACE_MAX_FANOUT set died at 3_4_place_resized.  The tclsh test of the
gate (tools/autopilot/test_gp_noconverge_gate.py) never set OT_PLACE_MAX_FANOUT, so it could not see the bug.
These stubs model the two OpenSTA calls the hook makes, so a regression fails here instead of in place."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOK = HERE / "gp_noconverge_gate.tcl"

# OpenSTA semantics: current_design -> name string; get_full_name/get_property need a SWIG handle (_<hex>_p_<Type>).
STA_STUBS = r"""
proc current_design {} { return "dp_top" }
proc sta_is_object {x} { return [regexp {^_[0-9a-f]+_p_[A-Za-z]+$} $x] }
proc get_property {obj prop} {
  if {![sta_is_object $obj]} { error "\[ERROR STA-2204\] get_property $obj is not an object." }
  return dp_top
}
proc get_full_name {obj} { return [get_property $obj full_name] }
proc get_name {obj} { return [get_property $obj name] }
proc set_max_fanout {fo objs} { puts "STUB set_max_fanout $fo $objs" }
"""

pytestmark = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh")


def run(tmp_path, hook_text, fanout):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "gp_noconverge_gate.tcl").write_text(hook_text)
    drv = kit / "drv.tcl"
    # a script file, as OpenROAD sources the hook: a Tcl error ends the run before HOOK_DONE
    drv.write_text(STA_STUBS + f"source {kit}/gp_noconverge_gate.tcl\nputs HOOK_DONE\n")
    env = dict(os.environ, LOG_DIR=str(kit / "no_logs"))  # no 3_3 log: the NOCONVERGE part stays inert
    env.pop("OT_GPL_NOCONV", None)
    if fanout is None:
        env.pop("OT_PLACE_MAX_FANOUT", None)
    else:
        env["OT_PLACE_MAX_FANOUT"] = fanout
    r = subprocess.run(["tclsh", str(drv)], text=True, capture_output=True, env=env)
    return r.stdout + r.stderr


@pytest.mark.parametrize("fanout", ["64", "32"])
def test_fanout_branch_runs_to_the_end_under_sta_semantics(tmp_path, fanout):
    out = run(tmp_path, HOOK.read_text(), fanout)
    assert "STA-2204" not in out, out
    assert f"STUB set_max_fanout {fanout} dp_top" in out
    assert f"PLACE-FANOUT set_max_fanout {fanout} on design dp_top" in out
    assert "HOOK_DONE" in out


def test_fanout_unset_skips_branch(tmp_path):
    out = run(tmp_path, HOOK.read_text(), None)
    assert "STUB set_max_fanout" not in out and "HOOK_DONE" in out, out


def test_stubs_catch_the_590cbd5fd0_hook(tmp_path):
    """negative control: the S81 wave-src form of line 13 fails here exactly as it failed in resize.tcl"""
    old = HOOK.read_text().replace("on design [current_design] (place", "on [get_full_name [current_design]] (place")
    assert old != HOOK.read_text()
    out = run(tmp_path, old, "64")
    assert "[ERROR STA-2204] get_property dp_top is not an object." in out
    assert "HOOK_DONE" not in out


def test_no_object_accessor_on_current_design_in_hooks():
    """the same mistake in any die_plan Tcl hook (or Tcl emitted from gen_phys.py) is caught statically"""
    bad = re.compile(r"get_(full_name|name|property)\s+\[current_design\]")
    hits = [f"{p.name}:{i}" for p in sorted(HERE.glob("*.tcl")) + [HERE / "gen_phys.py"] if p.is_file()
            for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1) if bad.search(line)]
    assert not hits, hits
