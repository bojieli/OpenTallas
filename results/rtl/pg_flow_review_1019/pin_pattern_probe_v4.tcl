read_db /clone/source_order_clone.odb
set block [ord::get_db_block]
read_lef /proof/pin_pattern_fixture.lef
set chosen NULL
foreach lib [[ord::get_db] getLibs] {
 foreach master [$lib getMasters] {if {[$master getName] eq "PG_PATTERN_FIXTURE"} {set chosen $master}}
}
if {$chosen eq "NULL"} {error NATIVE_FIXTURE_MASTER_MISSING}
puts "PIN_PATTERN_NATIVE_MASTER [$chosen getName]"
foreach rule [$block getGlobalConnects] {odb::dbGlobalConnect_destroy $rule}
foreach pattern {VDD ^VDD$} suffix {unanchored anchored} {
  set inst [odb::dbInst_create $block $chosen pg_pattern_$suffix]
  foreach pin {VDD VDDCE VDDPE} {if {[$inst findITerm $pin] eq "NULL"} {error "NATIVE_FIXTURE_ITERM_MISSING $pin"}}
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
  if {$count != 1} {error "NATIVE_PATTERN_VDD_POSITIVE_MISSING $pattern $count"}
  puts "NATIVE_PATTERN_EXACT_VDD_COUNT $pattern $count"
}
puts "NATIVE_PATTERN_FULL_MATCH_PASS VDD_does_not_match_VDDCE_or_VDDPE"
exit
