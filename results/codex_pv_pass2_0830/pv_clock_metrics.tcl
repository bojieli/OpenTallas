foreach l $::env(PV_LIBS) {read_liberty $l}
set rs [lindex [glob /work/run/results/asap7/*/base] 0]
read_db $rs/4_cts.odb
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [get_clocks clk]
estimate_parasitics -placement
source /work/clock_family.tcl
ot_cf_refresh
find_timing_paths -group_path_count 1
set c [get_clocks clk];set count 0;set sum 0.0;set amin 1e99;set amax -1e99
set f [open /work/pv_cts_clock_$::env(PV_CORNER).tsv w]
foreach p [all_registers -clock_pins -clock $c] {
 set a [ot_cf_wire $p $c]
 puts $f "[get_full_name $p]\t$a"
 incr count;set sum [expr {$sum+$a}];set amin [expr {min($amin,$a)}];set amax [expr {max($amax,$a)}]
}
close $f
puts "PV_CTS_PLACEMENT_RC_CLOCK $::env(PV_CORNER) pins=$count min=$amin mean=[expr {$sum/$count}] max=$amax window=[expr {$amax-$amin}]"
report_checks -path_delay min -group_path_count 3 -format full_clock_expanded > /work/pv_cts_$::env(PV_CORNER)_hold.rpt
report_checks -path_delay max -group_path_count 3 -format full_clock_expanded > /work/pv_cts_$::env(PV_CORNER)_setup.rpt
report_worst_slack -min
report_worst_slack -max
