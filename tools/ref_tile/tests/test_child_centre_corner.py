"""Pure Tcl corner classification; no OpenROAD simulation required."""
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[3] / "physical/common_flow/child_centre_tap.tcl"


def test_child_corner_is_not_contaminated_by_unrelated_libraries():
    text = HOOK.read_text()
    proc = text[text.index("proc ot_cct_corner "):text.index("proc ot_cct_worst ")]
    script = """
proc get_lib_cells {args} {return $::child_cells}
proc get_full_name {o} {return $o}
proc get_libs {args} {return $::libs}
""" + proc + """
set child_cells {child_tt/CHILD child_ff/CHILD}
set libs {child_tt child_ff}
puts [ot_cct_corner CHILD WC]
lappend libs unrelated_ss
puts [ot_cct_corner CHILD WC]
set child_cells {child_ss/CHILD child_ff/CHILD}
puts [ot_cct_corner CHILD WC]
set child_cells {CHILD}
set libs {child_tt child_ff}
puts [ot_cct_corner CHILD WC]
puts [ot_cct_corner CHILD BC]
"""
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert run.stderr == ""
    assert run.stdout.splitlines() == ["tt", "tt", "ss", "tt", "ff"]
