read_db /clone/source_order_clone.odb
set block [ord::get_db_block]
set chosen NULL
foreach inst [$block getInsts] {
  set master [$inst getMaster]
  if {[$master findMTerm VDDCE] ne "NULL" || [$master findMTerm VDDPE] ne "NULL"} {set chosen $master;break}
}
if {$chosen eq "NULL"} {
  # Native semantic fixture only: extend a loaded native PG master in memory;
  # no input or output ODB is written. New instance sees both native MTerms.
  foreach inst [$block getInsts] {
    set candidate [$inst getMaster]
    if {[$candidate findMTerm VDD] ne "NULL"} {set chosen $candidate;break}
  }
  if {$chosen eq "NULL"} {error "NO_NATIVE_VDD_MASTER"}
  odb::dbMTerm_create $chosen VDDCE INOUT POWER
  puts "FIXTURE_ONLY_ADDED_NATIVE_MTERM VDDCE"
}
puts "PIN_PATTERN_NATIVE_MASTER [$chosen getName]"
foreach rule [$block getGlobalConnects] {odb::dbGlobalConnect_destroy $rule}
foreach pattern {VDD ^VDD$} suffix {unanchored anchored} {
  set inst [odb::dbInst_create $block $chosen pg_pattern_$suffix]
  add_global_connection -net PG_PATTERN_$suffix -inst_pattern ^pg_pattern_${suffix}$ -pin_pattern $pattern -power
  global_connect
  set count 0
  foreach term [$inst getITerms] {
    set pin [[$term getMTerm] getName]
    set net [$term getNet]
    set net_name NULL
    if {$net ne "NULL"} {set net_name [$net getName]}
    puts "NATIVE_PATTERN pattern=$pattern pin=$pin net=$net_name"
    if {[string match VDD* $pin] && $pin ne "VDD" && $net ne "NULL"} {error "UNANCHORED_SUBSTRING_MATCH $pin"}
    if {$pin eq "VDD" && $net ne "NULL"} {incr count}
  }
  puts "NATIVE_PATTERN_EXACT_VDD_COUNT $pattern $count"
}
puts "NATIVE_PATTERN_FULL_MATCH_PASS VDD_does_not_match_VDDCE_or_VDDPE"
exit
