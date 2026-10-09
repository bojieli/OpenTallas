# Read an immutable failed-run checkpoint on an admitted remote host.
# This prints actual divider cell pins and nets, without re-running CTS/repair.
read_db $::env(OT_LOADER_CHECKPOINT)
foreach inst [[ord::get_db_block] getInsts] {
 set name [$inst getName]
 if {![string match {u_ld.ckd*} $name]} {continue}
 puts "OT_DIVIDER_INSTANCE $name MASTER [[$inst getMaster] getName]"
 foreach it [$inst getITerms] {
  set pin [[$it getMTerm] getName]
  set dir [[$it getMTerm] getIoType]
  set net [$it getNet]
  if {$net eq "NULL"} {set nn UNCONNECTED} else {set nn [$net getName]}
  puts "OT_DIVIDER_PIN $name/$pin DIRECTION $dir NET $nn"
 }
}
foreach net [[ord::get_db_block] getNets] {
 set name [$net getName]
 if {$name ne "u_ld.ckd"} {continue}
 puts "OT_DIVIDER_LOGICAL_NET $name"
 foreach it [$net getITerms] {puts "OT_DIVIDER_NET_ENDPOINT [[$it getInst] getName]/[[$it getMTerm] getName]"}
}
puts OT_DIVIDER_INVENTORY_DONE
exit
