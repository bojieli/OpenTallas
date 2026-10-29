foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /work/macros/*_tt.lib] { read_liberty $l }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
foreach i [get_cells -quiet {h16_* h15_* tb_* *tapbal* *OT_TAP*}] {
  set n [get_full_name $i]; set oi [[ord::get_db_block] findInst $n]
  set b [$oi getBBox]; set a [get_pins -quiet $n/A]
  set y [get_pins -quiet $n/Y]
  puts "CELL $n [[$oi getMaster] getName] [expr ([$b xMin]+[$b xMax])/2000.0] [expr ([$b yMin]+[$b yMax])/2000.0] A [get_property $a arrival_max_rise] sA [get_property $a slew_max_rise] Y [get_property $y arrival_max_rise] sY [get_property $y slew_max_rise]"
}
# driver of the clock path into h15_rs
set p [get_pins h15_rs/A]
puts "RSDRV [get_full_name [get_pins -of_objects [get_nets -of_objects $p] -filter direction==output]] "
