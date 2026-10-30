define_corners tc bc
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib}
read_liberty -corner tc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib}
read_liberty -corner bc {/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz}
read_liberty -corner tc /work/model_lvt/asap7sc7p5t_INVBUF_LVT_TT_nldm_220122.lib.gz
read_liberty -corner bc /work/model_lvt/asap7sc7p5t_INVBUF_LVT_FF_nldm_220122.lib.gz
read_db /work/eco2_grt/5_1_grt_pg_bound.odb
read_lef /work/model_lvt/asap7sc7p5t_28_L_1x_220121a.lef
read_sdc /work/eco2_grt/5_1_grt.sdc
source /work/setRC_rcx.tcl
source /work/clk_freeze_supported.tcl
foreach n [ot_clk_dbnets] {$n clearSpecial}
if {![grt::have_routes]} {error "no actual native routes"}
estimate_parasitics -global_routing
ot_clk_restore_parasitics {tc /work/eco2_grt/original_clock_only.spef bc /work/eco2_grt/original_clock_only.spef}
set_propagated_clock [get_clocks clk]
file mkdir /work/model_lvt/results

foreach {name master} {wire4506 BUFx16f place3260 BUFx10 place3259 BUFx10} {replace_cell $name ${master}_ASAP7_75t_L}
set target {};foreach p [all_registers -data_pins] {if {[get_full_name $p] eq {u_done.ib[1][50]$_DFFE_PP_/D}} {set target $p;break}}
if {$target eq ""} {error "id50short target absent"}
foreach {tag c kind lat} {TT tc max 250 FF bc min 202.5} {
 set_clock_latency -source $lat [get_clocks vclk]
 set_output_delay -min 0 -clock [get_clocks vclk] [all_outputs]
 set ins {};foreach p [all_inputs] {if {![string match ck* [get_full_name $p]]} {lappend ins $p}}
 set_input_delay -min -40 -clock [get_clocks vclk] $ins
 puts "CDC_TRUE_SHORT_ONEBUF $tag BEFORE_NO_INSERTION"
 report_checks -corner $c -path_delay $kind -to $target -format full_clock_expanded -fields {slew cap fanout} -digits 3
}
puts CDC_TRUE_SHORT_PRICE_DONE_NO_DB_SAVE_NO_PHYSICAL_ECO
