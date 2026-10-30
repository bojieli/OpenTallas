define_corners bc
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc /work/macros/ot_sram_1r1w_512x128_m1_r2c2_ff.lib
read_db /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement

set_propagated_clock [get_clocks clk]
set_clock_latency -source 202.5 [get_clocks vclk]
set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
set_input_delay -min -40 -clock [get_clocks vclk] $ins
puts PHY_IO_FF_CANONICAL_833_FULLCORE60_25_SEAM30_12p5_VCLK202.5_OVERLAY_INMINminus40_OUTMIN0
puts PHY_IO_FF_INPUT_WORST
report_checks -path_delay min -from $ins -group_path_count 1 -format full_clock_expanded -fields {slew cap fanout} -digits 3
puts PHY_IO_FF_OUTPUT_WORST
report_checks -path_delay min -to [all_outputs] -group_path_count 1 -format full_clock_expanded -fields {slew cap fanout} -digits 3
report_check_types -max_slew -max_capacitance -violators
puts PHY_IO_FF_SCREEN_DONE_NO_GRT_NO_QUALIFICATION
