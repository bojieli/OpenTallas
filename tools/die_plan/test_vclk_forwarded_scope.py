"""Actual clock ownership controls the boundary mean; names never exempt flops."""
from pathlib import Path
import subprocess

HERE = Path(__file__).parent


def measure(tmp_path, tag=True, extra_root=False):
    (tmp_path / "constraint.sdc").write_text(
        "# OT_FWD_RING_INPUTS forwarded data[*]\n" if tag else "# ordinary kit\n")
    script = r'''
proc get_full_name {o} {return $o}
proc all_clocks {} {return {clk derived forwarded vclk}}
proc get_clocks {args} {return [lindex $args end]}
proc all_inputs {args} {return {clk_pin data}}
proc all_outputs {} {return output}
proc all_registers {args} {
  switch [lindex $args 0] {
    -clock_pins {return {a/CK b/CK renamed/CK}}
    -data_pins {return {a/D b/D renamed/D}}
    -async_pins {return {}}
  }
}
proc get_fanout {args} {return {a/D b/D renamed/D}}
proc get_fanin {args} {return {a/Q b/Q renamed/Q}}
proc ot_cf_refresh {} {}
proc ot_cf_root {c} {
  if {$c eq "derived" && !$::extra_root} {return clk}
  return $c
}
proc ot_cf_wire {p c args} {
  switch $p {a/CK {return 300} b/CK {return 400} renamed/CK {return 100}}
}
proc get_property {o k} {
  if {$k eq "sources"} {if {$o eq "vclk"} {return {}}; return clk_pin}
  if {$k eq "clocks"} {
    switch $o {a/CK {return clk} b/CK {return derived} renamed/CK {return forwarded}}
  }
  error "unexpected property $o $k"
}
'''
    script += f"\nset extra_root {int(extra_root)}\nsource {{{HERE / 'vclk_measured_hold.tcl'}}}\n"
    script += f"set ::ot_vmh_dir {{{tmp_path}}}\nputs [ot_vmh_pinreg_mean]\n"
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert not run.stderr, run.stderr
    return run.stdout.strip()


def test_forwarded_writer_excluded_but_generated_local_kept(tmp_path):
    assert measure(tmp_path) == "350.0 2 0 1"


def test_without_forwarded_declaration_legacy_census_unchanged(tmp_path):
    assert measure(tmp_path, tag=False) == "266.6666666666667 3 0 3"


def test_other_independent_core_family_is_not_silently_dropped(tmp_path):
    assert measure(tmp_path, extra_root=True) == "350.0 2 0 2"


def native(tmp_path, tag):
    """Two families at the boundary: clk through the seam input, pad_ck only through a native pad input."""
    (tmp_path / "constraint.sdc").write_text(tag)
    script = r"""
proc get_full_name {o} {return $o}
proc all_clocks {} {return {clk pad_ck vclk}}
proc get_clocks {args} {return [lindex $args end]}
proc get_ports {args} {set s [lindex $args end]; if {$s eq {pad[*]}} {return {pad[0] pad[1]}}; return {}}
proc all_inputs {args} {return {clk_pin data pad[0] pad[1]}}
proc all_outputs {} {return output}
proc all_registers {args} {
  switch [lindex $args 0] {
    -clock_pins {return {a/CK r/CK}}
    -data_pins {return {a/D r/D}}
    -async_pins {return {}}
  }
}
proc get_fanout {args} {
  set from [lindex $args [expr {[lsearch $args -from] + 1}]]
  set out {}
  if {"data" in $from} {lappend out a/D}
  if {{pad[0]} in $from || {pad[1]} in $from} {lappend out r/D}
  return $out
}
proc get_fanin {args} {return {a/Q}}
proc ot_cf_refresh {} {}
proc ot_cf_root {c} {return $c}
proc ot_cf_wire {p c args} {switch $p {a/CK {return 300} r/CK {return 900}}}
proc get_property {o k} {
  if {$k eq "sources"} {if {$o eq "vclk"} {return {}}; return clk_pin}
  if {$k eq "clocks"} {switch $o {a/CK {return clk} r/CK {return pad_ck}}}
  error "unexpected property $o $k"
}
"""
    script += f"\nsource {{{HERE / 'vclk_measured_hold.tcl'}}}\n"
    script += f"set ::ot_vmh_dir {{{tmp_path}}}\nif {{[catch {{puts [ot_vmh_pinreg_mean]}} e]}} {{puts \"ERR $e\"}}\n"
    run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
    assert not run.stderr, run.stderr
    return run.stdout.strip()


def test_native_pad_capture_registers_leave_the_vclk_mean(tmp_path):
    assert native(tmp_path, "# OT_NATIVE_PAD_INPUT pad_ck pad[*] -265.0 166.6\n") == "300.0 1 0 1"


def test_undeclared_pad_family_still_reports_two_clocks(tmp_path):
    assert native(tmp_path, "# ordinary kit\n") == "600.0 2 0 2"


def test_malformed_or_empty_native_pad_tag_fails_closed(tmp_path):
    assert native(tmp_path, "# OT_NATIVE_PAD_INPUT pad_ck pad[*] -265.0\n").startswith("ERR OT_VCLK_MEASURED_HOLD: malformed")
    assert native(tmp_path, "# OT_NATIVE_PAD_INPUT pad_ck nope[*] -265.0 166.6\n").startswith("ERR OT_VCLK_MEASURED_HOLD: empty")
