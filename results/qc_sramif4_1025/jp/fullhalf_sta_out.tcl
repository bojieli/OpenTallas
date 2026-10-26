set C $::env(OT_CORNER)
set c [string tolower $C]
set B $::env(PHASE_NICK)
set EXPECT $::env(PHASE_FALL_COUNT)
read_db $::env(ODB)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_${c}.lib] {read_liberty $f}
read_sdc /work/constraint.sdc
source /work/cf/main/setRC_rcx_asap7.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
sta::worst_slack_cmd max
sta::worst_slack_cmd min
source /work/cf/mscts_core.tcl
ot_ms_pinmap
set pfile [open /work/run/results/asap7/$B/base/ot_face_flops.txt r]
set vals {}
foreach ln [split [read $pfile] "\n"] {
 if {$ln eq ""} continue
 set pn "[lindex [split $ln "\t"] 0]/CLK"
 set a [ot_ms_arr $pn max]
 if {$a ne ""} {lappend vals $a}
}
close $pfile
if {![llength $vals]} {error "no real pin-register clock arrivals"}
set sm 0.0;foreach a $vals {set sm [expr {$sm+$a}]}
set I [expr {$sm/[llength $vals]}]
set_clock_latency -source $I [get_clocks vclk]
puts "PHASE_BOUND $C I $I count [llength $vals]"
set neg {};set pos {};set mac {}
foreach cc [get_cells -hierarchical *] {
 set ref [get_property $cc ref_name]
 if {[string match "DFFL*" $ref]} {lappend neg $cc}
 if {[string match "DFFH*" $ref]} {lappend pos $cc}
 if {[string match "ot_sram_*" $ref]} {lappend mac $cc}
}
puts "PHASE_COHORT $C rising [llength $pos] falling [llength $neg] macro [llength $mac]"
if {[llength $neg]!=$EXPECT || [llength $mac]!=4} {error "incorrect phase cell cohort"}
proc phase_report {label from to} {
 foreach dly {max min} {
  puts "PHASE_PATH $::C $label $dly"
  set p [find_timing_paths -from $from -to $to -path_delay $dly -group_path_count 1 -endpoint_path_count 1]
  if {![llength $p]} {error "no actual halfcycle path $label $dly"}
  puts "PHASE_SLACK $::C $label $dly [get_property [lindex $p 0] slack]"
  report_checks -from $from -to $to -path_delay $dly -group_path_count 3 -endpoint_path_count 1 -format full_clock_expanded -digits 3
 }
}
phase_report rise_to_fall $pos $neg
phase_report fall_to_sram $neg $mac
puts "PHASE_ALL $C setup [sta::time_sta_ui [sta::worst_slack_cmd max]] hold [sta::time_sta_ui [sta::worst_slack_cmd min]]"
if {$C eq "FF"} {
 set paths [find_timing_paths -path_delay min -slack_max 0 -group_path_count 20000 -endpoint_path_count 1]
 set classes {};set file [open /out/fullhalf_hold_FF.tsv w]
 foreach p $paths {
  set sp [get_full_name [get_property $p startpoint]];set ep [get_full_name [get_property $p endpoint]]
  set kind internal;if {[string first / $sp]<0} {set kind input};if {[string first / $ep]<0} {set kind output}
  dict incr classes $kind;puts $file "$kind\t$sp\t$ep\t[get_property $p slack]"
 }
 close $file
 puts "PHASE_HOLD_CLASSES $C total[llength $paths] $classes"
}

exit
