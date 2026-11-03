set C $::env(OT_CORNER); set c [string tolower $C]
set L /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
read_db $::env(ODB)
foreach f [lsort [glob $L/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /kit/macros/*_${c}.lib] { read_liberty $f }
read_sdc $::env(SDC)
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {$::env(PARA)} { estimate_parasitics -placement }
if {$::env(PROP)} { set_propagated_clock [all_clocks] }
set mode $::env(MODE)
# class histogram of violating endpoints: strip indices
set paths [find_timing_paths -path_delay $mode -group_path_count 200000 -endpoint_path_count 1 -slack_max 100000]
array set cls {}
array set worst {}
foreach p $paths {
  set e [get_full_name [get_property $p endpoint]]
  set s [expr {[get_property $p slack]}]
  set sp [get_full_name [get_property $p startpoint]]
  regsub -all {\[[0-9]+\]} $e {[*]} k; regsub -all {\$_[A-Z0-9_]+} $k {} k
  regsub -all {\[[0-9]+\]} $sp {[*]} k2; regsub -all {\$_[A-Z0-9_]+} $k2 {} k2
  set k "$k2 -> $k"
  if {![info exists cls($k)]} { set cls($k) 0; set worst($k) 0 }
  incr cls($k); if {$s < $worst($k)} { set worst($k) $s }
}
puts "OT_PROBE mode=$mode nviol=[llength $paths]"
foreach k [lsort [array names cls]] { puts [format "CLS %6d %8.1f %s" $cls($k) $worst($k) $k] }
