read_db $::env(ODB)
set b [ord::get_db_block]
proc dumpnet {n} {
 if {$n eq "NULL"} {return};puts "NET [$n getName]"
 foreach t [$n getITerms] {set i [$t getInst];puts "TERM [$i getName]/[[$t getMTerm] getName] [[$i getMaster] getName] [[$t getMTerm] getIoType]"}
 foreach t [$n getBTerms] {puts "PORT [$t getName] [$t getIoType]"}
}
foreach name {{u_pqx.gn.g_s[2].u_r/wire85399} wire85407} {
 set i [$b findInst $name]
 if {$i eq "NULL"} {foreach ii [$b getInsts] {if {[string match *wire85399* [$ii getName]]} {set i $ii;puts "LOCATED [$ii getName]"}}}
 if {$i eq "NULL"} {puts "MISSING $name";continue}
 puts "TARGET $name MASTER [[$i getMaster] getName]"
 foreach t [$i getITerms] {
  set n [$t getNet];if {$n eq "NULL"} {continue};dumpnet $n
  foreach s [$n getITerms] {
   if {[[$s getMTerm] getIoType] eq "OUTPUT"} {
    set driver [$s getInst]
    foreach dt [$driver getITerms] {if {[[$dt getMTerm] getName] eq "D"} {dumpnet [$dt getNet]}}
   }
  }
 }
}
