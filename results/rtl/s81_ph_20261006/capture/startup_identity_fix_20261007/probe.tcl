read_db /input/6_final.odb
puts "MAPPING_COMMAND [info commands sta::sta_to_db_pin]"
set target {g_r[12].u_x.w_st_r[0]$_DFF_P_/D}
foreach inst [[ord::get_db_block] getInsts] {
 set n [$inst getName]
 if {[string first {g_r} $n]>=0 && [string first {12} $n]>=0 && [string first {w_st_r} $n]>=0} {puts "ODB_INSTANCE $n master=[[$inst getMaster] getName]"}
}
foreach pin [get_pins -hierarchical */D] {
 if {[get_full_name $pin] eq $target} {
  puts "STA_PIN [get_full_name $pin] handle=$pin"
  if {[catch {sta::sta_to_db_pin $pin} mapped]} {puts "MAPPING_ERROR $mapped"} else {puts "MAPPING_RESULT $mapped"}
 }
}
exit
