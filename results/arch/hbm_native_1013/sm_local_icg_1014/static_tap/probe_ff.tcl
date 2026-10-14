set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_liberty /probe/SEQ/asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib
read_lef /probe/ot_smh_own_eg/ot_smh_own_eg.lef
read_liberty /probe/ot_smh_own_eg/ot_smh_own_eg_ff.lib
read_lef /probe/ot_hbm_accel_smh_bdc/ot_hbm_accel_smh_bdc.lef
read_liberty /probe/ot_hbm_accel_smh_bdc/ot_hbm_accel_smh_bdc_ff.lib
read_lef /probe/ot_hbm_accel_smh_tcl/ot_hbm_accel_smh_tcl.lef
read_liberty /probe/ot_hbm_accel_smh_tcl/ot_hbm_accel_smh_tcl_ff.lib
read_lef /probe/ot_hbm_accel_smh_tct/ot_hbm_accel_smh_tct.lef
read_liberty /probe/ot_hbm_accel_smh_tct/ot_hbm_accel_smh_tct_ff.lib
read_lef /probe/ot_hbm_accel_smh_xs/ot_hbm_accel_smh_xs.lef
read_liberty /probe/ot_hbm_accel_smh_xs/ot_hbm_accel_smh_xs_ff.lib
read_lef /probe/ot_hbm_accel_smh_pt_e/ot_hbm_accel_smh_pt_e.lef
read_liberty /probe/ot_hbm_accel_smh_pt_e/ot_hbm_accel_smh_pt_e_ff.lib
read_lef /probe/ot_hbm_accel_smh_pt_w/ot_hbm_accel_smh_pt_w.lef
read_liberty /probe/ot_hbm_accel_smh_pt_w/ot_hbm_accel_smh_pt_w_ff.lib
read_liberty /probe/INVBUF_ff.lib
read_verilog /probe/gating.v
link_design gating
create_clock -name OWN_RAW -period 833.333 -waveform {0 416.6665} [get_ports clk]
create_clock -name OWN_AUX -period 833.333 [get_ports clk_aux]
set_clock_latency -source -34.900000000000006 [get_clocks OWN_AUX]
create_clock -name RAW_0 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_0]
create_generated_clock -name G_0 -master_clock RAW_0 -source [get_ports clk_child_0] -divide_by 1 [get_pins gate_0/GCLK]
create_clock -name RAW_1 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_1]
create_generated_clock -name G_1 -master_clock RAW_1 -source [get_ports clk_child_1] -divide_by 1 [get_pins gate_1/GCLK]
create_clock -name RAW_2 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_2]
create_generated_clock -name G_2 -master_clock RAW_2 -source [get_ports clk_child_2] -divide_by 1 [get_pins gate_2/GCLK]
create_clock -name RAW_3 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_3]
create_generated_clock -name G_3 -master_clock RAW_3 -source [get_ports clk_child_3] -divide_by 1 [get_pins gate_3/GCLK]
create_clock -name RAW_4 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_4]
create_generated_clock -name G_4 -master_clock RAW_4 -source [get_ports clk_child_4] -divide_by 1 [get_pins gate_4/GCLK]
create_clock -name RAW_5 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_5]
create_generated_clock -name G_5 -master_clock RAW_5 -source [get_ports clk_child_5] -divide_by 1 [get_pins gate_5/GCLK]
create_clock -name RAW_6 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_6]
create_generated_clock -name G_6 -master_clock RAW_6 -source [get_ports clk_child_6] -divide_by 1 [get_pins gate_6/GCLK]
create_clock -name RAW_7 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_7]
create_generated_clock -name G_7 -master_clock RAW_7 -source [get_ports clk_child_7] -divide_by 1 [get_pins gate_7/GCLK]
create_clock -name RAW_8 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_8]
create_generated_clock -name G_8 -master_clock RAW_8 -source [get_ports clk_child_8] -divide_by 1 [get_pins gate_8/GCLK]
create_clock -name RAW_9 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_9]
create_generated_clock -name G_9 -master_clock RAW_9 -source [get_ports clk_child_9] -divide_by 1 [get_pins gate_9/GCLK]
create_clock -name RAW_10 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_10]
create_generated_clock -name G_10 -master_clock RAW_10 -source [get_ports clk_child_10] -divide_by 1 [get_pins gate_10/GCLK]
create_clock -name RAW_11 -period 833.333 -waveform {0 416.6665} [get_ports clk_child_11]
create_generated_clock -name G_11 -master_clock RAW_11 -source [get_ports clk_child_11] -divide_by 1 [get_pins gate_11/GCLK]
set_input_transition 0 [all_inputs]
set_clock_transition 0 [get_clocks OWN_RAW]
# No generated GCLK slew override. Its real ICG output slew stays observable.
set_propagated_clock [all_clocks]
set_clock_uncertainty -setup 150 [all_clocks]
set_clock_uncertainty -hold 100 [all_clocks]
proc check_paths {tag} {
 set result [dict create]
 for {set i 0} {$i<12} {incr i} {
  foreach edge {rise fall} {
   foreach kind {max min} {
    set launch_pin [expr {$i in {4 9 10 11} ? "mirror/QN" : "mirror_aux/QN"}]
    set cmd [list find_timing_paths -from [get_pins $launch_pin] -${edge}_to [get_pins gate_$i/ENA] -path_delay $kind -group_path_count 1]
    set paths [{*}$cmd]
    if {[llength $paths]!=1} {error "missing actual ENA $i $edge $kind check"}
    set path [lindex $paths 0]
    set sc [get_property [get_property $path startpoint_clock] full_name]
    set ec [get_property [get_property $path endpoint_clock] full_name]
    set expected_clock [expr {$i in {4 9 10 11} ? "OWN_RAW" : "OWN_AUX"}]
    if {$sc ne $expected_clock || $ec ne "RAW_$i"} {error "wrong actual gating clock association $i $sc $ec"}
    set slack [get_property $path slack]
    dict set result $i $edge $kind $slack
    puts "SM_GATE_PATH $tag $i $edge $kind slack=$slack launch=$sc capture=$ec"
   }
  }
 }
 return $result
}
set_clock_latency -source -116.9 [get_clocks OWN_RAW]
set baseline [check_paths ff_before_entry_comp]
set ownarr [get_property [get_pins own/cut_2] arrival_max_rise]
if {abs($ownarr+116.9)>0.01} {error "OWN raw phase mismatch"}
source /probe/TT_levels.tcl
set rise [get_property [get_pins child_0/clk] arrival_max_rise]
set fall [get_property [get_pins child_0/clk] arrival_max_fall]
set slew [get_property [get_pins gate_0/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 0 actual_parent=u.u.g_lf[0].u_lh.u_bdc child=ot_hbm_accel_smh_bdc childR=148.0 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-148.0-$rise}] [get_clocks RAW_0]
set sm_gate_delta(0) [expr {148.0+$rise}]
set phi [expr {[get_property [get_pins child_0/clk] arrival_max_rise]+148.0}]
if {abs($phi)>0.02} {error "child phase mismatch 0"}
puts "SM_GATE_PHI ff 0 phi=$phi"
set u $sm_gate_U(0)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_0]
set current_U(0) $u
set rise [get_property [get_pins child_1/clk] arrival_max_rise]
set fall [get_property [get_pins child_1/clk] arrival_max_fall]
set slew [get_property [get_pins gate_1/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 1 actual_parent=u.u.g_lf[0].u_lh.u_tcc.u_h0 child=ot_hbm_accel_smh_tcl childR=139.6 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-139.6-$rise}] [get_clocks RAW_1]
set sm_gate_delta(1) [expr {139.6+$rise}]
set phi [expr {[get_property [get_pins child_1/clk] arrival_max_rise]+139.6}]
if {abs($phi)>0.02} {error "child phase mismatch 1"}
puts "SM_GATE_PHI ff 1 phi=$phi"
set u $sm_gate_U(1)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_1]
set current_U(1) $u
set rise [get_property [get_pins child_2/clk] arrival_max_rise]
set fall [get_property [get_pins child_2/clk] arrival_max_fall]
set slew [get_property [get_pins gate_2/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 2 actual_parent=u.u.g_lf[0].u_lh.u_tcc.u_h1 child=ot_hbm_accel_smh_tcl childR=139.6 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-139.6-$rise}] [get_clocks RAW_2]
set sm_gate_delta(2) [expr {139.6+$rise}]
set phi [expr {[get_property [get_pins child_2/clk] arrival_max_rise]+139.6}]
if {abs($phi)>0.02} {error "child phase mismatch 2"}
puts "SM_GATE_PHI ff 2 phi=$phi"
set u $sm_gate_U(2)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_2]
set current_U(2) $u
set rise [get_property [get_pins child_3/clk] arrival_max_rise]
set fall [get_property [get_pins child_3/clk] arrival_max_fall]
set slew [get_property [get_pins gate_3/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 3 actual_parent=u.u.g_lf[0].u_lh.u_tcc.u_tr child=ot_hbm_accel_smh_tct childR=143.1 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-143.1-$rise}] [get_clocks RAW_3]
set sm_gate_delta(3) [expr {143.1+$rise}]
set phi [expr {[get_property [get_pins child_3/clk] arrival_max_rise]+143.1}]
if {abs($phi)>0.02} {error "child phase mismatch 3"}
puts "SM_GATE_PHI ff 3 phi=$phi"
set u $sm_gate_U(3)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_3]
set current_U(3) $u
set rise [get_property [get_pins child_4/clk] arrival_max_rise]
set fall [get_property [get_pins child_4/clk] arrival_max_fall]
set slew [get_property [get_pins gate_4/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 4 actual_parent=u.u.g_lf[0].u_lh.u_xs child=ot_hbm_accel_smh_xs childR=261.4 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-261.4-$rise}] [get_clocks RAW_4]
set sm_gate_delta(4) [expr {261.4+$rise}]
set phi [expr {[get_property [get_pins child_4/clk] arrival_max_rise]+261.4}]
if {abs($phi)>0.02} {error "child phase mismatch 4"}
puts "SM_GATE_PHI ff 4 phi=$phi"
set u $sm_gate_U(4)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_4]
set current_U(4) $u
set rise [get_property [get_pins child_5/clk] arrival_max_rise]
set fall [get_property [get_pins child_5/clk] arrival_max_fall]
set slew [get_property [get_pins gate_5/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 5 actual_parent=u.u.g_lf[1].u_lh.u_bdc child=ot_hbm_accel_smh_bdc childR=148.0 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-148.0-$rise}] [get_clocks RAW_5]
set sm_gate_delta(5) [expr {148.0+$rise}]
set phi [expr {[get_property [get_pins child_5/clk] arrival_max_rise]+148.0}]
if {abs($phi)>0.02} {error "child phase mismatch 5"}
puts "SM_GATE_PHI ff 5 phi=$phi"
set u $sm_gate_U(5)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_5]
set current_U(5) $u
set rise [get_property [get_pins child_6/clk] arrival_max_rise]
set fall [get_property [get_pins child_6/clk] arrival_max_fall]
set slew [get_property [get_pins gate_6/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 6 actual_parent=u.u.g_lf[1].u_lh.u_tcc.u_h0 child=ot_hbm_accel_smh_tcl childR=139.6 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-139.6-$rise}] [get_clocks RAW_6]
set sm_gate_delta(6) [expr {139.6+$rise}]
set phi [expr {[get_property [get_pins child_6/clk] arrival_max_rise]+139.6}]
if {abs($phi)>0.02} {error "child phase mismatch 6"}
puts "SM_GATE_PHI ff 6 phi=$phi"
set u $sm_gate_U(6)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_6]
set current_U(6) $u
set rise [get_property [get_pins child_7/clk] arrival_max_rise]
set fall [get_property [get_pins child_7/clk] arrival_max_fall]
set slew [get_property [get_pins gate_7/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 7 actual_parent=u.u.g_lf[1].u_lh.u_tcc.u_h1 child=ot_hbm_accel_smh_tcl childR=139.6 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-139.6-$rise}] [get_clocks RAW_7]
set sm_gate_delta(7) [expr {139.6+$rise}]
set phi [expr {[get_property [get_pins child_7/clk] arrival_max_rise]+139.6}]
if {abs($phi)>0.02} {error "child phase mismatch 7"}
puts "SM_GATE_PHI ff 7 phi=$phi"
set u $sm_gate_U(7)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_7]
set current_U(7) $u
set rise [get_property [get_pins child_8/clk] arrival_max_rise]
set fall [get_property [get_pins child_8/clk] arrival_max_fall]
set slew [get_property [get_pins gate_8/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 8 actual_parent=u.u.g_lf[1].u_lh.u_tcc.u_tr child=ot_hbm_accel_smh_tct childR=143.1 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-143.1-$rise}] [get_clocks RAW_8]
set sm_gate_delta(8) [expr {143.1+$rise}]
set phi [expr {[get_property [get_pins child_8/clk] arrival_max_rise]+143.1}]
if {abs($phi)>0.02} {error "child phase mismatch 8"}
puts "SM_GATE_PHI ff 8 phi=$phi"
set u $sm_gate_U(8)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_8]
set current_U(8) $u
set rise [get_property [get_pins child_9/clk] arrival_max_rise]
set fall [get_property [get_pins child_9/clk] arrival_max_fall]
set slew [get_property [get_pins gate_9/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 9 actual_parent=u.u.g_lf[1].u_lh.u_xs child=ot_hbm_accel_smh_xs childR=261.4 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-261.4-$rise}] [get_clocks RAW_9]
set sm_gate_delta(9) [expr {261.4+$rise}]
set phi [expr {[get_property [get_pins child_9/clk] arrival_max_rise]+261.4}]
if {abs($phi)>0.02} {error "child phase mismatch 9"}
puts "SM_GATE_PHI ff 9 phi=$phi"
set u $sm_gate_U(9)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_9]
set current_U(9) $u
set rise [get_property [get_pins child_10/clk] arrival_max_rise]
set fall [get_property [get_pins child_10/clk] arrival_max_fall]
set slew [get_property [get_pins gate_10/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 10 actual_parent=u.u.u_pte child=ot_hbm_accel_smh_pt_e childR=281.0 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-281.0-$rise}] [get_clocks RAW_10]
set sm_gate_delta(10) [expr {281.0+$rise}]
set phi [expr {[get_property [get_pins child_10/clk] arrival_max_rise]+281.0}]
if {abs($phi)>0.02} {error "child phase mismatch 10"}
puts "SM_GATE_PHI ff 10 phi=$phi"
set u $sm_gate_U(10)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_10]
set current_U(10) $u
set rise [get_property [get_pins child_11/clk] arrival_max_rise]
set fall [get_property [get_pins child_11/clk] arrival_max_fall]
set slew [get_property [get_pins gate_11/GCLK] slew_max_rise]
puts "SM_GATE_CAL ff 11 actual_parent=u.u.u_ptw child=ot_hbm_accel_smh_pt_w childR=350.8 gate_rise=$rise gate_fall=[expr {$fall-416.6665}] GCLK_slew=$slew"
set_clock_latency -source [expr {-350.8-$rise}] [get_clocks RAW_11]
set sm_gate_delta(11) [expr {350.8+$rise}]
set phi [expr {[get_property [get_pins child_11/clk] arrival_max_rise]+350.8}]
if {abs($phi)>0.02} {error "child phase mismatch 11"}
puts "SM_GATE_PHI ff 11 phi=$phi"
set u $sm_gate_U(11)
set_clock_uncertainty -setup $u -from [get_clocks OWN_RAW] -to [get_clocks RAW_11]
set current_U(11) $u
for {set i 0} {$i<12} {incr i} {set_clock_uncertainty -setup $current_U($i) -from [get_clocks OWN_AUX] -to [get_clocks RAW_$i]}
set after [check_paths ff]
for {set i 0} {$i<12} {incr i} {
 foreach edge {rise fall} {
  foreach kind {max min} {
   set before [dict get $baseline $i $edge $kind]
   set now [dict get $after $i $edge $kind]
   set expected [expr {$before+($kind eq "max" ? -$sm_gate_delta($i)-($current_U($i)-150) : $sm_gate_delta($i))}]
   if {abs($now-$expected)>0.04} {error "gating phase/budget accounting mismatch $i $edge $kind"}
   puts "SM_GATE_ACCOUNT ff $i $edge $kind actual=$now expected=$expected"
  }
 }
}
report_checks -from [get_pins mirror/QN] -path_delay max -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 12 -digits 6
report_checks -from [get_pins mirror/QN] -path_delay min -format full_clock_expanded -fields {slew cap input fanout} -group_path_count 12 -digits 6
report_check_types -min_pulse_width -verbose
report_check_types -max_capacitance -verbose
report_arrival -digits 6 [get_pins mirror/QN]
report_slews -digits 6 [get_pins mirror/QN]
report_clock_properties [all_clocks]
write_sdc /probe/executed_ff.sdc
puts "SM_GATING_PASS ff REQUESTED_EARLY_TAP_20PS_IDEAL_WIRES_NO_D_SETUP_PHYSICAL_QUALIFICATION"
exit
