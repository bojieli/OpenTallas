
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty $l }
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_LVT_TT_* /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_SLVT_TT_*] { if {![string match *FAKE* $l]} { read_liberty $l } }
read_liberty /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]

foreach port {fv_i[3] fd_i[30] n_y[2487] n_yacc yfl ch_fd[1398]} {
puts "PIN_CLASSIFY $port"
set ps [get_ports -quiet $port]
if {[get_property $ps direction] eq "input"} { report_checks -from $ps -path_delay min_max -fields {slew capacitance fanout input_pin net} -digits 5 } else { report_checks -to $ps -path_delay min_max -fields {slew capacitance fanout input_pin net} -digits 5 }
}
exit
