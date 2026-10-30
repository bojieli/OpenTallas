define_corners tc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc /work/macros/ot_sram_1r1w_512x128_m1_r2c2_tt.lib
read_db /work/output_hold1_fixed/4_cts_outputhold.odb
read_sdc /work/run/results/asap7/hc_qkd_hr_phy_adp__103_68x95_04/base/4_cts.sdc
source /work/setRC_rcx.tcl
estimate_parasitics -placement
set_propagated_clock [get_clocks clk]
set_clock_latency -source 250 [get_clocks vclk]
set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
set_input_delay -min -40 -clock [get_clocks vclk] $ins
set paths [find_timing_paths -path_delay max -group_path_count 1 -endpoint_path_count 1]
set worst Inf;set wp {}
foreach p $paths {set sl [get_property $p slack];if {$sl<$worst} {set worst $sl;set wp $p}}
puts "PHY_POSTHOLD_PLACEMENT TT worst$worst SP[get_full_name [get_property $wp startpoint]] EP[get_full_name [get_property $wp endpoint]]"
report_checks -path_delay max -format full_clock_expanded -fields {slew cap fanout} -digits 3
set n [expr {[llength [all_registers -data_pins]]+[llength [all_registers -async_pins]]+[llength [all_outputs]]}]
set allp [find_timing_paths -path_delay max -group_path_count $n -endpoint_path_count 1]
set f [open /work/output_hold1_fixed/negative_TT.tsv w];set neg 0
foreach p $allp {set sl [get_property $p slack];if {$sl<0} {incr neg;puts $f "[get_full_name [get_property $p startpoint]]\t[get_full_name [get_property $p endpoint]]\t$sl"}};close $f
puts "PHY_POSTHOLD_ALL_ENDPOINTS TT count[llength $allp] negative$neg"
report_check_types -max_slew -max_capacitance -violators
puts PHY_POSTHOLD_TT_SCREEN_DONE_NO_GRT_NO_QUALIFICATION
