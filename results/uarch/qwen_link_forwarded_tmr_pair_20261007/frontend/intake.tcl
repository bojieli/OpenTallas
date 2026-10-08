read_liberty /tmp/qwen-link-forwarded-20261007/tmr-dispatch-archive/results/uarch/topk_station_SSFF_cell_model_20261002/inputs/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib
read_liberty /tmp/qwen-link-forwarded-20261007/tmr-dispatch-frontend/combo.lib
read_verilog /tmp/qwen-link-forwarded-20261007/tmr-dispatch-frontend/mapped.v
link_design ot_qwen_link_forwarded_tmr_pair
read_sdc /tmp/qwen-link-forwarded-20261007/tmr-dispatch-archive/physical/qwen_link_forwarded_tmr_pair/clocks.sdc
source /tmp/qwen-link-forwarded-20261007/tmr-dispatch-archive/physical/qwen_link_forwarded_tmr_pair/propagate.tcl
source /tmp/qwen-link-forwarded-20261007/tmr-dispatch-archive/physical/qwen_link_forwarded_tmr_pair/reset_inventory.tcl
report_clock_properties [all_clocks]
foreach c {ab_hop1 ba_hop1} {
 set endpoints [all_registers -clock $c -data_pins]
 if {[llength $endpoints]<528} {error "direction capture bank missing: $c"}
 report_checks -to $endpoints -path_delay min_max -group_path_count 2 -format full_clock_expanded
}
check_setup -verbose
puts "FORWARDED_FRONTEND_PASS"
exit
