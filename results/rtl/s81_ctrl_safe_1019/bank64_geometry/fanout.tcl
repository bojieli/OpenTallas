read_db /work/results/asap7/opentallas_dsfd_ctrl_rg2_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block]
foreach n [$b getNets] {
 set sinks 0;set ds {}
 foreach t [$n getITerms] {
  set ty [[$t getMTerm] getIoType]
  if {$ty eq "INPUT"} {incr sinks}
  if {$ty eq "OUTPUT"} {set i [$t getInst]; lappend ds "[$i getName]/[[$t getMTerm] getName]:[[$i getMaster] getName]"}
 }
 if {$sinks>32 && [llength $ds]} {puts "CTRL_FANOUT $sinks [$n getName] $ds"}
}
