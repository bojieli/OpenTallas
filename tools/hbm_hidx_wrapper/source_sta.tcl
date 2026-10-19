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
puts "SOURCE_DIAGNOSTIC_ONLY $corner; actual wire clock and neighbor NOT QUALIFIED"
report_checks -path_delay max -group_count 8 -fields {slew cap fanout input_pin nets} -digits 6
report_checks -path_delay min -group_count 8 -fields {slew cap fanout input_pin nets} -digits 6
report_check_types -max_slew -max_capacitance -violators
exit
