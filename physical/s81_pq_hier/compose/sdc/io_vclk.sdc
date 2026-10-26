# PQ screen composition IO (el1011-ds-misc/pqc 2026-10-11).  The top level holds NO registers: every port lands on /
# leaves from a hardened tile pin whose liberty folds the tile's internal clock latency in (TT max_clock_tree_path
# 116-206 ps for the IO tiles: T_BC/T_XIN ~120, T_RET ~146, T_CTL ~190, T_SROM/T_PROM ~190-200).  The flow's IO
# reference (io_ref_skew.sdc: median arrival of the boundary REGISTERS' CLK pins) would find no register, so IO is
# timed against a virtual clock at the die clock's arrival at the neighbours' registers = this composition's tile clock
# pin arrival (CTS-check measured, OT_PQC_VCLK_TOP) + the IO tiles' typical internal latency (150 ps), with the
# hbm_attn_tile_r io_vclk.sdc budget: 300 ps max each way (>= 150 ps arrival difference + 150 ps wire to the nearest
# die station), input min 0, output min -150.
set ot_top [expr {[info exists ::env(OT_PQC_VCLK_TOP)] ? $::env(OT_PQC_VCLK_TOP) : 120}]
if {[llength [get_clocks -quiet vclk]] == 0} {
  create_clock -name vclk -period [get_property [get_clocks core_clk] period]
}
set_clock_latency [expr {$ot_top + 150}] [get_clocks vclk]
set_clock_uncertainty -setup 60 [get_clocks vclk]
set_clock_uncertainty -hold 25 [get_clocks vclk]
set ot_in [all_inputs -no_clocks]
unset_input_delay $ot_in
unset_output_delay [all_outputs]
set_input_delay -max 300 -clock vclk $ot_in
set_input_delay -min 0 -clock vclk $ot_in
set_output_delay -max 300 -clock vclk [all_outputs]
set_output_delay -min -150 -clock vclk [all_outputs]
