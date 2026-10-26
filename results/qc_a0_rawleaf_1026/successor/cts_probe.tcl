# Diagnostic placement-RC CTS report; never a routed sign-off or die freeze.
set c $::env(CORNER)
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_${c}_nldm*.lib*] {
 if {![string match *FAKE* $l]} {read_liberty $l}
}
read_db /work/run/results/asap7/lsl_rawfault_m3/base/4_cts.odb
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
source /work/setRC_rcx.tcl
estimate_parasitics -placement
sta::worst_slack_cmd max
sta::worst_slack_cmd min
proc norm {s} {return [string map [list "\\" ""] $s]}
proc mean {v} {return [expr {[tcl::mathop::+ {*}$v]/double([llength $v])}]}
set all {}; set ar {}; set byname [dict create]
set f [open /work/clock_$c.tsv w]
foreach cell [get_cells * -filter {ref_name=~DFF*}] {
 set p [get_pins -of_objects $cell -filter {name==CLK}]
 if {[llength $p] != 1} {error "DFF clock missing"}
 set a [expr {[get_property $p arrival_max_rise]+0.0}]
 set n [norm [get_full_name $cell]]
 dict set byname $n $a; lappend all $a
 set i [sta::sta_to_db_inst $cell]; set r [$i getBBox]
 puts $f "$n\t[expr {([$r xMin]+[$r xMax])/2000.0}]\t[expr {([$r yMin]+[$r yMax])/2000.0}]\t$a"
}
close $f
set inputs {};set outputs {};set flags {};set pins {}
set f [open /work/port_flops.tsv r]
while {[gets $f line] >= 0} {
 lassign [split $line \t] port inst distance
 set n [norm $inst]
 if {![dict exists $byname $n]} {error "source pin flop absent after CTS: $inst"}
 set a [dict get $byname $n];lappend pins $a
 if {[string match t_out* $port] || [string match fault_q* $port]} {lappend outputs $a} else {lappend inputs $a}
 if {[string match fault_q* $port]} {lappend flags $a}
}
close $f
if {[llength $all] != 12030 || [llength $pins] != 504} {error "CTS cohort mismatch"}
set pm [mean $pins]
puts "A0CTS $c all [llength $all] mean [mean $all] min [tcl::mathfunc::min {*}$all] max [tcl::mathfunc::max {*}$all] pin_mean $pm in_mean [mean $inputs] out_mean [mean $outputs] flags_mean [mean $flags]"
# Option A: report actual local IO STA against the measured pin-register mean
# at this corner. The parent still has to compensate this core latency and prove
# the two-sided sender contract; these are diagnostic local numbers only.
set_clock_latency -source $pm [get_clocks vclk]
puts "A0CTS_LOCAL_BASIS $c pin_mean $pm generated two-sided IO40, parent receipt pending"
sta::worst_slack_cmd max
sta::worst_slack_cmd min
report_worst_slack -max -digits 3
report_worst_slack -min -digits 3
puts "A0CTS_VIOL $c setup [sta::endpoint_violation_count max] hold [sta::endpoint_violation_count min]"
report_checks -path_delay max -group_path_count 2 -digits 3 -fields {input_pin}
report_checks -path_delay min -group_path_count 2 -digits 3 -fields {input_pin}
source /work/pair_skew.tcl
exit
