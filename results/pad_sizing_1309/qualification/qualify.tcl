set c $::env(CORNER)
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_${c}_nldm_*.lib*] {read_liberty $f}
read_db /head/run/results/asap7/dp_hd_turn_a/base/6_final.odb
read_sdc /head/run/results/asap7/dp_hd_turn_a/base/6_final.sdc
read_spef /head/run/results/asap7/dp_hd_turn_a/base/6_final.spef
set_propagated_clock [get_clocks clk]
sta::worst_slack_cmd max
source /out/qualification_clock_family.tcl
ot_cf_refresh
set boundary [ot_cf_pinregs]
set fp [open /out/qualification_members_${c}.tsv w]
dict for {i p} $boundary {puts $fp "$i\t[get_full_name $p]"}
close $fp
set m [ot_cf_pinreg_measure [get_clocks clk]]
puts "QUALIFY_MEMBER $c boundary [dict size $boundary] measured [dict get $m n] mean [dict get $m mean] min [dict get $m min] max [dict get $m max]"
set fp [open /out/qualification_groups_${c}.tsv w]
puts $fp "group\tmean_ps\tn\tmin_ps\tmax_ps"
dict for {g v} [dict get $m groups] {puts $fp "$g\t[lindex $v 0]\t[lindex $v 1]\t[lindex $v 3]\t[lindex $v 4]"}
close $fp
set bound [expr {$c eq "TT"?250.0:202.5}]
puts "QUALIFY_LIMITS $c [ot_cf_pinreg_limits [dict get $m groups] $bound 20]"
if {$c eq "FF"} {puts "QUALIFY_CENSUS FF [ot_cf_output_hold_census]"}
puts "QUALIFY_API_COMPLETED $c"
