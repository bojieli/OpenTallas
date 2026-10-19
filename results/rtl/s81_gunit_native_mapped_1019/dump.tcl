read_db /gate/routes/gate/work/orfs/results/asap7/opentallas_dsdv_gunit_l5_asap7_ref_gate/base/1_synth.odb
set b [ord::get_db_block]
set f [open /out/native_pins.tsv w]
puts $f "META\t[$b getName]\t[$b getDbUnitsPerMicron]"
foreach i [$b getInsts] {
 set m [$i getMaster]
 puts $f "CELL\t[$i getName]\t[$m getName]\t[$m isBlock]\t[$m getWidth]\t[$m getHeight]"
 foreach t [$i getITerms] {
  set n [$t getNet];set nn "";if {$n ne "NULL" && $n ne ""} {set nn [$n getName]}
  set mt [$t getMTerm]
  puts $f "PIN\t[$i getName]\t[$mt getName]\t[$mt getIoType]\t[$mt getSigType]\t$nn"
 }
}
foreach t [$b getBTerms] {
 set n [$t getNet];set nn "";if {$n ne "NULL" && $n ne ""} {set nn [$n getName]}
 puts $f "PORT\t[$t getName]\t[$t getIoType]\t[$t getSigType]\t$nn"
}
close $f
exit
