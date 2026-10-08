# su_softmax round 5: die-integration IO budget check of the routed block (owner rule addendum 2026-10-06).
# The block's boundary is register to register (inputs captured at the pin, outputs launched from a flop), so the
# routed leaf is false-pathed at its IO; this check re-times the IO against a die clock whose arrival differs from
# the block's measured insertion L by up to SKEW (both directions), plus a wire allowance WIRE to the nearest die
# station, at 0.833333 ns, SS setup / FF hold.  Env: CORNER (ss|ff), L_PS (measured insertion), SKEW_PS, WIRE_PS.
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef
set C $::env(CORNER)
set U [string toupper $C]
foreach l [list asap7sc7p5t_AO_RVT_${U}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${U}_nldm_220122.lib.gz \
            asap7sc7p5t_OA_RVT_${U}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${U}_nldm_220123.lib \
            asap7sc7p5t_SIMPLE_RVT_${U}_nldm_211120.lib.gz] { read_liberty $PLAT/lib/NLDM/$l }
set b [glob /work/results/asap7/*/base]
read_db $b/6_final.odb
read_spef $b/6_final.spef
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core_clk]
set_clock_uncertainty -hold 25 [get_clocks core_clk]
set_propagated_clock [get_clocks core_clk]
set L $::env(L_PS); set S $::env(SKEW_PS); set W $::env(WIRE_PS)
set ins {}
foreach p [all_inputs -no_clocks] { if {[get_name $p] ne "rst_n"} { lappend ins $p } }
# upstream launch: clock at L +- S, clk->q ~50 ps, wire 0..W
set_input_delay -max [expr $L + $S + 50 + $W] -clock core_clk $ins
# RULE H1 (h1-verify 2026-10-08): the die skew S is carried once, by the sender (output min below); the receiver
# launches at L with no -S.  Hold clk->q is the FF minimum 20 ps (boundary_io.sdc), not the setup 50.
set_input_delay -min [expr $L + 20] -clock core_clk $ins
# downstream capture: clock at L +- S, setup ~30 ps / hold ~10 ps, wire 0..W
set_output_delay -max [expr 30 + $W - ($L - $S)] -clock core_clk [all_outputs]
set_output_delay -min [expr 10 - ($L + $S)] -clock core_clk [all_outputs]
set_false_path -from [get_ports rst_n]
set chk [expr {$C eq "ss" ? "max" : "min"}]
set pi [find_timing_paths -path_delay $chk -from $ins -group_path_count 1]
if {[llength $pi]} { puts "OT_IO_IN [get_property [lindex $pi 0] slack]" } else { puts "OT_IO_IN INF" }
set po [find_timing_paths -path_delay $chk -to [all_outputs] -group_path_count 1]
if {[llength $po]} { puts "OT_IO_OUT [get_property [lindex $po 0] slack]" } else { puts "OT_IO_OUT INF" }
report_checks -path_delay $chk -from $ins -group_path_count 1 -format full_clock_expanded
report_checks -path_delay $chk -to [all_outputs] -group_path_count 1 -format full_clock_expanded
exit
