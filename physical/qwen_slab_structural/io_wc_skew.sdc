# MARGIN (owner rule 2026-10-06): a die clock-arrival difference of OT_IO_SKEW ps (default 150) against this block's
# measured insertion is budgeted on every boundary delay, adversely: input launch later (setup) / earlier (hold),
# output capture earlier (setup) / later (hold).  Otherwise identical to the file named in the next line.
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
# hold side (coordinator decision 2026-10-06): a 50 ps die-clock IO hold allowance (OT_IO_HOLD_SKEW), not the setup skew
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
# from io_wc.sdc
# S1 die context for the multi-corner (WC setup + WC/BC hold) ORFS stages, post-CTS only.
# io_ref.sdc (-reference_pin) is NOT usable: OpenSTA 26Q3 drops every input-port path under it (report_checks -from
# res_in[*] finds no path, even -unconstrained), and GRT crashes in sta::Sim under it.  OpenSTA cannot give one port
# delay per corner, so the flow uses the reference register's propagated arrival at the WC (sign-off setup) corner:
#   input  setup: launch  = arr_late_WC(ref)  + 166.667     input  hold: launch  = arr_early_WC(ref) + 0
#   output setup: capture = arr_early_WC(ref) - 166.667     output hold: capture = arr_late_WC(ref)  - 0
# except the output hold capture, taken at BC (the FF sign-off corner): a WC capture would be ~400 ps late at BC and
# flood the outputs with hold buffers.  Setup is exact at WC; input hold exact at WC (optimistic at BC), output hold
# exact at BC (optimistic at WC, which is not a sign-off check).  Sign-off re-times each corner on its own with
# io_lat.sdc (single corner, exact).  Nothing in sign-off is relaxed.
proc qss_clk_at {corner minmax} {
  # capture-clock arrival at the reference register's CLK pin in one corner (full_clock_expanded report)
  # with_output_to_variable evaluates its body in its own frame: pass a fully substituted command
  with_output_to_variable v [list report_checks -corner $corner -path_delay $minmax \
    -to [get_pins {res_q\[0\]$_DFF_P_/D}] -format full_clock_expanded]
  set t ""
  foreach line [split $v "\n"] {
    if {[regexp {^\s*\S+\s+(-?[0-9.]+)\s+\S\s+res_q\[0\]\$_DFF_P_/CLK} $line -> a]} { set t $a }
  }
  if {$t eq ""} { error "QSS: no $minmax path to res_q\[0\] in corner $corner" }
  if {$minmax eq "max"} { set t [expr {$t - [get_property [get_clocks clk] period]}] }
  return $t
}
set qss_early [qss_clk_at WC max]
set qss_late  [qss_clk_at WC min]
set qss_late_bc [expr {[catch {qss_clk_at BC min} qss_t] ? $qss_late : $qss_t}]
# QSS_IO_HOLD_EXTRA (ps, default 0): flow-only extra boundary hold requirement (launch earlier / capture later), so
# hold repaired at WC also covers the FF corner the flow times optimistically.  Stricter only; sign-off ignores it.
set qss_hx [expr {[info exists ::env(QSS_IO_HOLD_EXTRA)] ? $::env(QSS_IO_HOLD_EXTRA) : 0}]
puts "QSS ref clock WC early $qss_early late $qss_late, BC late $qss_late_bc, hold_extra $qss_hx"
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set qss_in  [get_ports {rst_n p_* res_in*}]
set qss_out [get_ports {o_we o_addr* o_mask* o_data* ov am_tv am_top* am_rmax fault}]
set_input_delay  [expr {166.667 + $qss_late + $ot_sk}] -max -clock clk $qss_in
set ot_hki [expr {[info exists ::env(OT_IO_IN_HOLD_SKEW)] ? $::env(OT_IO_IN_HOLD_SKEW) : 0}]
set_input_delay  [expr {$qss_early - $qss_hx - $ot_hki}] -min -clock clk $qss_in
set_output_delay [expr {166.667 - $qss_early + $ot_sk}] -max -clock clk $qss_out
set_output_delay [expr {-$qss_late_bc - $qss_hx - $ot_hk}] -min -clock clk $qss_out
