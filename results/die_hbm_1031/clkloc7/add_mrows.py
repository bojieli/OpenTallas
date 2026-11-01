#!/usr/bin/env python3
"""HBM-CLKLOC-7: add polarity-resolved node FALL rows (M cell late early, as die_trial.clock_edge_readout) to a
mk_clkfirst clk.tcl whose readout writes only F/T/N rows, so tap_fall_merge.py --tree gets measured fall arrivals on
every clock node (start retime flops on virtual tree nodes may then sample on the fall edge).  Drops write_guides.
GRT is deterministic: the C12e rerun reproduced every T/N row byte-for-byte.  usage: add_mrows.py CLK_TCL (in place)"""
import sys
p = sys.argv[1]
s = open(p).read()
i = s.index("foreach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; set a")
j = s.index("\n", i)
m = ("\nforeach i [get_cells ck_*] { set q [get_pins [get_full_name $i]/Y]; "
     "set g [expr {[dict exists $ot_odd [get_full_name $i]] ? \"rise\" : \"fall\"}]; "
     "puts $fh \"M [string range [get_full_name $i] 3 end] [get_property $q arrival_max_$g] [get_property $q arrival_min_$g]\" }")
s = s[:j] + m + s[j:]
s = s.replace("write_guides /out/route_$::env(CORNER).guide\n", "")
open(p, "w").write(s)
