# H-DIE-CKGEN 2026-10-16: hfd_ckgen PARENT (hardened hb_ckgen cluster: PLL modelled hard core ot_hbm_pll_bb + the closed
# reset-release leaf hfd_ckgen_rel4, parent = wires only).  The four domain clocks are SOURCED here, at the PLL output
# pins (the analog hard IP is the only modelled element, owner rule 10-14); refclk is the 100 MHz reference only.
# The parent's clock outputs pll_* are the die clock-tree roots: each carries a GENERATED clock (divide_by 1 of its PLL
# source), so the propagated latency PLL pin -> port is timed and the die tree starts from that port.
# por_* (each domain's release flop inside hfd_ckgen_rel4) are timed against their OWN domain's forwarded clock at the
# port (hfd_ckgen_parent_io.tcl, re-applied after every boundary reset): launch = arrival(por_X) - arrival(pll_X) <=
# 220 ps (native launch budget) at setup, >= -50 ps at hold.  por_n is the asynchronous power-on assert (both
# consumers -- PLL reset and the leaf's arm -- are asynchronous), locked is the PLL's asynchronous status (synchronised
# in the leaf): neither is a data path.  No path crosses domains inside this block, so the domains are unrelated here.
create_clock -name core_clk -period 833.333 [get_pins u_pll/clk_stream]
create_clock -name ref_clk -period 10000 [get_ports refclk]
create_clock -name ck_serial -period 1111.111 [get_pins u_pll/clk_serial]
create_clock -name ck_hbm -period 1024 [get_pins u_pll/clk_hbm]
create_clock -name ck_link -period 833.333 [get_pins u_pll/clk_link]
create_generated_clock -name pll_stream_o -source [get_pins u_pll/clk_stream] -master_clock core_clk -divide_by 1 [get_ports pll_stream]
create_generated_clock -name pll_serial_o -source [get_pins u_pll/clk_serial] -master_clock ck_serial -divide_by 1 [get_ports pll_serial]
create_generated_clock -name pll_hbm_o -source [get_pins u_pll/clk_hbm] -master_clock ck_hbm -divide_by 1 [get_ports pll_hbm]
create_generated_clock -name pll_link_o -source [get_pins u_pll/clk_link] -master_clock ck_link -divide_by 1 [get_ports pll_link]
if {!$::ot_ref_pre_cts} { set_propagated_clock [all_clocks] }
set_clock_groups -asynchronous -group {core_clk pll_stream_o} -group {ref_clk} -group {ck_serial pll_serial_o} \
  -group {ck_hbm pll_hbm_o} -group {ck_link pll_link_o}
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
# boundary (the same lines as hfd_ckgen_parent_io.tcl, which the kit re-sources after every io_ref / io_plain reset)
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
foreach {d per} {stream 833.333 serial 1111.111 hbm 1024 link 833.333} {
  set_output_delay [expr {$per - 220.0 - 60.0}] -max -clock pll_${d}_o [get_ports por_${d}]
  set_output_delay [expr {25.0 + 50.0}] -min -clock pll_${d}_o [get_ports por_${d}]
}
set_false_path -from [get_ports por_n]
