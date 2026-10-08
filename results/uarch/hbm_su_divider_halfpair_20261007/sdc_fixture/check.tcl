read_liberty results/uarch/hbm_su_divider_halfpair_20261007/sdc_fixture/clock_fixture.lib
read_verilog results/uarch/hbm_su_divider_halfpair_20261007/sdc_fixture/clock_fixture.v
link_design top
create_clock -name core_clk -period 833.333 [get_ports clk]
source physical/hbm_su_div64/full_generated_clocks_candidate.sdc
if {[llength [get_clocks div64_*]] != 4} {error "missing clocks"}
report_clock_properties [all_clocks]
foreach c [get_clocks div64_*] {
 puts "PERIOD [get_property $c period] MASTER [get_property [get_clocks core_clk] period]"
 if {abs([get_property $c period]-1666.666)>0.01} {error "bad generated period"}
}
puts "PASS four generated clocks period1666.666ps; topology fixture only, no timing qualification"
exit
