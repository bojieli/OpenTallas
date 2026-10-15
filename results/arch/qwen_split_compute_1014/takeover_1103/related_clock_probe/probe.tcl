read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /work/probe.lef
read_liberty /work/probe.lib
read_verilog /work/probe.v
link_design probe
source /work/clocks.tcl
foreach pair {{a0/q b0/d} {b0/q c0/d} {c0/q a0/d}} {
 lassign $pair launch capture
 foreach kind {max min} {
  set paths [find_timing_paths -from $launch -to $capture -path_delay $kind]
  if {[llength $paths] == 0} {error "source related clock path missing: $pair $kind"}
  set slack [get_property [lindex $paths 0] slack]
  if {![string is double -strict $slack] || abs($slack)>1e8} {error "nonfinite related clock path: $pair $kind $slack"}
  puts "RELATED_CLOCK_PATH $launch -> $capture $kind slack=$slack"
  report_checks -from $launch -to $capture -path_delay $kind -format full_clock_expanded -digits 6
 }
}
puts RELATED_6_5_1_ALL_PATHS_PASS
exit
