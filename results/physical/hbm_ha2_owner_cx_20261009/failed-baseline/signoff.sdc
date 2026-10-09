# HA2 banked: period 833.333 ps, L SS 869.84..1073.58, FF min 519.71
create_clock -name clk -period 833.333 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports clk]]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins
set_input_delay -max 1523.580 -clock clk $ins
set_input_delay -min 499.710 -clock clk $ins
set_output_delay -max -494.840 -clock clk [all_outputs]
set_output_delay -min -469.710 -clock clk [all_outputs]
set_load 4.0 [all_outputs]
set_false_path -from [get_ports rst_n]
set_max_fanout 32 [current_design]

# half-rate core clock: the ICG AND output is a divide-by-2 generated clock of clk
set ot_g {}
foreach p [get_pins -hierarchical *] {
 set n [get_full_name $p]
 if {[regexp {u_icg.*/Y$} $n]} {
  set c [get_cells -of_objects $p]
  if {[regexp {AND} [get_property $c ref_name]]} {lappend ot_g $p}
 }
}
if {[llength $ot_g]!=1} {error "expected one ICG AND output, found [llength $ot_g]"}
create_generated_clock -name gclk -source [get_ports clk] -divide_by 2 [lindex $ot_g 0]
