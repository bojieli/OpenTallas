read_db /base/6_final.odb
set b [ord::get_db_block]
foreach name {c_fd[38] c_rv[4]} {
 set bt [$b findBTerm $name]
 if {$bt eq "NULL"} continue
 set net [$bt getNet]
 puts "NOARC_PORT $name [$net getName]"
 foreach it [$net getITerms] {puts "NOARC_ITERM [[$it getInst] getName] [[[$it getInst] getMaster] getName] [[$it getMTerm] getName] [[$it getMTerm] getIoType]"}
 set driver ""
 for {set hop 0} {$hop<12} {incr hop} {
  set driver ""
  foreach it [$net getITerms] {if {[$it isOutputSignal]} {set driver $it;break}}
  if {$driver eq ""} break
  set inst [$driver getInst];set master [[$inst getMaster] getName]
  puts "NOARC_DRIVER $name [$inst getName] $master [[$driver getMTerm] getName]"
  if {![regexp {^(INV|BUF)} $master]} break
  set pin [$inst findITerm A]
  if {$pin eq "NULL"} break
  set net [$pin getNet]
 }
}
exit
