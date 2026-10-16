# hfd_loader L-DIV clock v3 (struct-close 2026-10-09).  The RTL drives the core clock from the divider flop's QN directly
# (ckd = ~ckd_q, ot_hfd_loader_div.sv): the generated clock sits on that SEQUENTIAL pin, which every stage keeps (no
# inverter for CTS to lose: v2 bound the inverter after QN, CTS-0040 skipped the ckd tree, FF hold -18,672 ps).
# Before mapping (RTL STA) the logical net u_ld.ckd's driver is used.  Fails loudly when neither exists.
set ot_cksrc [get_ports -quiet ck]
if {[llength $ot_cksrc] == 0} { set ot_cksrc [get_ports {ck[0]}] }
if {[llength [get_clocks -quiet ckd]]} { delete_clock [get_clocks ckd] }
set ot_qn [get_pins -quiet -hierarchical {u_ld.ckd_q*/QN}]
if {[llength $ot_qn] == 1} {
  create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 -invert $ot_qn
  puts "OT_LOADER_DIV_V3: ckd on the divider flop QN [get_full_name $ot_qn]"
} else {
  set ot_ckd_pins [get_pins -quiet -of_objects [get_nets -quiet {u_ld.ckd}] -filter "direction == output"]
  if {[llength $ot_ckd_pins] != 1} { error "OT_LOADER_DIV_V3: no divider QN (u_ld.ckd_q*/QN) and no u_ld.ckd driver" }
  create_generated_clock -name ckd -source $ot_cksrc -divide_by 2 $ot_ckd_pins
  puts "OT_LOADER_DIV_V3: ckd on the logical net driver [get_full_name $ot_ckd_pins] (pre-map)"
}
set_clock_groups -asynchronous -group [get_clocks core_clk] -group [get_clocks ckd]
