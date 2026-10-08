# hfd_index_q_b0 (segment split): forwarded index-key clocks k[1024] / k[1025] at the stream clock period; each writes a
# capture register + two-clock FIFO on its FALLING edge (inverted at the pin).  Appended after io_vclk_m_<L>.sdc and
# re-applied as the last sign-off post-SDC (after vclk_corner_true.sdc): the key data k[1023:0] is timed against its own
# forwarded clock (launched on the rising edge with the clock, 0.2 T + 150 ps skew budget, captured on the falling edge),
# never against vclk / core_clk, which are asynchronous to the forwarded clocks.
# (clocks created only when absent: as a sign-off post-SDC they already exist and are propagated)
if {![llength [get_clocks -quiet fk0]]} { create_clock -name fk0 -period [get_property [get_clocks core_clk] period] [get_ports {k[1024]}] }
if {![llength [get_clocks -quiet fk1]]} { create_clock -name fk1 -period [get_property [get_clocks core_clk] period] [get_ports {k[1025]}] }
set_clock_uncertainty -setup 60 [get_clocks {fk0 fk1}]
set_clock_uncertainty -hold 25 [get_clocks {fk0 fk1}]
set ot_t [get_property [get_clocks core_clk] period]
set ot_k0 {}; set ot_k1 {}
for {set ot_b 0} {$ot_b < 512} {incr ot_b} { lappend ot_k0 [get_ports "k\[$ot_b\]"]; lappend ot_k1 [get_ports "k\[[expr {$ot_b + 512}]\]"] }
foreach {ot_c ot_p} [list fk0 $ot_k0 fk1 $ot_k1] {
  foreach ot_q $ot_p { catch { unset_input_delay -clock vclk $ot_q }; catch { unset_input_delay -clock core_clk $ot_q } }
  set_input_delay [expr {$ot_t * 0.2 + 150}] -clock $ot_c $ot_p
  set_input_delay -min 0 -clock $ot_c $ot_p
}
set_clock_groups -asynchronous -group [get_clocks {core_clk vclk}] -group [get_clocks fk0] -group [get_clocks fk1]
