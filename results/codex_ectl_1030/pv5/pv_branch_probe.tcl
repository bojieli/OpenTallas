read_db /work/run/results/asap7/hc_kv3_pv_pair__380_16x190_08_fMX/base/5_1_grt.odb
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron]
foreach nm {{u_s0.c_r[0]$_DFF_P_} rebuffer11019 place10813 place10812 place10811 place10810 _115855_} {
 set i [$b findInst $nm];if {$i eq "NULL"} {foreach j [$b getInsts] {if {[string map {\\ {}} [$j getName]] eq $nm} {set i $j;break}}};if {$i eq "NULL"} {error "missing $nm"};lassign [$i getLocation] x y
 puts "PV_BRANCH $nm [[$i getMaster] getName] [expr {double($x)/$u}] [expr {double($y)/$u}]"
 foreach it [$i getITerms] {set n [$it getNet];if {$n ne "NULL"} {puts "PV_EDGE $nm/[[$it getMTerm] getName] [$n getName]"}}
}
exit
