# MARGIN (owner rule 2026-10-06): a die clock-arrival difference of OT_IO_SKEW ps (default 150) against this block's
# measured insertion is budgeted on every boundary delay, adversely: input launch later (setup) / earlier (hold),
# output capture earlier (setup) / later (hold).  Otherwise identical to the file named in the next line.
set ot_sk [expr {[info exists ::env(OT_IO_SKEW)] ? $::env(OT_IO_SKEW) : 150}]
# hold side (coordinator decision 2026-10-06): a 50 ps die-clock IO hold allowance (OT_IO_HOLD_SKEW), not the setup skew
set ot_hk [expr {[info exists ::env(OT_IO_HOLD_SKEW)] ? $::env(OT_IO_HOLD_SKEW) : 50}]
# from io_ref.sdc
# Die context (post-CTS only), as physical/qwen_slab_structural/io_ref.sdc: the register on the other side of every
# core port is a unit boundary register (ME spine / vector stream / stream, or the memory port register) in the same
# core clock region, balanced to the same insertion, so each boundary delay is referenced to the PROPAGATED clock of a
# register of this block's tree.  Setup keeps the 0.2 T outside budget (166.6 ps); hold credits nothing outside (0).
# OpenROAD 26Q3 crashes on -reference_pin (load_design; GRT layer assignment slack update), so the same reference is
# applied numerically: L = the propagated clock arrival at the reference register's CLK (measured here, after CTS):
# the setup (max) analysis corner's arrival for the max delays, the hold (min) corner's for the min delays.
#   input  max = 166.6 + L_max   (launch at the boundary register, 0.2 T outside)   min = L_min (no outside credit)
#   output max = 166.6 - L_max   (capture at L, 0.2 T outside)                       min = -L_min (capture hold at L)
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
# the gated engine clock (ICG output to the ME spine) is a clock, not a boundary data port
set qcc_outs {}
foreach p [all_outputs] { if {[get_full_name $p] ne "u_me.clk"} { lappend qcc_outs $p } }
set qcc_ref {}
foreach qcc_c [get_cells -quiet {nx_v*}] {
  set qcc_p [get_pins -quiet "[get_full_name $qcc_c]/CLK"]
  if {[llength $qcc_p]} { set qcc_ref $qcc_p; break }
}
if {[llength $qcc_ref] == 0} { set qcc_ref [lindex [all_registers -clock_pins] 0] }
set qcc_w [sta::worst_slack_cmd max]
set qcc_lmax [get_property $qcc_ref arrival_max_rise]
set qcc_lmin [get_property $qcc_ref arrival_min_rise]
puts "QCC reference pin [get_full_name $qcc_ref] clock arrival max $qcc_lmax min $qcc_lmin"
set_input_delay [expr 166.6 + $qcc_lmax + $ot_sk] -max -clock core_clk [all_inputs -no_clocks]
set_input_delay [expr 0 + $qcc_lmin - $ot_hk] -min -clock core_clk [all_inputs -no_clocks]
set_output_delay [expr 166.6 - $qcc_lmax + $ot_sk] -max -clock core_clk $qcc_outs
set_output_delay [expr 0 - $qcc_lmin - $ot_hk] -min -clock core_clk $qcc_outs
