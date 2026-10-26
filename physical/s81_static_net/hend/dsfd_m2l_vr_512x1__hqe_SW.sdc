# S-NET dsfd_m2l_vr_512x1__hqe_SW (--hend-static): fixed-calendar crossing, no FIFO / credit / ready
create_clock -name core_clk -period 833.333 [get_ports {ck[0]}]
set ot_w {}
foreach p [get_ports {fi*}] { set n [get_property $p name]; regsub {\[0\]} $n {} b; create_clock -name w_$b -period 833.333 $p; lappend ot_w w_$b }
create_clock -name vclk -period 833.333
create_clock -name vw -period 833.333
set_clock_latency 0 [get_clocks {vclk vw}]
set_clock_uncertainty -setup 123 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
foreach w $ot_w {
  set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks $w] -to [get_clocks core_clk]
  set_max_delay -ignore_clock_latency 1190.0 -from [get_clocks core_clk] -to [get_clocks $w]
  set_min_delay -ignore_clock_latency 0 -from [get_clocks $w] -to [get_clocks core_clk]
  set_min_delay -ignore_clock_latency 0 -from [get_clocks core_clk] -to [get_clocks $w]
  set_false_path -from [get_clocks vw] -to [get_clocks core_clk]
  set_false_path -from [get_clocks core_clk] -to [get_clocks vw]
  set_false_path -from [get_clocks $w] -to [get_clocks vclk]
  set_false_path -from [get_clocks vclk] -to [get_clocks $w]
  foreach w2 $ot_w { if {$w2 ne $w} { set_false_path -from [get_clocks $w] -to [get_clocks $w2] } }
}
set_false_path -from [get_clocks vw] -to [get_clocks vclk]
set_input_delay 166.667 -clock vw [get_ports {di*}]
set_input_delay -min 0 -clock vw [get_ports {di*}]
set_output_delay 316.667 -clock vclk [get_ports {o*}]
set_output_delay -min 0 -clock vclk [get_ports {o*}]
set_false_path -from [get_ports {rs*}]
set_max_fanout 32 [current_design]
