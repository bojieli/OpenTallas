# ASAP7 flow uses ps. Never supply guessed caller/receiver delays or pin caps.
# The owner file must be generated from actual parent clock/receiver evidence,
# not from W512 macro caps or the invalidated r14 layout.
if {![info exists actual_parent_file] || ![file exists $actual_parent_file]} {
 error "OPEN parent contract: commit actual clock/root/reset authority and receiver delay/corner-cap evidence before preparing/submitting route"
}
source $actual_parent_file
foreach key {source_sha256 parent_authority cap_unit timing_unit physical_receiver_bound reset_debt_policy corner_cap_evidence} {
 if {![dict exists $parent_contract $key]} {error "missing actual parent field $key"}
}
if {[dict get $parent_contract source_sha256] ne $expected_source_sha256} {error "parent source binding changed; no old qualified source substitution"}
if {[dict get $parent_contract cap_unit] ne "fF"} {error "ASAP7 Liberty/UI fF cap units required"}
if {[dict get $parent_contract timing_unit] ne "ps"} {error "ASAP7 ps timing required"}
if {![dict get $parent_contract physical_receiver_bound]} {error "actual parent receiver remains OPEN"}
# Receiver loads are supplied in actual OpenSTA/Liberty UI units. The owner
# records SS/FF caps and the exact unit; no width scaling or zero default.
proc owner_input {clock ports} {
 foreach obj $ports {
  set pin [get_full_name $obj]
  if {![dict exists $::parent_contract input_delays_ps $pin]} {error "missing input delay $pin"}
  set_input_delay [dict get $::parent_contract input_delays_ps $pin] -clock $clock [get_ports $pin]
 }
}
proc owner_output {clock ports {fall 0}} {
 foreach obj $ports {
  set pin [get_full_name $obj]
  if {![dict exists $::parent_contract output_delays_ps $pin] || ![dict exists $::parent_contract receiver_load_ui $pin]} {error "missing actual receiver delay/load $pin"}
  set delay [dict get $::parent_contract output_delays_ps $pin]
  if {$fall} {set_output_delay $delay -clock $clock -clock_fall [get_ports $pin]} else {set_output_delay $delay -clock $clock [get_ports $pin]}
  set_load [dict get $::parent_contract receiver_load_ui $pin] [get_ports $pin]
 }
}
