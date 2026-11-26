from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from gen_phys import isolated_pg_stripe_cut_tcl, reserved_pg_cut_tcl


STRIPE = {"net": "VDD", "layer": "M5", "rect_um": [12.0, 13.0, 12.12, 13.27]}


def plan_with(rows):
    return SimpleNamespace(types={"T": {"outline_um": [100, 100], "clock": {"pg_isolated_stripes": rows}}})


def test_no_opt_in_leaves_reserved_rows_literal():
    assert isolated_pg_stripe_cut_tcl(plan_with([]), "T") == ""
    assert "foreach r {\n{1 2 3 4 {5}}\n} {" in reserved_pg_cut_tcl([([1, 2, 3, 4], [5])])


def test_typed_stripe_uses_dynamic_stock_windows():
    script = isolated_pg_stripe_cut_tcl(plan_with([STRIPE]), "T")
    assert "{VDD 5 {12 13 12.12 13.27}}" in script
    assert "foreach r $kcg_windows {" in script
    assert "$kc_cut != [llength $kcg_windows] || $kc_piece || $kc_via" in script


@pytest.mark.parametrize(
    "rows",
    [[{**STRIPE, "layer": "M2"}],
     [{**STRIPE, "rect_um": [12.12, 13.0, 12.12, 13.27]}],
     [STRIPE, {**STRIPE, "net": "VSS"}]],
)
def test_invalid_or_duplicate_boxes_are_refused(rows):
    with pytest.raises(ValueError, match="isolated PG stripe"):
        isolated_pg_stripe_cut_tcl(plan_with(rows), "T")


@pytest.mark.skipif(not shutil.which("tclsh"), reason="requires Tcl")
def test_native_guard_selects_only_exact_unattached_box(tmp_path):
    guard = Path(__file__).with_name("pg_isolated_stripes.tcl")
    tcl = tmp_path / "guard.tcl"
    tcl.write_text(guard.read_text() + r"""
namespace eval ord { proc get_db_block {} { return block } }
proc block {method args} {
  switch $method {
    getDbUnitsPerMicron { return 1000 }
    findNet { return [expr {$args eq {VDD} ? "vdd" : "NULL"}] }
    getInsts { return {} }
    default { error "unexpected block method $method" }
  }
}
proc vdd {method} {
  switch $method {
    getSWires { return {wire} }
    getBTerms { return {} }
    default { error "unexpected VDD method $method" }
  }
}
proc wire {method} {
  if {$method ne "getWires"} { error "unexpected wire method $method" }
  return $::boxes
}
proc m5 {method} {
  if {$method ne "getName"} { error "unexpected layer method $method" }
  return M5
}
proc wire_box {bounds method} {
  switch $method {
    xMin { return [lindex $bounds 0] }
    yMin { return [lindex $bounds 1] }
    xMax { return [lindex $bounds 2] }
    yMax { return [lindex $bounds 3] }
    getWireShapeType { return STRIPE }
    isVia { return 0 }
    getTechLayer { return m5 }
    default { error "unexpected box method $method" }
  }
}
interp alias {} exact {} wire_box {12000 13000 12120 13270}
interp alias {} attached {} wire_box {12000 13270 12120 14000}
set expected {{VDD 5 {12 13 12.12 13.27}}}
set boxes {exact}
if {[kcg_exact_windows $expected] ne {{12 13 12.12 13.27 5}}} { error "exact target not selected" }
set boxes {attached}
if {[llength [kcg_exact_windows $expected]]} { error "absent target cut another shape" }
set boxes {exact attached}
if {![catch {kcg_exact_windows $expected} why] || ![string match {*same-layer PG metal*} $why]} {
  error "touching metal was not refused"
}
if {[kcg_may_remove_via {1 2} 5 {5 6}]} { error "followpin via misclassified" }
if {![kcg_may_remove_via {4 5} 5 {5 6}]} { error "contact via missed" }
if {![kcg_may_remove_via {2 3} 5 {5 6}]} { error "unanchored lower via missed" }
if {[kcg_may_remove_via {2 3} 5 {3 5 6}]} { error "lower surviving anchor ignored" }
puts {GUARD_FIXTURE_PASS}
""")
    result = subprocess.run(["tclsh", str(tcl)], capture_output=True, text=True, check=True)
    assert "GUARD_FIXTURE_PASS" in result.stdout
