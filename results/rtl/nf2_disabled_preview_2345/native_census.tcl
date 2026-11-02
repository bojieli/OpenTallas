proc nf2_census {db out} {
 read_db $db
 set f [open $out w]
 puts $f "instance\tmaster\tclock_pin\tclock_net"
 set n 0; set bank 0
 foreach i [[ord::get_db_block] getInsts] {
  set m [[$i getMaster] getName]
  if {![regexp {^DFF} $m]} continue
  incr n
  if {[string first gqv [$i getName]] >= 0} {incr bank}
  foreach it [$i getITerms] {
   set mt [$it getMTerm]
   if {[$mt getSigType] ne "CLOCK"} continue
   set net [$it getNet]
   puts $f "[$i getName]\t$m\t[$mt getName]\t[$net getName]"
  }
 }
 close $f
 puts "NF2_NATIVE_CENSUS $out DFF=$n fault_bank=$bank"
}
nf2_census $::env(NF2_DB) $::env(NF2_OUT)
exit
