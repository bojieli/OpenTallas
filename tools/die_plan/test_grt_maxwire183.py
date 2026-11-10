"""MAXWIRE-183 (DIE-S81-85 2026-11-09): grt_maxwire.tcl keeps the GRT183-RESUME wrapper in front of the max-wire body.

Serdes t14 5_1_grt died with GRT-0183 inside 'OT_MAXWIRE repair_design' and no OT_GRT183_RESUME_SAVED: the hook renamed
the wrapper away, so the class resume never ran.  tclsh only; the wrapper is a stub of the shape grt183_resume.tcl
installs (its name is checked against that file), the real grt_maxwire.tcl is sourced.
"""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCL = HERE / "grt_maxwire.tcl"
RESUME = HERE.parents[1] / "physical/common_flow/grt183_resume.tcl"
STUBS = r"""
set ::env(OT_MAXWIRE_UM) 100
proc log_cmd {args} { puts "LOG [join $args { }]" }
namespace eval sta { proc network_leaf_instance_count {} { return 7 } }
"""
BASE = "proc repair_design_helper {} { puts ORIG_BASE }\n"
WRAP = r"""
proc ot_g183_orig_repair_design_helper {args} { puts ORIG_BODY }
proc repair_design_helper {args} {
  puts WRAP_ENTER
  set rc [catch {uplevel 1 [linsert $args 0 ot_g183_orig_repair_design_helper]} msg opts]
  puts WRAP_EXIT
  return -options $opts $msg
}
"""
needs_tclsh = pytest.mark.skipif(shutil.which("tclsh") is None, reason="tclsh not installed")


def run(tmp_path, body):
    t = tmp_path / "t.tcl"
    t.write_text(STUBS + body + f"source {TCL}\nrepair_design_helper\n")
    return subprocess.run(["tclsh", str(t)], capture_output=True, text=True, check=True).stdout


def test_stub_matches_resume_hook_names():
    text = RESUME.read_text()
    assert "ot_g183_orig_$ot_g183_helper" in text
    assert re.search(r"foreach ot_g183_helper \{[^}]*\brepair_design_helper\b", text)


@needs_tclsh
def test_wrapper_kept_and_body_is_maxwire(tmp_path):
    out = run(tmp_path, WRAP)
    assert out.index("WRAP_ENTER") < out.index("OT_MAXWIRE repair_design") < out.index("WRAP_EXIT")
    assert "ORIG_BODY" not in out
    assert "LOG repair_design" in out and "-max_wire_length 100" in out


@needs_tclsh
def test_without_wrapper_behaviour_unchanged(tmp_path):
    out = run(tmp_path, BASE)
    assert "WRAP_ENTER" not in out and "ORIG_BASE" not in out
    assert "OT_MAXWIRE repair_design" in out and "-max_wire_length 100" in out
