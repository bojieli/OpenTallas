read_db /diag/after_repair.odb
set block [ord::get_db_block]
set f [open /diag/data_edges.tsv w]
set a [open /diag/master_area.tsv w]
set seen [dict create]
set dbu [$block getDbUnitsPerMicron]
foreach i [$block getInsts] {
  set name [$i getName]
  set master [$i getMaster]
  set mn [$master getName]
  if {![dict exists $seen $mn]} {
    puts $a "$mn\t[expr {double([$master getWidth])*[$master getHeight]/$dbu/$dbu}]"
    dict set seen $mn 1
  }
  foreach t [$i getITerms] {
    if {[[$t getMTerm] getIoType] ne "OUTPUT"} {continue}
    set net [$t getNet]
    if {$net eq "NULL"} {continue}
    foreach l [$net getITerms] {
      if {[[$l getMTerm] getIoType] eq "INPUT"} {
        set li [$l getInst]
        puts $f "$name\t[$li getName]\t[[$li getMaster] getName]\t[[$l getMTerm] getName]"
      }
    }
  }
}
close $f
close $a
puts "PASS_FAILED_STATE_CONNECTIVITY_CAPTURE"
exit
