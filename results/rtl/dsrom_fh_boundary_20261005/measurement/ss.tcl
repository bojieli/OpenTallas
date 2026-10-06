
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_SS_*.lib*]] { read_liberty $f }
read_liberty /src/physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2_ss.lib
read_db /route/6_final.odb
read_sdc /out/boundary.sdc
read_spef /route/6_final.spef
set_propagated_clock [all_clocks]
set refs [get_pins -hierarchical {u_fh.u_rh*/*CLK}]
if {[llength $refs] == 0} { error "missing result-hold local clock leaf" }
set ref [lindex $refs 0]
puts "FHBOUND reference [get_full_name $ref]"
set q [get_ports {ra_q[*]}]
if {[llength $q] != 2048} { error "not full G4W16" }
set_input_delay -min 0 -clock core_clk -reference_pin $ref $q
set_input_delay -max 0 -clock core_clk -reference_pin $ref $q
set_driving_cell -lib_cell ot_sram_1r1w_512x128_m4_r2c2 -pin {rd_out[0]} -from_pin clk     -input_transition_rise 20 -input_transition_fall 20 $q
set a [get_ports {ra_addr[*] ra_re[*]}]
set_load 2.315064000 $a
set_output_delay -max 39.800541169 -clock core_clk -reference_pin $ref $a
set_output_delay -min -30.074020585 -clock core_clk -reference_pin $ref $a
report_units
puts "FHBOUND input_setup"
report_checks -from $q -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND input_hold"
report_checks -from $q -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND address_setup"
report_checks -to $a -path_delay max -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND address_hold"
report_checks -to $a -path_delay min -group_path_count 1 -format full_clock_expanded -digits 6
puts "FHBOUND checks"
report_check_types -max_slew -max_capacitance -violators
puts "FHBOUND end"
