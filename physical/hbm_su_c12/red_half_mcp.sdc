# SU reducer HALF-RATE vehicles (ot_hdc_v41x_vred_{slice64,top1024}_c12h): every flop except the fast event/status
# pin flops (u_pv.*), the contract check (viol) and the clock-gate enable (u_g.*) is clocked by the gated clock
# (one edge every two fast cycles, all blocks in the same phase), so gclk -> gclk paths get two periods; the slow
# data pins (slice lv_o / fault_o, top lv_in / sfault_in, top o_addr / o_data / o_meta) are sampled by the partner's
# gated / pulse-qualified edge two fast cycles after launch.  Appended to the route SDC and re-read at sign-off
# (after the io150 IO SDC, which resets port paths).
set ot_slow {}
set ot_fast 0
foreach ot_c [all_registers] {
  set ot_n [get_full_name $ot_c]
  if {[string match {u_pv.*} $ot_n] || [string match {u_pv/*} $ot_n] || [string match {viol*} $ot_n] || [string match {u_g.*} $ot_n] || [string match {u_g/*} $ot_n]} { incr ot_fast; continue }
  lappend ot_slow $ot_c
}
if {[llength $ot_slow]} {
  set_multicycle_path -setup 2 -from $ot_slow -to $ot_slow
  set_multicycle_path -hold 1 -from $ot_slow -to $ot_slow
}
set ot_sin [get_ports -quiet {lv_in* sfault_in*}]
if {[llength $ot_sin]} { set_multicycle_path -setup 2 -from $ot_sin; set_multicycle_path -hold 1 -from $ot_sin }
set ot_sout [get_ports -quiet {lv_o* fault_o* o_addr* o_data* o_meta*}]
if {[llength $ot_sout]} { set_multicycle_path -setup 2 -to $ot_sout; set_multicycle_path -hold 1 -to $ot_sout }
puts "OT_RED_HALF multicycle slow=[llength $ot_slow] fast=$ot_fast slow_in=[llength $ot_sin] slow_out=[llength $ot_sout]"
