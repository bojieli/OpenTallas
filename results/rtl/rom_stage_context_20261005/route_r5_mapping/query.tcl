read_db /res/1_synth.odb
set b [ord::get_db_block]
foreach i [$b getInsts] {
 set n [$i getName];set m [[$i getMaster] getName]
 if {![string match DFF* $m]} {continue}
 if {![regexp {^u_stage\.u_ao\.(u_p|g_checked\.u_r)[./]|^u_ld\.(u_p|g_protected\.u_r)[./]} $n]} {continue}
 foreach t [$i getITerms] {
  if {[$t getIoType] ne "OUTPUT"} {continue}
  set net [$t getNet]
  if {$net eq "NULL"} {error "unconnected protected register output $n"}
  puts "W5_MAPPED_Q [$i getId] $n/[[$t getMTerm] getName] $m [$net getId] [$net getName]"
 }
}
