# S81 FILL 2026-10-15: forwarded-clock station boundary (ref_tile boundary_tcl + sdc_extra, re-applied after every io_ref
# switch and at sign-off).
#
# The station is ot_fwd_link_stage: data captured on the FALLING edge of fi0, fo0 = ~fi0 (kept ot_fwd_clk_inv), and the
# next station captures do* on the falling edge of ITS fi = our fo0.  Every hop is source-synchronous: the clock travels
# with its data, so the hop is timed against the forwarded clock, not against a common die clock.
#
# (1) fo0 is the forwarded CLOCK output, not a data pin (10:09 verdicts: the io_ref data output budget on fo0 made
#     fi0 -> fo0 a timed I2O data path -> FF hold -58 'pin register missing' on stnh/stnv 3x1/10x1/70x1/86x1).
#     -> generated clock fo0_fwd (inverted fi0), no data budget on it.
# (2) do* (f3 pilot s81fill_stnh_3x1-f3-61c3c6803: TT -40.18, WC -27.5 at do0[0]) were still timed by the common-clock
#     io_ref against the NEXT RISING edge of fi0 (half a period after the negedge launch) with the full common-clock
#     outside share (0.2 T) + 90 ps skew + the propagated L: a common-clock budget applied to a half-cycle forwarded hop.
#     -> same rule as the forwarded-link fixture physical/rom_clock/fwd_hop2.sdc (fwd_w512.sdc rule): do* are checked
#     against the falling edge of the forwarded clock fo0_fwd (where the next station captures them), outside share
#     0.2 T; hold: the next station's capture edge one fo0 half-period after launch, hold skew OT_IO_HOLD_SKEW.
# (3) di* are launched by the previous station on the edge that arrives here as the RISING edge of fi0 (its fo = ~its fi,
#     launched on its fi fall) and captured on our fi0 fall.  The sender's clock-to-port latency travels with the data, so
#     the input share is the 0.2 T outside budget relative to the fi0 port edge, without the common-clock L + skew terms
#     (fwd_hop2.sdc: set_input_delay 166.666 -clock incoming).
# The forwarded-clock vs data skew over the die wire is the die-level hop check (S-DIE), not this tile's.
if {[llength [get_ports -quiet fo0]] && [llength [get_ports -quiet fi0]]} {
  set ot_fw_ib [expr {[info exists ::env(OT_IO_IN_BUDGET_PS)] ? $::env(OT_IO_IN_BUDGET_PS) : 166.667}]
  set ot_fw_ob [expr {[info exists ::env(OT_IO_OUT_BUDGET_PS)] ? $::env(OT_IO_OUT_BUDGET_PS) : 166.667}]
  set ot_fw_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
  unset_output_delay [get_ports fo0]
  if {![llength [get_clocks -quiet fo0_fwd]]} {
    create_generated_clock -name fo0_fwd -source [get_ports fi0] -invert -divide_by 1 [get_ports fo0]
  }
  # (4) fn0 (dsfd_stnv_566x1 only): the NON-inverted forwarded clock tap (two kept inverters on fi0), a clock output like
  #     fo0.  As a data pin the io_ref output budget timed fi0 -> fn0 as an I2O hold path (f8 e40f0ef1c FF -51.98 ps,
  #     output external delay 115 ps; the hold ECO cannot fix a clock pin) -> generated clock fn0_fwd, no data budget.
  if {[llength [get_ports -quiet fn0]]} {
    unset_output_delay [get_ports fn0]
    if {![llength [get_clocks -quiet fn0_fwd]]} {
      create_generated_clock -name fn0_fwd -source [get_ports fi0] -divide_by 1 [get_ports fn0]
    }
  }
  set ot_fw_do [get_ports -quiet do*]
  set ot_fw_di [get_ports -quiet di*]
  if {[llength $ot_fw_do]} {
    unset_output_delay $ot_fw_do
    set_output_delay $ot_fw_ob -max -clock fo0_fwd -clock_fall $ot_fw_do
    set_output_delay [expr {0 - $ot_fw_hk}] -min -clock fo0_fwd -clock_fall $ot_fw_do
  }
  if {[llength $ot_fw_di]} {
    unset_input_delay $ot_fw_di
    set_input_delay $ot_fw_ib -max -clock core_clk $ot_fw_di
    set_input_delay 0 -min -clock core_clk $ot_fw_di
  }
  puts "OT_FWD_CLOCK_OUT: fo0 = generated clock fo0_fwd (inverted fi0)[expr {[llength [get_ports -quiet fn0]] ? {, fn0 = fn0_fwd (non-inverted fi0)} : {}}]; [llength $ot_fw_do] do* vs fo0_fwd fall (max $ot_fw_ob / min -$ot_fw_hk), [llength $ot_fw_di] di* vs fi0 rise (max $ot_fw_ib / min 0)"
}
