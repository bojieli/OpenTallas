read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_$::env(C)_nldm_220123.lib
read_verilog /w/r.v
link_design r
create_clock -name clk -period 833.333 [get_ports clk]
set_clock_transition $::env(SLEW) [get_clocks clk]
set_input_delay 0 -clock clk [get_ports d]
set_input_transition 20 [get_ports d]
set_output_delay 0 -clock clk [get_ports q]
foreach ld {6.6 0.6} {
  set_load $ld [get_ports q]
  foreach pd {max min} {
    set pe [find_timing_paths -to [get_ports q] -path_delay $pd -group_path_count 1]
    foreach x $pe { puts "CLKQ $::env(C) load $ld $pd slack [get_property $x slack]" }
  }
}
report_checks -to [get_pins u/D] -path_delay max -digits 3
report_checks -to [get_pins u/D] -path_delay min -digits 3
