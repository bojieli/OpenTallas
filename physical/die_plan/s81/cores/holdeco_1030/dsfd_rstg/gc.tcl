read_db /out/6_final.odb
set blk [ord::get_db_block]
set nrules [llength [$blk getGlobalConnects]]
puts "GC rules_in_db $nrules"
if {$nrules == 0} {
  add_global_connection -net VDD -pin_pattern {^VDD$} -power
  add_global_connection -net VSS -pin_pattern {^VSS$} -ground
}
global_connect
set unb 0; foreach i [$blk getInsts] { foreach it [$i getITerms] { set t [[$it getMTerm] getSigType]; if {$t in {POWER GROUND} && [$it getNet] eq "NULL"} { incr unb } } }
puts "GC unbound_supply_after $unb"
write_db /out/6_final.odb
write_def /out/6_final.def
exit
