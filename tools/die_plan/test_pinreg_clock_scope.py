"""Forwarded-ring writer clocks must not contaminate the local insertion census."""
from pathlib import Path
import subprocess
import pytest

SRC = Path(__file__).with_name("pinreg_measure.tcl")
STUBS = r"""
proc get_full_name {p} {return $p}
proc get_clocks {args} {return [lindex $args end]}
proc all_registers {args} {
  set n [lsearch -exact $args -clock]
  if {$n < 0} {return {local/CK writer/CK generated/CK}}
  switch [lindex $args [expr {$n+1}]] {
    clk {return {local/CK generated/CK}}
    fclk_in {return {writer/CK}}
    default {return {}}
  }
}
proc all_inputs {args} {return {data}}
proc all_outputs {} {return {out}}
proc get_fanout {args} {return {local/D writer/D generated/D}}
proc get_fanin {args} {return {local/Q writer/Q generated/Q}}
"""

def run(body):
    p = subprocess.run(["tclsh"], input=STUBS + "\nsource {" + str(SRC) + "}\n" + body,
                       capture_output=True, text=True)
    assert p.returncode == 0 and not p.stderr, p.stderr
    return p.stdout.strip()

def test_forwarded_writer_is_outside_local_clock_budget():
    assert run("puts [dict keys [ot_pinreg_set]]") == "generated local"

def test_forwarded_writer_can_be_measured_against_own_clock():
    assert run("puts [dict keys [ot_pinreg_set_for_clock fclk_in]]") == "writer"

def test_missing_clock_fails_closed():
    assert run('rename get_clocks old_get_clocks\nproc get_clocks {args} {return {}}\nputs [catch {ot_pinreg_set} message]\nputs $message') == "1\nOT_PINREG: missing unique clock clk"

def test_generated_descendants_use_clock_family_ownership():
    assert run("proc ot_cf_pins {clock} {return [list {local/CK generated/CK} {}]}\nputs [dict keys [ot_pinreg_set]]") == "generated local"

def test_single_clock_census_is_unchanged():
    assert run("rename all_registers old_all_registers\nproc all_registers {args} {return {local/CK writer/CK generated/CK}}\nputs [dict keys [ot_pinreg_set]]") == "generated local writer"


def test_declared_multiple_core_roots_are_unioned_without_forwarded_ring():
    body = """rename all_registers old_all_registers
proc all_registers {args} {
  set name [lindex $args end]
  if {$name eq "clk_cr_s"} {return {crs/CK}}
  if {$name eq "clk_xk"} {return {xk/CK}}
  return [old_all_registers {*}$args]
}
rename get_fanout old_get_fanout
proc get_fanout {args} {return {local/D writer/D generated/D crs/D xk/D}}
set ::ot_pinreg_clocks {clk clk_cr_s clk_xk}
puts [dict keys [ot_pinreg_set]]"""
    assert run(body) == "crs generated local xk"


@pytest.mark.parametrize("legacy_virtual", [False, True])
def test_multiroot_generator_declares_all_insertion_clock_families(tmp_path, legacy_virtual):
    import ast
    source = SRC.parents[2] / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"
    tree = ast.parse(source.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "multi_root_tcl_patches")
    ns = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), ns)
    (tmp_path / "core_face_post_synth.tcl").write_text(
        'if {$ot_fc_ck eq "" || $ot_fc_ck eq "NULL"} { error "OT_FCAP: clock port $::env(OT_CORE_CLK) has no net" }\n'
        + "  [$ci findITerm CLK] connect $ot_fc_ck\n" * 2)
    # Older anchor intentionally required by the existing generator's kit patch.
    gate = (SRC.with_name("postcts_gate.tcl")).read_text()
    if legacy_virtual:
        gate = gate.replace("set ot_pg_virtual {}", "set vck [lsearch -all -inline -not [all_clocks] [get_clocks clk]]\nset ot_pg_virtual {}")
    (tmp_path / "postcts_gate.tcl").write_text(gate)
    (tmp_path / "corners.tcl").write_text("set_propagated_clock [get_clocks clk]\n")
    ns["multi_root_tcl_patches"](tmp_path, {"roots": [{"clock": c} for c in ("clk", "clk_cr_s", "clk_xk")], "domain_of_bus": {}})
    assert "set ::ot_pinreg_clocks {clk clk_cr_s clk_xk}" in (tmp_path / "postcts_gate.tcl").read_text()
