#!/usr/bin/env python3
"""DIE-KV-61/grt: add the DIE-KV-58 both-edge duty readout + SDF write before OT_DONE in a mk_combo_kv combo.tcl"""
import sys
p = sys.argv[1]; s = open(p).read()
extra = r"""set fh [open /out/duty_$::env(CORNER).txt w]
foreach p [get_ports t_*] { puts $fh "D [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}] [expr {833.333 - [get_property $p slack_max_fall]}] [get_property $p slew_max_rise] [get_property $p slew_max_fall]" }
close $fh
write_sdf -divider / /out/die_$::env(CORNER).sdf
puts OT_DONE
"""
assert s.count("puts OT_DONE") == 1
open(p, "w").write(s.replace("puts OT_DONE\n", extra))
