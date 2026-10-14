
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_FF_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_FF_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
foreach port {r_i[1943] r_i[2071] d_i[0] v_i[0] r_o[1271]} {
puts "PIN_CLASSIFY $port"
set ps [get_ports -quiet $port]
if {[get_property $ps direction] eq "input"} { report_checks -from $ps -path_delay min_max -fields {slew capacitance fanout input_pin net} -digits 5 } else { report_checks -to $ps -path_delay min_max -fields {slew capacitance fanout input_pin net} -digits 5 }
}
exit
