foreach f [lsort [glob /tmp/l/*.lib]] { read_liberty $f }
read_verilog /w/pad_net.v
link_design padchain
create_clock -name clk -period 833 [get_ports clk]
foreach a {0.0 0.1435 0.5} {
  set_power_activity -input_ports [all_inputs -no_clocks] -activity $a -duty 0.5
  foreach r [all_registers -edge_triggered] { foreach p [get_pins -quiet -of_objects $r -filter "direction == output"] { set_power_activity -pins $p -activity $a -duty 0.5 } }
  puts "OT_ACT $a"
  report_power -digits 7
}
puts "OT_NREG [llength [all_registers -edge_triggered]]"
