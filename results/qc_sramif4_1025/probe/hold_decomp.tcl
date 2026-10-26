# PATH-QC-SRAMIF4 diagnostic (read-only on the kit ODB): decompose FF input hold, legacy -40 vs IO-HOLD A (+12.5 vectors)
set C FF
set B $::env(PHASE_NICK)
read_db $::env(ODB)
foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${C}_nldm_*.lib*]] { read_liberty $f }
foreach f [glob -nocomplain /work/macros/*_ff.lib] {read_liberty $f}
read_sdc /work/constraint.sdc
source /work/cf/main/setRC_rcx_asap7.tcl
estimate_parasitics -global_routing
set_propagated_clock [all_clocks]
source /work/cf/mscts_core.tcl
ot_ms_pinmap
set pfile [open /work/run/results/asap7/$B/base/ot_face_flops.txt r]
set vals {}
foreach ln [split [read $pfile] "\n"] {
 if {$ln eq ""} continue
 set a [ot_ms_arr "[lindex [split $ln "\t"] 0]/CLK" max]
 if {$a ne ""} {lappend vals $a}
}
close $pfile
set sm 0.0;foreach a $vals {set sm [expr {$sm+$a}]}
set I [expr {$sm/[llength $vals]}]
set_clock_latency -source $I [get_clocks vclk]
puts "BOUND I $I n [llength $vals] min [tcl::mathfunc::min {*}$vals] max [tcl::mathfunc::max {*}$vals]"
proc census {tag} {
 set paths [find_timing_paths -path_delay min -slack_max 0 -group_path_count 20000 -endpoint_path_count 1]
 set n 0; set w 0
 foreach p $paths { set sp [get_full_name [get_property $p startpoint]]; if {[string first / $sp]<0} {incr n}; set w [expr {min($w,[get_property $p slack])}] }
 puts "CENSUS $tag fail [llength $paths] input $n worst $w"
}
census legacy
report_checks -path_delay min -from [all_inputs -no_clocks] -format full_clock_expanded -digits 3
# IO-HOLD A frame: vector inputs = plan sender contract +12.5, scalars keep -40
set vec {}; set sca {}
foreach pt [all_inputs -no_clocks] {
 set n [get_full_name $pt]
 if {[regexp {\[} $n]} {lappend vec $pt} else {lappend sca $pt}
}
set_input_delay -min 12.5 -clock vclk $vec
census ioholdA_vec12.5
foreach v {20 25 30 35 45} {
 set_input_delay -min $v -clock vclk $vec
 census sender$v
}
set_input_delay -min 12.5 -clock vclk $vec
foreach p [find_timing_paths -path_delay min -slack_max 0 -group_path_count 50 -endpoint_path_count 1] {
 puts "A_FAIL [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]] [get_property $p slack]"
}
report_checks -path_delay min -through [lindex $vec 0] -format full_clock_expanded -digits 3
puts "SCALARS [llength $sca]: [join [lmap s $sca {get_full_name $s}] { }]"
exit
