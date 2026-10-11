read_liberty /tmp/claude-1000/bfhier/frontv/ot_s81_bf_front_ff.lib
read_liberty /tmp/claude-1000/bfhier/colv/ot_v41_bf_col_ff.lib
read_verilog /tmp/claude-1000/bfhier/compose600/bf_pair.v
link_design bf_pair
create_clock -name core_clk -period 833.333 [get_ports clk]
set_clock_uncertainty -hold 75.0 [all_clocks]
set_false_path -from [get_ports rst_n]
set_clock_latency 291.955 [get_pins u_front/clk]
set_clock_latency 0.000 [get_pins u_col0/clk]
set_clock_latency 0.000 [get_pins u_col1/clk]
set fo [open /tmp/claude-1000/bfhier/compose600/sta_ff_bal_skew.txt w]
foreach {nm fr to} {f2c0 u_front u_col0 f2c1 u_front u_col1 c02f u_col0 u_front c12f u_col1 u_front} {
  set ps [find_timing_paths -path_delay min -from [get_pins $fr/clk] -to [get_cells $to] -group_count 1]
  if {[llength $ps] == 0} { puts $fo "$nm none"; continue }
  set p [lindex $ps 0]
  puts $fo "$nm [get_property $p slack] [get_full_name [get_property $p endpoint]]"
}
close $fo
report_checks -path_delay min -through [get_pins u_col0/*] -through [get_pins u_front/*] -group_count 3 -format full_clock_expanded > /tmp/claude-1000/bfhier/compose600/paths_ff_bal_skew.rpt
report_checks -path_delay min -from [get_pins u_front/clk] -group_count 3 -format full_clock_expanded >> /tmp/claude-1000/bfhier/compose600/paths_ff_bal_skew.rpt
exit
