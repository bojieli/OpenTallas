# worst setup (TT) / hold (FF) slack per launch child -> capture child of the composition; env CORNER, DB, SDC
set C $::env(CORNER); set c [string tolower $C]
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
foreach l [glob $PLAT/lib/NLDM/*RVT_${C}*] { read_liberty $l }
foreach v {physical/s81_ph_views/closed/dsfd_engram_lkp/dsfd_engram_lkp physical/s81_ph_views/closed/dsfd_engram_sink/dsfd_engram_sink physical/s81_engc_tiles/views/ot_engc_t_win/ot_engc_t_win physical/s81_engc_tiles/views/ot_engc_t_io/ot_engc_t_io physical/s81_engc_tiles/views/ot_engc_t_ws/ot_engc_t_ws physical/s81_engc_tiles/views/ot_engc_t_pbb/ot_engc_t_pbb physical/s81_engc_tiles/views/ot_engc_t_pbc/ot_engc_t_pbc} { read_liberty /src/${v}_$c.lib }
read_db /base/$::env(DB)
read_sdc /base/$::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef /base/$::env(SPEF) } else { source $PLAT/setRC.tcl; estimate_parasitics -placement }
set_propagated_clock [get_clocks core_clk]
set kind [expr {$C eq "FF" ? "min" : "max"}]
set ends {u_win u_io u_ws u_sink u_lkp u_pb0 u_pb1 u_pb2}
proc ot_w {from to kind} {
  set ps [find_timing_paths -path_delay $kind -from $from -to $to -group_path_count 1 -sort_by_slack]
  if {![llength $ps]} { return "" }
  return [format %.1f [get_property [lindex $ps 0] slack]]
}
foreach a $ends {
  set fa [get_pins -filter "direction==output" $a/*]
  foreach bq $ends {
    if {$a eq $bq} continue
    set s [ot_w $fa [get_pins -filter "direction==input" $bq/*] $kind]
    if {$s ne ""} { puts "PAIR $C $kind $a $bq $s" }
  }
  set s [ot_w $fa [all_outputs] $kind]; if {$s ne ""} { puts "PAIR $C $kind $a OUT $s" }
  set s [ot_w [all_inputs -no_clocks] [get_pins -filter "direction==input" $a/*] $kind]; if {$s ne ""} { puts "PAIR $C $kind IN $a $s" }
}
# Dedicated local reset checks: stage-to-stage and conditioner output to
# hardened child reset are measured without multicycle or false-path waivers.
foreach child {win io ws pb1 pb0 pb2 lkp sink} {
  set regs [get_cells -quiet *u_rst_${child}*]
  if {![llength $regs]} { error "ENGC reset cells missing: $child" }
  set q [get_pins -of_objects $regs -filter "direction==output"]
  set d [get_pins -of_objects $regs -filter "direction==input"]
  set rpin rst
  if {$child in {lkp sink}} { set rpin rst_n }
  foreach pair [list [list STAGES $q $d] [list CHILD $q [get_pins u_${child}/$rpin]] [list ASYNC [get_ports {rst[0]}] $d]] {
    lassign $pair tag from to
    set v [ot_w $from $to $kind]
    puts "RESET $C $kind $child $tag $v"
  }
}
puts "PAIR $C $kind WNS [format %.1f [sta::worst_slack -$kind]]"
exit
