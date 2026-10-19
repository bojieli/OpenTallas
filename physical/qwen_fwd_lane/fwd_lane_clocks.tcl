# Q-DIE11-RLY 10-18: clocks of the Qwen forwarded half-cycle lane frames (rtl/qwen_split/qfd_fwd_lane.sv, generated
# wrappers physical/qwen_fwd_lane/qfd_fwd_lane_masters.sv), sdc_extra + boundary_tcl of every qfwd_* kit (re-applied
# after every io_ref switch and at sign-off).
#   station  qfd_rlyh_*   clock port ckf; ck_o = ~ckf through ONE kept inverter -> generated clock ck_o_fwd INVERTED
#   hop 0    qfd_rlyh0_*  clock port ck (source root); capture on cko = ICG(ck) (RISING ck edge, Q-DIE11 10-18 kit fix),
#                         ck_o = ~cko -> generated clock ck_o_fwd INVERTED (the S81 dsfd_dvrlyh form)
#   landing  qfd_landh_*  clock port ck (receiving root, read side); ckf = the lane clock (ring write side) -> clock
#                         lane_ckf, same period; landh0: ck_s (source root, ring written on ICG(~ck_s))
#   ck_o carries no data budget.  The landing's lane inputs a / ea are captured on the lane clock: their IO budget is
#   re-referenced to lane_ckf.  The ring -> o crossing (lane clock -> ck) is the die STA's landing window
#   (LANDING-CONTRACT L5: MCP -setup E -hold D-1 at the die, one E per link): no tile check (false path).
set ot_fl_ck [get_clocks core_clk]
set ot_fl_T [get_property $ot_fl_ck period]
if {[llength [get_ports -quiet ck_o]]} {
  unset_output_delay [get_ports ck_o]
  if {![llength [get_clocks -quiet ck_o_fwd]]} {
    if {[llength [get_ports -quiet ckf]]} {
      create_generated_clock -name ck_o_fwd -source [get_ports ckf] -divide_by 1 -invert [get_ports ck_o]
      puts "OT_FWD_LANE: station ck_o = ~ckf (generated ck_o_fwd INVERTED, half-cycle hop)"
    } elseif {[llength [get_ports -quiet ck]]} {
      create_generated_clock -name ck_o_fwd -source [get_ports ck] -divide_by 1 -invert [get_ports ck_o]
      puts "OT_FWD_LANE: hop-0 ck_o = ~(ck gated) (generated ck_o_fwd INVERTED), capture on the rising ck edge"
    }
  }
} else {
  set ot_fl_wp [expr {[llength [get_ports -quiet ckf]] ? "ckf" : "ck_s"}]
  if {[llength [get_ports -quiet $ot_fl_wp]] && ![llength [get_clocks -quiet lane_ckf]]} {
    create_clock -name lane_ckf -period $ot_fl_T [get_ports $ot_fl_wp]
    set_propagated_clock [get_clocks lane_ckf]
    set ot_fl_in [get_ports -quiet {a[*] ea[*] ea en[*] en}]
    if {[llength $ot_fl_in]} {
      set_input_delay [expr {0.2 * $ot_fl_T}] -clock lane_ckf $ot_fl_in
    }
    set_false_path -from [get_clocks lane_ckf] -to $ot_fl_ck
    set_false_path -from $ot_fl_ck -to [get_clocks lane_ckf]
    puts "OT_FWD_LANE: landing write clock lane_ckf on $ot_fl_wp; ring -> o window = die STA landing MCP"
  }
}
