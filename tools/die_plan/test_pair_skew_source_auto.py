"""DIE-HEAD-71 11-05: a clock on several source ports with different -source latency (HEAD l48ue per-port tap
windows: clk clk_t1..t4, early -24/-11/-9/0) has no single source insertion.  ot_ps_add_clock switches to the exact
per-path source mode instead of erroring (tag method only); OT_PS_SOURCE_AUTO=0 keeps the old error; one root keeps
the per-clock insertion; ot_ps_regs clears an automatic switch."""
import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = r"""
set ::ot_ps_lib_only 1
source @SOURCE@
proc get_full_name {o} {return $o}
proc get_property {obj prop} {
  if {$prop eq "clocks"} {return clk}
  if {$prop eq "sources"} {return $::srcs}
  return ""
}
proc ot_ps_ckarr {pin clk which {rf rise}} {
  if {[dict exists $::arr $pin]} {return [dict get $::arr $pin]}
  return 100.0
}
set ::ot_ps_method @METHOD@
set ::srcs {@SRCS@}
set ::arr [dict create clk 0.0 clk_t1 @T1@ clk_t2 -11.0]
set ::ot_ps_R {}; set ::ot_ps_by_clock {}; set ::ot_ps_insertion {}
if {[catch {ot_ps_add_clock u_a/CK rise} e]} {puts "ERR $e"; exit 0}
puts "BYPATH [expr {[info exists ::ot_ps_source_by_path] ? $::ot_ps_source_by_path : 0}] INS [dict size $::ot_ps_insertion]"
proc all_registers {args} {return {}}
ot_ps_regs
puts "AFTER [expr {[info exists ::ot_ps_source_by_path] ? $::ot_ps_source_by_path : 0}]"
"""


def run(method="tag", srcs="clk clk_t1 clk_t2", t1=-24.0, env=None):
    s = SCRIPT
    for k, v in dict(SOURCE=Path(__file__).with_name("pair_skew.tcl"), METHOD=method, SRCS=srcs, T1=t1).items():
        s = s.replace("@" + k + "@", str(v))
    e = dict(os.environ, **(env or {}))
    p = subprocess.run(["tclsh"], input=s, text=True, capture_output=True, check=True, env=e)
    return p.stdout


def test_multi_root_switches_to_per_path():
    out = run()
    assert "OT_PS_SOURCE_AUTO clock clk rise roots 3" in out
    assert "BYPATH 1 INS 0" in out and "AFTER 0" in out


def test_single_root_keeps_per_clock_insertion():
    out = run(srcs="clk clk_t1", t1=0.0)
    assert "OT_PS_SOURCE_AUTO" not in out and "BYPATH 0 INS 1" in out


def test_switch_off_is_old_error():
    out = run(env={"OT_PS_SOURCE_AUTO": "0"})
    assert "ERR clock clk has no unique rise source insertion arrival" in out


def test_property_fallback_still_errors():
    out = run(method="property")
    assert "ERR clock clk has no unique rise source insertion arrival" in out
