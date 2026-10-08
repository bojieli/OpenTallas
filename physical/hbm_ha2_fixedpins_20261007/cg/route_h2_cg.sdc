# drive-1443: make_sdc.py --period-ps 730 --l-max 813.67 --l-min 650.22 --l-ff-min 519.71 --half --h1 (TT / FF insertion measured on the ha2_h2_fixedpins_ca0d6a5a2-tt route: the route corner is TC, hold repair at BC/FF)
# HA2 banked: period 730.0 ps, L SS 650.22..813.67, FF min 519.71
create_clock -name clk -period 730.000 [get_ports clk]
set_clock_uncertainty -setup 60 [all_clocks]
set_clock_uncertainty -hold 25 [all_clocks]
set ins [delete_from_list [all_inputs] [get_ports clk]]
set_driving_cell -lib_cell BUFx4_ASAP7_75t_R -pin Y $ins
set_input_delay -max 1160.337 -clock clk $ins
set_input_delay -min 549.710 -clock clk $ins
set_output_delay -max -378.553 -clock clk [all_outputs]
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
if {![llength $ot_g]} {error "expected at least one ICG AND output"}
# cg_pushdown (PRE_CTS) clones the gate per sink cluster: gclk is generated at every clone output
create_generated_clock -name gclk -source [get_ports clk] -divide_by 2 $ot_g
# the gclk edge comes from the AND's clock input; en_l changes only while clk is low: no clock through en_l
set ot_q {}
foreach p [get_pins -hierarchical *] { if {[regexp {u_icg.*en_l.*/QN?$} [get_full_name $p]]} {lappend ot_q $p} }
if {[llength $ot_q] && [catch {set_sense -type clock -stop_propagation -clocks [get_clocks clk] $ot_q} ot_e]} {puts "set_sense: $ot_e"}
set_clock_uncertainty -setup 60 [get_clocks gclk]
set_clock_uncertainty -hold 25 [get_clocks gclk]
