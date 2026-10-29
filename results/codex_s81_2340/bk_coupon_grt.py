#!/usr/bin/env python3
"""Prepare one frozen native-body bk_sel actual2W2S clock-only routing coupon."""
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=p.read_text();start=s.index('set_wire_rc -signal');end=s.index('create_clock -name vclk')
route='''source /inputs/pg_obs.tcl
set b [ord::get_db_block]
set tech [ord::get_db_tech]
set u [$tech getDbUnitsPerMicron]
set widths {}; set spaces {}
foreach ln {M8 M9} {
  set l [$tech findLayer $ln]
  lappend widths $ln [expr {2.0*[$l getWidth]/double($u)}]
  lappend spaces $ln [expr {2.0*[$l getSpacing]/double($u)}]
}
create_ndr -name OT_CLOCK_2W2S -width $widths -spacing $spaces
set nd [$b findNonDefaultRule OT_CLOCK_2W2S]
if {$nd eq "NULL"} {error "clock NDR creation failed"}
set nn 0
foreach n [$b getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 $n setNonDefaultRule $nd
 $n setSigType CLOCK
 incr nn
}
puts "OT_ACTUAL_CLOCK_NDR widths=$widths spacing=$spaces nets=$nn"
create_clock -name dck -period 833.333 [get_ports root]
set_routing_layers -signal M8-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
global_route -congestion_iterations 50 -critical_nets_percentage 0 -allow_congestion -verbose -congestion_report_file /out/congestion.rpt
write_guides /out/clock.guide
write_db /out/clock_grt.odb
delete_clock [get_clocks dck]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing
'''
s=s[:start]+route+s[end:];s=s.replace('/work/clock/arr_$::env(CORNER).txt','/out/arr_$::env(CORNER).txt');s=s.replace('puts OT_DONE','report_check_types -max_slew -min_pulse_width -violators\nputs OT_DONE')
Path(sys.argv[2]).write_text(s)
