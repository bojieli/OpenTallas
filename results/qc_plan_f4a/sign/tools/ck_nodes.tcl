# arrival at the input of every ot_ms_* clock cell (+ cell location, master) on RCX (SPEF) or GRT basis; and for RCX,
# per clock net routed length by layer (dbWire).  Env ODB SDC [SPEF] OT_CORNER OUT
set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] { read_liberty $f }
read_db $::env(ODB); read_sdc $::env(SDC)
if {[info exists ::env(SPEF)] && $::env(SPEF) ne ""} { read_spef $::env(SPEF) } else { set ::env(OT_RC_CAL) 0.8,0.9; source /work/cf/rc_cal.tcl; estimate_parasitics -global_routing }
set_propagated_clock [all_clocks]
report_worst_slack -max
set blk [ord::get_db_block]; set u [$blk getDbUnitsPerMicron]
set f [open $::env(OUT) w]
foreach cell [get_cells ot_ms_*] {
  set nm [get_full_name $cell]; set i [$blk findInst $nm]; set loc [$i getLocation]
  foreach p [get_pins -of_objects $cell -filter "direction==input"] {
    set a [get_property $p arrival_max_rise]
    set n [get_nets -of_objects $p]; set nn [get_full_name $n]
    set len {}
    puts $f [format "%s\t%s\t%.1f\t%.1f\t%s\t%s\t%s" $nm [get_property $cell ref_name] [expr [lindex $loc 0]*1.0/$u] [expr [lindex $loc 1]*1.0/$u] $a $nn $len]
  }
}
close $f; puts "NODES_DONE"; exit
