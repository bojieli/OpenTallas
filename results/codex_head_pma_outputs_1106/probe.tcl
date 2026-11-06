read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f {
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib.gz
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib.gz
} {read_liberty $f}
read_verilog /work/top.v
link_design top
read_sdc /work/constraint.sdc
set_propagated_clock [all_clocks]
set tx [get_ports {pma_tx[*]}]
if {[llength $tx] != 4} {error "native TX selector is not four real ports"}
set tc [get_clocks pma_tck]
if {[llength $tc] != 1 || ![$tc is_generated]} {error "missing actual exported generated clock"}
set maxp [find_timing_paths -to $tx -path_delay max -group_path_count 1]
set minp [find_timing_paths -to $tx -path_delay min -group_path_count 1]
if {![llength $maxp] || ![llength $minp]} {error "native TX has no actual setup/hold timing path"}
puts "PHY_OUTPUT_MAX_BEGIN"
report_checks -to $tx -path_delay max -format full_clock_expanded -digits 3
puts "PHY_OUTPUT_MIN_BEGIN"
report_checks -to $tx -path_delay min -format full_clock_expanded -digits 3
puts "PHY_OUTPUT_ASSOC_READ_PASS tx_ports [llength $tx] setup_paths [llength $maxp] hold_paths [llength $minp]"
exit
