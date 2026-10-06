# ASAP7 ps/fF. Missing actual caller/receiver data is a fatal OPEN contract.
set authority /src/physical/hbm_die_abstracts_20261006/links/native_quarter/actual_frame_station_parent.tcl
if {![file exists $authority]} {error "OPEN full73 station receiver clock/reset/delay/corner-cap authority"}
source $authority
foreach k {source_hashes clock_reset_authority reset_debt_policy receiver_bound input_min_ps input_max_ps output_min_ps output_max_ps receiver_caps_fF selected_corner actual_slot} {
 if {![dict exists $parent_contract $k]} {error "missing station parent field $k"}
}
if {![dict get $parent_contract receiver_bound]} {error "receiver routing remains OPEN"}
# Owner authority must cover every selected source hash in the recipe. No
# historical leaf substitution. Verify source bytes inside the pinned checkout.
foreach required {rtl/gpu/w6/ot_gpu_w6_secded_pkg.sv rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank.sv rtl/common/ot_fwd_link_stage.sv physical/hbm_die_abstracts_20261006/links/ot_hbm_native_register_slice.sv physical/hbm_die_abstracts_20261006/links/parents/ot_hbm_native_station.sv physical/hbm_die_abstracts_20261006/links/native_quarter/ot_hbm_native_frame_station.sv} {
 if {![dict exists $parent_contract source_hashes $required]} {error "missing selected source hash $required"}
}
dict for {path expected} [dict get $parent_contract source_hashes] {
 set actual [lindex [exec sha256sum /src/$path] 0]
 if {$actual ne $expected} {error "changed actual selected station source $path"}
}
create_clock -name clk_sm -period 833.333333 [get_ports clk_sm]
set previous [get_ports clk_sm]
set master clk_sm
for {set i 0} {$i<4} {incr i} {
 set roots {}
 foreach pin [get_pins -hierarchical *] {
  if {[regexp "u_clk${i}.*/Y$" [get_full_name $pin]]} {lappend roots $pin}
 }
 if {[llength $roots]!=1} {error "missing/ambiguous real kept forwarding inverter $i"}
 create_generated_clock -name forwarded$i -source $previous -master_clock $master -divide_by 1 -invert [lindex $roots 0]
 set previous [lindex $roots 0];set master forwarded$i
}
create_generated_clock -name receiver_root -source $previous -master_clock $master -divide_by 1 [get_ports fclk_o]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
foreach p [all_inputs] {
 set n [get_full_name $p]
 if {$n eq "clk_sm"} {continue}
 foreach k {input_min_ps input_max_ps} {
  if {![dict exists $parent_contract $k $n]} {error "missing actual input delay $k $n"}
 }
 set_input_delay -min [dict get $parent_contract input_min_ps $n] -clock clk_sm $p
 set_input_delay -max [dict get $parent_contract input_max_ps $n] -clock clk_sm $p
}
set corner [dict get $parent_contract selected_corner]
if {$corner ni {SS FF}} {error "actual SS/FF corner caps required"}
foreach p [all_outputs] {
 set n [get_full_name $p]
 if {![dict exists $parent_contract receiver_caps_fF $corner $n]} {error "missing actual $corner receiver cap $n"}
 set_load [dict get $parent_contract receiver_caps_fF $corner $n] $p
 if {$n eq "fclk_o"} {continue}
 foreach k {output_min_ps output_max_ps} {
  if {![dict exists $parent_contract $k $n]} {error "missing actual receiver delay $k $n"}
 }
 set c clk_sm
 if {[regexp {^out_(v|data|owner|frame)} $n]} {set c receiver_root}
 set_output_delay -min [dict get $parent_contract output_min_ps $n] -clock $c $p
 set_output_delay -max [dict get $parent_contract output_max_ps $n] -clock $c $p
}
# No reset false paths, asynchronous cuts or unconstrained clock output.
