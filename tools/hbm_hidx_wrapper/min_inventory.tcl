# Read-only electrical source diagnostic: no init_floorplan/place/CTS/route.
set corner $::env(CORNER)
set p /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
foreach family {AO INVBUF OA SIMPLE} {
 foreach f [glob $p/asap7sc7p5t_${family}_RVT_${corner}_*.lib.gz] {read_liberty $f}
}
read_liberty $p/asap7sc7p5t_SEQ_RVT_${corner}_nldm_220123.lib
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_verilog out/netlist.v
link_design hidx_coupon1
read_sdc out/coupon.sdc
puts "SOURCE_MIN_INVENTORY_DIAGNOSTIC_ONLY $corner; no actual wire/clock/neighbor"
set ds [all_registers -data_pins]
set os [get_ports {compacted* pair_select* quad_select*}]
if {[llength $ds] !=2904 || [llength $os] !=2304} {error "incomplete endpoint inventory"}
foreach p $ds {
 puts "BEGIN_NATIVE_MIN_TARGET FF [get_full_name $p]"
 report_checks -to $p -path_delay min -group_path_count 1 -endpoint_path_count 1 -fields {slew cap input_pin} -digits 6
 puts "END_NATIVE_MIN_TARGET"
}
foreach p $os {
 puts "BEGIN_NATIVE_MIN_TARGET OUTPUT [get_full_name $p]"
 report_checks -to $p -path_delay min -group_path_count 1 -endpoint_path_count 1 -fields {slew cap input_pin} -digits 6
 puts "END_NATIVE_MIN_TARGET"
}
puts "MIN_INVENTORY_DONE ff=[llength $ds] output=[llength $os]"
exit
