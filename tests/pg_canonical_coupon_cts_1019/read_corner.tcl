set corner $::env(COUPON_CORNER)
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach name [list asap7sc7p5t_AO_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_OA_RVT_${corner}_nldm_211120.lib.gz asap7sc7p5t_INVBUF_RVT_${corner}_nldm_220122.lib.gz asap7sc7p5t_SEQ_RVT_${corner}_nldm_220123.lib asap7sc7p5t_SIMPLE_RVT_${corner}_nldm_211120.lib.gz] {read_liberty $plat/lib/NLDM/$name}
read_db $::env(COUPON_ODB)
read_sdc $::env(COUPON_SDC)
source $plat/setRC.tcl
estimate_parasitics -placement
source /src/physical/common_flow/native_pg_binding.tcl
ot_pg_audit_snapshot [ord::get_db_block] $::env(COUPON_PG_JSON)
report_units
report_clocks
report_clock_latency -clock [get_clocks core_clk]
report_clock_skew -setup
report_clock_skew -hold
report_check_types -max_slew -max_capacitance -max_fanout -violators
# Every native sequential input and every output separately; both check senses.
set endpoints [all_registers -data_pins]
foreach i [[ord::get_db_block] getInsts] {
 foreach t [$i getITerms] {
  if {[[$t getMTerm] getName] in {RESETN SETN}} {lappend endpoints [get_pins -quiet "[$i getName]/[[$t getMTerm] getName]"]}
 }
}
set endpoints [concat $endpoints [all_outputs]]
puts "COUPON_COMPLETE_ENDPOINT_COUNT [llength $endpoints]"
foreach p $endpoints {
 puts "COUPON_ENDPOINT [get_full_name $p]"
 foreach sense {min max} {report_checks -to $p -path_delay $sense -format full_clock_expanded -fields {slew capacitance fanout input_pins nets} -digits 6}
}
report_worst_slack -max
report_worst_slack -min
exit
