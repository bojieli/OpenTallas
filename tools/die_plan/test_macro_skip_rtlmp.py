"""KW-FIX-45 11-12 (PHY MPL-0006): all-plan-fixed (hard wrapper) kits skip rtl_macro_placer; mixed/other kits are unchanged."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(HERE))
import gen_phys as G


def test_hard_wrapper_is_all_plan_fixed_and_other_types_are_not():
    assert G._macros_all_plan_fixed({"hard": True, "hard_cores": [{"inst": "u"}]}) is True
    assert G._macros_all_plan_fixed({"hard": False, "hard_cores": [{"inst": "u"}]}) is False
    assert G._macros_all_plan_fixed({"hard_cores": [{"inst": "u"}]}) is False          # ordinary partition with macros
    assert G._macros_all_plan_fixed({"hard": True, "hard_cores": []}) is False


def test_generator_wiring_is_conditional_on_all_fixed():
    src = (HERE / "gen_phys.py").read_text()
    assert 'export PRE_MACRO_PLACE_TCL = /work/macro_skip_rtlmp.tcl"] if macros and _macros_all_plan_fixed(t) else []' in src
    assert "if _macros_all_plan_fixed(t):" in src and "macro_skip_rtlmp.tcl" in src


def test_tcl_replaces_rtl_macro_placer_with_a_firm_noop():
    script = ("namespace eval ord {}\n"
              "set ::fixed 0\n"
              "proc ord::get_db_block {} { return blk }\n"
              "proc blk {cmd} { return {i1 i2} }\n"
              "proc i1 {cmd args} { if {$cmd eq \"getMaster\"} { return m1 }; if {$cmd eq \"setPlacementStatus\"} { incr ::fixed } }\n"
              "proc i2 {cmd args} { if {$cmd eq \"getMaster\"} { return m2 }; if {$cmd eq \"setPlacementStatus\"} { incr ::fixed } }\n"
              "proc m1 {cmd} { return 1 }\nproc m2 {cmd} { return 0 }\n"
              "proc rtl_macro_placer {args} { puts NATIVE }\n"
              "source %s\nrtl_macro_placer -halo_width 10\nputs \"fixed=$::fixed\"\n" % (HERE / "macro_skip_rtlmp.tcl"))
    out = subprocess.run(["tclsh"], input=script, capture_output=True, text=True).stdout
    assert "NATIVE" not in out and "OT_RTLMP_SKIP: all 1 macro(s) are plan-fixed" in out and "fixed=1" in out
