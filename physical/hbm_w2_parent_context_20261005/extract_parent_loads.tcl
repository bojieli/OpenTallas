# Run only in an actual SS/FF parent session with its ODB/Liberty/SDC/SPEF read.
# The exact port/bit/net map comes from the selected parent, not an H16 envelope.
foreach key {OT_W2_PORT_NET_MAP OT_W2_LOAD_OUTPUT OT_W2_CLOCK_OUTPUT} {
 if {![info exists ::env($key)]} {error "W2 HOLD: missing $key"}
}
set_units -time ps -capacitance fF
set block [ord::get_db_block]
proc w2_receiver_load {net} {
 set cap 0;set pins {}
 foreach it [$net getITerms] {
  if {[$it isOutputSignal] || [[$it getMTerm] getSigType] in {POWER GROUND}} {continue}
  set inst [$it getInst];set pin [[$it getMTerm] getName];set ref [[$inst getMaster] getName]
  set lib [get_lib_pins -quiet */$ref/$pin]
  if {[llength $lib]!=1} {error "W2 HOLD: missing actual receiver capacitance $ref/$pin"}
  set c [get_property $lib capacitance]
  set cap [expr {$cap+$c}]
  lappend pins [list [$inst getName] $pin $ref $c]
 }
 return [list $cap $pins]
}
set map [open $::env(OT_W2_PORT_NET_MAP) r]
set out [open $::env(OT_W2_LOAD_OUTPUT) w]
set seen [dict create]
while {[gets $map row]>=0} {
 if {$row eq "" || [string index $row 0] eq "#"} {continue}
 lassign [split $row "\t"] port bit name
 if {[dict exists $seen $port/$bit]} {error "W2 HOLD: duplicate port-bit binding $port/$bit"}
 dict set seen $port/$bit 1
 if {$name eq "UNCONNECTED"} {
  if {$port ne "quiet" || $bit ne "0"} {error "W2 HOLD: live boundary bit has no receiver $port/$bit"}
  # .quiet() is unconnected in both actual parent and this source cut. This
  # reserved track has no load claim; missing live loads cannot use this case.
  puts $out [join [list $port $bit UNCONNECTED NOT_APPLICABLE {}] "\t"]
  continue
 }
 set net [$block findNet $name]
 if {$net eq "NULL"} {error "W2 HOLD: actual mapped net missing $port/$bit $name"}
 lassign [w2_receiver_load $net] cap pins
 puts $out [join [list $port $bit $name $cap $pins] "\t"]
}
close $map;close $out
if {[dict size $seen]!=1213} {error "W2 HOLD: incomplete actual sink boundary map"}
# Expanded clock paths expose source phase, propagated insertion/skew and the
# actual FF endpoints. Pin-cap sums above exclude extracted wire capacitance;
# SPEF and these complete paths remain required, never silently replaced by 0.
set_propagated_clock [get_clocks {clk_sm clk_mem}]
redirect $::env(OT_W2_CLOCK_OUTPUT) {
 puts OT_W2_ACTUAL_REGISTER_PATHS_MAX
 report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 20 -format full_clock_expanded
 puts OT_W2_ACTUAL_REGISTER_PATHS_MIN
 report_checks -path_delay min -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 20 -format full_clock_expanded
 puts OT_W2_ACTUAL_INPUT_PATHS
 report_checks -path_delay min -from [all_inputs] -to [all_registers -data_pins] -group_path_count 20 -format full_clock_expanded
 puts OT_W2_ROOT_RESET_RECOVERY_REMOVAL
 set reset [get_pins -hierarchical */RESETN]
 if {[llength $reset]} {
  report_checks -path_delay max -to $reset -group_path_count 20 -format full_clock_expanded
  report_checks -path_delay min -to $reset -group_path_count 20 -format full_clock_expanded
 }
}
puts "OT_W2_ACTUAL_RECEIVER_MAP [dict size $seen]"
