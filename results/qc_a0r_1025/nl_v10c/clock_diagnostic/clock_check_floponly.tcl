set c $::env(MC)
foreach l [split $::env(PLIBS)] {
 if {$c eq "TT"} {set l [string map {_FF_ _TT_ _ff.lib _tt.lib} $l]}
 read_liberty $l
}
read_db $::env(ODB)
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
read_sdc $::env(SDC)
set_propagated_clock [all_clocks]
if {$::env(MODE) eq "affinity"} {
 set ::env(OT_LEAF_AFF_REPORT_ONLY) 1
 source /own/leaf_affinity.tcl
} else {
 set ::ot_ps_lib_only 1
 source /own/pair_skew_floponly.tcl
 unset ::ot_ps_lib_only
 ot_ps_zero_unc
 set m [ot_ps_measure]
 ot_ps_write $m /own/nl_floponly_${c}_pairs.tsv $c
 foreach k {max min} {puts "A0_PAIR $c $k [dict get $m $k]"}
}
exit
