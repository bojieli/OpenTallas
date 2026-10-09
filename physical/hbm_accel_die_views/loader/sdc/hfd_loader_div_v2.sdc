# hfd_loader L-DIV clock (struct-close 2026-10-09; replaces hfd_loader_div.sdc in the L-DIV routes, REVIEW_20261009 W3).
# hbm_loader_ldiv_A/B_f8e459542 died with "OT_LOADER_DIV: divider output u_ld.ckd not found": synthesis maps the divider
# to a toggle flop whose QN (plus an inverter CTS may remove) drives the core clock, so the logical net u_ld.ckd is gone.
# Order: (1) the logical net's driver pin if it still exists (pre-map / RTL STA); (2) the mapped toggle flop's QN with the
# inversion kept (Codex fbea9b388 hfd_loader_div_driver.sdc binding); else fail loudly (an unclocked core reads as closed).
set ot_cksrc [get_ports -quiet ck]
if {[llength $ot_cksrc] == 0} { set ot_cksrc [get_ports {ck[0]}] }
if {[llength [get_clocks -quiet ckd]]} { delete_clock [get_clocks ckd] }
set ot_ckd_pins [get_pins -quiet -of_objects [get_nets -quiet {u_ld.ckd}] -filter "direction == output"]
if {[llength $ot_ckd_pins] == 1} {
  create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 $ot_ckd_pins
  puts "OT_LOADER_DIV_V2: ckd on the logical net driver [get_full_name $ot_ckd_pins]"
} else {
  set ot_qn [get_pins -quiet {u_ld.ckd$_DFF_PP0_/QN}]
  if {[llength $ot_qn] != 1} { error "OT_LOADER_DIV_V2: neither u_ld.ckd nor the mapped toggle QN u_ld.ckd\$_DFF_PP0_/QN found" }
  create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 -invert $ot_qn
  puts "OT_LOADER_DIV_V2: ckd on the mapped toggle QN (inverted waveform)"
}
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks ckd]
