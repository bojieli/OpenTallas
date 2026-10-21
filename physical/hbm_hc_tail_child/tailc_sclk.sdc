# HBM-HC7-TAILK 10-20: the generated /7 Sinkhorn sink clock of ot_hbm_hc_tail_child_static (spec sdc_extra, inlined at the
# end of clock.sdc and signoff.sdc; core_clk on port clk is created by ref_tile and is not relaxed here).
# RTL: sclk <= (cnt == SDIV-1) on clk (one flop, SDIV 7): high for one clk period in seven.  In the gate-level cloned netlist
# (rtl/hbm_accel/generic/peers/static_hc/native/ot_hbm_hc_tail_child_static_bfc24.v) that flop's QN feeds INV iv4540_c,
# whose output net is 'sclk' (compact_netlist.py --clock-net) and clocks the 3,088 sink registers.
# Edges in master edges: rise at a clk rise (1), fall at the next clk rise (3), next rise seven periods later (15).  Every
# clk <-> sclk arc is therefore a normal synchronous single-period check (no multicycle, no false path, no groups).
# the flow may wrap the netlist (reset landing -> u_ot_pr_core, flattened to 'u_ot_pr_core.iv4540_c'): match by suffix, exactly one
set ot_sk [get_pins -quiet -of_objects [get_cells -quiet {iv4540_c *.iv4540_c}] -filter "direction == output"]
if {[llength $ot_sk] != 1} { error "tailc_sclk.sdc: generated-clock driver iv4540_c output pin not unique ([llength $ot_sk])" }
create_generated_clock -name sclk -source [get_ports clk] -edges {1 3 15} $ot_sk
set_clock_uncertainty -setup 60 [get_clocks sclk]
set_clock_uncertainty -hold 25 [get_clocks sclk]
set ot_sk_prop 0
catch {set ot_sk_prop [get_property [get_clocks core_clk] is_propagated]}
if {$ot_sk_prop} { set_propagated_clock [get_clocks sclk] }
