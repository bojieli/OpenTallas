# worst setup (TT) / hold (FF) slack per launch child -> capture child of the composition; env CORNER, DB, SDC
set C $::env(CORNER); set c [string tolower $C]
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_${C}*] { read_liberty $l }
foreach v {physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink physical/s81_engc_tiles/views/ot_engc_t_win/ot_engc_t_win physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io physical/s81_engc_tiles/views/ot_engc_t_ws/ot_engc_t_ws physical/s81_engc_tiles/views/ot_engc_t_pbb/ot_engc_t_pbb physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc} { read_liberty /src/${v}_$c.lib }
read_db /base/$::env(DB)
read_sdc /base/$::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef /base/$::env(SPEF) } else { source $PLAT/setRC.tcl; estimate_parasitics -placement }
set_propagated_clock [get_clocks core_clk]
set kind $::env(PATH_DELAY)
# Owner fixed same-level/cross-level setup150/210; H1 hold100.
# Use210 conservatively for all core paths, then retain pair-specific raw checks separately.
if {$::env(STRICT_BUDGET) ne "raw"} {
  set_clock_uncertainty -setup 60 [all_clocks]
  set_clock_uncertainty -setup $::env(STRICT_BUDGET) -from [get_clocks core_clk] -to [get_clocks core_clk]
  set_clock_uncertainty -hold 100 [all_clocks]
}

foreach pair {{win status_win} {pb0 xtrans_pb0}} {
 lassign $pair child leaf
 set q {}; set controls {}
 foreach pin [get_pins -of_objects [get_cells -quiet *u_rst_${child}*]] {
  if {[string match */QN [get_full_name $pin]]} {lappend q $pin}
 }
 foreach pin [get_pins -of_objects [get_cells -quiet *u_${leaf}*]] {
  if {[string match */RESETN [get_full_name $pin]]} {lappend controls $pin}
 }
 puts "RESET_TO_RELAY $C $kind $child $leaf n=[llength $controls]"
 report_checks -path_delay $kind -from $q -to $controls -group_path_count 3 -format full_clock_expanded -fields {slew cap fanout input net} -digits 3
}
exit
