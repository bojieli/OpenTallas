#!/usr/bin/env python3
"""DIE-S81-13: patch a mk_combo_dcm.py combo.tcl for an inverter clock tree (die_trial --clock-cell inv/inv2), same
readout as DIE-QC-11 mk_clkfirst.py: per-instance output polarity from ctree.v; the N readout takes the edge that carries
the source RISING edge (fall at an odd-parity output); F lines = tap fall/rise arrivals (duty readout); + MPW report.
usage: patch_combo_inv.py CTREE_V COMBO_TCL"""
import re, sys
cv = open(sys.argv[1]).read(); fn = sys.argv[2]; tail = open(fn).read()
drv = {}
for mm in re.finditer(r"^\s+(\S+) (\S+) \(\.A\((\S+)\), \.Y\((\S+)\)\);", cv, re.M):
    drv[mm.group(4)] = (mm.group(1), mm.group(2), mm.group(3))
par = {}


def parity(net):
    st = []
    while net != "root" and net not in par:
        st.append(net)
        net = drv[net][2]
    v = par.get(net, 0)
    for n_ in reversed(st):
        v = (v + ("INV" in drv[n_][0])) % 2
        par[n_] = v
    return v


odd = sorted("ck_" + drv[n_][1] for n_ in drv if parity(n_))
oddtcl = "set ot_odd [dict create " + " ".join(f"{x} 1" for x in odd) + "]\n"
assert tail.count("set fh [open") == 1
tail = tail.replace("set fh [open", oddtcl + "set fh [open", 1)
old = 'puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_rise] [get_property $q arrival_min_rise]'
assert tail.count(old) == 1
tail = tail.replace(old, 'set e [expr {[dict exists $ot_odd [get_full_name $i]] ? "fall" : "rise"}]; puts $fh "N [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$e] [get_property $q arrival_min_$e]', 1)
old = 'foreach p [get_ports t_*] { puts $fh "T '
assert tail.count(old) == 1
tail = tail.replace(old, 'foreach p [get_ports t_*] { puts $fh "F [get_full_name $p] [expr {833.0 - [get_property $p slack_max_fall]}] [expr {833.0 - [get_property $p slack_max_rise]}] [get_property $p slew_max_fall]" }\n' + old, 1)
tail = tail.replace("puts OT_DONE", "report_check_types -min_pulse_width -violators\nputs OT_DONE", 1)
tp = [n_ for n_ in drv if n_.startswith("t_")]
bad = [n_ for n_ in tp if parity(n_)]
open(fn, "w").write(tail)
print("odd-parity clock instances", len(odd), "tap nets", len(tp), "odd-parity taps", len(bad))
