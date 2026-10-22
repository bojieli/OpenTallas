#!/usr/bin/env python3
"""Pure Tcl control check for shared compensation; no hardware simulation."""
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[3]
hook = root / "tools/qwen_cluster/cb16_km/cb16_ckbranch.tcl"
base = root / "tools/qwen_cluster/cb16_km/cb16_ckring3.tcl"
script = hook.read_text().replace("source /src/tools/qwen_cluster/cb16_km/cb16_ckring3.tcl", "source {" + str(base) + "}")
script += """
set ::ot_ckb_children {root {left right} left {a b} right {c d} a {} b {} c {} d {}}
set ::ot_ckb_rho 0.75
set ::ot_ckb_requests {}
set result [ot_ckb_need root {a {100 75} b {100 75} c {200 150} d {200 150}}]
if {$result ne {200 150}} {error "bad root target: $result"}
if {[dict size $::ot_ckb_requests] != 1 || ![dict exists $::ot_ckb_requests left]} {error "compensation copied to leaves: $::ot_ckb_requests"}
if {[dict get $::ot_ckb_requests left] != 100.0} {error "bad shared compensation"}
set ::ot_ckb_requests {}
ot_ckb_need root {a {200 150} b {200 150} c {200 150} d {200 150}}
if {[dict size $::ot_ckb_requests]} {error "balanced tree received pads"}
puts "SHARED_COMPENSATION PASS: sibling deficit shared once; balanced tree identity"
"""
run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
assert not run.stderr, run.stderr
print(run.stdout, end="")
