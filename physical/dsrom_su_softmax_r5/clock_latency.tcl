# su_softmax round 5: the routed block's clock insertion (min / max network latency) at CORNER (ss|ff), the L of
# io_budget.tcl.  Env: CORNER.
set PLAT /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $PLAT/lef/asap7_tech_1x_201209.lef
read_lef $PLAT/lef/asap7sc7p5t_28_R_1x_220121a.lef
set U [string toupper $::env(CORNER)]
foreach l [list asap7sc7p5t_AO_RVT_${U}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${U}_nldm_220122.lib.gz \
            asap7sc7p5t_OA_RVT_${U}_nldm_211120.lib.gz asap7sc7p5t_SEQ_RVT_${U}_nldm_220123.lib \
            asap7sc7p5t_SIMPLE_RVT_${U}_nldm_211120.lib.gz] { read_liberty $PLAT/lib/NLDM/$l }
set b [glob /work/results/asap7/*/base]
read_db $b/6_final.odb
read_spef $b/6_final.spef
create_clock -name core_clk -period 833.333 [get_ports clk]
set_propagated_clock [get_clocks core_clk]
report_clock_latency -clock core_clk
exit
