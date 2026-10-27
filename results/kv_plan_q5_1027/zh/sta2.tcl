set P /OpenROAD-flow-scripts/flow/platforms/asap7
set c $::env(CORNER)
set lo [string tolower $c]
read_liberty [glob $P/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_*.lib*]
read_liberty /work/ot_nhb_zh_${lo}.lib
read_verilog /work/c2/pair_BUFx12f.v
link_design pair_BUFx12f
read_spef /work/c2/pair_BUFx12f.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 pair_BUFx12f u0 $c"
report_checks -unconstrained -to [get_pins u0/clk] -digits 2 -fields {slew cap}
puts "ROW2 pair_BUFx12f u1 $c"
report_checks -unconstrained -to [get_pins u1/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/pair_BUFx24_.v
link_design pair_BUFx24_
read_spef /work/c2/pair_BUFx24_.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 pair_BUFx24_ u0 $c"
report_checks -unconstrained -to [get_pins u0/clk] -digits 2 -fields {slew cap}
puts "ROW2 pair_BUFx24_ u1 $c"
report_checks -unconstrained -to [get_pins u1/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh1_2.v
link_design m7_zh1_2
read_spef /work/c2/m7_zh1_2.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh1_2 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh1_3.v
link_design m7_zh1_3
read_spef /work/c2/m7_zh1_3.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh1_3 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh1_4.v
link_design m7_zh1_4
read_spef /work/c2/m7_zh1_4.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh1_4 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh0_2.v
link_design m7_zh0_2
read_spef /work/c2/m7_zh0_2.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh0_2 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh0_3.v
link_design m7_zh0_3
read_spef /work/c2/m7_zh0_3.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh0_3 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/c2/m7_zh0_4.v
link_design m7_zh0_4
read_spef /work/c2/m7_zh0_4.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW2 m7_zh0_4 u $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
