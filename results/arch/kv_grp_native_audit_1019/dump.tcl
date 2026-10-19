read_db $::env(AUDIT_ODB)
set f [open $::env(AUDIT_TSV) w]
set block [ord::get_db_block]
foreach n [$block getNets] {
 if {[$n getSigType] in {POWER GROUND}} {continue}
 set nn [$n getName]
 foreach p [$n getITerms] {
  set i [$p getInst]
  puts $f [join [list $nn I [$i getName] [[$i getMaster] getName] [[$p getMTerm] getName] [$p getIoType]] "\t"]
 }
 foreach p [$n getBTerms] {
  puts $f [join [list $nn B [$p getName] TOP [$p getName] [$p getIoType]] "\t"]
 }
}
close $f
