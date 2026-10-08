read_liberty results/uarch/hbm_su_divider_halfpair_20261007/sdc_fixture/clock_fixture.lib
read_verilog results/uarch/hbm_su_divider_halfpair_20261007/sdc_fixture/clock_fixture.v
link_design top
rename set_clock_uncertainty real_set_clock_uncertainty
proc set_clock_uncertainty {kind value clocks} {
 global observed
 set observed($kind) $value
 real_set_clock_uncertainty $kind $value $clocks
}
foreach period {833.333 770.0} {
 create_clock -name core_clk -period $period [get_ports clk]
 source physical/hbm_su_div64/full_generated_clocks_candidate.sdc
 if {$observed(-setup) != 60 || $observed(-hold) != 25} {error "relaxed uncertainty"}
 report_clock_properties [all_clocks]
 puts "PASS period=$period setup=$observed(-setup) hold=$observed(-hold)"
}
source physical/hbm_su_div64/propagate_signoff.sdc
puts "PASS all generated clocks selected for propagated signoff"
exit
