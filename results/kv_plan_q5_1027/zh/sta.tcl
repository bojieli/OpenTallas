set P /OpenROAD-flow-scripts/flow/platforms/asap7
set c $::env(CORNER)
set lo [string tolower $c]
read_liberty [glob $P/lib/NLDM/asap7sc7p5t_INVBUF_RVT_${c}_nldm_*.lib*]
read_liberty /work/ot_nhb_zh_${lo}.lib
read_liberty /work/ot_qkh_recip_leaf_${lo}.lib
read_verilog /work/cases/m0.v
link_design m0
read_spef /work/cases/m0.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 0 273.62 zh1 BUFx12f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m1.v
link_design m1
read_spef /work/cases/m1.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 1 273.62 zh1 BUFx12f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m2.v
link_design m2
read_spef /work/cases/m2.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 2 273.62 zh1 BUFx12f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m3.v
link_design m3
read_spef /work/cases/m3.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 3 273.62 zh1 BUFx12f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m4.v
link_design m4
read_spef /work/cases/m4.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 4 273.62 zh1 BUFx16f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m5.v
link_design m5
read_spef /work/cases/m5.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 5 273.62 zh1 BUFx16f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m6.v
link_design m6
read_spef /work/cases/m6.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 6 273.62 zh1 BUFx16f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m7.v
link_design m7
read_spef /work/cases/m7.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 7 273.62 zh1 BUFx16f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m8.v
link_design m8
read_spef /work/cases/m8.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 8 273.62 zh1 BUFx24_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m9.v
link_design m9
read_spef /work/cases/m9.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 9 273.62 zh1 BUFx24_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m10.v
link_design m10
read_spef /work/cases/m10.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 10 273.62 zh1 BUFx24_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m11.v
link_design m11
read_spef /work/cases/m11.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 11 273.62 zh1 BUFx24_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m12.v
link_design m12
read_spef /work/cases/m12.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 12 295.3 zh0 BUFx12f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m13.v
link_design m13
read_spef /work/cases/m13.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 13 295.3 zh0 BUFx12f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m14.v
link_design m14
read_spef /work/cases/m14.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 14 295.3 zh0 BUFx12f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m15.v
link_design m15
read_spef /work/cases/m15.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 15 295.3 zh0 BUFx12f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m16.v
link_design m16
read_spef /work/cases/m16.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 16 295.3 zh0 BUFx16f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m17.v
link_design m17
read_spef /work/cases/m17.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 17 295.3 zh0 BUFx16f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m18.v
link_design m18
read_spef /work/cases/m18.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 18 295.3 zh0 BUFx16f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m19.v
link_design m19
read_spef /work/cases/m19.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 19 295.3 zh0 BUFx16f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m20.v
link_design m20
read_spef /work/cases/m20.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 20 295.3 zh0 BUFx24_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m21.v
link_design m21
read_spef /work/cases/m21.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 21 295.3 zh0 BUFx24_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m22.v
link_design m22
read_spef /work/cases/m22.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 22 295.3 zh0 BUFx24_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m23.v
link_design m23
read_spef /work/cases/m23.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 23 295.3 zh0 BUFx24_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m24.v
link_design m24
read_spef /work/cases/m24.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 24 75.08 recip BUFx12f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m25.v
link_design m25
read_spef /work/cases/m25.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 25 75.08 recip BUFx12f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m26.v
link_design m26
read_spef /work/cases/m26.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 26 75.08 recip BUFx12f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m27.v
link_design m27
read_spef /work/cases/m27.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 27 75.08 recip BUFx12f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m28.v
link_design m28
read_spef /work/cases/m28.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 28 75.08 recip BUFx16f_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m29.v
link_design m29
read_spef /work/cases/m29.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 29 75.08 recip BUFx16f_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m30.v
link_design m30
read_spef /work/cases/m30.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 30 75.08 recip BUFx16f_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m31.v
link_design m31
read_spef /work/cases/m31.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 31 75.08 recip BUFx16f_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m32.v
link_design m32
read_spef /work/cases/m32.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 32 75.08 recip BUFx24_ASAP7_75t_R 1 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m33.v
link_design m33
read_spef /work/cases/m33.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 33 75.08 recip BUFx24_ASAP7_75t_R 2 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m34.v
link_design m34
read_spef /work/cases/m34.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 34 75.08 recip BUFx24_ASAP7_75t_R 3 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
read_verilog /work/cases/m35.v
link_design m35
read_spef /work/cases/m35.spef
set_input_transition 20 [get_ports ck]
set_input_delay 0 [get_ports ck]
puts "ROW 35 75.08 recip BUFx24_ASAP7_75t_R 4 $c"
report_checks -unconstrained -to [get_pins u/clk] -digits 2 -fields {slew cap}
