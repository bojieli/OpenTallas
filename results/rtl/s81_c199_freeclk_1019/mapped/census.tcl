read_db /work/results/asap7/opentallas_ot_v41_bf_col_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block]
set area 0.0; set count 0
array set masters {}
foreach i [$b getInsts] {set m [$i getMaster];set mn [$m getName];incr masters($mn);incr count;set area [expr {$area+[$m getWidth]*[$m getHeight]/1e6}]}
puts "CENSUS_COUNT $count AREA $area"
foreach mn [lsort [array names masters]] {puts "CENSUS_MASTER $masters($mn) $mn"}
foreach n [$b getNets] {
 set sinks 0;set ds {};set inputs {}
 foreach t [$n getITerms] {set ty [[$t getMTerm] getIoType];if {$ty eq "INPUT"} {incr sinks};if {$ty eq "OUTPUT"} {set i [$t getInst];lappend ds "[$i getName]/[[$t getMTerm] getName]:[[$i getMaster] getName]"}}
 foreach t [$n getBTerms] {if {[$t getIoType] eq "INPUT"} {lappend inputs [$t getName]}}
 if {$sinks>32} {puts "CENSUS_FANOUT $sinks [$n getName] DRIVERS=$ds INPUTS=$inputs"}
}
